"""
normalizer.py — convert raw parsed strings into standard Python types.

dateparser handles the many date formats seen on labels (dd/mm/yyyy,
"Jan 2026", etc.). quantulum3 handles quantity strings ("500 g", "1 L")
and turns them into a value + unit pair the rule engine can compare
against the standard package sizes in the spec.
"""

from datetime import datetime

import dateparser
from quantulum3 import parser as quantity_parser


def normalize_date(raw_date: str | None) -> datetime | None:
    """Parse a raw date string into a datetime object, or None if unparseable."""
    if not raw_date:
        return None
    return dateparser.parse(raw_date, settings={"DATE_ORDER": "DMY"})


def normalize_quantity(raw_quantity: str | None) -> dict | None:
    """
    Parse a raw quantity string like '500 g' into a structured value.

    Returns {"value": 500.0, "unit": "gram"} or None if unparseable.
    """
    if not raw_quantity:
        return None

    quantities = quantity_parser.parse(raw_quantity)
    if not quantities:
        return None

    best = quantities[0]
    return {"value": best.value, "unit": best.unit.name}


def normalize_parsed_fields(parsed_fields: dict) -> dict:
    """
    Take field_parser.parse_matched_fields() output and normalize the
    date and quantity fields in place, leaving other fields as-is.
    """
    normalized = dict(parsed_fields)
    normalized["mfg_date"] = normalize_date(parsed_fields.get("mfg_date"))
    normalized["net_quantity"] = normalize_quantity(parsed_fields.get("net_quantity"))
    return normalized