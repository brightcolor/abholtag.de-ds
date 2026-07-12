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


def fetch_location_ics(location_id: int, year: int, cache_dir=None, retries: int = 3) -> str:
    """Fetch (and cache) the ICS for one bmsLocationId."""
    import requests

    if cache_dir is not None:
        cache_file = cache_dir / f"{location_id}-{year}.ics"
        if cache_file.exists():
            return cache_file.read_text(encoding="utf-8")

    url = f"{BMS_BASE}/Main/Calender?bmsLocationId={location_id}&year={year}"
    for attempt in range(retries):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
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
