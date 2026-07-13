from datetime import date

import pytest

from apps.addresses.models import AddressKey, City, Street, StreetAssignment
from apps.calendars.ics import build_calendar, calendar_etag
from apps.schedules.models import (
    CollectionDate,
    CollectionZone,
    ScheduleYear,
    ScheduleYearStatus,
)
from apps.schedules.services import feed_dates_for_address
from apps.waste_types.models import WasteType


@pytest.fixture
def setup(db):
    city = City.objects.create(name="Lübeck", slug="luebeck")
    street = Street.objects.create(city=city, name="Musterstraße")
    waste_type = WasteType.objects.get(slug="gelber-sack")
    zone = CollectionZone.objects.create(waste_type=waste_type, code="A")
    StreetAssignment.objects.create(street=street, zone=zone)
    year = ScheduleYear.objects.create(
        waste_type=waste_type, year=2030, status=ScheduleYearStatus.PUBLISHED
    )
    d1 = CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 1, 7))
    d2 = CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 1, 21))
    address_key = AddressKey.objects.create(street=street, house_number=12)
    return {"address_key": address_key, "zone": zone, "year": year, "dates": [d1, d2]}


def content_for(setup_data) -> str:
    dates = feed_dates_for_address(setup_data["address_key"])
    return build_calendar(setup_data["address_key"], dates, "Test").decode("utf-8")


def test_rfc_basics(setup):
    content = content_for(setup)
    assert content.startswith("BEGIN:VCALENDAR\r\n")
    assert content.endswith("END:VCALENDAR\r\n")
    assert "CALSCALE:GREGORIAN" in content
    assert "METHOD:PUBLISH" in content
    assert content.count("BEGIN:VEVENT") == 2
    assert "DTSTART;VALUE=DATE:20300107" in content
    assert "DTEND;VALUE=DATE:20300108" in content
    # every line CRLF-terminated and folded below 76 octets
    for line in content.split("\r\n"):
        assert len(line.encode("utf-8")) <= 75


def test_uid_stable_across_builds(setup):
    first = content_for(setup)
    second = content_for(setup)
    uid_lines = [line for line in first.split("\r\n") if line.startswith("UID:")]
    assert uid_lines == [line for line in second.split("\r\n") if line.startswith("UID:")]
    assert setup["address_key"].public_id in uid_lines[0]


def test_cancelled_date_stays_in_feed_as_cancelled(setup):
    record = setup["dates"][0]
    record.is_cancelled = True
    record.save()
    content = content_for(setup)
    assert "STATUS:CANCELLED" in content
    assert content.count("BEGIN:VEVENT") == 2  # bleibt enthalten, damit Clients löschen


def test_sequence_bumps_on_change(setup):
    record = setup["dates"][0]
    assert record.sequence == 0
    record.note = "verschoben"
    record.save()
    record.refresh_from_db()
    assert record.sequence == 1
    assert "SEQUENCE:1" in content_for(setup)


def test_unpublished_year_not_in_feed(setup):
    setup["year"].status = ScheduleYearStatus.WITHDRAWN
    setup["year"].save()
    assert content_for(setup).count("BEGIN:VEVENT") == 0


def test_etag_changes_with_content(setup):
    first = calendar_etag(content_for(setup).encode())
    setup["dates"][0].note = "neu"
    setup["dates"][0].save()
    assert calendar_etag(content_for(setup).encode()) != first


def test_feed_view_http_caching(setup, client):
    url = f"/calendar/address/{setup['address_key'].public_id}/gelber-sack.ics"
    response = client.get(url)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/calendar")
    etag = response["ETag"]
    assert client.get(url, HTTP_IF_NONE_MATCH=etag).status_code == 304


def test_subscribe_page_one_tap_links(setup, client):
    """Smartphone-Abo: webcal- und Google-Kalender-Link auf der Abo-Seite."""
    response = client.get(f"/a/{setup['address_key'].public_id}/kalender/")
    content = response.content.decode()
    assert response.status_code == 200
    assert 'href="webcal://' in content
    assert "calendar.google.com/calendar/render?cid=webcal%3A%2F%2F" in content
