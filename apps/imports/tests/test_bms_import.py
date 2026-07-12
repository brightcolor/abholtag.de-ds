"""Tests for the BMS (insert-it.de) street/house-number import."""

import json

import pytest
from django.core.management import call_command

from apps.addresses.models import City, HouseNumber, Street
from apps.core.models import Origin


@pytest.fixture
def bms_files(tmp_path):
    streets = [
        {"id": 3339, "name": "Beethovenstraße"},        # matcht "Beethovenstr."
        {"id": 3713, "name": "Geniner Ufer"},            # keine Hausnummern (404-Fall)
        {"id": 9999, "name": "Nagelneue Straße"},        # unbekannt → neu anlegen
        {"id": 11904, "name": "19/Anschlussstelle Sereetz"},  # ohne Hausnummern → inaktiv
    ]
    locations = [
        {"street_id": 3339, "street_name": "Beethovenstraße", "locations": [
            {"id": 100069, "house_number": "1"},
            {"id": 100070, "house_number": "6a"},
            {"id": 138278, "house_number": "21-31"},     # geteilte Location / Bereichstext
            {"id": 138278, "house_number": "33"},        # gleiche ID, andere Nummer (erlaubt)
        ]},
        {"street_id": 3713, "street_name": "Geniner Ufer", "locations": []},
        {"street_id": 9999, "street_name": "Nagelneue Straße", "locations": [
            {"id": 555, "house_number": "2"},
        ]},
        {"street_id": 11904, "street_name": "19/Anschlussstelle Sereetz", "locations": []},
    ]
    streets_path = tmp_path / "streets.json"
    locations_path = tmp_path / "locations.json"
    streets_path.write_text(json.dumps(streets, ensure_ascii=False), encoding="utf-8")
    locations_path.write_text(json.dumps(locations, ensure_ascii=False), encoding="utf-8")
    return streets_path, locations_path


@pytest.fixture
def existing_street(db):
    city = City.objects.create(name="Lübeck", slug="luebeck")
    return Street.objects.create(city=city, name="Beethovenstr.")


def run_import(bms_files):
    streets_path, locations_path = bms_files
    call_command("import_bms_addresses", streets=str(streets_path), locations=str(locations_path))


def test_matches_existing_street_via_normalization(bms_files, existing_street):
    run_import(bms_files)
    existing_street.refresh_from_db()
    assert existing_street.bms_street_id == 3339


def test_house_numbers_imported_with_parsing(bms_files, existing_street):
    run_import(bms_files)
    numbers = {hn.text: hn for hn in existing_street.house_numbers.all()}
    assert set(numbers) == {"1", "6a", "21-31", "33"}
    assert numbers["6a"].number == 6 and numbers["6a"].suffix == "a"
    assert numbers["21-31"].number is None  # Bereichstext wird roh gespeichert
    # geteilte Location-IDs sind zulässig (kein Unique-Constraint)
    assert numbers["21-31"].bms_location_id == numbers["33"].bms_location_id == 138278


def test_unknown_streets_created_with_origin(bms_files, existing_street):
    run_import(bms_files)
    new = Street.objects.get(name="Nagelneue Straße")
    assert new.origin == Origin.EXTERNAL_API
    assert new.is_active is True
    assert new.house_numbers.count() == 1


def test_streets_without_house_numbers_stay_inactive(bms_files, existing_street):
    run_import(bms_files)
    ramp = Street.objects.get(name="19/Anschlussstelle Sereetz")
    assert ramp.is_active is False
    assert Street.objects.get(name="Geniner Ufer").house_numbers.count() == 0


def test_reimport_is_idempotent(bms_files, existing_street):
    run_import(bms_files)
    run_import(bms_files)
    assert HouseNumber.objects.filter(street=existing_street).count() == 4
    assert Street.objects.filter(name="Nagelneue Straße").count() == 1
