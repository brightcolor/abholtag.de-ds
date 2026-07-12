from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.analytics.models import AnalyticsAggregate, AnalyticsEvent


class Command(BaseCommand):
    help = "Verdichtet Roh-Ereignisse zu Tagesaggregaten (§19)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=3, help="Zeitraum rückwirkend in Tagen.")

    def handle(self, *args, **options):
        since = date.today() - timedelta(days=options["days"])
        events = AnalyticsEvent.objects.filter(created_at__date__gte=since)
        written = 0

        def upsert(day, event_type, dimension, count):
            nonlocal written
            AnalyticsAggregate.objects.update_or_create(
                date=day, event_type=event_type, dimension=dimension[:150], defaults={"count": count}
            )
            written += 1

        # totals per day/event type
        for row in events.values("created_at__date", "event_type").annotate(n=Count("id")):
            upsert(row["created_at__date"], row["event_type"], "total", row["n"])

        # dimension breakdowns
        breakdowns = [
            ("district", "district_id", "district:{}"),
            ("street", "street_id", "street:{}"),
            ("waste_type", "waste_type__slug", "waste:{}"),
            ("client", "calendar_client", "client:{}"),
            ("device", "device_class", "device:{}"),
            ("noresult", "query", "noresult:{}"),
        ]
        for label, field, template in breakdowns:
            queryset = events.exclude(**{f"{field}__isnull": True}) if "_id" in field else events
            queryset = queryset.exclude(**{field: ""}) if "_id" not in field else queryset
            if label == "noresult":
                queryset = queryset.filter(event_type="street_search_no_result")
            for row in queryset.values("created_at__date", "event_type", field).annotate(n=Count("id")):
                value = row[field]
                if value in (None, ""):
                    continue
                upsert(row["created_at__date"], row["event_type"], template.format(value), row["n"])

        self.stdout.write(self.style.SUCCESS(f"{written} Aggregate aktualisiert."))
