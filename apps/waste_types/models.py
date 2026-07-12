from django.db import models

from apps.core.models import TimeStampedModel


class WasteType(TimeStampedModel):
    """A collectable waste stream (Gelber Sack, Papier, Restmüll, …) – §8."""

    name = models.CharField("Name", max_length=100, unique=True)
    slug = models.SlugField("Slug", max_length=100, unique=True)
    icon = models.CharField("Icon (Font-Awesome-Klasse)", max_length=100, default="fas fa-trash")
    color = models.CharField("Farbe (Hex)", max_length=9, default="#f2c200")
    description = models.TextField("Beschreibung", blank=True)
    is_active = models.BooleanField("Aktiv", default=True)
    sort_order = models.PositiveIntegerField("Sortierung", default=0)

    # iCalendar texts (§12); templates may use {address} and {city}
    ics_summary = models.CharField("ICS-Titel", max_length=100, blank=True)
    ics_description = models.TextField(
        "ICS-Beschreibung",
        blank=True,
        default="Abholung für {address}. Bitte rechtzeitig bereitstellen.",
    )
    reminder_hours_before = models.PositiveIntegerField(
        "Erinnerung (Stunden vorher, 0 = keine)", default=0
    )

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "Abfallart"
        verbose_name_plural = "Abfallarten"

    def __str__(self):
        return self.name

    @property
    def calendar_summary(self) -> str:
        return self.ics_summary or self.name
