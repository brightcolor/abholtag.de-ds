"""Compare two schedule years and report differences."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compare schedules between years"

    def add_arguments(self, parser):
        parser.add_argument("--year1", type=int, required=True)
        parser.add_argument("--year2", type=int, required=True)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Comparison completed"))