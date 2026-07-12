"""Schedules for Restabfall/Bioabfall/Papier from the EBL online calendar (BMS).

The BMS ICS endpoint (`Main/Calender?bmsLocationId=<id>&year=<year>`) is
per-address; fetching all 45k locations is neither necessary nor polite.
Collections are tour based, so ONE sampled location per street suffices:
streets with identical date patterns per waste type form a tour ("zone").

Pipeline:
  1. sample one bmsLocationId per street (lowest house number, deterministic)
  2. fetch the ICS per location (≤4 parallel, retries, disk cache)
  3. parse events → dates per waste type
  4. cluster identical date sets → CollectionZone (codes R01…, B01…, P01…)
  5. write StreetAssignments + ScheduleYear/CollectionDates (review gate as
     with every import – publishing stays an explicit step)

Known limitation (documented): if a single street is split between tours by
house number, the sampled location decides for the whole street. The official
calendar link on the schedule page allows citizens to cross-check.
"""

import logging
import re
import time
from datetime import date, datetime

logger = logging.getLogger(__name__)

BMS_BASE = "https://insert-it.de/BMSAbfallkalenderLuebeck"
USER_AGENT = "abholtag.de/1.0 (Open-Source-Projekt; Kontakt siehe Impressum)"

# SUMMARY → waste type slug (created inactive by waste_types migration 0003)
SUMMARY_MAP = {
    "Restabfall": "restabfall",
    "Bioabfall": "bioabfall",
    "PPK": "papier",
}
ZONE_PREFIX = {"restabfall": "R", "bioabfall": "B", "papier": "P"}

_EVENT_RE = re.compile(r"BEGIN:VEVENT(.*?)END:VEVENT", re.S)
_SUMMARY_RE = re.compile(r"SUMMARY:(?:Leerung:\s*)?(.+)")
_DTSTART_RE = re.compile(r"DTSTART;VALUE=DATE:(\d{8})")


def parse_bms_ics(content: str) -> tuple[dict[str, list[date]], set[str]]:
    """Parse a BMS ICS document into {waste_slug: [dates]} + unknown summaries."""
    per_type: dict[str, list[date]] = {}
    unknown: set[str] = set()
    for block in _EVENT_RE.findall(content):
        summary_match = _SUMMARY_RE.search(block)
        date_match = _DTSTART_RE.search(block)
        if not summary_match or not date_match:
            continue
        summary = summary_match.group(1).strip()
        slug = SUMMARY_MAP.get(summary)
        if slug is None:
            unknown.add(summary)
            continue
        day = datetime.strptime(date_match.group(1), "%Y%m%d").date()
        per_type.setdefault(slug, []).append(day)
    for dates in per_type.values():
        dates.sort()
    return per_type, unknown


def fetch_location_ics(
    location_id: int, year: int, cache_dir=None, retries: int = 3, timeout: int = 30
) -> str:
    """Fetch (and cache) the ICS for one bmsLocationId."""
    import requests

    if cache_dir is not None:
        cache_file = cache_dir / f"{location_id}-{year}.ics"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    url = f"{BMS_BASE}/Main/Calender?bmsLocationId={location_id}&year={year}"
    for attempt in range(retries):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            if response.status_code == 404:
                return ""
            response.raise_for_status()
            content = response.text
            if cache_dir is not None:
                cache_file.write_text(content, encoding="utf-8")
            return content
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    return ""


def cluster_signatures(street_dates: dict[int, tuple[date, ...]]) -> dict[tuple[date, ...], list[int]]:
    """Group street ids by identical date signature (one waste type)."""
    clusters: dict[tuple[date, ...], list[int]] = {}
    for street_id, signature in street_dates.items():
        clusters.setdefault(signature, []).append(street_id)
    return clusters


def zone_codes_for(clusters: dict, prefix: str) -> dict[tuple, str]:
    """Deterministic zone codes: ordered by first collection date, then size."""
    ordered = sorted(clusters.items(), key=lambda kv: (kv[0][0] if kv[0] else date.max, kv[0]))
    return {signature: f"{prefix}{index:02d}" for index, (signature, _) in enumerate(ordered, 1)}


