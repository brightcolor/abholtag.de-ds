from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ImportKind(models.TextChoices):
    SCHEDULE = "schedule", "Jahresplan"
    STREETS = "streets", "Straßenliste"
    FULL = "full", "Vollständig"


class ImportRunStatus(models.TextChoices):
    RUNNING = "running", "läuft"
    PARSE_FAILED = "parse_failed", "Verarbeitung fehlgeschlagen"
    VALIDATION_FAILED = "validation_failed", "Validierung fehlgeschlagen"
    NEEDS_REVIEW = "needs_review", "Prüfung erforderlich"
    COMPLETED = "completed", "abgeschlossen"
    REJECTED = "rejected", "verworfen"


class ImportRun(TimeStampedModel):
    """One parsing/import attempt of a source document (§14, §15)."""

    source_document = models.ForeignKey(
        "data_sources.SourceDocument", on_delete=models.CASCADE, related_name="import_runs",
        null=True, blank=True, verbose_name="Quelldokument",
    )
    parser_key = models.CharField("Parser", max_length=100)
    kind = models.CharField("Art", max_length=20, choices=ImportKind.choices, default=ImportKind.FULL)
    status = models.CharField(
        "Status", max_length=20, choices=ImportRunStatus.choices, default=ImportRunStatus.RUNNING
    )
    started_at = models.DateTimeField("Gestartet", auto_now_add=True)
    finished_at = models.DateTimeField("Beendet", null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    stats = models.JSONField(default=dict, blank=True)
    issues = models.JSONField(default=list, blank=True)
    diff = models.JSONField(default=dict, blank=True)
    log = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "Importlauf"
        verbose_name_plural = "Importläufe"

    def __str__(self):
        return f"Import #{self.pk} ({self.parser_key}, {self.get_status_display()})"

    @property
    def blocking_issues(self):
        return [i for i in self.issues if i.get("level") == "error"]

    @property
    def warning_issues(self):
        return [i for i in self.issues if i.get("level") == "warning"]
