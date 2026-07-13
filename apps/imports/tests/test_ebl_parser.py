"""Tests for the EBL "Wegweiser" parser and its house-range logic.

The parser tests run against the archived sample PDF (no network, §39); they
are skipped automatically when the sample is not present.
"""

from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from apps.core.text import parse_house_ranges
from apps.imports.parsers.luebeck_ebl import LuebeckEblParser

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "samples" / "abfuhrplan-ebl-2026.pdf"
needs_sample = pytest.mark.skipif(not SAMPLE.exists(), reason="EBL-Beispiel-PDF nicht vorhanden")


# ---------------------------------------------------------------------------
# house-number range parsing (pure, no PDF)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", None),
        ("—", None),
        ("1-23 + 2-22a", [
            {"house_from": 1, "house_to": 23, "parity": "odd"},
            {"house_from": 2, "house_to": 22, "parity": "even"},
        ]),
        ("24-Ende + 25-Ende", [
            {"house_from": 24, "house_to": None, "parity": "even"},
            {"house_from": 25, "house_to": None, "parity": "odd"},
        ]),
        ("5 + 13a", [
            {"house_from": 5, "house_to": 5, "parity": "odd"},
            {"house_from": 13, "house_to": 13, "parity": "odd"},
        ]),
        ("1a", [{"house_from": 1, "house_to": 1, "parity": "odd"}]),
    ],
)
def test_parse_house_ranges(raw, expected):
    assert parse_house_ranges(raw) == expected


def test_parse_house_ranges_rejects_irregular():
    # never guess: irregular strings return None so the caller keeps them raw
    assert parse_house_ranges("21-Eisenbahn-") is None
    assert parse_house_ranges("24 + 40 bis Buntekuhweg") is None
    assert parse_house_ranges("- Ende (beide Seiten)") is None


# ---------------------------------------------------------------------------
# full parser against the sample PDF
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def plans():
    return LuebeckEblParser().parse_multi(str(SAMPLE))


@needs_sample
def test_all_streams_present(plans):
    assert set(plans) == {"restabfall", "bioabfall", "papier", "gelber-sack"}


@needs_sample
def test_year_detected(plans):
    for plan in plans.values():
        assert plan.year == 2026


@needs_sample
def test_no_blocking_issues(plans):
    for slug, plan in plans.items():
        assert not plan.has_blocking_issues, (slug, [i.message for i in plan.issues])


@needs_sample
def test_calendar_letter_counts(plans):
    # Rest/Bio & Gelber Sack run bi-weekly (≈26/letter), Papier every 4 weeks
    gs = Counter(e.zone_code for e in plans["gelber-sack"].calendar)
    assert set(gs) == set("ABCDEFGHIJ")
    assert all(22 <= n <= 28 for n in gs.values())
    papier = Counter(e.zone_code for e in plans["papier"].calendar)
    assert set(papier) == set("ABCDEFGHIJKLMNOPQRST")
    assert all(10 <= n <= 15 for n in papier.values())


@needs_sample
def test_gelber_sack_matches_known_districts(plans):
    # spot checks verified against the independent OCR import
    by_name = {}
    for s in plans["gelber-sack"].streets:
        by_name.setdefault(s.name.split("(")[0].strip(), s)
    assert by_name["Achatweg"].zone_codes == ["D"]
    assert by_name["Achterdeck"].zone_codes == ["H"]


@needs_sample
def test_may_13_present_for_zone_c(plans):
    # the EBL plan contains the 13 May / zone C date the Veolia OCR PDF dropped
    c_dates = {e.date for e in plans["gelber-sack"].calendar if e.zone_code == "C"}
    assert date(2026, 5, 13) in c_dates


@needs_sample
def test_street_index_complete(plans):
    names = {s.name for s in plans["gelber-sack"].streets}
    assert len(names) > 1600
    assert "Beethovenstraße" in names
    assert "Achatweg" in names


@needs_sample
def test_house_ranges_extracted(plans):
    # Kahlhorststraße is split by house number in the 2026 plan
    kahl = [s for s in plans["gelber-sack"].streets if s.name.startswith("Kahlhorst") and s.raw_range]
    assert kahl, "expected at least one ranged Kahlhorststraße entry"
    assert any(parse_house_ranges(s.raw_range) for s in kahl)


@needs_sample
def test_old_town_split_codes(plans):
    aegidien = [s for s in plans["gelber-sack"].streets if s.name.startswith("Aegidienstraße")]
    assert any(len(s.zone_codes) == 2 for s in aegidien)
