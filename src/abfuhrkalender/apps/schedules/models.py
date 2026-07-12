"""Schedules - collection dates, schedule years."""
import uuid
from django.db import models
from apps.core.models import TimeStampedMixin, SourceMixin


class ScheduleYear(TimeStampedMixin):
    """Jahresplan für eine Abfallart."""
    PUBLICATION_STATUS = [
        ("discovered", "Entdeckt"),
        ("downloaded", "Heruntergeladen"),
        ("parsing", "Wird verarbeitet"),
        ("parse_failed", "Verarbeitung fehlgeschlagen"),
        ("parsed", "Verarbeitet"),
        ("validation_failed", "Validierung fehlgeschlagen"),
        ("needs_review", "Benötigt Prüfung"),
        ("approved", "Freigegeben"),
        ("published", "Veröffentlicht"),
        ("superseded", "Ersetzt"),
        ("withdrawn", "Zurückgezogen"),
        ("archived", "Archiviert"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE,
        related_name="schedule_years", verbose_name="Abfallart",
    )
    year = models.IntegerField(verbose_name="Jahr")
    status = models.CharField(
        max_length=20, choices=PUBLICATION_STATUS, default="discovered",
        verbose_name="Status",
    )
    import_run = models.ForeignKey(
        "data_sources.ImportRun", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="schedule_years",
        verbose_name="Import-Durchlauf",
    )
    published_at = models.DateTimeField(null=True, blank=True, verbose_name="Veröffentlicht am")
    superseded_by = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Ersetzt durch", related_name="superseded_years",
    )
    notes = models.TextField(blank=True, verbose_name="Anmerkungen")
    statistics = models.JSONField(default=dict, blank=True, verbose_name="Statistiken")

    class Meta:
        verbose_name = "Jahresplan"
        verbose_name_plural = "Jahrespläne"
        unique_together = ["waste_type", "year"]
        ordering = ["-year"]

    def __str__(self):
        return f"{self.waste_type.name} {self.year} ({self.get_status_display()})"


class CollectionDate(TimeStampedMixin, SourceMixin):
    """Einzelner Abfuhrtermin."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    schedule_year = models.ForeignKey(
        ScheduleYear, on_delete=models.CASCADE,
        related_name="collection_dates", verbose_name="Jahresplan",
    )
    zone = models.ForeignKey(
        "addresses.CollectionZone", on_delete=models.CASCADE,
        related_name="collection_dates", verbose_name="Abfuhrbezirk",
    )
    collection_date = models.DateField(verbose_name="Abfuhrdatum")
    is_special = models.BooleanField(default=False, verbose_name="Sondertermin")
    note = models.TextField(blank=True, verbose_name="Hinweis")
    manual_override = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Manuelle Überschreibung", related_name="overridden_dates",
    )

    class Meta:
        verbose_name = "Abfuhrtermin"
        verbose_name_plural = "Abfuhrtermine"
        ordering = ["collection_date"]
        indexes = [
            models.Index(fields=["collection_date"]),
            models.Index(fields=["zone", "collection_date"]),
            models.Index(fields=["schedule_year", "zone"]),
        ]

    def __str__(self):
        return f"{self.collection_date} - Bezirk {self.zone.letter}"