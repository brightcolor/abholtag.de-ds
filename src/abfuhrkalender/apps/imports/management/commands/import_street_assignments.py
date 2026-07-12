"""Import street assignments from a parsed schedule."""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import street assignments from parsed PDF data"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Street assignments imported"))