import pytest

from apps.addresses.models import AssignmentStatus, City, Parity, Street, StreetAssignment
from apps.addresses.services import resolve_address, search_streets
from apps.schedules.models import CollectionZone
from apps.waste_types.models import WasteType


@pytest.fixture
def city(db):
    return City.objects.create(name="Testhausen", slug="testhausen")


@pytest.fixture
def waste_type(db):
    return WasteType.objects.get(slug="gelber-sack")


@pytest.fixture
def zones(waste_type):
    return {
        code: CollectionZone.objects.create(waste_type=waste_type, code=code) for code in ("A", "B")
    }


def make_street(city, name, **kwargs):
    return Street.objects.create(city=city, name=name, **kwargs)


def test_search_tolerates_spelling(city, zones):
    street = make_street(city, "Beispielstraße")
    StreetAssignment.objects.create(street=street, zone=zones["A"])
    assert street in search_streets("beispielstrasse")
    assert street in search_streets("Beispielstr.")


def test_simple_street_resolves_without_house_number(city, zones):
    street = make_street(city, "Ahornweg")
    StreetAssignment.objects.create(street=street, zone=zones["A"])
    result = resolve_address(street, None)
    assert result.ok
    assert [z.code for z in result.zones] == ["A"]


def test_ranged_street_requires_house_number(city, zones):
    street = make_street(city, "Lange Allee")
    StreetAssignment.objects.create(street=street, zone=zones["A"], house_from=1, house_to=50)
    StreetAssignment.objects.create(street=street, zone=zones["B"], house_from=51)
    result = resolve_address(street, None)
    assert not result.ok
    assert result.needs_house_number


def test_ranged_street_resolves_by_number_and_parity(city, zones):
    street = make_street(city, "Parity-Straße")
    StreetAssignment.objects.create(
        street=street, zone=zones["A"], house_from=1, house_to=99, parity=Parity.ODD
    )
    StreetAssignment.objects.create(
        street=street, zone=zones["B"], house_from=2, house_to=98, parity=Parity.EVEN
    )
    assert [z.code for z in resolve_address(street, 7).zones] == ["A"]
    assert [z.code for z in resolve_address(street, 8).zones] == ["B"]


def test_pending_assignments_do_not_resolve(city, zones):
    """Ambiguous imported ranges must never silently resolve (§10)."""
    street = make_street(city, "Unklare Straße")
    StreetAssignment.objects.create(
        street=street, zone=zones["A"], status=AssignmentStatus.PENDING, raw_range="1-32/43"
    )
    result = resolve_address(street, 10)
    assert not result.ok


def test_multi_zone_street_returns_both(city, zones):
    street = make_street(city, "Altstadtgasse")
    StreetAssignment.objects.create(street=street, zone=zones["A"])
    StreetAssignment.objects.create(street=street, zone=zones["B"])
    result = resolve_address(street, None)
    assert [z.code for z in result.zones] == ["A", "B"]


def test_address_key_is_stable(city, zones):
    street = make_street(city, "Stabile Straße")
    StreetAssignment.objects.create(street=street, zone=zones["A"])
    first = resolve_address(street, 12, "a").address_key
    second = resolve_address(street, 12, "a").address_key
    assert first.pk == second.pk
    assert first.public_id == second.public_id
