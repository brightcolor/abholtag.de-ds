"""Submit URLs to IndexNow (Bing, Seznam, Naver, Yandex) for instant indexing."""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.addresses.models import AssignmentStatus, Street


class Command(BaseCommand):
    help = "Meldet alle öffentlichen URLs per IndexNow an Suchmaschinen (Bing & Co.)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        import requests

        key = getattr(settings, "INDEXNOW_KEY", "")
        if not key:
            raise CommandError("INDEXNOW_KEY ist nicht gesetzt (Umgebungsvariable).")
        base = settings.SITE_BASE_URL.rstrip("/")
        host = base.replace("https://", "").replace("http://", "")

        urls = [f"{base}/", f"{base}/strassen/", f"{base}/status/"]
        urls += [
            f"{base}/strasse/{slug}/"
            for slug in Street.objects.filter(is_active=True, assignments__status=AssignmentStatus.ACTIVE)
            .exclude(slug__isnull=True)
            .distinct()
            .values_list("slug", flat=True)
        ]
        self.stdout.write(f"{len(urls)} URLs vorbereitet.")
        if options["dry_run"]:
            return

        # IndexNow erlaubt bis zu 10.000 URLs pro POST
        payload = {
            "host": host,
            "key": key,
            "keyLocation": f"{base}/{key}.txt",
            "urlList": urls,
        }
        response = requests.post(
            "https://api.indexnow.org/indexnow",
            json=payload,
            timeout=30,
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        self.stdout.write(self.style.SUCCESS(f"IndexNow: HTTP {response.status_code}"))
        if response.status_code not in (200, 202):
            self.stderr.write(response.text[:500])
