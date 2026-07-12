"""Parser tests against the archived official PDF (no network access, §39)."""

from collections import Counter
from pathlib import Path

import pytest

from apps.imports.parsers.luebeck_gelber_sack import LuebeckGelberSackParser

SAMPLE = Path(__file__).resolve().parents[3] / "data" / "samples" / "abfuhrplan-gelber-sack-2026.pdf"

pytestmark = pytest.mark.skipif(not SAMPLE.exists(), reason="Beispiel-PDF nicht vorhanden")


@pytest.fixture(scope="module")
def plan():
    return LuebeckGelberSackParser().parse(str(SAMPLE))


def test_year_detected(plan):
    assert plan.year == 2026


def test_street_count_plausible(plan):
    assert len(plan.streets) > 1500


def test_known_streets_present(plan):
    names = {s.name for s in plan.streets}
    assert "Beethovenstr." in names
    assert "Achterdeck" in names
    # letter-spaced rows of the source PDF must be reconstructed correctly
    assert "Kahlhorststr." in names
    assert "Am Bach" in names
    assert "An der Bäk" in names
    assert "Beckergrube" in names


def test_zone_codes_valid(plan):
    for street in plan.streets:
        for code in street.zone_codes:
            assert code in set("ABCDEFGHIJ")


def test_old_town_streets_have_two_zones(plan):
    fischergrube = next(s for s in plan.streets if s.name == "Fischergrube")
    assert sorted(fischergrube.zone_codes) == ["B", "G"]


def test_ranged_streets_keep_raw_range(plan):
    ranged = [s for s in plan.streets if s.raw_range]
    assert len(ranged) >= 10  # Kahlhorststr., Geniner Str., Ratzeburger Allee, …


def test_calendar_dates_complete(plan):
    counts = Counter(entry.zone_code for entry in plan.calendar)
    assert set(counts) == set("ABCDEFGHIJ")
    for zone, count in counts.items():
        # 14-täglich → 26 Termine, Bezirk I hat 2026 zwei Jahresrand-Donnerstage (27)
        assert 25 <= count <= 27, f"Bezirk {zone}: {count}"


def test_calendar_rhythm(plan):
    per_zone: dict[str, list] = {}
    for entry in plan.calendar:
        per_zone.setdefault(entry.zone_code, []).append(entry.date)
    for zone, dates in per_zone.items():
        dates.sort()
        gaps = [(b - a).days for a, b in zip(dates, dates[1:], strict=False)]
        # Feiertagsverschiebungen erlauben 12-16; C hat eine dokumentierte Lücke im Quell-PDF
        allowed = {12, 13, 14, 15, 16} | ({29} if zone == "C" else set())
        assert set(gaps) <= allowed, f"Bezirk {zone}: {sorted(set(gaps))}"


def test_holiday_shift_detected(plan):
    shifted = {(e.date.isoformat(), e.zone_code) for e in plan.calendar if e.kind == "shifted"}
    assert ("2026-01-03", "J") in shifted  # Neujahrswoche: J von Fr auf Sa
    assert ("2026-12-19", "A") in shifted  # Weihnachtswoche


def test_official_pdf_gap_flagged(plan):
    """Das amtliche PDF 2026 enthält für Bezirk C im Mai keinen Termin –
    der Parser muss das als Warnung melden statt zu raten (§32)."""
    warnings = [i for i in plan.issues if i.level == "warning" and i.code == "zone_rhythm"]
    assert any("Bezirk C" in w.message for w in warnings)
