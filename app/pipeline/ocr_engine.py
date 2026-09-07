"""
ocr_engine.py — PaddleOCR wrapper.

Loading the PaddleOCR model is slow (a few seconds, plus a one-time model
download), so we keep a single cached instance instead of recreating it
on every scan.
"""

import numpy as np
from paddleocr import PaddleOCR

_ocr_instance = None


def _get_ocr():
    """Lazily create and cache the PaddleOCR instance."""
    global _ocr_instance
    if _ocr_instance is None:
        # use_angle_cls helps with slightly rotated text that deskew() didn't
        # fully fix; lang='en' since Legal Metrology labels are English-only
        # for this project's scope.
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
    return _ocr_instance


def run_ocr(image_array: np.ndarray) -> list[dict]:
    """
    Run OCR on a preprocessed image (grayscale or binarized numpy array).

    Returns a list of dicts, one per detected text line:
        {"text": str, "confidence": float, "bbox": [[x,y], [x,y], [x,y], [x,y]]}
    """
    ocr = _get_ocr()
    raw_result = ocr.ocr(image_array, cls=True)

    lines = []
    if not raw_result or raw_result[0] is None:
        return lines

    for detection in raw_result[0]:
        bbox, (text, confidence) = detection
        lines.append({
            "text": text,
            "confidence": float(confidence),
            "bbox": bbox,
        })
    return lines


def get_full_text(ocr_lines: list[dict]) -> str:
    """Join all detected lines into one block of text for display/debugging."""
    return "\n".join(line["text"] for line in ocr_lines)