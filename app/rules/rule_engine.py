"""
rule_engine.py — evaluates extracted/normalized label fields against the
rule table in rule_definitions.json.

Called by pipeline_runner.py as:
    evaluate_all(normalized_fields, extracted_text) -> list[dict]

Each returned check dict looks like:
    {"rule_id": "DECL-1", "section": "...", "rule_ref": "6(1)(a)",
     "description": "...", "status": "PASS" | "FAIL" | "NOT_APPLICABLE" | "OUT_OF_SCOPE"}
"""

from app.rules.rule_table import get_auto_rules, get_manual_only_rules

# Tiny-package exemption threshold (Rule 26 / SCOPE-3). Applies to weight/
# volume units only — not to "number" quantities.
TINY_PACKAGE_UNITS = {"gram", "millilitre", "milliliter"}
TINY_PACKAGE_MAX_VALUE = 10


def _check_scope(fields: dict) -> dict | None:
    """
    SCOPE-3: packages with net qty <= 10g/mL are exempt from Chapter II
    declarations entirely. If this applies, the whole scan is out of scope.
    """
    qty = fields.get("net_quantity")
    if not qty or qty.get("value") is None:
        return None

    unit = (qty.get("unit") or "").lower()
    value = qty.get("value")

    if unit in TINY_PACKAGE_UNITS and value <= TINY_PACKAGE_MAX_VALUE:
        return {
            "rule_id": "SCOPE-3",
            "section": "Scope Check",
            "rule_ref": "Rule 26",
            "description": (
                f"Net quantity ({value} {unit}) is 10 g/mL or below — this "
                "package is exempt from Chapter II mandatory declarations "
                "under the tiny-package exemption."
            ),
            "status": "OUT_OF_SCOPE",
        }
    return None


def _is_field_present(field_name: str, value) -> bool:
    """Field-specific presence logic — dict-shaped fields need special handling."""
    if value is None:
        return False
    if field_name == "net_quantity" and isinstance(value, dict):
        return value.get("value") is not None
    if field_name == "consumer_care" and isinstance(value, dict):
        return bool(value.get("phone") or value.get("email"))
    if isinstance(value, str):
        return value.strip() != ""
    return True


def _check_field_present(rule: dict, fields: dict) -> dict:
    field_name = rule["field"]
    present = _is_field_present(field_name, fields.get(field_name))
    return {
        "rule_id": rule["rule_id"],
        "section": rule["section"],
        "rule_ref": rule["rule_ref"],
        "description": rule["description"],
        "status": "PASS" if present else "FAIL",
    }


def _check_keyword_absence(rule: dict, extracted_text: str) -> dict:
    text_lower = extracted_text.lower()
    found = [kw for kw in rule["keywords"] if kw in text_lower]
    description = rule["description"]
    if found:
        description += f" (found: {', '.join(found)})"
    return {
        "rule_id": rule["rule_id"],
        "section": rule["section"],
        "rule_ref": rule["rule_ref"],
        "description": description,
        "status": "FAIL" if found else "PASS",
    }


def _check_text_contains(rule: dict, extracted_text: str) -> dict:
    text_lower = extracted_text.lower()
    found_any = any(kw in text_lower for kw in rule["keywords"])
    return {
        "rule_id": rule["rule_id"],
        "section": rule["section"],
        "rule_ref": rule["rule_ref"],
        "description": rule["description"],
        "status": "PASS" if found_any else "FAIL",
    }


def _manual_only_check(rule: dict) -> dict:
    return {
        "rule_id": rule["rule_id"],
        "section": rule["section"],
        "rule_ref": rule["rule_ref"],
        "description": rule["description"],
        "status": "NOT_APPLICABLE",
    }


def evaluate_all(fields: dict, extracted_text: str = "") -> list[dict]:
    """
    Run the full rule table against extracted/normalized fields.

    If the scope check triggers an exemption, only the scope result plus
    the manual-only rules are returned (manual checks still get logged,
    matching the spec's "still let officer log it" guidance).
    """
    checks = []

    scope_result = _check_scope(fields)
    if scope_result is not None:
        checks.append(scope_result)
        checks.extend(_manual_only_check(r) for r in get_manual_only_rules())
        return checks

    for rule in get_auto_rules():
        check_type = rule["check_type"]
        if check_type == "field_present":
            checks.append(_check_field_present(rule, fields))
        elif check_type == "keyword_absence":
            checks.append(_check_keyword_absence(rule, extracted_text))
        elif check_type == "text_contains":
            checks.append(_check_text_contains(rule, extracted_text))

    checks.extend(_manual_only_check(r) for r in get_manual_only_rules())

    return checks