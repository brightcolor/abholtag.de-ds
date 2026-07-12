"""Admin notifications – deliberately simple (mail_admins based)."""

import logging

from django.core.mail import mail_admins

logger = logging.getLogger(__name__)


def notify_admins(subject: str, body: str) -> None:
    try:
        mail_admins(subject, body, fail_silently=True)
    except Exception:  # noqa: BLE001 - notifications must never break flows
        logger.exception("Admin-Benachrichtigung fehlgeschlagen: %s", subject)
