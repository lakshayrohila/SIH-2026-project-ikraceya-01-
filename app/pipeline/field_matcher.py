"""
field_matcher.py — fuzzy-match OCR text lines to the mandatory declaration
fields required under the Legal Metrology (Packaged Commodities) Rules, 2011.

OCR text is noisy ("MR P : Rs 99" instead of "MRP: Rs. 99"), so we fuzzy-match
against several label variants per field rather than doing exact string checks.
"""

from rapidfuzz import fuzz, process

# Each field maps to label variants commonly seen on Indian packaged labels.
# Extend this list as you test against real product photos — OCR misreads
# are the main reason a field gets missed, not the rule logic itself.
FIELD_LABELS = {
    "mrp": ["MRP", "Maximum Retail Price", "M.R.P", "Price"],
    "net_quantity": ["Net Qty", "Net Quantity", "Net Weight", "Net Wt", "Net Volume"],
    "mfg_date": ["Mfg Date", "Manufacturing Date", "Date of Manufacture", "Mfd"],
    "manufacturer_name_address": ["Manufactured by", "Marketed by", "Packed by", "Mfg by"],
    "country_of_origin": ["Country of Origin", "Made in", "Origin"],
    "consumer_care": ["Consumer Care", "Customer Care", "For Complaints", "Contact"],
    "fssai_license": ["FSSAI", "FSSAI Lic No", "License No", "Lic No"],
}

# Below this fuzzy score (0-100), we treat the field as "not found" rather
# than risk matching an unrelated line.
MATCH_THRESHOLD = 70


def match_fields(ocr_lines: list[dict]) -> dict:
    """
    For each mandatory field, find the best-matching OCR line (if any).

    Returns:
        {
            "mrp": {"line": "MRP Rs 199", "score": 88.0} | None,
            "net_quantity": {...} | None,
            ...
        }
    """
    texts = [line["text"] for line in ocr_lines]
    matches = {}

    for field_key, label_variants in FIELD_LABELS.items():
        best_score = 0
        best_line = None

        for variant in label_variants:
            if not texts:
                continue
            result = process.extractOne(variant, texts, scorer=fuzz.partial_ratio)
            if result is None:
                continue
            matched_text, score, _ = result
            if score > best_score:
                best_score = score
                best_line = matched_text

        if best_line is not None and best_score >= MATCH_THRESHOLD:
            matches[field_key] = {"line": best_line, "score": best_score}
        else:
            matches[field_key] = None

    return matches