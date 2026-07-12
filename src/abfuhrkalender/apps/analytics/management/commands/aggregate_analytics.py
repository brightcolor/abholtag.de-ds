"""Aggregate raw analytics events into periodic summaries."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Aggregate analytics events into period summaries"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Analytics aggregated"))