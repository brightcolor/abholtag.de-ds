"""Seeds the first waste type (Gelber Sack) and its official data source."""

from django.db import migrations

OFFICIAL_URL = "https://entsorgung.luebeck.de/files/Abfuhrplan/abfuhrplan-gelber-sack-luebeck.pdf"


def seed(apps, schema_editor):
    WasteType = apps.get_model("waste_types", "WasteType")
    DataSource = apps.get_model("data_sources", "DataSource")

    waste_type, _ = WasteType.objects.get_or_create(
        slug="gelber-sack",
        defaults={
            "name": "Gelber Sack",
            "icon": "fas fa-recycle",
            "color": "#f2c200",
            "description": (
                "Abholung der Gelben Säcke (Verkaufsverpackungen) alle 14 Tage. "
                "Säcke am Abfuhrtag bis 6:00 Uhr am Straßenrand bereitstellen."
            ),
            "sort_order": 10,
            "ics_summary": "Gelber Sack",
            "ics_description": (
                "Abholung des Gelben Sacks für {address}. "
                "Bitte bis 6:00 Uhr bereitstellen."
            ),
        },
    )
    DataSource.objects.get_or_create(
        waste_type=waste_type,
        kind="pdf_url",
        url=OFFICIAL_URL,
        defaults={
            "name": "Offizieller Abfuhrplan (entsorgung.luebeck.de)",
            "parser_key": "luebeck_gelber_sack",
            "check_interval_hours": 24,
        },
    )


def unseed(apps, schema_editor):
    WasteType = apps.get_model("waste_types", "WasteType")
    WasteType.objects.filter(slug="gelber-sack").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("waste_types", "0001_initial"),
        ("data_sources", "0001_initial"),
    ]

    operations = [migrations.RunPython(seed, unseed)]
