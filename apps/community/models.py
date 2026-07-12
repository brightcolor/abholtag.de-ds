from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel, generate_token


class ReportCategory(models.TextChoices):
    WRONG_DATE = "wrong_date", "Falscher Termin"
    MISSING_DATE = "missing_date", "Fehlender Termin"
    WRONG_ZONE = "wrong_zone", "Falscher Abfuhrbezirk"
    WRONG_STREET_ASSIGNMENT = "wrong_street_assignment", "Falsche Straßenzuordnung"
    WRONG_HOUSE_RANGE = "wrong_house_range", "Falscher Hausnummernbereich"
    STREET_MISSING = "street_missing", "Straße fehlt"
    WRONG_DISTRICT = "wrong_district", "Falscher Ortsteil"
    IMPORT_ERROR = "import_error", "Fehlerhafter PDF-Import"
    FEED_BROKEN = "feed_broken", "Kalenderfeed funktioniert nicht"
    SHORT_NOTICE_CHANGE = "short_notice_change", "Kurzfristige Terminänderung"
    OTHER = "other", "Sonstiges Problem"


class ReportStatus(models.TextChoices):
    NEW = "new", "neu"
    DUPLICATE = "duplicate", "Duplikat"
    IN_REVIEW = "in_review", "in Prüfung"
    ANSWERED = "answered", "beantwortet"
    RESOLVED = "resolved", "gelöst"
    REJECTED = "rejected", "abgelehnt"


class ErrorReport(TimeStampedModel):
    """Citizen error report (§20)."""

    public_token = models.CharField(max_length=12, unique=True, default=generate_token, editable=False)
    category = models.CharField(max_length=40, choices=ReportCategory.choices)
    description = models.TextField("Beschreibung")
    source_hint = models.CharField("Quelle (optional)", max_length=255, blank=True)
    contact_email = models.EmailField("E-Mail für Rückfragen (optional)", blank=True)

    address_key = models.ForeignKey(
        "addresses.AddressKey", on_delete=models.SET_NULL, null=True, blank=True
    )
    street = models.ForeignKey("addresses.Street", on_delete=models.SET_NULL, null=True, blank=True)
    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.SET_NULL, null=True, blank=True
    )

    status = models.CharField(max_length=20, choices=ReportStatus.choices, default=ReportStatus.NEW)
    public_response = models.TextField("Öffentliche Antwort", blank=True)
    internal_note = models.TextField("Interne Notiz", blank=True)
    session_hash = models.CharField(max_length=32, blank=True, editable=False)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Fehlermeldung"
        verbose_name_plural = "Fehlermeldungen"

    def __str__(self):
        return f"{self.public_token} – {self.get_category_display()}"


class ProposalKind(models.TextChoices):
    DATE_MOVE = "date_move", "Termin verschieben"
    DATE_ADD = "date_add", "Termin hinzufügen"
    DATE_REMOVE = "date_remove", "Termin entfernen"
    ZONE_CHANGE = "zone_change", "Tourenbuchstaben ändern"
    HOUSE_RANGE_CHANGE = "house_range_change", "Hausnummernbereich ändern"
    STREET_ADD = "street_add", "Straße ergänzen"
    DISTRICT_FIX = "district_fix", "Ortsteil korrigieren"
    SPELLING_FIX = "spelling_fix", "Schreibweise ändern"
    NOTE = "note", "Hinweis"


class ProposalStatus(models.TextChoices):
    """Lifecycle of citizen proposals (§31)."""

    DRAFT = "draft", "Entwurf"
    SUBMITTED = "submitted", "eingereicht"
    DUPLICATE = "duplicate", "Duplikat"
    AWAITING_CONFIRMATION = "awaiting_confirmation", "wartet auf Bestätigungen"
    QUORUM_REACHED = "quorum_reached", "Quorum erreicht"
    UNDER_REVIEW = "under_review", "in Prüfung"
    ACCEPTED = "accepted", "angenommen"
    PARTIALLY_ACCEPTED = "partially_accepted", "teilweise angenommen"
    REJECTED = "rejected", "abgelehnt"
    PUBLISHED = "published", "umgesetzt"
    WITHDRAWN = "withdrawn", "zurückgezogen"
    SUPERSEDED = "superseded", "durch offiziellen Import überholt"


