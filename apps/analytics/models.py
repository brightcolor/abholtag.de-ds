from django.db import models


class EventType(models.TextChoices):
    """Analytics events (§17.1)."""

    PAGE_VIEW = "page_view", "Seitenaufruf"
    STREET_SEARCH = "street_search", "Straßensuche"
    STREET_SEARCH_NO_RESULT = "street_search_no_result", "Suche ohne Ergebnis"
    ADDRESS_RESOLVED = "address_resolved", "Adresse aufgelöst"
    SCHEDULE_VIEW = "schedule_view", "Terminansicht"
    CALENDAR_SUBSCRIPTION_PAGE_VIEW = "calendar_subscription_page_view", "Abo-Seite"
    CALENDAR_FEED_REQUESTED = "calendar_feed_requested", "Kalenderfeed abgerufen"
    CALENDAR_DOWNLOADED = "calendar_downloaded", "Kalender heruntergeladen"
    ERROR_REPORT_OPENED = "error_report_opened", "Fehlerformular geöffnet"
    ERROR_REPORT_SUBMITTED = "error_report_submitted", "Fehlermeldung abgesendet"
    CORRECTION_SUBMITTED = "correction_submitted", "Korrektur vorgeschlagen"
    PROPOSAL_CONFIRMED = "proposal_confirmed", "Vorschlag bestätigt"
    COMMUNITY_ENTRY_SUBMITTED = "community_entry_submitted", "Community-Eintrag"


class AnalyticsEvent(models.Model):
    """A single privacy friendly usage event (§17, §19).

    No IP addresses, no persistent user identifiers – only a daily rotating
    session hash and coarse device/browser classes are stored. Raw events are
    purged after ANALYTICS_RAW_RETENTION_DAYS (see purge_old_analytics).
    """

    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    session_hash = models.CharField(max_length=32, blank=True)

    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.SET_NULL, null=True, blank=True
    )
    street = models.ForeignKey("addresses.Street", on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey("addresses.District", on_delete=models.SET_NULL, null=True, blank=True)
    address_key = models.ForeignKey(
        "addresses.AddressKey", on_delete=models.SET_NULL, null=True, blank=True
    )
    year = models.PositiveIntegerField(null=True, blank=True)

    device_class = models.CharField(max_length=20, blank=True)
    browser_family = models.CharField(max_length=30, blank=True)
    calendar_client = models.CharField(max_length=50, blank=True)
    referrer_domain = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=30, blank=True)
    query = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Nutzungsereignis"
        verbose_name_plural = "Nutzungsereignisse"
        indexes = [models.Index(fields=["event_type", "created_at"])]

    def __str__(self):
        return f"{self.event_type} @ {self.created_at:%d.%m.%Y %H:%M}"


class AnalyticsAggregate(models.Model):
    """Daily aggregates that are kept long-term after raw events are purged."""

    date = models.DateField(db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    dimension = models.CharField(
        max_length=150,
        default="total",
        help_text="z. B. total, district:12, street:1023, waste:gelber-sack, client:Google Kalender",
    )
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("date", "event_type", "dimension")]
        verbose_name = "Aggregat"
        verbose_name_plural = "Aggregate"

    def __str__(self):
        return f"{self.date} {self.event_type} {self.dimension}: {self.count}"
