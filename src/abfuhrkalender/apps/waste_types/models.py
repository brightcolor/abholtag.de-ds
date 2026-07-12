"""Waste types - Abfallarten (Gelber Sack, Papier, Restmüll...)."""
import uuid
from django.db import models
from django.utils.text import slugify


class WasteType(models.Model):
    """Abfallart wie Gelber Sack, Papier, Restmüll, Biomüll."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Name")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    icon_name = models.CharField(max_length=50, default="bi-trash", verbose_name="Icon")
    color_hex = models.CharField(max_length=7, default="#6c757d", verbose_name="Farbe (Hex)")
    sort_order = models.IntegerField(default=0, verbose_name="Sortierung")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")
    has_collection_zones = models.BooleanField(default=True, verbose_name="Hat Abfuhrbezirke")
    quorum_config = models.JSONField(default=dict, blank=True, verbose_name="Quorum-Konfiguration")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Abfallart"
        verbose_name_plural = "Abfallarten"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)