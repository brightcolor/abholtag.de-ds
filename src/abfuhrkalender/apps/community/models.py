"""Community - error reports, correction proposals, voting."""
import uuid
from django.db import models
from django.conf import settings
from apps.core.models import TimeStampedMixin, PublicIdMixin


class ErrorReport(TimeStampedMixin, PublicIdMixin):
    """Fehlermeldung durch Bürger."""
    CATEGORY_CHOICES = [
        ("wrong_date", "Falscher Termin"),
        ("missing_date", "Fehlender Termin"),
        ("wrong_zone", "Falscher Abfuhrbezirk"),
        ("wrong_street_assignment", "Falsche Straßenzuordnung"),
        ("wrong_number_range", "Falscher Hausnummernbereich"),
        ("street_missing", "Straße fehlt"),
        ("wrong_district", "Falscher Ortsteil"),
        ("pdf_import_error", "Fehlerhafter PDF-Import"),
        ("calendar_feed_broken", "Kalenderfeed funktioniert nicht"),
        ("short_term_change", "Kurzfristige Terminänderung"),
        ("other", "Sonstiges Problem"),
    ]
    STATUS_CHOICES = [
        ("new", "Neu"),
        ("under_review", "In Prüfung"),
        ("accepted", "Angenommen"),
        ("rejected", "Abgelehnt"),
        ("duplicate", "Duplikat"),
        ("resolved", "Gelöst"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, verbose_name="Kategorie")
    affected_street = models.ForeignKey(
        "addresses.Street", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Betroffene Straße",
    )
    affected_date = models.ForeignKey(
        "schedules.CollectionDate", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Betroffener Termin",
    )
    description = models.TextField(verbose_name="Beschreibung")
    suggested_correction = models.TextField(blank=True, verbose_name="Korrekturvorschlag")
    source_info = models.TextField(blank=True, verbose_name="Quellenangabe")
    reporter_email = models.EmailField(
        blank=True, verbose_name="E-Mail (optional für Rückfragen)",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="new")
    duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Duplikat von",
    )
    moderator_comment = models.TextField(blank=True, verbose_name="Moderatoren-Kommentar")
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Fehlermeldung"
        verbose_name_plural = "Fehlermeldungen"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.public_id}: {self.get_category_display()}"

    def _get_prefix(self):
        return "FRM"


class CorrectionProposal(TimeStampedMixin, PublicIdMixin):
    """Strukturierter Korrekturvorschlag."""
    TARGET_CHOICES = [
        ("collection_date", "Abfuhrtermin"),
        ("zone", "Abfuhrbezirk"),
        ("street_assignment", "Straßenzuordnung"),
        ("street", "Straße"),
        ("district", "Ortsteil"),
        ("house_number_range", "Hausnummernbereich"),
    ]
    STATUS_CHOICES = [
        ("new", "Neu"),
        ("duplicate", "Duplikat"),
        ("awaiting_confirmation", "Bestätigungen ausstehend"),
        ("under_review", "In Prüfung"),
        ("accepted", "Angenommen"),
        ("partially_accepted", "Teilweise angenommen"),
        ("rejected", "Abgelehnt"),
        ("implemented", "Umgesetzt"),
        ("superseded", "Durch Import überholt"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Ersteller",
    )
    target_type = models.CharField(
        max_length=30, choices=TARGET_CHOICES, verbose_name="Zieltyp",
    )
    target_id = models.UUIDField(null=True, blank=True, verbose_name="Ziel-ID")
    old_value = models.JSONField(default=dict, blank=True, verbose_name="Alter Wert")
    new_value = models.JSONField(default=dict, verbose_name="Neuer Wert")
    reason = models.TextField(verbose_name="Begründung")
    source = models.TextField(blank=True, verbose_name="Quelle")
    confidence = models.IntegerField(default=5, verbose_name="Vertrauensstufe (1-10)")
    status = models.CharField(
        max_length=25, choices=STATUS_CHOICES, default="new",
    )
    votes_needed = models.IntegerField(default=3, verbose_name="Benötigte Bestätigungen")
    votes_yes = models.IntegerField(default=1, verbose_name="Positive Stimmen")
    votes_no = models.IntegerField(default=0, verbose_name="Negative Stimmen")
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="moderated_proposals",
        verbose_name="Moderator",
    )
    moderator_decision = models.TextField(blank=True, verbose_name="Entscheidungsbegründung")
    similar_proposals = models.ManyToManyField(
        "self", blank=True, verbose_name="Ähnliche Vorschläge",
    )
    error_report = models.ForeignKey(
        ErrorReport, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Zugehörige Fehlermeldung",
    )

    class Meta:
        verbose_name = "Korrekturvorschlag"
        verbose_name_plural = "Korrekturvorschläge"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.public_id}: {self.get_target_type_display()}"

    def _get_prefix(self):
        return "KOR"


