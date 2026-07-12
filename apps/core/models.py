import secrets

from django.db import models

PUBLIC_ID_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"  # unambiguous, lowercase


def generate_public_id(length: int = 12) -> str:
    return "".join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(length))


def generate_token(length: int = 10) -> str:
    return "".join(secrets.choice(PUBLIC_ID_ALPHABET.upper() + "0123456789") for _ in range(length))


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Origin(models.TextChoices):
    """Provenance of a data record (§23 of the specification)."""

    OFFICIAL_IMPORT = "official_import", "Offizieller PDF-Import"
    ADMIN = "admin", "Administrator"
    MODERATOR = "moderator", "Moderator"
    CITIZEN = "citizen", "Bürgerbeitrag"
    QUORUM = "quorum", "Quorum-bestätigt"
    EXTERNAL_API = "external_api", "Externe API"
    MANUAL_IMPORT = "manual_import", "Manueller Import"