# ---------------------------------------------------------------------------
# Self-healing live lookup: streets without a BMS zone assignment get their
# dates fetched on first page view and persisted ("cached") in the regular
# zone model, so no address triggers more than one upstream request.
# ---------------------------------------------------------------------------

def ensure_bms_schedule_for_street(street, year: int | None = None, cache_dir=None) -> bool:
    """Fetch + persist BMS dates for a street that has no zone assignment yet.

    Only fills into already *published* ScheduleYears (the bulk import went
    through review; a single street joining an existing plan is the same data
    from the same source). Returns True if anything was added. Fail-silent:
    the page must render regardless of upstream availability.
    """
    from pathlib import Path

    from django.core.cache import cache

    from apps.addresses.models import AssignmentStatus, StreetAssignment
    from apps.core.models import Origin
    from apps.schedules.models import (
        CollectionDate,
        CollectionZone,
        ScheduleYear,
        ScheduleYearStatus,
    )
    from apps.waste_types.models import WasteType

    year = year or date.today().year
    if not street.bms_street_id:
        return False

    missing = [
        slug for slug in ZONE_PREFIX
        if not StreetAssignment.objects.filter(
            street=street, zone__waste_type__slug=slug, status=AssignmentStatus.ACTIVE
        ).exists()
    ]
    if not missing:
        return False

    # negative cache: one upstream attempt per street and day
    guard_key = f"bms-live:{street.pk}:{year}"
    if cache.get(guard_key):
        return False
    cache.set(guard_key, True, timeout=60 * 60 * 24)

    house = street.house_numbers.order_by("number", "text").first()
    if house is None:
        return False

    try:
        content = fetch_location_ics(
            house.bms_location_id, year,
            cache_dir=Path(cache_dir) if cache_dir else Path("data/bms/ics_cache"),
            retries=1, timeout=6,
        )
    except Exception:  # noqa: BLE001 – upstream problems must not break the page
        logger.warning("BMS-Live-Abruf fehlgeschlagen (Straße %s)", street, exc_info=True)
        return False
    if not content:
        return False

    parsed, _unknown = parse_bms_ics(content)
    added = False
    for slug in missing:
        dates = [d for d in parsed.get(slug, []) if d.year == year]
        if not dates:
            continue
        waste_type = WasteType.objects.filter(slug=slug).first()
        schedule_year = ScheduleYear.objects.filter(
            waste_type=waste_type, year=year, status=ScheduleYearStatus.PUBLISHED
        ).first()
        if schedule_year is None:
            continue

        signature = tuple(dates)
        # reuse a zone with the identical date set, else create the next one
        zone = None
        for candidate in CollectionZone.objects.filter(waste_type=waste_type):
            candidate_dates = tuple(
                candidate.dates.filter(schedule_year=schedule_year)
                .order_by("date").values_list("date", flat=True)
            )
            if candidate_dates == signature:
                zone = candidate
                break
        if zone is None:
            prefix = ZONE_PREFIX[slug]
            numbers = [
                int(code[len(prefix):])
                for code in CollectionZone.objects.filter(
                    waste_type=waste_type, code__startswith=prefix
                ).values_list("code", flat=True)
                if code[len(prefix):].isdigit()
            ]
            zone = CollectionZone.objects.create(
                waste_type=waste_type, code=f"{prefix}{(max(numbers) if numbers else 0) + 1:02d}"
            )
            CollectionDate.objects.bulk_create(
                CollectionDate(
                    schedule_year=schedule_year, zone=zone, date=day,
                    origin=Origin.OFFICIAL_IMPORT,
                )
                for day in signature
            )
        StreetAssignment.objects.get_or_create(
            street=street, zone=zone,
            defaults={
                "origin": Origin.EXTERNAL_API,
                "status": AssignmentStatus.ACTIVE,
                "note": "live ergänzt (BMS-Abruf)",
            },
        )
        added = True
        logger.info("BMS-Live: %s → %s %s ergänzt", street, slug, zone.code)
    return added
