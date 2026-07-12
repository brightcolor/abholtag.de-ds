"""Management command to fetch the waste source PDF.

Checks the remote PDF URL for updates, downloads if changed,
and creates an ImportRun record.
"""
import hashlib
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.data_sources.models import DataSource, ImportRun


class Command(BaseCommand):
    help = "Fetch the waste collection source PDF and check for updates"

    def add_arguments(self, parser):
        parser.add_argument("--url", type=str, default=settings.PDF_GELBER_SACK_URL)
        parser.add_argument("--force", action="store_true", help="Force download even if unchanged")

    def handle(self, *args, **options):
        url = options["url"]
        force = options["force"]

        self.stdout.write(f"Checking {url}...")

        # HEAD request to check status
        try:
            head = requests.head(url, timeout=30, headers={"User-Agent": "Abfuhrkalender-Luebeck/1.0"})
            head.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"HEAD failed: {e}"))
            return

        etag = head.headers.get("ETag", "")
        last_modified = head.headers.get("Last-Modified", "")
        content_length = head.headers.get("Content-Length", "0")

        self.stdout.write(f"  ETag: {etag}")
        self.stdout.write(f"  Last-Modified: {last_modified}")
        self.stdout.write(f"  Size: {content_length} bytes")

        # Get or create data source
        source, _ = DataSource.objects.get_or_create(
            slug="gelber-sack-pdf",
            defaults={
                "name": "Gelber Sack PDF (Entsorgung Lübeck)",
                "source_type": "pdf_url",
                "url": url,
                "is_active": True,
            },
        )

        # Check if we already have this version
        last_run = ImportRun.objects.filter(
            data_source=source, status="downloaded"
        ).order_by("-created_at").first()

        if last_run and last_run.etag == etag and not force:
            self.stdout.write(self.style.SUCCESS("No changes detected. Skipping."))
            return

        # Download the file
        self.stdout.write("Downloading...")
        try:
            response = requests.get(url, timeout=60, headers={"User-Agent": "Abfuhrkalender-Luebeck/1.0"})
            response.raise_for_status()
        except requests.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Download failed: {e}"))
            return

        content = response.content
        sha256 = hashlib.sha256(content).hexdigest()

        self.stdout.write(f"  SHA-256: {sha256}")
        self.stdout.write(f"  Size: {len(content)} bytes")

        # Create import run
        import_run = ImportRun.objects.create(
            data_source=source,
            status="downloaded",
            file_hash=sha256,
            file_size=len(content),
            etag=etag,
            last_modified=last_modified,
        )

        # Save file
        import os
        from django.conf import settings
        media_root = settings.MEDIA_ROOT
        file_dir = os.path.join(media_root, "imports", "pdf")
        os.makedirs(file_dir, exist_ok=True)
        file_path = os.path.join(file_dir, f"gelber-sack-{sha256[:12]}.pdf")
        with open(file_path, "wb") as f:
            f.write(content)

        import_run.file_path = file_path
        import_run.save(update_fields=["file_path"])

        self.stdout.write(self.style.SUCCESS(f"Downloaded and saved to {file_path}"))
        self.stdout.write(self.style.SUCCESS(f"ImportRun #{import_run.id} created"))