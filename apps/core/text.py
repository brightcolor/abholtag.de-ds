"""Street name normalization for tolerant search (§10)."""

import re

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def normalize_street_name(raw: str) -> str:
    """Return the canonical search form of a street name.

    Handles case, umlauts, Straße/Strasse/Str., Sankt/St., hyphens and
    whitespace so that user input and official spellings meet in one form.
    """
    value = raw.strip().lower().translate(_UMLAUTS)
    value = value.replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    # unify Sankt
    value = re.sub(r"\bst\.\s*", "sankt ", value)
    value = re.sub(r"\bsankt\b", "sankt", value)
    # unify Straße endings: "musterstr." / "muster str." / "musterstrasse"
    value = re.sub(r"str\.(?=\s|$)", "strasse", value)
    value = re.sub(r"\bstr\b(?=\s|$)", "strasse", value)
    value = value.replace(" strasse", "strasse")
    value = re.sub(r"\s+", " ", value).strip()
    return value


HOUSE_NUMBER_RE = re.compile(r"^\s*(\d+)\s*([a-zA-Z]?)\s*$")


def parse_house_number(raw: str) -> tuple[int | None, str]:
    """Split '12a' into (12, 'a'). Returns (None, '') for empty input."""
    if not raw or not raw.strip():
        return None, ""
    match = HOUSE_NUMBER_RE.match(raw)
    if not match:
        return None, ""
    return int(match.group(1)), match.group(2).lower()
