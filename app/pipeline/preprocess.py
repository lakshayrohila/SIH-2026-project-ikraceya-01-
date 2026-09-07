"""
preprocess.py — OpenCV preprocessing pipeline for label photos.

Takes a PIL Image (from upload or camera) and returns a cleaned-up
numpy array ready for OCR: grayscale, contrast-enhanced, thresholded,
and deskewed.
"""

import cv2
import numpy as np
from PIL import Image


def pil_to_cv2(image: Image.Image) -> np.ndarray:
    """Convert a PIL Image (RGB) to an OpenCV array (BGR)."""
    rgb_array = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)


def to_grayscale(image_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def enhance_contrast(gray: np.ndarray) -> np.ndarray:
    """CLAHE (adaptive histogram equalization) — helps with uneven lighting
    and glare, which is extremely common on shiny plastic packaging."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)


def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """Binarize the image. Adaptive threshold handles uneven lighting
    across the label better than a single global threshold value."""
    return cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=31,
        C=15,
    )


def deskew(image: np.ndarray) -> np.ndarray:
    """Detect and correct small rotation angles so text lines are horizontal.
    Falls back to the original image if no clear angle is found (e.g. blank
    or very noisy image) rather than risking a bad rotation."""
    coords = np.column_stack(np.where(image > 0))
    if coords.shape[0] < 50:
        return image  # not enough foreground pixels to estimate an angle safely

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Ignore near-zero corrections and anything implausibly large (likely a
    # bad estimate rather than a real skew) to avoid making things worse.
    if abs(angle) < 0.5 or abs(angle) > 15:
        return image

    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image, rotation_matrix, (w, h),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
    )


def preprocess_image(image: Image.Image) -> np.ndarray:
    """
    Full pipeline: PIL Image -> deskewed, thresholded, contrast-enhanced
    grayscale numpy array, ready to hand to PaddleOCR.
    """
    bgr = pil_to_cv2(image)
    gray = to_grayscale(bgr)
    contrasted = enhance_contrast(gray)
    thresholded = adaptive_threshold(contrasted)
    straightened = deskew(thresholded)
    return straightened