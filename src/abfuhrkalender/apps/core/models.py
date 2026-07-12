"""Base models, mixins, and utilities for all apps."""
import uuid
from django.db import models
from django.utils import timezone


class TimeStampedMixin(models.Model):
    """Adds created_at and updated_at timestamp fields."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDMixin(models.Model):
    """UUID primary key for public-safe IDs."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class PublicIdMixin(models.Model):
    """Short public-facing ID for user reference (e.g., ERR-A3F2)."""
    public_id = models.CharField(max_length=20, unique=True, blank=True)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.public_id:
            self.public_id = self._generate_public_id()
        super().save(*args, **kwargs)

    def _generate_public_id(self):
        """Generate a short readable public ID."""
        import secrets
        import string
        chars = string.ascii_uppercase + string.digits
        prefix = self._get_prefix()
        suffix = ''.join(secrets.choice(chars) for _ in range(6))
        return f"{prefix}-{suffix}"

    def _get_prefix(self):
        """Override in subclass to set a custom prefix like 'ERR' or 'COR'."""
        return "GEN"


class SoftDeleteMixin(models.Model):
    """Adds soft-delete functionality."""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()


class VersionedMixin(models.Model):
    """Optimistic locking for concurrent edits."""
    version = models.IntegerField(default=1)

    class Meta:
        abstract = True


class SourceMixin(models.Model):
    """Tracks the origin of a data record."""
    SOURCE_CHOICES = [
        ("pdf_import", "Offizieller PDF-Import"),
        ("admin", "Administrator"),
        ("moderator", "Moderator"),
        ("citizen", "Bürgerbeitrag"),
        ("quorum", "Quorum"),
        ("external_api", "Externe API"),
        ("manual", "Manueller Import"),
    ]
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="admin")
    source_detail = models.CharField(max_length=255, blank=True)

    class Meta:
        abstract = True


class ValidityMixin(models.Model):
    """Validity period for time-limited data."""
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True


class StatusMixin(models.Model):
    """Basic active/inactive status."""
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True