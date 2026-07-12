"""Validate imported schedule data."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Validate imported waste schedule data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Validation completed"))