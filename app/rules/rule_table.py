"""
rule_table.py — loads the rule table from rule_definitions.json.

Keeping rules as data (not hardcoded if/else chains) means new amendments
can be added by editing the JSON file, without touching rule_engine.py.
This is the design decision your spec doc itself recommends mentioning
to judges.
"""

import json
import os

_RULES_PATH = os.path.join(os.path.dirname(__file__), "rule_definitions.json")

_cached_rules = None


def _load_rules() -> dict:
    global _cached_rules
    if _cached_rules is None:
        with open(_RULES_PATH, "r", encoding="utf-8") as f:
            _cached_rules = json.load(f)
    return _cached_rules


def get_rule_version() -> str:
    return _load_rules().get("rule_version", "unknown")


def get_auto_rules() -> list[dict]:
    """Rules that can be checked automatically from OCR-extracted fields."""
    return _load_rules().get("auto_rules", [])


def get_manual_only_rules() -> list[dict]:
    """Rules that require physical/lab inspection — not scannable from a photo."""
    return _load_rules().get("manual_only_rules", [])