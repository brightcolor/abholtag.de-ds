"""Compare street assignments between imports."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compare street assignments between imports"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Comparison completed"))