"""Fail-safe event recording – analytics must never break a request."""

import logging

from django.conf import settings

from apps.core.http import (
    browser_family,
    calendar_client,
    device_class,
    referrer_domain,
    session_hash,
)

logger = logging.getLogger(__name__)


def record_event(
    request,
    event_type: str,
    waste_type=None,
    street=None,
    district=None,
    address_key=None,
    year: int | None = None,
    status: str = "",
    query: str = "",
) -> None:
    if not settings.ANALYTICS_ENABLED:
        return
    try:
        from .models import AnalyticsEvent

        user_agent = request.META.get("HTTP_USER_AGENT", "")
        if district is None and street is not None:
            district = street.district
        if street is None and address_key is not None:
            street = address_key.street
            district = district or address_key.street.district
        is_feed = event_type in ("calendar_feed_requested", "calendar_downloaded")
        AnalyticsEvent.objects.create(
            event_type=event_type,
            session_hash=session_hash(request),
            waste_type=waste_type,
            street=street,
            district=district,
            address_key=address_key,
            year=year,
            device_class=device_class(user_agent),
            browser_family=browser_family(user_agent),
            calendar_client=calendar_client(user_agent) if is_feed else "",
            referrer_domain=referrer_domain(request),
            status=status[:30],
            query=query[:100],
        )
    except Exception:  # noqa: BLE001
        logger.exception("Analytics-Ereignis konnte nicht gespeichert werden")
