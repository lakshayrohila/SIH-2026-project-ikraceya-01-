import numpy as np
from typing import Tuple, List, Optional, Any
from paddleocr import PaddleOCR
from dataclasses import dataclass
from numpy.typing import NDArray

from config import OCRConfig, default_config

@dataclass
class OCRResult:
    texts: NDArray[np.str_]
    scores: NDArray[np.float32]
    boxes: NDArray[np.int32]
    angles: NDArray[np.float32]
    orientations: NDArray[np.str_]

    def __str__(self) -> str:
        num_items = len(self.texts)
        if num_items == 0:
            return "<OCRResult: 0 items detected>"

        avg_score = float(np.mean(self.scores)) if num_items > 0 else 0.0

        # Build header summary
        lines = [
            f"=== OCRResult Summary ===",
            f"Total Detections : {num_items}",
            f"Avg Confidence   : {avg_score:.2%}",
            f"Box Shape        : {self.boxes.shape}",
            f"--------------------------",
            "Detected Text Sample:"
        ]

        # Preview up to top 5 detected texts with confidence and bounding box
        max_preview = num_items+1
        for i in range(min(num_items, max_preview)):
            text = self.texts[i]
            score = self.scores[i]
            # Truncate text if it's too long
            display_text = f"'{text[:30]}...'" if len(text) > 30 else f"'{text}'"
            lines.append(f"  [{i+1}] {display_text:<35} | Conf: {score:.2f} | Orient: {self.orientations[i]}")

        lines.append("==========================")
        return "\n".join(lines)

class HelperFuncs:
    @staticmethod
    def compute_angles_and_orientations(boxes_4pt: np.ndarray) -> tuple[NDArray[np.float32], NDArray[np.str_]]:
        """
        Computes reading angle and orientation category from 4-point polygon boxes.
        Point 0 -> Point 1 defines the text baseline vector.
        """
        if len(boxes_4pt) == 0:
            return np.array([], dtype=np.float32), np.array([], dtype=str)

        # 4-point boxes shape: (N, 4, 2)
        if boxes_4pt.ndim == 2 and boxes_4pt.shape[1] == 4:
            # Convert [x1, y1, x2, y2] to 4-point rect if required
            x1, y1, x2, y2 = boxes_4pt[:, 0], boxes_4pt[:, 1], boxes_4pt[:, 2], boxes_4pt[:, 3]
            dx = x2 - x1
            dy = y2 - y1
        else:
            # Vector from top-left (pt 0) to top-right (pt 1)
            dx = boxes_4pt[:, 1, 0] - boxes_4pt[:, 0, 0]
            dy = boxes_4pt[:, 1, 1] - boxes_4pt[:, 0, 1]

        # Angle in degrees (-180 to 180)
        angles = np.degrees(np.arctan2(dy, dx)).astype(np.float32)

        orientations = []
        for angle in angles:
            # Normalize angle to [0, 360)
            norm_angle = angle % 360

            if 45 <= norm_angle < 135:
                orientations.append("vertical_down")  # 90° clockwise
            elif 135 <= norm_angle < 225:
                orientations.append("upside_down")     # 180° inverted
            elif 225 <= norm_angle < 315:
                orientations.append("vertical_up")    # 270° counter-clockwise
            else:
                orientations.append("horizontal")     # ~0° standard

        return angles, np.array(orientations, dtype=str)

class OCREngine(HelperFuncs):
    """Wrapper around PaddleOCR for package declaration text detection & recognition."""

    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or default_config.ocr
        self._engine: Optional[PaddleOCR] = None

    @property
    def engine(self) -> PaddleOCR:
        if self._engine is None:
            conf = self.config

            self._engine = PaddleOCR(
                use_angle_cls = conf.use_angle_cls,
                lang = conf.lang,
                enable_mkldnn = conf.enable_mkldnn,
                cpu_threads = conf.cpu_threads,
                text_detection_model_name = conf.text_detection_model_name,
                text_recognition_model_name = conf.text_recognition_model_name,
                device = conf.device
            )
        return self._engine

    def predict(self, image_path: str) -> OCRResult:
        """Performs text detection and recognition on image array."""

        prediction = self.engine.predict(image_path)

        empty_result = OCRResult(
                        texts=np.array([], dtype=str),
                        scores=np.array([], dtype=np.float32),
                        boxes=np.empty((0, 4), dtype=np.int32),
                        angles=np.array([], dtype=np.float32),
                        orientations=np.array([], dtype=str)
                    )

        for res in prediction:
            buff = [
                (text, score, box) for text, score, box
                in zip(res["rec_texts"], res["rec_scores"], res["rec_boxes"])
                if score >= self.config.min_confidence
            ]

            if not buff:
                # Prevent indexing errors on empty OCR results
                return empty_result

            texts, scores, boxes = zip(*buff)

            ocr_boxes = np.array(boxes)
            angles, orientations = self.compute_angles_and_orientations(ocr_boxes)

            return OCRResult(
                texts=np.array(texts, dtype=str),
                scores=np.array(scores, dtype=np.float32),
                boxes=ocr_boxes,
                angles=angles,
                orientations=orientations
            )

        return empty_result
