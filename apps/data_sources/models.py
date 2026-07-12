from django.db import models

from apps.core.models import TimeStampedModel


class SourceKind(models.TextChoices):
    PDF_URL = "pdf_url", "PDF-Abruf per URL"
    MANUAL = "manual", "Manuelle Pflege"
    COMMUNITY = "community", "Community-Erfassung"
    API = "api", "Externe API"


class DataSource(TimeStampedModel):
    """Where the data of a waste type comes from (§8, §14)."""

    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE, related_name="data_sources"
    )
    name = models.CharField("Name", max_length=150)
    kind = models.CharField("Art", max_length=20, choices=SourceKind.choices, default=SourceKind.PDF_URL)
    url = models.URLField("URL", blank=True)
    parser_key = models.CharField(
        "Parser", max_length=100, blank=True,
        help_text="Registrierter Parser-Schlüssel, z. B. „luebeck_gelber_sack“.",
    )
    check_interval_hours = models.PositiveIntegerField("Prüfintervall (Stunden)", default=24)
    is_active = models.BooleanField("Aktiv", default=True)

    last_checked_at = models.DateTimeField(null=True, blank=True, editable=False)
    last_status = models.CharField(max_length=200, blank=True, editable=False)
    last_etag = models.CharField(max_length=200, blank=True, editable=False)
    last_modified_header = models.CharField(max_length=100, blank=True, editable=False)
    last_sha256 = models.CharField(max_length=64, blank=True, editable=False)

    class Meta:
        verbose_name = "Datenquelle"
        verbose_name_plural = "Datenquellen"

    def __str__(self):
        return f"{self.name} ({self.waste_type.name})"


class DocumentStatus(models.TextChoices):
    ARCHIVED = "archived", "archiviert"
    ACTIVE = "active", "aktuelle Version"
    SUPERSEDED = "superseded", "abgelöst"


class SourceDocument(TimeStampedModel):
    """An archived original file (e.g. the yearly PDF) – §14 step 1."""

    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField("Datei", upload_to="source_documents/%Y/")
    sha256 = models.CharField(max_length=64, unique=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    content_type = models.CharField(max_length=100, blank=True)
    etag = models.CharField(max_length=200, blank=True)
    last_modified_header = models.CharField(max_length=100, blank=True)
    fetched_at = models.DateTimeField("Abgerufen am")
    page_count = models.PositiveIntegerField(null=True, blank=True)
    detected_year = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=DocumentStatus.choices, default=DocumentStatus.ACTIVE
    )

    class Meta:
        ordering = ["-fetched_at"]
        verbose_name = "Quelldokument"
        verbose_name_plural = "Quelldokumente"

    def __str__(self):
        return f"{self.data_source.name} – {self.fetched_at:%d.%m.%Y %H:%M}"