class ProposalVote(TimeStampedMixin):
    """Abstimmung über einen Korrekturvorschlag (Quorum)."""
    VOTE_CHOICES = [("yes", "Dafür"), ("no", "Dagegen")]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    proposal = models.ForeignKey(
        CorrectionProposal, on_delete=models.CASCADE, related_name="votes",
    )
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    session_key = models.CharField(max_length=255, blank=True, verbose_name="Session (anonym)")
    vote = models.CharField(max_length=5, choices=VOTE_CHOICES, verbose_name="Stimme")
    weight = models.IntegerField(default=1, verbose_name="Gewichtung")

    class Meta:
        verbose_name = "Abstimmung"
        verbose_name_plural = "Abstimmungen"
        unique_together = [["proposal", "voter"], ["proposal", "session_key"]]

    def __str__(self):
        return f"{self.get_vote_display()} für {self.proposal.public_id}"


class QuorumRule(models.Model):
    """Quorum-Regeln je Abfallart und Änderungstyp."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE,
        related_name="quorum_rules",
    )
    target_type = models.CharField(
        max_length=30, choices=CorrectionProposal.TARGET_CHOICES,
    )
    min_votes = models.IntegerField(default=3, verbose_name="Minimale Stimmen")
    min_independent_voters = models.IntegerField(
        default=3, verbose_name="Min. unabhängige Abstimmende",
    )
    voting_period_days = models.IntegerField(default=14, verbose_name="Abstimmungszeitraum (Tage)")
    requires_source = models.BooleanField(default=False, verbose_name="Quelle erforderlich")
    min_confidence = models.IntegerField(default=1, verbose_name="Min. Vertrauensniveau")

    class Meta:
        verbose_name = "Quorum-Regel"
        verbose_name_plural = "Quorum-Regeln"
        unique_together = ["waste_type", "target_type"]

    def __str__(self):
        return f"{self.waste_type.name} - {self.get_target_type_display()}: {self.min_votes} Stimmen"


class CommunityContribution(TimeStampedMixin, PublicIdMixin):
    """Community-Erfassung von Terminen (Fallback-Modus)."""
    STATUS_CHOICES = [
        ("draft", "Entwurf"),
        ("submitted", "Eingereicht"),
        ("duplicate", "Duplikat"),
        ("awaiting_confirmation", "Bestätigungen ausstehend"),
        ("quorum_reached", "Quorum erreicht"),
        ("under_review", "In Prüfung"),
        ("accepted", "Angenommen"),
        ("partially_accepted", "Teilweise angenommen"),
        ("rejected", "Abgelehnt"),
        ("published", "Veröffentlicht"),
        ("withdrawn", "Zurückgezogen"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waste_type = models.ForeignKey(
        "waste_types.WasteType", on_delete=models.CASCADE,
        verbose_name="Abfallart",
    )
    year = models.IntegerField(verbose_name="Jahr")
    collection_date = models.DateField(verbose_name="Abfuhrdatum")
    zone = models.ForeignKey(
        "addresses.CollectionZone", on_delete=models.CASCADE,
        verbose_name="Abfuhrbezirk",
    )
    street = models.ForeignKey(
        "addresses.Street", on_delete=models.CASCADE, verbose_name="Straße",
    )
    house_number_start = models.CharField(max_length=10, blank=True)
    house_number_end = models.CharField(max_length=10, blank=True)
    source = models.TextField(blank=True, verbose_name="Quelle")
    notes = models.TextField(blank=True, verbose_name="Anmerkungen")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default="draft")
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    image = models.FileField(
        upload_to="community/%Y/", blank=True, verbose_name="Foto/Beleg",
    )

    class Meta:
        verbose_name = "Community-Beitrag"
        verbose_name_plural = "Community-Beiträge"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.public_id}: {self.street.name} am {self.collection_date}"

    def _get_prefix(self):
        return "COM"