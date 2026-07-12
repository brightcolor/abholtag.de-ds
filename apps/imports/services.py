"""Applying parsed plans to the database – with validation, diff and
review gates. Master data is never overwritten automatically (§6, §16).
"""

import logging
from datetime import date as date_cls

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.addresses.models import (
    AssignmentStatus,
    City,
    District,
    Street,
    StreetAssignment,
)
from apps.core.models import Origin
from apps.core.text import normalize_street_name
from apps.schedules.models import (
    CollectionDate,
    CollectionDateKind,
    CollectionZone,
    ScheduleYear,
    ScheduleYearStatus,
)

from .models import ImportKind, ImportRun, ImportRunStatus
from .parsers.base import ParsedPlan

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Validation (§32)
# ---------------------------------------------------------------------------

def validate_plan(plan: ParsedPlan, waste_type) -> list[dict]:
    issues = [i.as_dict() for i in plan.issues]

    if plan.year is None:
        issues.append({"level": "error", "code": "year", "message": "Kein Kalenderjahr erkannt."})
        return issues

    current_year = date_cls.today().year
    if not current_year - 1 <= plan.year <= current_year + 2:
        issues.append(
            {
                "level": "error",
                "code": "year_implausible",
                "message": f"Kalenderjahr {plan.year} liegt außerhalb des plausiblen Bereichs.",
            }
        )

    for entry in plan.calendar:
        if entry.date.year != plan.year:
            issues.append(
                {
                    "level": "error",
                    "code": "date_outside_year",
                    "message": f"Termin {entry.date} liegt außerhalb des Kalenderjahres {plan.year}.",
                }
            )
            break

    known_zones = set(
        CollectionZone.objects.filter(waste_type=waste_type).values_list("code", flat=True)
    )
    parsed_zones = {e.zone_code for e in plan.calendar}
    if known_zones:
        unknown = parsed_zones - known_zones
        if unknown:
            issues.append(
                {
                    "level": "warning",
                    "code": "new_zones",
                    "message": f"Neue, bisher unbekannte Bezirke: {', '.join(sorted(unknown))}.",
                }
            )
        missing = known_zones - parsed_zones
        if missing:
            issues.append(
                {
                    "level": "warning",
                    "code": "zones_without_dates",
                    "message": f"Aktive Bezirke ohne Termine: {', '.join(sorted(missing))}.",
                }
            )

    previous = (
        ScheduleYear.objects.filter(waste_type=waste_type, year=plan.year - 1)
        .exclude(status=ScheduleYearStatus.WITHDRAWN)
        .first()
    )
    if previous:
        prev_count = previous.dates.count()
        if prev_count and plan.calendar and abs(len(plan.calendar) - prev_count) > prev_count * 0.2:
            issues.append(
                {
                    "level": "warning",
                    "code": "count_deviation",
                    "message": (
                        f"Terminanzahl ({len(plan.calendar)}) weicht stark vom Vorjahr ({prev_count}) ab."
                    ),
                }
            )
    return issues


# ---------------------------------------------------------------------------
# Schedule import
# ---------------------------------------------------------------------------

@transaction.atomic
def apply_schedule(plan: ParsedPlan, waste_type, import_run: ImportRun) -> ScheduleYear:
    """Write parsed calendar entries as a reviewable (not yet published)
    schedule year. Manual overrides (origin != official) are preserved.
    """
    schedule_year, _created = ScheduleYear.objects.get_or_create(
        waste_type=waste_type, year=plan.year
    )
    if schedule_year.status == ScheduleYearStatus.PUBLISHED:
        # Re-imports of a published year go to review, never straight to live data.
        schedule_year.status = ScheduleYearStatus.NEEDS_REVIEW
    else:
        schedule_year.status = (
            ScheduleYearStatus.NEEDS_REVIEW if import_run.warning_issues else ScheduleYearStatus.PARSED
        )
    schedule_year.source_document = import_run.source_document
    schedule_year.import_run = import_run
    schedule_year.save()

    zones: dict[str, CollectionZone] = {}
    for entry in plan.calendar:
        if entry.zone_code not in zones:
            zones[entry.zone_code], _ = CollectionZone.objects.get_or_create(
                waste_type=waste_type, code=entry.zone_code
            )

    # replace official dates; keep manual/admin/community records untouched (§32)
    removed, _ = (
        CollectionDate.objects.filter(
            schedule_year=schedule_year, origin=Origin.OFFICIAL_IMPORT
        ).delete()
    )
    created = 0
    for entry in plan.calendar:
        _, was_created = CollectionDate.objects.update_or_create(
            schedule_year=schedule_year,
            zone=zones[entry.zone_code],
            date=entry.date,
            defaults={
                "kind": entry.kind,
                "note": entry.note,
                "origin": Origin.OFFICIAL_IMPORT,
            },
        )
        created += int(was_created)

    import_run.stats = {
        **import_run.stats,
        "year": plan.year,
        "dates_parsed": len(plan.calendar),
        "dates_created": created,
        "dates_removed": removed,
        "zones": sorted(zones),
    }
    import_run.save(update_fields=["stats"])
    return schedule_year


# ---------------------------------------------------------------------------
# Street master data: initial seed and diff (§16)
# ---------------------------------------------------------------------------

