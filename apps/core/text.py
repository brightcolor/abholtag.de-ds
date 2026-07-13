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


# House-number ranges as printed in the EBL "Wegweiser" street index, e.g.
#   "1-23 + 2-22a"          odd 1–23 and even 2–22
#   "1-3 + 7-13 + 2-Ende"   odd 1–3, odd 7–13, even 2–open
#   "24-Ende + 25-Ende"     even 24–open and odd 25–open
#   "5 + 13a"               the single numbers 5 and 13
_RANGE_SEG_RE = re.compile(
    r"^\s*(\d+)\s*[a-z]?\s*(?:[-–]\s*(\d+\s*[a-z]?|Ende))?\s*$",
    re.IGNORECASE,
)
_END_TOKENS = {"ende", "end"}


def _parity_of(low: int, high: int | None) -> str:
    """EBL lists odd and even sides as separate ranges; derive which one."""
    if high is None or low == high:
        return "odd" if low % 2 else "even"
    if low % 2 == high % 2:
        return "odd" if low % 2 else "even"
    return "all"  # mixed endpoints → spans both sides


def parse_house_ranges(raw: str) -> list[dict] | None:
    """Parse an EBL house-number range string into assignment segments.

    Returns a list of ``{"house_from", "house_to", "parity"}`` dicts
    (``house_to`` is ``None`` for open "…-Ende" ranges), or ``None`` if any
    part cannot be parsed with confidence – the caller then keeps the raw
    text for human review instead of guessing (§10).
    """
    if not raw or not raw.strip() or raw.strip() == "—":
        return None
    segments: list[dict] = []
    for chunk in re.split(r"[+&]", raw):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = _RANGE_SEG_RE.match(chunk)
        if not match:
            return None
        low = int(match.group(1))
        upper = match.group(2)
        if upper is None:
            high: int | None = low
        elif upper.strip().lower() in _END_TOKENS:
            high = None
        else:
            high_match = re.match(r"(\d+)", upper.strip())
            if not high_match:
                return None
            high = int(high_match.group(1))
        if high is not None and high < low:
            return None
        segments.append({"house_from": low, "house_to": high, "parity": _parity_of(low, high)})
    return segments or None
