"""Automatic audit logging for curated data models.

The actor is taken from thread-local context set by middleware-free helper
`audit_context` (management commands) or from Django admin via
`LogEntry`-independent signal capture. Values are serialised snapshots.
"""

import threading

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict

_local = threading.local()

TRACKED_MODELS = {
    "waste_types.WasteType",
    "addresses.Street",
    "addresses.StreetAlias",
    "addresses.StreetAssignment",
    "addresses.District",
    "schedules.CollectionZone",
    "schedules.ScheduleYear",
    "schedules.CollectionDate",
    "data_sources.DataSource",
    "community.QuorumRule",
}


class audit_context:
    """with audit_context(user, reason): ... – attributes changes to an actor."""

    def __init__(self, actor=None, reason: str = ""):
        self.actor = actor
        self.reason = reason

    def __enter__(self):
        _local.actor = self.actor
        _local.reason = self.reason
        return self

    def __exit__(self, *exc):
        _local.actor = None
        _local.reason = ""


def _serialize(instance) -> dict:
    data = model_to_dict(instance)
    return {key: str(value) for key, value in data.items()}


def _label(sender) -> str:
    return f"{sender._meta.app_label}.{sender.__name__}"


@receiver(pre_save)
def _capture_before(sender, instance, **kwargs):
    if _label(sender) not in TRACKED_MODELS or instance.pk is None:
        return
    try:
        previous = sender.objects.get(pk=instance.pk)
        instance._audit_before = _serialize(previous)
    except sender.DoesNotExist:
        instance._audit_before = None


@receiver(post_save)
def _log_save(sender, instance, created, **kwargs):
    if _label(sender) not in TRACKED_MODELS:
        return
    from .models import AuditAction, AuditLog

    before = getattr(instance, "_audit_before", None)
    after = _serialize(instance)
    if not created and before == after:
        return
    AuditLog.objects.create(
        actor=getattr(_local, "actor", None),
        action=AuditAction.CREATE if created else AuditAction.UPDATE,
        model_label=_label(sender),
        object_pk=str(instance.pk),
        object_repr=str(instance)[:255],
        before=None if created else before,
        after=after,
        reason=getattr(_local, "reason", ""),
    )


@receiver(post_delete)
def _log_delete(sender, instance, **kwargs):
    if _label(sender) not in TRACKED_MODELS:
        return
    from .models import AuditAction, AuditLog

    AuditLog.objects.create(
        actor=getattr(_local, "actor", None),
        action=AuditAction.DELETE,
        model_label=_label(sender),
        object_pk=str(instance.pk),
        object_repr=str(instance)[:255],
        before=_serialize(instance),
        after=None,
        reason=getattr(_local, "reason", ""),
    )
