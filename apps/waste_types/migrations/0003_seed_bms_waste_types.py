"""Seeds the waste types served by the EBL online calendar (BMS/insert-it.de).

They are created inactive: the address master data (streets, house numbers,
bmsLocationIds) is already imported, the per-zone schedule pipeline for these
types is the next step (docs/ROADMAP.md). Activating them is an admin decision.
"""

from django.db import migrations

BMS_TYPES = [
    {
        "slug": "restabfall",
        "name": "Restabfall",
        "icon": "fas fa-trash-can",
        "color": "#4b5563",
        "sort_order": 20,
        "description": "Leerung der grauen Restabfalltonne (Quelle: EBL-Online-Abfallkalender).",
        "ics_summary": "Restabfall",
    },
    {
        "slug": "bioabfall",
        "name": "Bioabfall",
        "icon": "fas fa-leaf",
        "color": "#92400e",
        "sort_order": 30,
        "description": "Leerung der braunen Biotonne (Quelle: EBL-Online-Abfallkalender).",
        "ics_summary": "Bioabfall",
    },
    {
        "slug": "papier",
        "name": "Papier (PPK)",
        "icon": "fas fa-newspaper",
        "color": "#2563eb",
        "sort_order": 40,
        "description": "Leerung der blauen Papiertonne (Quelle: EBL-Online-Abfallkalender).",
        "ics_summary": "Papiertonne",
    },
]


def seed(apps, schema_editor):
    WasteType = apps.get_model("waste_types", "WasteType")
    for spec in BMS_TYPES:
        WasteType.objects.get_or_create(
            slug=spec["slug"],
            defaults={
                **spec,
                "is_active": False,
                "ics_description": "Abholung für {address}. Bitte rechtzeitig bereitstellen.",
            },
        )


def unseed(apps, schema_editor):
    WasteType = apps.get_model("waste_types", "WasteType")
    WasteType.objects.filter(slug__in=[t["slug"] for t in BMS_TYPES]).delete()


class Migration(migrations.Migration):
    dependencies = [("waste_types", "0002_seed_gelber_sack")]
    operations = [migrations.RunPython(seed, unseed)]
