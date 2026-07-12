"""Addresses - streets, districts, assignments."""
import uuid
from django.db import models
from django.core.validators import RegexValidator
from apps.core.models import TimeStampedMixin, SourceMixin, ValidityMixin, StatusMixin


class District(models.Model):
    """Ortsteil in Lübeck."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, verbose_name="Name")
    search_name = models.CharField(max_length=100, blank=True, verbose_name="Suchname")
    postal_codes = models.CharField(max_length=255, blank=True, verbose_name="PLZ (kommasepariert)")

    class Meta:
        verbose_name = "Ortsteil"
        verbose_name_plural = "Ortsteile"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.search_name:
            import unicodedata
            self.search_name = unicodedata.normalize("NFKD", self.name.lower())\
                .encode("ascii", "ignore").decode()
        super().save(*args, **kwargs)


class Street(TimeStampedMixin, SourceMixin, ValidityMixin, StatusMixin):
    """Straße mit normalisierten Suchnamen."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Straßenname")
    search_name = models.CharField(max_length=255, blank=True, verbose_name="Normalisierter Suchname")
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Ortsteil", related_name="streets",
    )
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="PLZ")
    city = models.CharField(max_length=100, default="Lübeck", verbose_name="Stadt")
    has_number_ranges = models.BooleanField(default=True, verbose_name="Hat Hausnummernbereiche")
    notes = models.TextField(blank=True, verbose_name="Hinweise")
    version = models.IntegerField(default=1, verbose_name="Version")

    class Meta:
        verbose_name = "Straße"
        verbose_name_plural = "Straßen"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["search_name"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        district_str = f" ({self.district.name})" if self.district else ""
        return f"{self.name}{district_str}"

    def save(self, *args, **kwargs):
        if not self.search_name:
            import unicodedata
            self.search_name = Street.normalize_name(self.name)
        super().save(*args, **kwargs)

    @staticmethod
    def normalize_name(name):
        """Normalisiere Straßennamen für die Suche."""
        import unicodedata
        normalized = unicodedata.normalize("NFKD", name.lower())
        normalized = normalized.encode("ascii", "ignore").decode()
        normalized = normalized.replace("str.", "strasse")
        normalized = normalized.replace("str ", "strasse ")
        normalized = normalized.replace("sankt ", "st. ")
        normalized = normalized.replace("-", " ")
        normalized = " ".join(normalized.split())
        return normalized


class StreetAlias(models.Model):
    """Alternativname für eine Straße (z.B. 'Strasse' vs 'Straße')."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    street = models.ForeignKey(Street, on_delete=models.CASCADE, related_name="aliases")
    alias = models.CharField(max_length=255, verbose_name="Alternativname")
    search_alias = models.CharField(max_length=255, blank=True, verbose_name="Normalisierter Alias")

    class Meta:
        verbose_name = "Straßenalias"
        verbose_name_plural = "Straßenaliase"

    def __str__(self):
        return f"{self.alias} → {self.street.name}"

    def save(self, *args, **kwargs):
        if not self.search_alias:
            self.search_alias = Street.normalize_name(self.alias)
        super().save(*args, **kwargs)


class CollectionZone(models.Model):
    """Abfuhrbezirk (Tourenbuchstabe A-J)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    letter = models.CharField(
        max_length=5, verbose_name="Buchstabe",
        help_text="Einzelbuchstabe (A-J) oder Kombination (B/G)",
    )
    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE,
        related_name="zones", verbose_name="Abfallart",
    )
    name = models.CharField(max_length=100, blank=True, verbose_name="Name")
    is_active = models.BooleanField(default=True, verbose_name="Aktiv")

    class Meta:
        verbose_name = "Abfuhrbezirk"
        verbose_name_plural = "Abfuhrbezirke"
        unique_together = ["letter", "waste_type"]
        ordering = ["letter"]

    def __str__(self):
        return f"Bezirk {self.letter} ({self.waste_type.name})"


class StreetAssignment(TimeStampedMixin, SourceMixin):
    """Zuordnung einer Straße (mit Hausnummernbereich) zu einem Abfuhrbezirk."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    street = models.ForeignKey(
        Street, on_delete=models.CASCADE, related_name="assignments",
        verbose_name="Straße",
    )
    zone = models.ForeignKey(
        CollectionZone, on_delete=models.CASCADE, related_name="assignments",
        verbose_name="Abfuhrbezirk",
    )
    house_number_start = models.CharField(
        max_length=10, blank=True, verbose_name="Hausnummer von",
    )
    house_number_end = models.CharField(
        max_length=10, blank=True, verbose_name="Hausnummer bis",
    )
    house_number_parity = models.CharField(
        max_length=5, choices=[
            ("all", "Alle"), ("even", "Gerade"), ("odd", "Ungerade"),
        ],
        default="all", verbose_name="Hausnummern-Parität",
    )
    house_number_suffix = models.CharField(
        max_length=20, blank=True, verbose_name="Hausnummernzusatz",
    )
    location_note = models.CharField(max_length=255, blank=True, verbose_name="Ortshinweis")
    valid_from = models.DateField(null=True, blank=True, verbose_name="Gültig ab")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Gültig bis")
    override_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Überschreibt", related_name="overrides",
    )
    priority = models.IntegerField(default=0, verbose_name="Priorität")
    version = models.IntegerField(default=1)

    class Meta:
        verbose_name = "Straßenzuordnung"
        verbose_name_plural = "Straßenzuordnungen"
        indexes = [
            models.Index(fields=["street", "zone"]),
        ]

    def __str__(self):
        return f"{self.street.name} → {self.zone.letter}"


class AddressKey(models.Model):
    """Öffentlicher Adressschlüssel für stabile URLs über Jahre."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    public_id = models.CharField(max_length=20, unique=True, verbose_name="Öffentliche ID")
    street = models.ForeignKey(
        Street, on_delete=models.CASCADE, related_name="address_keys",
    )
    house_number = models.CharField(max_length=10, blank=True)
    house_number_suffix = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Adressschlüssel"
        verbose_name_plural = "Adressschlüssel"
        unique_together = ["street", "house_number", "house_number_suffix"]

    def __str__(self):
        return f"{self.street.name} {self.house_number}{self.house_number_suffix}"