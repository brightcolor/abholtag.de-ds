from datetime import date

import pytest

from apps.accounts.models import User
from apps.addresses.models import AddressKey, City, Street, StreetAssignment
from apps.schedules.models import (
    CollectionDate,
    CollectionZone,
    ScheduleYear,
    ScheduleYearStatus,
)
from apps.waste_types.models import WasteType


@pytest.fixture
def setup(db):
    city = City.objects.create(name="Lübeck", slug="luebeck")
    street = Street.objects.create(city=city, name="Testweg")
    waste_type = WasteType.objects.get(slug="gelber-sack")
    zone = CollectionZone.objects.create(waste_type=waste_type, code="A")
    StreetAssignment.objects.create(street=street, zone=zone)
    year = ScheduleYear.objects.create(
        waste_type=waste_type, year=2030, status=ScheduleYearStatus.PUBLISHED
    )
    CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 5, 6))
    return {"street": street, "address_key": AddressKey.objects.create(street=street)}


def test_home_renders(client, db):
    response = client.get("/")
    assert response.status_code == 200
    assert "Adresse" in response.content.decode()


def test_street_suggestions_htmx(client, setup):
    response = client.get("/suche/vorschlaege/?q=testw")
    assert response.status_code == 200
    assert "Testweg" in response.content.decode()


def test_resolve_redirects_to_address_page(client, setup):
    response = client.get(f"/termine/?street_id={setup['street'].pk}&waste_type=gelber-sack")
    assert response.status_code == 302
    assert response.url.startswith("/a/")


def test_schedule_page(client, setup):
    response = client.get(f"/a/{setup['address_key'].public_id}/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Testweg" in content
    assert "06.05.2030" in content


def test_report_form_flow(client, setup):
    response = client.post(
        "/melden/",
        {
            "category": "wrong_date",
            "description": "Der Termin war laut Aushang einen Tag später.",
            "source_hint": "",
            "contact_email": "",
            "website": "",
            "form_started": "1",
        },
    )
    assert response.status_code == 302
    assert response.url.startswith("/melden/status/")


def test_report_honeypot_blocks(client, db):
    response = client.post(
        "/melden/",
        {
            "category": "wrong_date",
            "description": "Bot-Inhalt mit ausreichend Länge.",
            "website": "http://spam.example",
            "form_started": "1",
        },
    )
    assert response.status_code == 200  # Formular mit Fehler, keine Weiterleitung


def test_health_endpoints(client, db):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 200


def test_internal_pages_require_staff(client, setup):
    for url in ("/intern/statistik/", "/intern/moderation/", "/intern/status/"):
        response = client.get(url)
        assert response.status_code == 302  # redirect zum Login

    staff = User.objects.create_user("staff", password="x", is_staff=True, is_superuser=True)
    client.force_login(staff)
    for url in ("/intern/statistik/", "/intern/moderation/", "/intern/status/"):
        assert client.get(url).status_code == 200


def test_analytics_event_recorded(client, setup):
    from apps.analytics.models import AnalyticsEvent

    client.get("/")
    assert AnalyticsEvent.objects.filter(event_type="page_view").exists()


def test_multi_waste_type_filter(client, setup):
    """Mehrfachauswahl: arten=… filtert Terminliste und Chips (§8, Mehrfachliste)."""
    from datetime import date

    from apps.core.models import Origin
    from apps.schedules.models import CollectionDate, CollectionZone, ScheduleYear, ScheduleYearStatus
    from apps.waste_types.models import WasteType

    bio = WasteType.objects.get(slug="bioabfall")
    bio.is_active = True
    bio.save()
    zone = CollectionZone.objects.create(waste_type=bio, code="B01")
    year = ScheduleYear.objects.create(waste_type=bio, year=2030, status=ScheduleYearStatus.PUBLISHED)
    CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 6, 1), origin=Origin.OFFICIAL_IMPORT)
    from apps.addresses.models import StreetAssignment
    StreetAssignment.objects.create(street=setup["street"], zone=zone)

    public_id = setup["address_key"].public_id
    # ohne Filter: beide Arten sichtbar
    both = client.get(f"/a/{public_id}/").content.decode()
    assert "06.05.2030" in both and "01.06.2030" in both
    # nur Bioabfall
    only_bio = client.get(f"/a/{public_id}/?arten=bioabfall").content.decode()
    assert "01.06.2030" in only_bio and "06.05.2030" not in only_bio
    # zwei Arten explizit
    two = client.get(f"/a/{public_id}/?arten=bioabfall,gelber-sack").content.decode()
    assert "01.06.2030" in two and "06.05.2030" in two


def test_combined_feed_respects_arten_filter(client, setup):
    from datetime import date

    from apps.addresses.models import StreetAssignment
    from apps.core.models import Origin
    from apps.schedules.models import CollectionDate, CollectionZone, ScheduleYear, ScheduleYearStatus
    from apps.waste_types.models import WasteType

    bio = WasteType.objects.get(slug="bioabfall")
    bio.is_active = True
    bio.save()
    zone = CollectionZone.objects.create(waste_type=bio, code="B01")
    year = ScheduleYear.objects.create(waste_type=bio, year=2030, status=ScheduleYearStatus.PUBLISHED)
    CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 6, 1), origin=Origin.OFFICIAL_IMPORT)
    StreetAssignment.objects.create(street=setup["street"], zone=zone)

    public_id = setup["address_key"].public_id
    full = client.get(f"/calendar/address/{public_id}/all.ics").content.decode()
    assert full.count("BEGIN:VEVENT") == 2
    filtered = client.get(f"/calendar/address/{public_id}/all.ics?arten=bioabfall").content.decode()
    assert filtered.count("BEGIN:VEVENT") == 1
    assert "Bioabfall" in filtered and "Gelber Sack" not in filtered


def test_admin_dashboard(client, setup):
    """Eigene Admin-Startseite: KPIs + Bereichs-Erklärungen (nur für Staff)."""
    from apps.accounts.models import User

    assert client.get("/admin/").status_code == 302  # Login-Redirect
    staff = User.objects.create_user("chef", password="x", is_staff=True, is_superuser=True)
    client.force_login(staff)
    response = client.get("/admin/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Bereiche" in content and "Moderationsqueue" in content
    assert "Jahrespläne" in content and "Audit-Log" in content
