"""Street name normalization for tolerant search (§10)."""

import re

_UMLAUTS = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})

# Letter-spaced print ("K a h l h o r s t s t r .") – collapse runs of at
# least four single characters separated by single spaces.
_LETTER_SPACING_RE = re.compile(r"(?<!\S)(?:\S ){3,}\S(?!\S)")

# word boundaries in collapsed text: lower/dot -> upper ("AmBach" -> "Am Bach")
# and letter/dot -> digit ("Kahlhorststr.1-15" -> "Kahlhorststr. 1-15")
_WORD_BOUNDARY_RE = re.compile(r"(?<=[a-zäöüß.])(?=[A-ZÄÖÜ0-9])")

# collapsed two-part connectors: "AnderBäk" -> "An der Bäk"
_CONNECTOR_RE = re.compile(r"\b(An|Auf|Bei|Vor|Unter|Hinter|Zu|In)(der|dem|den|des|de)\b")

# lowercase words that legitimately follow a space in street names
_LOWERCASE_WORDS = {
    "der", "die", "das", "den", "dem", "des", "de", "am", "an", "im", "in",
    "auf", "bei", "zum", "zur", "zu", "vor", "hinter", "unter", "über",
    "neben", "ab", "bis", "und", "op", "to", "ut",
}


def _restore_boundaries(collapsed: str) -> str:
    value = _WORD_BOUNDARY_RE.sub(" ", collapsed)
    return _CONNECTOR_RE.sub(r"\1 \2", value)


def collapse_letter_spacing(raw: str) -> str:
    """Collapse letter-spaced text ("A m B a c h") as printed in some PDF rows.

    Spaces inside a spaced run are removed; word boundaries are restored at
    lowercase→uppercase and letter→digit transitions plus known two-part
    connectors ("An der"), which is reliable for German street names and
    house number ranges.
    """

    def _fix(match: re.Match) -> str:
        return _restore_boundaries(match.group(0).replace(" ", ""))

    value = _LETTER_SPACING_RE.sub(_fix, raw)

    # Fallback for partially merged fragments ("Dröge st r.", "B e e re nweg"):
    # in German street names every word after a space starts uppercase except
    # a known set of prepositions/articles – lowercase continuations are
    # therefore glue fragments and get merged into the previous token.
    tokens = value.split()
    merged: list[str] = []
    for token in tokens:
        if (
            merged
            and token[0].isalpha()
            and token[0].islower()
            and token.rstrip(".").lower() not in _LOWERCASE_WORDS
        ):
            merged[-1] += token
        else:
            merged.append(token)
    return " ".join(merged)


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