class CorrectionProposal(TimeStampedModel):
    """Structured correction proposal (§21)."""

    kind = models.CharField(max_length=30, choices=ProposalKind.choices)
    status = models.CharField(
        max_length=30, choices=ProposalStatus.choices, default=ProposalStatus.SUBMITTED
    )

    street = models.ForeignKey("addresses.Street", on_delete=models.SET_NULL, null=True, blank=True)
    zone = models.ForeignKey("schedules.CollectionZone", on_delete=models.SET_NULL, null=True, blank=True)
    collection_date = models.ForeignKey(
        "schedules.CollectionDate", on_delete=models.SET_NULL, null=True, blank=True
    )
    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.SET_NULL, null=True, blank=True
    )

    old_value = models.JSONField("Bisheriger Wert", default=dict, blank=True)
    new_value = models.JSONField("Vorgeschlagener Wert", default=dict, blank=True)
    reason = models.TextField("Begründung")
    source_url = models.URLField("Quelle (optional)", blank=True)
    contact_email = models.EmailField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="proposals",
    )
    session_hash = models.CharField(max_length=32, blank=True, editable=False)
    confirmations = models.PositiveIntegerField(default=0, editable=False)
    objections = models.PositiveIntegerField(default=0, editable=False)

    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="decided_proposals",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Korrekturvorschlag"
        verbose_name_plural = "Korrekturvorschläge"

    def __str__(self):
        return f"#{self.pk} {self.get_kind_display()} ({self.get_status_display()})"


class ProposalVote(TimeStampedModel):
    """Independent confirmation/objection of a proposal (§22).

    session_hash prevents trivial repeated anonymous voting; registered
    users are deduplicated by account.
    """

    proposal = models.ForeignKey(CorrectionProposal, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    session_hash = models.CharField(max_length=32)
    is_support = models.BooleanField(default=True)
    comment = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("proposal", "session_hash")]
        verbose_name = "Bestätigung"
        verbose_name_plural = "Bestätigungen"


class QuorumRule(TimeStampedModel):
    """Configurable quorum per waste type and change kind (§22)."""

    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE, null=True, blank=True,
        help_text="Leer = gilt für alle Abfallarten.",
    )
    change_kind = models.CharField(max_length=30, choices=ProposalKind.choices)
    min_confirmations = models.PositiveIntegerField("Benötigte Bestätigungen", default=5)
    max_objection_ratio = models.FloatField(
        "Maximaler Gegenstimmen-Anteil", default=0.25,
        help_text="0.25 = Quorum scheitert, wenn mehr als 25 % Gegenstimmen vorliegen.",
    )
    requires_source = models.BooleanField("Quelle erforderlich", default=False)
    window_days = models.PositiveIntegerField("Zeitfenster (Tage)", default=30)
    auto_publish = models.BooleanField(
        "Automatisch veröffentlichen", default=False,
        help_text="Nur wirksam, wenn der Community-Modus global aktiviert ist (§22).",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Quorum-Regel"
        verbose_name_plural = "Quorum-Regeln"

    def __str__(self):
        scope = self.waste_type.name if self.waste_type else "alle Abfallarten"
        return f"{self.get_change_kind_display()} ({scope}): {self.min_confirmations} Bestätigungen"


class ContributionStatus(models.TextChoices):
    SUBMITTED = "submitted", "eingereicht"
    ACCEPTED = "accepted", "übernommen"
    REJECTED = "rejected", "abgelehnt"
    EXPIRED = "expired", "verfallen"


class CommunityContribution(TimeStampedModel):
    """Structured community data entry for the fallback mode (§24)."""

    waste_type = models.ForeignKey("waste_types.WasteType", on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    date = models.DateField(null=True, blank=True)
    zone_code = models.CharField(max_length=10, blank=True)
    street_text = models.CharField("Straße", max_length=150, blank=True)
    district_text = models.CharField("Ortsteil", max_length=100, blank=True)
    house_range = models.CharField("Hausnummernbereich", max_length=100, blank=True)
    note = models.TextField("Anmerkung", blank=True)
    source_hint = models.CharField("Quelle", max_length=255, blank=True)
    evidence = models.FileField(
        "Beleg (Foto/Dokument)", upload_to="community_evidence/%Y/", null=True, blank=True
    )
    contact_email = models.EmailField(blank=True)
    session_hash = models.CharField(max_length=32, blank=True, editable=False)
    status = models.CharField(
        max_length=20, choices=ContributionStatus.choices, default=ContributionStatus.SUBMITTED
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Community-Beitrag"
        verbose_name_plural = "Community-Beiträge"

    def __str__(self):
        return f"{self.waste_type} {self.year} {self.zone_code} {self.date or ''}"
