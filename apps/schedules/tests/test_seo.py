from datetime import date

import pytest

from apps.addresses.models import City, Street, StreetAssignment
from apps.schedules.models import (
    CollectionDate,
    CollectionZone,
    ScheduleYear,
    ScheduleYearStatus,
)
from apps.waste_types.models import WasteType


@pytest.fixture
def seo_setup(db):
    city = City.objects.create(name="Lübeck", slug="luebeck")
    street = Street.objects.create(city=city, name="Beethovenstr.")
    waste_type = WasteType.objects.get(slug="gelber-sack")
    zone = CollectionZone.objects.create(waste_type=waste_type, code="A")
    StreetAssignment.objects.create(street=street, zone=zone)
    year = ScheduleYear.objects.create(waste_type=waste_type, year=2030, status=ScheduleYearStatus.PUBLISHED)
    CollectionDate.objects.create(schedule_year=year, zone=zone, date=date(2030, 5, 6))
    return street


def test_street_gets_slug_on_save(seo_setup):
    assert seo_setup.slug == "beethovenstr"


def test_street_index(client, seo_setup):
    response = client.get("/strassen/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Beethovenstr." in content
    assert "/strasse/beethovenstr/" in content


def test_street_index_search(client, seo_setup):
    response = client.get("/strassen/?q=beethoven")
    assert "Beethovenstr." in response.content.decode()


def test_street_page(client, seo_setup):
    response = client.get("/strasse/beethovenstr/")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Abfuhrtermine Beethovenstr." in content
    assert "BreadcrumbList" in content
    assert '<link rel="canonical"' in content


def test_street_page_404(client, db):
    assert client.get("/strasse/gibt-es-nicht/").status_code == 404


def test_street_without_assignment_404(client, db):
    city = City.objects.create(name="Lübeck", slug="luebeck")
    Street.objects.create(city=city, name="Leerweg")
    assert client.get("/strasse/leerweg/").status_code == 404


def test_street_house_dependent_only_noindex(client, seo_setup):
    city = seo_setup.city
    street = Street.objects.create(city=city, name="Teilweg")
    zone = CollectionZone.objects.get(code="A")
    StreetAssignment.objects.create(street=street, zone=zone, house_from=1, house_to=20)
    response = client.get("/strasse/teilweg/")
    content = response.content.decode()
    assert response.status_code == 200
    assert 'name="robots" content="noindex' in content


def test_sitemap(client, seo_setup):
    response = client.get("/sitemap.xml")
    content = response.content.decode()
    assert response.status_code == 200
    assert "/strasse/beethovenstr/" in content
    assert "/strassen/" in content


def test_robots_txt(client, db):
    response = client.get("/robots.txt")
    content = response.content.decode()
    assert response.status_code == 200
    assert "Disallow: /admin/" in content
    assert "Sitemap:" in content


def test_home_has_seo_schema(client, db):
    content = client.get("/").content.decode()
    assert "FAQPage" in content
    assert "SearchAction" in content
    assert "og:image" in content


def test_address_pages_noindex(client, seo_setup):
    from apps.addresses.models import AddressKey

    key = AddressKey.objects.create(street=seo_setup)
    content = client.get(f"/a/{key.public_id}/").content.decode()
    assert 'name="robots" content="noindex' in content


def test_indexnow_key_route(client, db, settings):
    settings.INDEXNOW_KEY = "abc123"
    assert client.get("/abc123.txt").content == b"abc123"
    assert client.get("/wrong.txt").status_code == 404
