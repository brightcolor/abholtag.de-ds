from django.db import models

from apps.core.models import Origin, TimeStampedModel, generate_public_id
from apps.core.text import normalize_street_name


class City(TimeStampedModel):
    name = models.CharField("Name", max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = "Stadt"
        verbose_name_plural = "Städte"

    def __str__(self):
        return self.name


class District(TimeStampedModel):
    """Ortsteil (e.g. Krummesse, Travemünde)."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="districts")
    name = models.CharField("Name", max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        unique_together = [("city", "slug")]
        ordering = ["name"]
        verbose_name = "Ortsteil"
        verbose_name_plural = "Ortsteile"

    def __str__(self):
        return self.name


class Street(TimeStampedModel):
    """Master data street record (§6) – never overwritten by imports."""

    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name="streets", verbose_name="Stadt")
    district = models.ForeignKey(
        District, on_delete=models.SET_NULL, null=True, blank=True, related_name="streets",
        verbose_name="Ortsteil",
    )
    name = models.CharField("Name", max_length=150)
    normalized_name = models.CharField(max_length=150, db_index=True, editable=False)
    postal_code = models.CharField("PLZ", max_length=5, blank=True)
    note = models.CharField("Hinweis", max_length=255, blank=True)
    origin = models.CharField(
        "Herkunft", max_length=30, choices=Origin.choices, default=Origin.OFFICIAL_IMPORT
    )
    is_active = models.BooleanField("Aktiv", default=True)
    # ID im Online-Abfallkalender der EBL (insert-it.de); nicht unique, weil
    # Ortsteil-Varianten derselben physischen Straße dieselbe BMS-ID tragen.
    bms_street_id = models.IntegerField(
        "BMS-Straßen-ID", null=True, blank=True, db_index=True,
        help_text="Straßen-ID im Online-Abfallkalender (insert-it.de).",
    )
    slug = models.SlugField(
        "URL-Slug", max_length=180, unique=True, null=True, blank=True,
        help_text="Für die öffentliche Straßen-Seite (/strasse/<slug>/).",
    )

    class Meta:
        ordering = ["name"]
        indexes = [models.Index(fields=["city", "normalized_name"])]
        verbose_name = "Straße"
        verbose_name_plural = "Straßen"

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_street_name(self.name)
        if not self.slug:
            self.slug = self.build_slug()
        super().save(*args, **kwargs)

    def build_slug(self) -> str:
        from django.utils.text import slugify

        base = slugify(self.name)
        if self.district:
            base = f"{base}-{slugify(self.district.name)}"
        slug, counter = base, 2
        while Street.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug[:180]

    def __str__(self):
        if self.district:
            return f"{self.name} ({self.district.name})"
        return self.name


class HouseNumber(TimeStampedModel):
    """Official house numbers of a street from the EBL online calendar (BMS).

    `bms_location_id` addresses the per-address calendar at insert-it.de and
    is NOT unique: several house numbers can share one location (e.g. a common
    waste collection point for Achternhof 21–31).
    """

    street = models.ForeignKey(
        Street, on_delete=models.CASCADE, related_name="house_numbers", verbose_name="Straße"
    )
    text = models.CharField("Hausnummer", max_length=20)
    number = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    suffix = models.CharField(max_length=10, blank=True, default="")
    bms_location_id = models.IntegerField("BMS-Location-ID", db_index=True)
    origin = models.CharField(
        "Herkunft", max_length=30, choices=Origin.choices, default=Origin.EXTERNAL_API
    )

    class Meta:
        unique_together = [("street", "text")]
        ordering = ["number", "suffix", "text"]
        verbose_name = "Hausnummer"
        verbose_name_plural = "Hausnummern"

    def __str__(self):
        return f"{self.street.name} {self.text}"


class StreetAlias(TimeStampedModel):
    """Alternative spellings that should resolve to the same street."""

    street = models.ForeignKey(Street, on_delete=models.CASCADE, related_name="aliases")
    name = models.CharField("Alternative Schreibweise", max_length=150)
    normalized_name = models.CharField(max_length=150, db_index=True, editable=False)

    class Meta:
        verbose_name = "Straßen-Alias"
        verbose_name_plural = "Straßen-Aliasse"

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_street_name(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} → {self.street.name}"


class Parity(models.TextChoices):
    ALL = "all", "alle Hausnummern"
    ODD = "odd", "ungerade"
    EVEN = "even", "gerade"


class AssignmentStatus(models.TextChoices):
    ACTIVE = "active", "aktiv"
    PENDING = "pending", "in Prüfung"
    RETIRED = "retired", "außer Kraft"


class StreetAssignment(TimeStampedModel):
    """Maps a street (or a house number range of it) to a collection zone (§6).

    A street may have several assignments: multiple zones (e.g. B/G in the
    Lübeck old town) or different zones per house number range.
    """

    street = models.ForeignKey(
        Street, on_delete=models.CASCADE, related_name="assignments", verbose_name="Straße"
    )
    zone = models.ForeignKey(
        "schedules.CollectionZone", on_delete=models.PROTECT, related_name="assignments",
        verbose_name="Bezirk",
    )
    house_from = models.PositiveIntegerField("Hausnummer von", null=True, blank=True)
    house_to = models.PositiveIntegerField("Hausnummer bis (leer = offen)", null=True, blank=True)
    parity = models.CharField("Seite", max_length=5, choices=Parity.choices, default=Parity.ALL)
    raw_range = models.CharField(
        "Original-Bereichsangabe", max_length=255, blank=True,
        help_text="Unveränderte Bereichsangabe aus der Quelle, z. B. „1-32/43“.",
    )
    note = models.CharField("Hinweis", max_length=255, blank=True)
    origin = models.CharField(
        "Herkunft", max_length=30, choices=Origin.choices, default=Origin.OFFICIAL_IMPORT
    )
    status = models.CharField(
        "Status", max_length=10, choices=AssignmentStatus.choices,
        default=AssignmentStatus.ACTIVE,
    )
    valid_from = models.DateField("Gültig ab", null=True, blank=True)
    valid_to = models.DateField("Gültig bis", null=True, blank=True)

    class Meta:
        ordering = ["street__name", "house_from"]
        verbose_name = "Tourenzuordnung"
        verbose_name_plural = "Tourenzuordnungen"

    def __str__(self):
        span = ""
        if self.house_from is not None:
            span = f" {self.house_from}-{self.house_to or 'Ende'} ({self.get_parity_display()})"
        return f"{self.street.name}{span} → {self.zone.code}"

    def matches(self, house_number: int | None) -> bool:
        """True if the given house number falls into this assignment."""
        if self.status != AssignmentStatus.ACTIVE:
            return False
        if self.house_from is None:
            return True
        if house_number is None:
            return False
        if self.parity == Parity.ODD and house_number % 2 == 0:
            return False
        if self.parity == Parity.EVEN and house_number % 2 == 1:
            return False
        if house_number < self.house_from:
            return False
        if self.house_to is not None and house_number > self.house_to:
            return False
        return True


class AddressKey(TimeStampedModel):
    """Stable public identifier for one resolved address (§12).

    The public_id is used in calendar feed URLs and must stay stable over
    years – it therefore never encodes internal database ids.
    """

    public_id = models.CharField(max_length=16, unique=True, default=generate_public_id, editable=False)
    street = models.ForeignKey(Street, on_delete=models.CASCADE, related_name="address_keys")
    house_number = models.PositiveIntegerField(null=True, blank=True)
    suffix = models.CharField(max_length=5, blank=True, default="")

    class Meta:
        unique_together = [("street", "house_number", "suffix")]
        verbose_name = "Adressschlüssel"
        verbose_name_plural = "Adressschlüssel"

    def __str__(self):
        return self.label

    @property
    def label(self) -> str:
        number = f" {self.house_number}{self.suffix}" if self.house_number else ""
        return f"{self.street.name}{number}"

    @property
    def full_label(self) -> str:
        district = f", {self.street.district.name}" if self.street.district else ""
        return f"{self.label}{district}, {self.street.city.name}"
