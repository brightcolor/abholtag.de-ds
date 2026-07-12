"""Seed initial data for development."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.waste_types.models import WasteType
from apps.addresses.models import District, CollectionZone
from apps.data_sources.models import DataSource


class Command(BaseCommand):
    help = "Seed initial development data"

    def handle(self, *args, **options):
        self.stdout.write("Seeding initial data...")

        # Create waste types
        gelber_sack, _ = WasteType.objects.get_or_create(
            slug="gelber-sack",
            defaults={"name": "Gelber Sack", "color_hex": "#F9A825", "icon_name": "bi-trash3", "sort_order": 1},
        )

        # Create data source
        DataSource.objects.get_or_create(
            slug="gelber-sack-pdf",
            defaults={
                "name": "Gelber Sack PDF (Entsorgung Lübeck)",
                "source_type": "pdf_url",
                "url": "https://entsorgung.luebeck.de/files/Abfuhrplan/abfuhrplan-gelber-sack-luebeck.pdf",
            },
        )

        # Create collection zones A-J
        for letter in "ABCDEFGHIJ":
            CollectionZone.objects.get_or_create(
                letter=letter, waste_type=gelber_sack,
                defaults={"name": f"Bezirk {letter}"},
            )

        # Create superuser
        User = get_user_model()
        User.objects.get_or_create(
            email="admin@luebeck.de",
            defaults={
                "display_name": "Admin",
                "role": "administrator",
                "is_staff": True,
                "is_superuser": True,
            },
        )

        self.stdout.write(self.style.SUCCESS("Seed data created!"))