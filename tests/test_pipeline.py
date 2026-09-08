"""
tests/test_pipeline.py — unit tests for the extraction pipeline components.

Run with: pytest tests/test_pipeline.py -v

Deliberately does NOT test ocr_engine.py directly, since that requires the
full PaddleOCR model to be downloaded and loaded (slow, and not meaningful
without a real label photo). Test that manually via the Streamlit app
instead — drop a photo into tests/sample_images/ and run a scan.

field_parser.py's parse_country_of_origin() also isn't tested here since it
needs the spaCy model loaded — same reasoning as OCR above.
"""

import numpy as np
from PIL import Image

from app.pipeline.preprocess import preprocess_image, pil_to_cv2, to_grayscale
from app.pipeline.field_matcher import match_fields
from app.pipeline.field_parser import parse_mrp, parse_net_quantity, parse_fssai_license, parse_consumer_care
from app.pipeline.normalizer import normalize_date, normalize_quantity


# --- preprocess.py ---

def test_preprocess_returns_2d_array():
    # A plain white image is enough to check the pipeline runs without
    # crashing and returns a single-channel (grayscale/binary) array.
    blank_image = Image.new("RGB", (200, 100), color="white")
    result = preprocess_image(blank_image)

    assert isinstance(result, np.ndarray)
    assert result.ndim == 2  # grayscale/binary, not RGB


def test_pil_to_cv2_shape():
    image = Image.new("RGB", (50, 30), color="red")
    cv2_image = pil_to_cv2(image)

    assert cv2_image.shape == (30, 50, 3)


def test_to_grayscale_reduces_channels():
    image = Image.new("RGB", (50, 30), color="blue")
    cv2_image = pil_to_cv2(image)
    gray = to_grayscale(cv2_image)

    assert gray.ndim == 2


# --- field_matcher.py ---

def test_match_fields_finds_mrp_line():
    ocr_lines = [
        {"text": "MRP Rs 199 inclusive of all taxes", "confidence": 0.95, "bbox": []},
        {"text": "Net Wt 500g", "confidence": 0.92, "bbox": []},
    ]
    matches = match_fields(ocr_lines)

    assert matches["mrp"] is not None
    assert "199" in matches["mrp"]["line"]


def test_match_fields_returns_none_when_no_match():
    ocr_lines = [{"text": "Some unrelated text about flavor", "confidence": 0.9, "bbox": []}]
    matches = match_fields(ocr_lines)

    assert matches["fssai_license"] is None


# --- field_parser.py ---

def test_parse_mrp_extracts_number():
    assert parse_mrp("MRP Rs. 199.00 inclusive of all taxes") == "199.00"


def test_parse_mrp_handles_rupee_symbol():
    assert parse_mrp("MRP ₹150 incl. of all taxes") == "150"


def test_parse_net_quantity_extracts_value_and_unit():
    assert parse_net_quantity("Net Wt 500 g") == "500 g"


def test_parse_net_quantity_returns_none_when_absent():
    assert parse_net_quantity("No quantity here") is None


def test_parse_fssai_license_extracts_14_digits():
    assert parse_fssai_license("FSSAI Lic No 12345678901234") == "12345678901234"


def test_parse_fssai_license_rejects_wrong_length():
    assert parse_fssai_license("FSSAI Lic No 12345") is None


def test_parse_consumer_care_extracts_phone_and_email():
    result = parse_consumer_care("Consumer Care: 1800123456, care@example.com")
    assert result["phone"] is not None
    assert result["email"] == "care@example.com"


# --- normalizer.py ---

def test_normalize_date_parses_common_format():
    result = normalize_date("15/01/2026")
    assert result is not None
    assert result.year == 2026


def test_normalize_date_handles_none():
    assert normalize_date(None) is None


def test_normalize_quantity_parses_grams():
    result = normalize_quantity("500 g")
    assert result is not None
    assert result["value"] == 500.0


def test_normalize_quantity_handles_none():
    assert normalize_quantity(None) is None