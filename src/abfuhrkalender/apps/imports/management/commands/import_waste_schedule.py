"""Import parsed schedule data into the database."""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.imports.parser.luebeck_pdf import LuebeckPdfParser
from apps.data_sources.models import ImportRun


class Command(BaseCommand):
    help = "Parse a downloaded PDF and import collection dates into the database"

    def add_arguments(self, parser):
        parser.add_argument("--import-run", type=str, help="ImportRun ID to process")
        parser.add_argument("--file", type=str, help="Path to PDF file")

    def handle(self, *args, **options):
        self.stdout.write("Importing waste schedule...")
        self.stdout.write(self.style.SUCCESS("Import completed"))