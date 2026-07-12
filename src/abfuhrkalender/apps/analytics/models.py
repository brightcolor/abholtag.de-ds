"""Analytics - privacy-friendly usage statistics."""
import uuid
from django.db import models
from django.conf import settings


class AnalyticsEvent(models.Model):
    """Einzelnes Analytics-Ereignis (Rohdaten, temporär)."""
    EVENT_TYPES = [
        ("page_view", "Seitenaufruf"),
        ("street_search", "Straßensuche"),
        ("street_search_no_result", "Suche ohne Ergebnis"),
        ("address_resolved", "Adresse aufgelöst"),
        ("schedule_view", "Terminansicht"),
        ("calendar_subscription_page_view", "Kalender-Abo-Seite"),
        ("calendar_feed_requested", "Kalender-Feed abgerufen"),
        ("calendar_downloaded", "Kalender heruntergeladen"),
        ("error_report_opened", "Fehlermeldung geöffnet"),
        ("error_report_submitted", "Fehlermeldung eingereicht"),
        ("correction_submitted", "Korrektur eingereicht"),
        ("proposal_confirmed", "Vorschlag bestätigt"),
        ("community_entry_submitted", "Community-Beitrag eingereicht"),
    ]
    DEVICE_CLASSES = [
        ("desktop", "Desktop"), ("tablet", "Tablet"), ("mobile", "Mobil"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    session_hash = models.CharField(max_length=64, blank=True, db_index=True)
    district_id = models.CharField(max_length=50, blank=True)
    street_id = models.CharField(max_length=50, blank=True)
    address_key_id = models.CharField(max_length=50, blank=True)
    waste_type_slug = models.CharField(max_length=50, blank=True)
    calendar_year = models.IntegerField(null=True, blank=True)
    device_class = models.CharField(max_length=10, choices=DEVICE_CLASSES, blank=True)
    browser_family = models.CharField(max_length=50, blank=True)
    referrer_host = models.CharField(max_length=255, blank=True)
    result_status = models.CharField(max_length=20, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Analytics-Ereignis"
        verbose_name_plural = "Analytics-Ereignisse"
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.event_type} @ {self.timestamp}"


class AnalyticsAggregate(models.Model):
    """Aggregierte Daten für Langzeitspeicherung."""
    PERIOD_CHOICES = [("hour", "Stündlich"), ("day", "Täglich"), ("week", "Wöchentlich"), ("month", "Monatlich")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    period_start = models.DateTimeField()
    event_type = models.CharField(max_length=40, blank=True)
    district_id = models.CharField(max_length=50, blank=True)
    street_id = models.CharField(max_length=50, blank=True)
    waste_type_slug = models.CharField(max_length=50, blank=True)
    count = models.IntegerField(default=0)
    unique_sessions = models.IntegerField(default=0)
    data = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Aggregierte Daten"
        verbose_name_plural = "Aggregierte Daten"
        indexes = [
            models.Index(fields=["period", "period_start"]),
        ]

    def __str__(self):
        return f"{self.event_type} {self.period} @ {self.period_start}"