"""Audit log - track all changes."""
import uuid
from django.db import models
from django.conf import settings


class ChangeSet(models.Model):
    """Gruppiert zusammengehörige Änderungen."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    user_display = models.CharField(max_length=255, blank=True)
    action = models.CharField(max_length=50, verbose_name="Aktion")
    comment = models.TextField(blank=True, verbose_name="Kommentar")
    source = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = "Änderungssatz"
        verbose_name_plural = "Änderungssätze"

    def __str__(self):
        return f"{self.action} @ {self.timestamp}"


class AuditLog(models.Model):
    """Einzelner Audit-Eintrag."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    change_set = models.ForeignKey(
        ChangeSet, on_delete=models.CASCADE, related_name="entries",
    )
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255, blank=True)
    field_name = models.CharField(max_length=100, blank=True)
    old_value = models.TextField(blank=True)
    new_value = models.TextField(blank=True)

    class Meta:
        ordering = ["change_set__timestamp"]
        verbose_name = "Audit-Log-Eintrag"
        verbose_name_plural = "Audit-Log-Einträge"

    def __str__(self):
        return f"{self.model_name}#{self.object_id}: {self.field_name}"