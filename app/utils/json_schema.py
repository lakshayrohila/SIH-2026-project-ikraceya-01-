"""
json_schema.py — converts a pipeline_runner.py result into the JSON blob
shapes expected by scan_logs (see spec Section 12: SUGGESTED VALIDATION
ENGINE OUTPUT SCHEMA).

Used by app.db.crud.save_scan() (built in a later batch) right before
writing to MySQL — each *_json field on ScanLog is one of these dicts,
json.dumps'd at insert time.
"""

from datetime import datetime


def _find_check(checks: list[dict], rule_id: str) -> dict | None:
    for check in checks:
        if check.get("rule_id") == rule_id:
            return check
    return None


def build_scope_check(checks: list[dict]) -> dict:
    scope_check = _find_check(checks, "SCOPE-3")
    if scope_check:
        return {"in_scope": False, "reason": scope_check["description"]}
    return {"in_scope": True, "reason": ""}


def build_declarations(fields: dict, checks: list[dict]) -> dict:
    def status_of(rule_id: str) -> str:
        check = _find_check(checks, rule_id)
        return check["status"] if check else "NOT_APPLICABLE"

    net_qty = fields.get("net_quantity") or {}
    mfg_date = fields.get("mfg_date")

    return {
        "manufacturer_address": {
            "present": status_of("DECL-1") == "PASS",
            "text": fields.get("manufacturer_name_address") or "",
            "rule": "6(1)(a)",
        },
        "net_quantity": {
            "present": status_of("DECL-3") == "PASS",
            "value": net_qty.get("value"),
            "unit": net_qty.get("unit"),
            "rule": "6(1)(c)",
        },
        "mfg_date": {
            "present": status_of("DECL-4") == "PASS",
            "value": mfg_date.isoformat() if isinstance(mfg_date, datetime) else None,
            "rule": "6(1)(d)",
        },
        "mrp": {
            "present": status_of("DECL-5") == "PASS",
            "value": fields.get("mrp"),
            "format_valid": status_of("MRP-FORMAT") == "PASS",
            "rule": "6(1)(e), 2(m)",
        },
        "consumer_care": {
            "present": status_of("DECL-7") == "PASS",
            "details": fields.get("consumer_care") or {},
            "rule": "6(2)",
        },
    }


def build_font_checks(checks: list[dict]) -> dict:
    """Font/readability checks are manual-only (see FONT-CHECK) — placeholder
    values until a physical-inspection form feeds real measurements in."""
    manual_check = _find_check(checks, "FONT-CHECK")
    return {
        "numeral_height_mm": None,
        "required_min_mm": None,
        "pass": None,
        "contrast_pass": None,
        "note": manual_check["description"] if manual_check else "Not evaluated.",
    }


def build_quantity_checks(checks: list[dict]) -> dict:
    qty3 = _find_check(checks, "QTY-3")
    qty6 = _find_check(checks, "QTY-6")
    misleading_found = []
    if qty3 and qty3["status"] == "FAIL" and "(found:" in qty3["description"]:
        found_part = qty3["description"].split("(found:", 1)[1].rstrip(")")
        misleading_found = [w.strip() for w in found_part.split(",")]

    return {
        "unit_correct": None,  # requires Fourth Schedule cross-check — not yet automated
        "misleading_words_found": misleading_found,
        "standard_size_match": None,  # informational-only per spec (repealed provision)
        "prohibited_unit_words_found": qty6["status"] == "FAIL" if qty6 else False,
    }


def build_violations(checks: list[dict]) -> list[dict]:
    """Every FAIL becomes a violation entry; PASS/NOT_APPLICABLE/OUT_OF_SCOPE don't."""
    violations = []
    for check in checks:
        if check["status"] == "FAIL":
            violations.append({
                "rule_id": check["rule_id"],
                "rule_ref": check["rule_ref"],
                "description": check["description"],
                "severity": "violation",
            })
    return violations


def build_scan_record(user_id: int, persona: str, pipeline_result: dict) -> dict:
    """
    Top-level builder — assembles everything save_scan() needs to write
    a ScanLog row. Returns a dict with plain Python values (dicts/lists),
    ready for json.dumps() at insert time.
    """
    checks = pipeline_result.get("checks", [])
    fields = pipeline_result.get("parsed_fields", {})

    return {
        "user_id": user_id,
        "persona": persona,
        "extracted_text": pipeline_result.get("extracted_text", ""),
        "scope_check": build_scope_check(checks),
        "declarations": build_declarations(fields, checks),
        "font_checks": build_font_checks(checks),
        "quantity_checks": build_quantity_checks(checks),
        "violations": build_violations(checks),
        "overall_status": pipeline_result.get("overall_status", "UNKNOWN"),
    }