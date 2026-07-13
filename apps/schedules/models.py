from django.db import models

from apps.core.models import Origin, TimeStampedModel


class CollectionZone(TimeStampedModel):
    """Tour / Abfuhrbezirk, e.g. letter A–J for the Gelber Sack (§6)."""

    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE, related_name="zones",
        verbose_name="Abfallart",
    )
    code = models.CharField("Kennung", max_length=10)
    name = models.CharField("Name", max_length=100, blank=True)
    description = models.TextField("Beschreibung", blank=True)
    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        unique_together = [("waste_type", "code")]
        ordering = ["waste_type", "code"]
        verbose_name = "Abfuhrbezirk"
        verbose_name_plural = "Abfuhrbezirke"

    def __str__(self):
        return f"{self.waste_type.name} – Bezirk {self.code}"


class ScheduleYearStatus(models.TextChoices):
    """Lifecycle of a yearly plan (§31)."""

    DISCOVERED = "discovered", "entdeckt"
    DOWNLOADED = "downloaded", "heruntergeladen"
    PARSING = "parsing", "wird verarbeitet"
    PARSE_FAILED = "parse_failed", "Verarbeitung fehlgeschlagen"
    PARSED = "parsed", "verarbeitet"
    VALIDATION_FAILED = "validation_failed", "Validierung fehlgeschlagen"
    NEEDS_REVIEW = "needs_review", "Prüfung erforderlich"
    APPROVED = "approved", "freigegeben"
    PUBLISHED = "published", "veröffentlicht"
    SUPERSEDED = "superseded", "abgelöst"
    WITHDRAWN = "withdrawn", "zurückgezogen"
    ARCHIVED = "archived", "archiviert"


class ScheduleYear(TimeStampedModel):
    """One waste type's plan for one calendar year (§7)."""

    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE, related_name="schedule_years",
        verbose_name="Abfallart",
    )
    year = models.PositiveIntegerField("Kalenderjahr")
    status = models.CharField(
        "Status", max_length=20, choices=ScheduleYearStatus.choices,
        default=ScheduleYearStatus.DISCOVERED,
    )
    source_document = models.ForeignKey(
        "data_sources.SourceDocument", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="schedule_years", verbose_name="Quelldokument",
    )
    import_run = models.ForeignKey(
        "imports.ImportRun", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="schedule_years", verbose_name="Importlauf",
    )
    published_at = models.DateTimeField("Veröffentlicht am", null=True, blank=True)
    notes = models.TextField("Interne Notizen", blank=True)

    class Meta:
        unique_together = [("waste_type", "year")]
        ordering = ["-year"]
        verbose_name = "Jahresplan"
        verbose_name_plural = "Jahrespläne"

    def __str__(self):
        return f"{self.waste_type.name} {self.year} ({self.get_status_display()})"

    @property
    def is_public(self) -> bool:
        return self.status == ScheduleYearStatus.PUBLISHED


class CollectionDateKind(models.TextChoices):
    REGULAR = "regular", "regulär"
    SHIFTED = "shifted", "verschoben (Feiertag)"
    SPECIAL = "special", "Sondertermin"


class CollectionDate(TimeStampedModel):
    """A single collection day for one zone (§7)."""

    schedule_year = models.ForeignKey(
        ScheduleYear, on_delete=models.CASCADE, related_name="dates", verbose_name="Jahresplan"
    )
    zone = models.ForeignKey(
        CollectionZone, on_delete=models.CASCADE, related_name="dates", verbose_name="Bezirk"
    )
    date = models.DateField("Datum", db_index=True)
    kind = models.CharField(
        "Art", max_length=10, choices=CollectionDateKind.choices,
        default=CollectionDateKind.REGULAR,
    )
    note = models.CharField("Hinweis", max_length=255, blank=True)
    origin = models.CharField(
        "Herkunft", max_length=30, choices=Origin.choices, default=Origin.OFFICIAL_IMPORT
    )
    is_cancelled = models.BooleanField("Entfällt", default=False)
    sequence = models.PositiveIntegerField(default=0, help_text="ICS SEQUENCE, wird bei Änderungen erhöht.")

    class Meta:
        unique_together = [("schedule_year", "zone", "date")]
        ordering = ["date"]
        verbose_name = "Abfuhrtermin"
        verbose_name_plural = "Abfuhrtermine"

    def __str__(self):
        return f"{self.date} – {self.zone}"

    def save(self, *args, **kwargs):
        # Bump the ICS sequence whenever an existing date record changes so
        # calendar clients pick up moved/cancelled events (§12).
        if self.pk:
            self.sequence += 1
        super().save(*args, **kwargs)
