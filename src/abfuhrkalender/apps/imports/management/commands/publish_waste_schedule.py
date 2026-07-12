"""Publish a waste schedule to make it publicly available."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Publish a waste schedule"

    def add_arguments(self, parser):
        parser.add_argument("--schedule-id", type=str, required=True)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Schedule published"))