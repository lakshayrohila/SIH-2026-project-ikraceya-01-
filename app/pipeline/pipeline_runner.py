"""
pipeline_runner.py — orchestrates the full scan pipeline.

Called by pages/2_Scan.py as: run_pipeline(pil_image) -> result dict.

Depends on app.rules.rule_engine.evaluate_all(normalized_fields) — built in
the next batch. Until then, this still returns extracted text and parsed
fields, with overall_status = "PENDING_RULE_ENGINE" so the Results page
has something meaningful to show rather than crashing.
"""

from PIL import Image

from app.pipeline.preprocess import preprocess_image
from app.pipeline.ocr_engine import run_ocr, get_full_text
from app.pipeline.field_matcher import match_fields
from app.pipeline.field_parser import parse_matched_fields
from app.pipeline.normalizer import normalize_parsed_fields


def run_pipeline(image: Image.Image) -> dict:
    """
    Run the full pipeline on a captured/uploaded label image.

    Returns a dict shaped for pages/3_Results.py:
        {
            "overall_status": str,
            "extracted_text": str,
            "parsed_fields": dict,   # for debugging / History page detail view
            "checks": list[dict],    # rule-by-rule PASS/FAIL, once rule engine exists
        }
    """
    # 1. Preprocess
    preprocessed = preprocess_image(image)

    # 2. OCR
    ocr_lines = run_ocr(preprocessed)
    full_text = get_full_text(ocr_lines)

    # 3. Fuzzy field matching
    matches = match_fields(ocr_lines)

    # 4. Clean value extraction
    parsed_fields = parse_matched_fields(matches)

    # 5. Normalization (dates, quantities)
    normalized_fields = normalize_parsed_fields(parsed_fields)

    # 6. Rule engine — deferred import so this file works before rules/ exists
    try:
        from app.rules.rule_engine import evaluate_all

        checks = evaluate_all(normalized_fields, extracted_text=full_text)
        overall_status = _compute_overall_status(checks)
    except ModuleNotFoundError:
        checks = []
        overall_status = "PENDING_RULE_ENGINE"

    return {
        "overall_status": overall_status,
        "extracted_text": full_text,
        "parsed_fields": normalized_fields,
        "checks": checks,
    }


def _compute_overall_status(checks: list[dict]) -> str:
    """Roll up individual rule results into one overall status."""
    if not checks:
        return "OUT_OF_SCOPE"

    if any(c.get("status") == "OUT_OF_SCOPE" for c in checks):
        return "OUT_OF_SCOPE"

    statuses = [c.get("status") for c in checks]
    if all(s in ("PASS", "NOT_APPLICABLE") for s in statuses):
        return "COMPLIANT"
    if all(s == "FAIL" for s in statuses if s != "NOT_APPLICABLE"):
        return "NON_COMPLIANT"
    return "PARTIAL"