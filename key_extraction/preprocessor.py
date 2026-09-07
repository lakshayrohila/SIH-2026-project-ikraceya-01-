import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional

class ImagePreprocessor:
    """OpenCV preprocessing pipeline for enhancing product packaging OCR accuracy."""

    @staticmethod
    def read_image(image_input) -> np.ndarray:
        """Reads image from filepath, bytes, or numpy array."""
        if isinstance(image_input, str):
            img = cv2.imread(image_input)
            if img is None:
                raise ValueError(f"Could not read image from path: {image_input}")
            return img
        elif isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image from bytes.")
            return img
        elif isinstance(image_input, np.ndarray):
            return image_input.copy()
        else:
            raise TypeError("Unsupported image input type.")

    @staticmethod
    def crop_to_content(img: np.ndarray, padding: int = 10, bg_color: str = "white") -> np.ndarray:
        """Crops the image to its non-background content box with optional padding."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img.copy()

        # Threshold non-background pixels
        if bg_color == "white":
            # Keeps darker content on lighter backgrounds (< 240 gray level)
            _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        else:
            # Keeps lighter content on darker backgrounds (> 15 gray level)
            _, thresh = cv2.threshold(gray, 15, 255, cv2.THRESH_BINARY)

        points = cv2.findNonZero(thresh)
        if points is None:
            return img  # Return original if image is completely solid/empty

        x, y, w, h = cv2.boundingRect(points)

        # Apply safety padding within image boundaries
        h_img, w_img = img.shape[:2]
        x1, y1 = max(0, x - padding), max(0, y - padding)
        x2, y2 = min(w_img, x + w + padding), min(h_img, y + h + padding)

        return img[y1:y2, x1:x2]

    @staticmethod
    def resize_max_dimension(img: np.ndarray, max_dim: int = 1600, padding: int = 10) -> np.ndarray:
        """Crops to non-background content, then resizes keeping aspect ratio if larger than max_dim."""
        # 1. Crop to content first
        cropped_img = ImagePreprocessor.crop_to_content(img, padding=padding)

        # 2. Resize maintaining aspect ratio
        h, w = cropped_img.shape[:2]
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w, new_h = int(w * scale), int(h * scale)
            return cv2.resize(cropped_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return cropped_img

    @staticmethod
    def apply_clahe(img: np.ndarray, clip_limit: float = 2.0, tile_grid: Tuple[int, int] = (8, 8)) -> np.ndarray:
        """Applies Contrast Limited Adaptive Histogram Equalization in LAB color space."""
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid)
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

    @staticmethod
    def deskew(img: np.ndarray) -> np.ndarray:
        """Detects text angle using Canny edges & minAreaRect, rotates image if skew < 30 degrees."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

        # Dilate to connect text lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(thresh, kernel, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        angles = []
        for c in contours:
            area = cv2.contourArea(c)
            if area > 500:
                rect = cv2.minAreaRect(c)
                angle = rect[-1]
                if angle < -45:
                    angle = -(90 + angle)
                else:
                    angle = -angle
                if abs(angle) < 30:
                    angles.append(angle)

        if not angles:
            return img

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return img

        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    @staticmethod
    def sharpen(img: np.ndarray) -> np.ndarray:
        """Sharpens image using a 3x3 kernel."""
        kernel = np.array([[0, -1, 0],
                           [-1, 5, -1],
                           [0, -1, 0]], dtype=np.float32)
        return cv2.filter2D(img, -1, kernel)

    @staticmethod
    def denoise_bilateral(img: np.ndarray, d: int = 7, sigma_color: int = 50, sigma_space: int = 50) -> np.ndarray:
        """Applies edge-preserving bilateral filtering."""
        return cv2.bilateralFilter(img, d, sigma_color, sigma_space)

    @staticmethod
    def binarize_adaptive(img: np.ndarray) -> np.ndarray:
        """Converts image to high contrast black and white using adaptive thresholding."""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )
        return cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

    def process(self, image_input, preset: str = "standard") -> Tuple[np.ndarray, Dict[str, Any]]:
        """Processes image according to preset pipeline."""
        img = self.read_image(image_input)
        img = self.resize_max_dimension(img, max_dim=1600)
        meta = {"preset": preset, "original_shape": img.shape}

        if preset == "raw":
            return img, meta

        # Deskew first
        img = self.deskew(img)

        if preset == "standard":
            img = self.apply_clahe(img, clip_limit=2.0)
            img = self.sharpen(img)
        elif preset == "glare_reduction":
            img = self.denoise_bilateral(img, d=9, sigma_color=75, sigma_space=75)
            img = self.apply_clahe(img, clip_limit=3.0)
            img = self.sharpen(img)
        elif preset == "low_light":
            # Gamma correction for low-light boost
            gamma = 1.4
            invGamma = 1.0 / gamma
            table = np.array([((i / 255.0) ** invGamma) * 255 for i in np.arange(0, 256)]).astype("uint8")
            img = cv2.LUT(img, table)
            img = self.apply_clahe(img, clip_limit=2.5)
            img = self.sharpen(img)
        elif preset == "binarized":
            img = self.apply_clahe(img, clip_limit=2.0)
            img = self.binarize_adaptive(img)

        meta["final_shape"] = img.shape
        return img, meta
