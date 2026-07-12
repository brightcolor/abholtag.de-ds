"""Privacy friendly request classification helpers."""

import hashlib
from datetime import date
from urllib.parse import urlparse

from django.conf import settings

_MOBILE_MARKERS = ("mobile", "iphone", "android")
_TABLET_MARKERS = ("ipad", "tablet")
_BOT_MARKERS = ("bot", "crawler", "spider", "curl", "wget", "python-requests")

_CALENDAR_CLIENTS = (
    ("google-calendar", "Google Kalender"),
    ("googlecalendar", "Google Kalender"),
    ("calendaragent", "Apple Kalender"),
    ("ios", "Apple Kalender"),
    ("dataaccessd", "Apple Kalender"),
    ("remindd", "Apple Erinnerungen"),
    ("outlook", "Outlook"),
    ("microsoft office", "Outlook"),
    ("thunderbird", "Thunderbird"),
    ("lightning", "Thunderbird"),
    ("davdroid", "DAVx5"),
    ("davx5", "DAVx5"),
    ("icsx5", "ICSx5"),
    ("nextcloud", "Nextcloud"),
)


def device_class(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    if any(m in ua for m in _BOT_MARKERS):
        return "bot"
    if any(m in ua for m in _TABLET_MARKERS):
        return "tablet"
    if any(m in ua for m in _MOBILE_MARKERS):
        return "mobile"
    return "desktop" if ua else "unbekannt"


def browser_family(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    for marker, name in (
        ("edg/", "Edge"),
        ("opr/", "Opera"),
        ("firefox/", "Firefox"),
        ("chrome/", "Chrome"),
        ("safari/", "Safari"),
    ):
        if marker in ua:
            return name
    return "Sonstige"


def calendar_client(user_agent: str) -> str:
    ua = (user_agent or "").lower()
    for marker, name in _CALENDAR_CLIENTS:
        if marker in ua:
            return name
    return "Sonstiger Client"


def referrer_domain(request) -> str:
    ref = request.META.get("HTTP_REFERER", "")
    if not ref:
        return ""
    try:
        return urlparse(ref).netloc[:100]
    except ValueError:
        return ""


def session_hash(request) -> str:
    """Rotating pseudonymous session key: sha256(secret + day + ip + ua).

    The raw IP address is never stored; the salt rotates daily so hashes
    cannot be linked across days (documented in docs/ANALYTICS-DATENSCHUTZ.md).
    """
    ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip() or request.META.get(
        "REMOTE_ADDR", ""
    )
    ua = request.META.get("HTTP_USER_AGENT", "")
    raw = f"{settings.SECRET_KEY}:{date.today().isoformat()}:{ip}:{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