def seed_streets(plan: ParsedPlan, waste_type, import_run: ImportRun, city_name: str = "Lübeck") -> dict:
    """Initial import of street master data into an empty street table."""
    city, _ = City.objects.get_or_create(name=city_name, defaults={"slug": slugify(city_name)})
    zones: dict[str, CollectionZone] = {}
    created_streets = 0
    created_assignments = 0
    pending_assignments = 0

    with transaction.atomic():
        for entry in plan.streets:
            district = None
            if entry.district:
                district, _ = District.objects.get_or_create(
                    city=city, slug=slugify(entry.district), defaults={"name": entry.district}
                )
            street, street_created = Street.objects.get_or_create(
                city=city,
                district=district,
                normalized_name=normalize_street_name(entry.name),
                defaults={"name": entry.name, "origin": Origin.OFFICIAL_IMPORT},
            )
            created_streets += int(street_created)

            for code in entry.zone_codes:
                if code not in zones:
                    zones[code], _ = CollectionZone.objects.get_or_create(
                        waste_type=waste_type, code=code
                    )
                # Streets listed with explicit house number ranges are stored
                # as PENDING – ranges in the source are ambiguous and must be
                # confirmed by a human (§10: never guess).
                status = AssignmentStatus.PENDING if entry.raw_range else AssignmentStatus.ACTIVE
                _, a_created = StreetAssignment.objects.get_or_create(
                    street=street,
                    zone=zones[code],
                    raw_range=entry.raw_range,
                    defaults={
                        "origin": Origin.OFFICIAL_IMPORT,
                        "status": status,
                        "note": entry.note,
                    },
                )
                created_assignments += int(a_created)
                pending_assignments += int(a_created and status == AssignmentStatus.PENDING)

    stats = {
        "streets_parsed": len(plan.streets),
        "streets_created": created_streets,
        "assignments_created": created_assignments,
        "assignments_pending_review": pending_assignments,
    }
    import_run.stats = {**import_run.stats, **stats}
    import_run.save(update_fields=["stats"])
    return stats


def diff_streets(plan: ParsedPlan, waste_type) -> dict:
    """Compare a parsed street list against existing master data (§16).

    Returns a diff structure; nothing is written. Applying changes is an
    explicit admin decision.
    """
    existing: dict[str, set[str]] = {}
    for assignment in StreetAssignment.objects.filter(
        zone__waste_type=waste_type
    ).select_related("street", "zone"):
        existing.setdefault(assignment.street.normalized_name, set()).add(assignment.zone.code)

    parsed: dict[str, dict] = {}
    for entry in plan.streets:
        key = normalize_street_name(entry.name)
        record = parsed.setdefault(key, {"name": entry.name, "zones": set(), "district": entry.district})
        record["zones"].update(entry.zone_codes)

    added = [
        {"name": data["name"], "zones": sorted(data["zones"]), "district": data["district"]}
        for key, data in sorted(parsed.items())
        if key not in existing
    ]
    removed = [
        {"normalized_name": key, "zones": sorted(zones)}
        for key, zones in sorted(existing.items())
        if key not in parsed
    ]
    changed = [
        {
            "name": parsed[key]["name"],
            "zones_old": sorted(existing[key]),
            "zones_new": sorted(parsed[key]["zones"]),
        }
        for key in sorted(set(existing) & set(parsed))
        if existing[key] != parsed[key]["zones"]
    ]
    return {
        "streets_added": added,
        "streets_removed": removed,
        "assignments_changed": changed,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": len(set(existing) & set(parsed)) - len(changed),
        },
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_import(source_document, waste_type, kind: str = ImportKind.FULL, user=None) -> ImportRun:
    """Parse a source document and stage its contents for review."""
    from .parsers.registry import get_parser

    parser_key = source_document.data_source.parser_key
    import_run = ImportRun.objects.create(
        source_document=source_document,
        parser_key=parser_key,
        kind=kind,
        created_by=user,
    )
    try:
        parser = get_parser(parser_key)
        plan = parser.parse(source_document.file.path)
    except Exception as exc:  # noqa: BLE001 - import must fail gracefully
        logger.exception("Parserlauf fehlgeschlagen")
        import_run.status = ImportRunStatus.PARSE_FAILED
        import_run.log = f"Parser-Ausnahme: {exc}"
        import_run.finished_at = timezone.now()
        import_run.save()
        return import_run

    issues = validate_plan(plan, waste_type)
    import_run.issues = issues
    blocking = [i for i in issues if i["level"] == "error"]

    if blocking:
        import_run.status = ImportRunStatus.VALIDATION_FAILED
        import_run.finished_at = timezone.now()
        import_run.save()
        return import_run

    if plan.year and source_document.detected_year != plan.year:
        source_document.detected_year = plan.year
        source_document.save(update_fields=["detected_year"])

    street_table_empty = not Street.objects.exists()
    if kind in (ImportKind.FULL, ImportKind.STREETS):
        if street_table_empty:
            seed_streets(plan, waste_type, import_run)
        else:
            import_run.diff = diff_streets(plan, waste_type)

    if kind in (ImportKind.FULL, ImportKind.SCHEDULE) and plan.calendar:
        apply_schedule(plan, waste_type, import_run)

    has_warnings = any(i["level"] == "warning" for i in issues)
    has_street_diff = bool(import_run.diff and any(import_run.diff.get("summary", {}).values()))
    import_run.status = (
        ImportRunStatus.NEEDS_REVIEW if (has_warnings or has_street_diff) else ImportRunStatus.COMPLETED
    )
    import_run.finished_at = timezone.now()
    import_run.save()
    return import_run


def publish_schedule_year(schedule_year: ScheduleYear, user=None) -> None:
    schedule_year.status = ScheduleYearStatus.PUBLISHED
    schedule_year.published_at = timezone.now()
    schedule_year.save()
    logger.info("Jahresplan veröffentlicht: %s durch %s", schedule_year, user or "System")


def withdraw_schedule_year(schedule_year: ScheduleYear, user=None) -> None:
    schedule_year.status = ScheduleYearStatus.WITHDRAWN
    schedule_year.save()
    logger.info("Jahresplan zurückgezogen: %s durch %s", schedule_year, user or "System")
