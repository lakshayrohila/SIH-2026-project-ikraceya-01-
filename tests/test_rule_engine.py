"""
tests/test_rule_engine.py — unit tests for app/rules/rule_engine.py.

Run with: pytest tests/test_rule_engine.py -v

These use hand-built "normalized_fields" dicts instead of running the full
OCR pipeline, so they run in under a second and don't need PaddleOCR/spaCy
models loaded. That's intentional — this file tests the rule LOGIC, not
the extraction pipeline (see test_pipeline.py for that).
"""

from app.rules.rule_engine import evaluate_all


def _status_of(checks, rule_id):
    for c in checks:
        if c["rule_id"] == rule_id:
            return c["status"]
    return None


def test_tiny_package_is_out_of_scope():
    fields = {
        "net_quantity": {"value": 8, "unit": "gram"},
        "mrp": "50",
        "manufacturer_name_address": "ACME Foods, Delhi",
        "mfg_date": None,
        "consumer_care": {"phone": "9999999999", "email": None},
    }
    checks = evaluate_all(fields, extracted_text="")

    assert _status_of(checks, "SCOPE-3") == "OUT_OF_SCOPE"
    # Manual-only rules should still be logged even when out of scope
    assert _status_of(checks, "FONT-CHECK") == "NOT_APPLICABLE"


def test_all_mandatory_fields_present_passes():
    fields = {
        "net_quantity": {"value": 500, "unit": "gram"},
        "mrp": "199",
        "manufacturer_name_address": "ACME Foods Pvt Ltd, Mumbai 400001",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": "9999999999", "email": "care@acme.com"},
    }
    checks = evaluate_all(fields, extracted_text="MRP Rs 199 inclusive of all taxes")

    assert _status_of(checks, "DECL-1") == "PASS"
    assert _status_of(checks, "DECL-3") == "PASS"
    assert _status_of(checks, "DECL-4") == "PASS"
    assert _status_of(checks, "DECL-5") == "PASS"
    assert _status_of(checks, "DECL-7") == "PASS"
    assert _status_of(checks, "MRP-FORMAT") == "PASS"


def test_missing_mrp_fails_decl5():
    fields = {
        "net_quantity": {"value": 500, "unit": "gram"},
        "mrp": None,
        "manufacturer_name_address": "ACME Foods, Mumbai",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": "9999999999", "email": None},
    }
    checks = evaluate_all(fields, extracted_text="")

    assert _status_of(checks, "DECL-5") == "FAIL"


def test_missing_consumer_care_fails_decl7():
    fields = {
        "net_quantity": {"value": 500, "unit": "gram"},
        "mrp": "199",
        "manufacturer_name_address": "ACME Foods, Mumbai",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": None, "email": None},
    }
    checks = evaluate_all(fields, extracted_text="")

    assert _status_of(checks, "DECL-7") == "FAIL"


def test_misleading_quantity_words_fail_qty3():
    fields = {
        "net_quantity": {"value": 500, "unit": "gram"},
        "mrp": "199",
        "manufacturer_name_address": "ACME Foods, Mumbai",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": "9999999999", "email": None},
    }
    checks = evaluate_all(fields, extracted_text="Net Wt. approximately 500g")

    assert _status_of(checks, "QTY-3") == "FAIL"


def test_dozen_unit_word_fails_qty6():
    fields = {
        "net_quantity": {"value": 12, "unit": "number"},
        "mrp": "199",
        "manufacturer_name_address": "ACME Foods, Mumbai",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": "9999999999", "email": None},
    }
    checks = evaluate_all(fields, extracted_text="Contains 1 dozen pieces")

    assert _status_of(checks, "QTY-6") == "FAIL"


def test_mrp_missing_tax_phrase_fails_format():
    fields = {
        "net_quantity": {"value": 500, "unit": "gram"},
        "mrp": "199",
        "manufacturer_name_address": "ACME Foods, Mumbai",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": "9999999999", "email": None},
    }
    checks = evaluate_all(fields, extracted_text="MRP Rs 199")  # no "inclusive of all taxes"

    assert _status_of(checks, "MRP-FORMAT") == "FAIL"


def test_manual_only_rules_always_not_applicable():
    fields = {
        "net_quantity": {"value": 500, "unit": "gram"},
        "mrp": "199",
        "manufacturer_name_address": "ACME Foods, Mumbai",
        "mfg_date": "2026-01-01",
        "consumer_care": {"phone": "9999999999", "email": None},
    }
    checks = evaluate_all(fields, extracted_text="")

    for manual_id in ("FONT-CHECK", "MPE-CHECK", "PRICE-REVISION", "PENALTIES"):
        assert _status_of(checks, manual_id) == "NOT_APPLICABLE"