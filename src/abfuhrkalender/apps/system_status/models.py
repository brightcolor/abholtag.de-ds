"""System status monitoring."""
import uuid
from django.db import models


class SystemCheck(models.Model):
    """Ergebnis eines System-Checks."""
    STATUS_CHOICES = [
        ("ok", "OK"),
        ("warning", "Warnung"),
        ("error", "Fehler"),
        ("unknown", "Unbekannt"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    check_name = models.CharField(max_length=100)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="unknown")
    message = models.TextField(blank=True)
    checked_at = models.DateTimeField(auto_now=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "System-Check"
        verbose_name_plural = "System-Checks"
        ordering = ["-checked_at"]

    def __str__(self):
        return f"{self.check_name}: {self.get_status_display()}"