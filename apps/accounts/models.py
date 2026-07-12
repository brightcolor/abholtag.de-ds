from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    """Custom user model – roles are mapped to Django groups (§29)."""

    class Meta:
        verbose_name = "Benutzer"
        verbose_name_plural = "Benutzer"


class UserTrustProfile(TimeStampedModel):
    """Reputation of registered contributors (§28, §22)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="trust_profile")
    score = models.FloatField(default=0.0)
    accepted_count = models.PositiveIntegerField(default=0)
    rejected_count = models.PositiveIntegerField(default=0)
    last_contribution_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Vertrauensprofil"
        verbose_name_plural = "Vertrauensprofile"

    def __str__(self):
        return f"Vertrauen {self.user.username}: {self.score:.1f}"
