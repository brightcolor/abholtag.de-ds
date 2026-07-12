from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class ModerationComment(TimeStampedModel):
    """Internal or public comment on a report or proposal (§27)."""

    report = models.ForeignKey(
        "community.ErrorReport", on_delete=models.CASCADE, null=True, blank=True,
        related_name="comments",
    )
    proposal = models.ForeignKey(
        "community.CorrectionProposal", on_delete=models.CASCADE, null=True, blank=True,
        related_name="comments",
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    is_public = models.BooleanField(
        "Öffentlich sichtbar", default=False,
        help_text="Öffentliche Kommentare erscheinen auf der Statusseite der Meldung.",
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Moderationskommentar"
        verbose_name_plural = "Moderationskommentare"

    def __str__(self):
        target = self.report or self.proposal
        return f"Kommentar zu {target}"
