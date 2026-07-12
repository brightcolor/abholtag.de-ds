"""RFC 5545 iCalendar generation (§12) – no external dependency.

Design decisions:
* All-day events (DTSTART;VALUE=DATE) – waste collection has no fixed time.
* Stable UID per address, waste type and date so that clients update instead
  of duplicating events across feed refreshes and year changes.
* Cancelled dates stay in the feed as STATUS:CANCELLED with a bumped
  SEQUENCE so subscribed clients remove them.
* CRLF line endings and 75-octet line folding as required by the RFC.
"""

import hashlib
from datetime import timedelta
from urllib.parse import urlparse

from django.conf import settings

PRODID = "-//Abfuhrkalender Luebeck//Open Source//DE"


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")
    )


def _fold(line: str) -> str:
    """Fold content lines longer than 75 octets (RFC 5545 §3.1)."""
    encoded = line.encode("utf-8")
    if len(encoded) <= 75:
        return line
    parts = []
    current = b""
    for char in line:
        char_bytes = char.encode("utf-8")
        limit = 75 if not parts else 74  # continuation lines start with a space
        if len(current) + len(char_bytes) > limit:
            parts.append(current)
            current = char_bytes
        else:
            current += char_bytes
    parts.append(current)
    return "\r\n ".join(p.decode("utf-8") for p in parts)


def _domain() -> str:
    return urlparse(settings.SITE_BASE_URL).netloc or "abfuhrkalender.local"


def build_calendar(address_key, dates, calendar_name: str, with_alarm: bool = False) -> bytes:
    """Build an ICS document for the given CollectionDate queryset/list."""
    domain = _domain()
    lines: list[str] = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{PRODID}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
        "X-WR-TIMEZONE:Europe/Berlin",
        "X-PUBLISHED-TTL:PT12H",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
    ]

    location = f"{address_key.label}, {address_key.street.city.name}"
    for record in dates:
        waste_type = record.zone.waste_type
        stamp = record.updated_at.strftime("%Y%m%dT%H%M%SZ")
        uid = f"{address_key.public_id}-{waste_type.slug}-{record.date:%Y%m%d}@{domain}"
        description = waste_type.ics_description.format(address=location, city=address_key.street.city.name)
        if record.note:
            description = f"{description}\nHinweis: {record.note}"
        description += "\nQuelle: offizieller Abfuhrplan; Angaben ohne Gewähr."

        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{stamp}",
            f"LAST-MODIFIED:{stamp}",
            f"SEQUENCE:{record.sequence}",
            f"DTSTART;VALUE=DATE:{record.date:%Y%m%d}",
            f"DTEND;VALUE=DATE:{record.date + timedelta(days=1):%Y%m%d}",
            f"SUMMARY:{_escape(waste_type.calendar_summary)}",
            f"DESCRIPTION:{_escape(description)}",
            f"LOCATION:{_escape(location)}",
            "TRANSP:TRANSPARENT",
            f"STATUS:{'CANCELLED' if record.is_cancelled else 'CONFIRMED'}",
            "CLASS:PUBLIC",
        ]
        if with_alarm and not record.is_cancelled:
            hours = waste_type.reminder_hours_before or 12
            lines += [
                "BEGIN:VALARM",
                "ACTION:DISPLAY",
                f"DESCRIPTION:{_escape(f'Morgen: {waste_type.calendar_summary} bereitstellen')}",
                f"TRIGGER:-PT{hours}H",
                "END:VALARM",
            ]
        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return ("\r\n".join(_fold(line) for line in lines) + "\r\n").encode("utf-8")


def calendar_etag(content: bytes) -> str:
    return f'"{hashlib.sha256(content).hexdigest()[:32]}"'
