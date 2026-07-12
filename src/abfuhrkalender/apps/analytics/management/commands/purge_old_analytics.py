"""Purge analytics events older than retention period."""
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.analytics.models import AnalyticsEvent
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Purge old analytics events"

    def handle(self, *args, **options):
        retention = getattr(settings, "ANALYTICS_RETENTION_DAYS", 90)
        cutoff = timezone.now() - timedelta(days=retention)
        deleted, _ = AnalyticsEvent.objects.filter(timestamp__lt=cutoff).delete()
        self.stdout.write(self.style.SUCCESS(f"Purged {deleted} old events"))