"""
field_parser.py — turn a matched raw OCR line into a clean extracted value.

Regex handles the well-structured fields (money, phone/email, license
numbers). spaCy's NER is used only where a plain regex isn't reliable
(pulling a country name out of a free-text "Made in ..." line).
"""

import re
import spacy

_nlp = None


def _get_nlp():
    """Lazily load the spaCy model — loading it is slow, so cache it."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


def parse_mrp(raw_line: str) -> str | None:
    """Extract a currency amount like '199', '99.00' from a line mentioning MRP."""
    match = re.search(r"(?:rs\.?|inr|₹)\s*[:\-]?\s*([\d,]+\.?\d*)", raw_line, re.IGNORECASE)
    if match:
        return match.group(1).replace(",", "")
    # Fallback: any number in the line, if no currency symbol was OCR'd cleanly
    match = re.search(r"(\d+\.?\d*)", raw_line)
    return match.group(1) if match else None


def parse_net_quantity(raw_line: str) -> str | None:
    """Pull out the number+unit chunk, e.g. '500 g', '1 L'. Left as a raw
    string here — normalizer.py converts it into a structured value."""
    match = re.search(r"(\d+\.?\d*)\s*(g|kg|ml|l|gm|gms|litre|litres|pcs|pieces)\b", raw_line, re.IGNORECASE)
    return match.group(0) if match else None


def parse_mfg_date(raw_line: str) -> str | None:
    """Pull out the date-looking substring; normalizer.py parses it properly."""
    match = re.search(r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{4})", raw_line)
    return match.group(0) if match else None


def parse_manufacturer_name_address(raw_line: str) -> str | None:
    """Strip the leading label ('Manufactured by:', etc.) and keep the rest."""
    cleaned = re.sub(r"^(manufactured by|marketed by|packed by|mfg by)\s*[:\-]?\s*", "", raw_line, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


def parse_country_of_origin(raw_line: str) -> str | None:
    """Use spaCy NER to find a country/place (GPE) entity in the line;
    falls back to stripping the label prefix if NER finds nothing."""
    nlp = _get_nlp()
    doc = nlp(raw_line)
    for ent in doc.ents:
        if ent.label_ == "GPE":
            return ent.text

    cleaned = re.sub(r"^(country of origin|made in|origin)\s*[:\-]?\s*", "", raw_line, flags=re.IGNORECASE)
    cleaned = cleaned.strip()
    return cleaned if cleaned else None


def parse_consumer_care(raw_line: str) -> dict:
    """Extract a phone number and/or email address from the consumer-care line."""
    phone_match = re.search(r"(\+?\d[\d\-\s]{8,15}\d)", raw_line)
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", raw_line)
    return {
        "phone": phone_match.group(1).strip() if phone_match else None,
        "email": email_match.group(0) if email_match else None,
    }


def parse_fssai_license(raw_line: str) -> str | None:
    """FSSAI license numbers are 14 digits."""
    match = re.search(r"\b(\d{14})\b", raw_line)
    return match.group(1) if match else None


# Maps each field key to its parser function, used by pipeline_runner.py
FIELD_PARSERS = {
    "mrp": parse_mrp,
    "net_quantity": parse_net_quantity,
    "mfg_date": parse_mfg_date,
    "manufacturer_name_address": parse_manufacturer_name_address,
    "country_of_origin": parse_country_of_origin,
    "consumer_care": parse_consumer_care,
    "fssai_license": parse_fssai_license,
}


def parse_matched_fields(matches: dict) -> dict:
    """
    Given field_matcher.match_fields() output, run the right parser on each
    matched line. Fields with no match stay None.
    """
    parsed = {}
    for field_key, match_info in matches.items():
        if match_info is None:
            parsed[field_key] = None
            continue
        parser_fn = FIELD_PARSERS.get(field_key)
        parsed[field_key] = parser_fn(match_info["line"]) if parser_fn else match_info["line"]
    return parsed