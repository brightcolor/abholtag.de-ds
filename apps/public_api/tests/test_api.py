import json
from datetime import date

import pytest

from apps.addresses.models import City, Street, StreetAssignment
from apps.community.models import ErrorReport
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
    street = Street.objects.create(city=city, name="Beispielweg")
    waste_type = WasteType.objects.get(slug="gelber-sack")
    zone = CollectionZone.objects.create(waste_type=waste_type, code="A")
    StreetAssignment.objects.create(street=street, zone=zone)
    year = ScheduleYear.objects.create(
        waste_type=waste_type, year=2030, status=ScheduleYearStatus.PUBLISHED
    )
    CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 3, 4))
    return {"street": street}


def test_waste_types(client, db):
    data = client.get("/api/v1/waste-types").json()
    assert any(item["slug"] == "gelber-sack" for item in data["results"])


def test_street_search_and_resolve_flow(client, setup):
    data = client.get("/api/v1/streets?q=beispielw").json()
    assert data["results"][0]["name"] == "Beispielweg"
    street_id = data["results"][0]["id"]

    resolved = client.get(f"/api/v1/address/resolve?street_id={street_id}").json()
    assert resolved["zones"][0]["code"] == "A"

    collections = client.get(f"/api/v1/addresses/{resolved['public_id']}/collections").json()
    assert collections["count"] == 1
    assert collections["results"][0]["date"] == "2030-03-04"


def test_resolve_unknown_street_404(client, db):
    response = client.get("/api/v1/address/resolve?street=GibtEsNicht")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_zone_collections(client, setup):
    data = client.get("/api/v1/zones/A/collections?year=2030").json()
    assert data["count"] == 1


def test_create_report(client, db):
    payload = {"category": "wrong_date", "description": "Der Termin am 4.3. war falsch angegeben."}
    response = client.post(
        "/api/v1/reports", json.dumps(payload), content_type="application/json"
    )
    assert response.status_code == 201
    token = response.json()["token"]
    assert ErrorReport.objects.filter(public_token=token).exists()


def test_create_report_validation(client, db):
    response = client.post("/api/v1/reports", "{}", content_type="application/json")
    assert response.status_code == 400
