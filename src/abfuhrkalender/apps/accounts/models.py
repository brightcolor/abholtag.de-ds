"""Custom User model with role-based permissions."""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Manager für benutzerdefinierte User mit E-Mail als Identifier."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("E-Mail-Adresse ist erforderlich")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", User.Role.ADMINISTRATOR)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Erweiterter Benutzer mit Rollen und Vertrauensniveau."""

    class Role(models.TextChoices):
        CITIZEN = "citizen", _("Bürger")
        VERIFIED = "verified", _("Verifizierter Nutzer")
        MODERATOR = "moderator", _("Moderator")
        DATA_MANAGER = "data_manager", _("Datenmanager")
        ANALYST = "analyst", _("Analyst")
        AUDITOR = "auditor", _("Auditor")
        ADMINISTRATOR = "administrator", _("Administrator")

    username = None  # Remove username, use email
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("E-Mail-Adresse"), unique=True)
    display_name = models.CharField(_("Anzeigename"), max_length=100, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITIZEN,
        verbose_name=_("Rolle"),
    )
    trust_level = models.IntegerField(
        default=0,
        verbose_name=_("Vertrauensniveau"),
        help_text=_("Steigt durch bestätigte Beiträge"),
    )
    is_two_factor_enabled = models.BooleanField(
        default=False,
        verbose_name=_("Zwei-Faktor-Authentifizierung"),
    )
    accepted_contributions = models.IntegerField(default=0)
    rejected_contributions = models.IntegerField(default=0)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _("Benutzer")
        verbose_name_plural = _("Benutzer")
        ordering = ["-date_joined"]

    def __str__(self):
        return self.display_name or self.email

    @property
    def is_administrator(self):
        return self.role == self.Role.ADMINISTRATOR or self.is_superuser

    @property
    def is_moderator(self):
        return self.role in (self.Role.MODERATOR, self.Role.DATA_MANAGER, self.Role.ADMINISTRATOR)

    @property
    def can_edit_data(self):
        return self.role in (self.Role.DATA_MANAGER, self.Role.ADMINISTRATOR)

    @property
    def can_view_analytics(self):
        return self.role in (
            self.Role.ANALYST, self.Role.DATA_MANAGER,
            self.Role.ADMINISTRATOR, self.Role.AUDITOR,
        )

    def increment_trust(self, points=1):
        """Erhöht Vertrauensniveau bei erfolgreichen Beiträgen."""
        self.trust_level += points
        self.accepted_contributions += 1
        self.save(update_fields=["trust_level", "accepted_contributions"])

    def decrement_trust(self, points=1):
        """Verringert Vertrauensniveau bei abgelehnten Beiträgen."""
        self.trust_level = max(0, self.trust_level - points)
        self.rejected_contributions += 1
        self.save(update_fields=["trust_level", "rejected_contributions"])