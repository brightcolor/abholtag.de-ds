"""Data sources - track import runs and source files."""
import uuid
from django.db import models
from django.conf import settings


class DataSource(models.Model):
    """Datenquelle (PDF, API, manuell)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Name")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    source_type = models.CharField(
        max_length=20, choices=[
            ("pdf_url", "PDF-URL"),
            ("api", "API"),
            ("manual", "Manuelle Eingabe"),
            ("community", "Community-Erfassung"),
        ],
        verbose_name="Quellentyp",
    )
    url = models.URLField(blank=True, verbose_name="URL")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    parser_class = models.CharField(max_length=255, blank=True, verbose_name="Parser-Klasse")
    config = models.JSONField(default=dict, blank=True, verbose_name="Konfiguration")

    class Meta:
        verbose_name = "Datenquelle"
        verbose_name_plural = "Datenquellen"

    def __str__(self):
        return self.name


class ImportRun(models.Model):
    """Ein Import-Durchlauf einer Datenquelle."""
    STATUS_CHOICES = [
        ("pending", "Ausstehend"),
        ("downloading", "Lädt herunter"),
        ("downloaded", "Heruntergeladen"),
        ("parsing", "Wird verarbeitet"),
        ("parsed", "Verarbeitet"),
        ("validating", "Wird validiert"),
        ("validated", "Validiert"),
        ("failed", "Fehlgeschlagen"),
        ("cancelled", "Abgebrochen"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name="import_runs",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    file_hash = models.CharField(max_length=64, blank=True, verbose_name="SHA-256")
    file_path = models.TextField(blank=True, verbose_name="Dateipfad")
    file_size = models.IntegerField(null=True, blank=True, verbose_name="Dateigröße")
    detected_year = models.IntegerField(null=True, blank=True, verbose_name="Erkanntes Jahr")
    parser_version = models.CharField(max_length=20, blank=True)
    etag = models.CharField(max_length=255, blank=True)
    last_modified = models.CharField(max_length=100, blank=True)
    error_log = models.JSONField(default=list, blank=True)
    stats = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Import-Durchlauf"
        verbose_name_plural = "Import-Durchläufe"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.data_source.name} #{self.id}"