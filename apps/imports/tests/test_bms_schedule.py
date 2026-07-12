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
