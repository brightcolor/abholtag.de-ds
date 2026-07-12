from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.analytics.models import AnalyticsEvent


class Command(BaseCommand):
    help = "Löscht Roh-Ereignisse nach Ablauf der Aufbewahrungsfrist (§19). Aggregate bleiben erhalten."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days", type=int, default=None,
            help="Aufbewahrungsfrist in Tagen (Standard: ANALYTICS_RAW_RETENTION_DAYS).",
        )

    def handle(self, *args, **options):
        days = options["days"] or settings.ANALYTICS_RAW_RETENTION_DAYS
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AnalyticsEvent.objects.filter(created_at__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"{deleted} Roh-Ereignisse älter als {days} Tage gelöscht."))
