from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ChangeSet(TimeStampedModel):
    """Groups related audit entries into one reviewable unit (§30)."""

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField("Begründung", max_length=255, blank=True)
    source = models.CharField("Quelle", max_length=50, blank=True)

    class Meta:
        verbose_name = "Änderungspaket"
        verbose_name_plural = "Änderungspakete"

    def __str__(self):
        return f"ChangeSet #{self.pk} ({self.created_at:%d.%m.%Y %H:%M})"


class AuditAction(models.TextChoices):
    CREATE = "create", "angelegt"
    UPDATE = "update", "geändert"
    DELETE = "delete", "gelöscht"


class AuditLog(models.Model):
    """Immutable change log for curated models (§25, §34)."""

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=10, choices=AuditAction.choices)
    model_label = models.CharField(max_length=100, db_index=True)
    object_pk = models.CharField(max_length=64)
    object_repr = models.CharField(max_length=255)
    before = models.JSONField(null=True, blank=True)
    after = models.JSONField(null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    changeset = models.ForeignKey(
        ChangeSet, on_delete=models.SET_NULL, null=True, blank=True, related_name="entries"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Audit-Eintrag"
        verbose_name_plural = "Audit-Einträge"

    def __str__(self):
        return f"{self.model_label}#{self.object_pk} {self.get_action_display()}"
