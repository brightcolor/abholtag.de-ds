"""Tests for BMS ICS parsing and tour clustering (no network access)."""

from datetime import date

from apps.imports.bms_schedule import cluster_signatures, parse_bms_ics, zone_codes_for

SAMPLE_ICS = """BEGIN:VCALENDAR
PRODID:-//github.com/rianjs/ical.net//NONSGML ical.net 4.0//EN
VERSION:2.0
BEGIN:VEVENT
DTEND;VALUE=DATE:20260114
DTSTAMP:20260712T215245Z
DTSTART;VALUE=DATE:20260113
SEQUENCE:0
SUMMARY:Leerung: Bioabfall
UID:1cbce18c-4d09-42de-854c-6944ff2715f2
END:VEVENT
BEGIN:VEVENT
DTEND;VALUE=DATE:20260114
DTSTART;VALUE=DATE:20260113
SUMMARY:Leerung: PPK
UID:5d947026
END:VEVENT
BEGIN:VEVENT
DTEND;VALUE=DATE:20260128
DTSTART;VALUE=DATE:20260127
SUMMARY:Leerung: Bioabfall
UID:abc
END:VEVENT
BEGIN:VEVENT
DTEND;VALUE=DATE:20260120
DTSTART;VALUE=DATE:20260119
SUMMARY:Leerung: Restabfall
UID:def
END:VEVENT
BEGIN:VEVENT
DTEND;VALUE=DATE:20261207
DTSTART;VALUE=DATE:20261206
SUMMARY:Weihnachtsbaumabholung
UID:xyz
END:VEVENT
END:VCALENDAR
"""


def test_parse_bms_ics_groups_by_waste_type():
    parsed, unknown = parse_bms_ics(SAMPLE_ICS)
    assert parsed["bioabfall"] == [date(2026, 1, 13), date(2026, 1, 27)]
    assert parsed["papier"] == [date(2026, 1, 13)]
    assert parsed["restabfall"] == [date(2026, 1, 19)]
    assert unknown == {"Weihnachtsbaumabholung"}


def test_parse_empty_document():
    parsed, unknown = parse_bms_ics("BEGIN:VCALENDAR\nEND:VCALENDAR\n")
    assert parsed == {} and unknown == set()


def test_clustering_groups_identical_patterns():
    a = (date(2026, 1, 5), date(2026, 1, 19))
    b = (date(2026, 1, 6), date(2026, 1, 20))
    clusters = cluster_signatures({1: a, 2: b, 3: a})
    assert clusters[a] == [1, 3]
    assert clusters[b] == [2]


def test_zone_codes_deterministic_by_first_date():
    a = (date(2026, 1, 5),)
    b = (date(2026, 1, 6),)
    codes = zone_codes_for({b: [2], a: [1]}, "R")
    assert codes == {a: "R01", b: "R02"}


# ---------------------------------------------------------------------------
# Live-Fallback (ensure_bms_schedule_for_street) – ohne Netz über den Disk-Cache
# ---------------------------------------------------------------------------

import pytest  # noqa: E402

from apps.imports.bms_schedule import ensure_bms_schedule_for_street  # noqa: E402


@pytest.fixture
def live_setup(db, tmp_path):
    from django.core.cache import cache

    from apps.addresses.models import City, HouseNumber, Street
    from apps.schedules.models import CollectionZone, ScheduleYear, ScheduleYearStatus
    from apps.waste_types.models import WasteType

    cache.clear()  # Tagesdrossel aus vorherigen Tests zurücksetzen (LocMem)
    city = City.objects.create(name="Lübeck", slug="luebeck")
    street = Street.objects.create(city=city, name="Frischer Weg", bms_street_id=4711)
    HouseNumber.objects.create(street=street, text="1", number=1, bms_location_id=77001)
    bio = WasteType.objects.get(slug="bioabfall")
    year = ScheduleYear.objects.create(
        waste_type=bio, year=2026, status=ScheduleYearStatus.PUBLISHED
    )
    # bestehende Zone mit identischem Muster wie im Beispiel-ICS (13.01./27.01.)
    zone = CollectionZone.objects.create(waste_type=bio, code="B01")
    from apps.core.models import Origin
    from apps.schedules.models import CollectionDate

    CollectionDate.objects.create(
        schedule_year=year, zone=zone, date=date(2026, 1, 13), origin=Origin.OFFICIAL_IMPORT
    )
    CollectionDate.objects.create(
        schedule_year=year, zone=zone, date=date(2026, 1, 27), origin=Origin.OFFICIAL_IMPORT
    )
    (tmp_path / "77001-2026.ics").write_text(SAMPLE_ICS, encoding="utf-8")
    return {"street": street, "zone": zone, "cache": tmp_path}


def test_live_fallback_reuses_matching_zone(live_setup):
    street = live_setup["street"]
    added = ensure_bms_schedule_for_street(street, year=2026, cache_dir=live_setup["cache"])
    assert added
    assignment = street.assignments.get(zone__waste_type__slug="bioabfall")
    assert assignment.zone == live_setup["zone"]  # Muster identisch → Zone wiederverwendet
    assert "live ergänzt" in assignment.note


def test_live_fallback_creates_new_zone_for_new_pattern(live_setup):
    from apps.schedules.models import ScheduleYear, ScheduleYearStatus
    from apps.waste_types.models import WasteType

    rest = WasteType.objects.get(slug="restabfall")
    ScheduleYear.objects.create(waste_type=rest, year=2026, status=ScheduleYearStatus.PUBLISHED)
    street = live_setup["street"]
    ensure_bms_schedule_for_street(street, year=2026, cache_dir=live_setup["cache"])
    zone = street.assignments.get(zone__waste_type__slug="restabfall").zone
    assert zone.code == "R01"  # neue Zone, fortlaufende Nummer
    assert zone.dates.count() == 1  # 19.01. aus dem Beispiel-ICS


def test_live_fallback_noop_when_assigned(live_setup):
    street = live_setup["street"]
    ensure_bms_schedule_for_street(street, year=2026, cache_dir=live_setup["cache"])
    from django.core.cache import cache
    cache.clear()  # Tagesdrossel zurücksetzen
    assert ensure_bms_schedule_for_street(street, year=2026, cache_dir=live_setup["cache"]) is False


def test_live_fallback_throttled(live_setup):
    street = live_setup["street"]
    from django.core.cache import cache
    cache.clear()
    ensure_bms_schedule_for_street(street, year=2026, cache_dir=live_setup["cache"])
    street.assignments.all().delete()
    # zweiter Aufruf am selben Tag: gedrosselt, kein erneuter Abruf
    assert ensure_bms_schedule_for_street(street, year=2026, cache_dir=live_setup["cache"]) is False
