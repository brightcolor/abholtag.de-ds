"""Apply the parsed EBL "Wegweiser" to the database (all four waste streams).

The EBL plan is the authoritative source for Restabfall, Bioabfall, Papier and
Gelber Sack. This module stages it through the same review discipline as the
PDF import: calendar dates and street assignments are written, but a schedule
year only becomes public when it is explicitly published (§6, §16, §32).

Zone codes are the official tour letters printed in the plan (A–J for Rest/Bio
and Gelber Sack, A–T for Papier). They are stable across years, so a later
edition updates the same zones instead of introducing a new scheme.
"""

import logging

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.addresses.models import (
    AssignmentStatus,
    City,
    Parity,
    Street,
    StreetAssignment,
)
from apps.core.models import Origin
from apps.core.text import normalize_street_name, parse_house_ranges
from apps.schedules.models import (
    CollectionDate,
    CollectionZone,
    ScheduleYear,
    ScheduleYearStatus,
)
from apps.waste_types.models import WasteType

from .models import ImportKind, ImportRun, ImportRunStatus
from .parsers.luebeck_ebl import STREAMS, LuebeckEblParser
from .services import validate_plan

logger = logging.getLogger(__name__)

# assignments the import owns and rebuilds; manual work is never touched
_MANAGED_ORIGINS = (Origin.OFFICIAL_IMPORT, Origin.EXTERNAL_API)
_PARITY = {"odd": Parity.ODD, "even": Parity.EVEN, "all": Parity.ALL}


def run_ebl_import(path, source_document=None, user=None, publish=False) -> ImportRun:
    """Parse and stage the EBL plan for all waste types. Returns the ImportRun."""
    import_run = ImportRun.objects.create(
        source_document=source_document,
        parser_key=LuebeckEblParser.key,
        kind=ImportKind.FULL,
        created_by=user,
    )
    try:
        plans = LuebeckEblParser().parse_multi(path)
    except Exception as exc:  # noqa: BLE001 - import must fail gracefully
        logger.exception("EBL-Parserlauf fehlgeschlagen")
        import_run.status = ImportRunStatus.PARSE_FAILED
        import_run.log = f"Parser-Ausnahme: {exc}"
        import_run.finished_at = timezone.now()
        import_run.save()
        return import_run

    waste_types = {wt.slug: wt for wt in WasteType.objects.all()}
    all_issues: list[dict] = []
    stats: dict = {"publish": publish, "waste_types": {}}
    blocking = False

    # collect + validate every stream before writing anything
    validated: dict[str, tuple] = {}
    for slugs in STREAMS.values():
        for slug in slugs:
            plan = plans.get(slug)
            wt = waste_types.get(slug)
            if plan is None or wt is None:
                all_issues.append({
                    "level": "error", "code": "waste_type_missing",
                    "message": f"Abfallart {slug!r} fehlt in der Datenbank.",
                })
                blocking = True
                continue
            issues = validate_plan(plan, wt)
            # The EBL import replaces the whole zone scheme (BMS cluster codes
            # → official letters), so "new zones" and "old zones now empty"
            # are expected, not warnings – they would otherwise fire for every
            # letter on every run.
            issues = [i for i in issues if i["code"] not in ("new_zones", "zones_without_dates")]
            for issue in issues:
                issue["waste_type"] = slug
            all_issues.extend(issues)
            if any(i["level"] == "error" for i in issues) or plan.has_blocking_issues:
                blocking = True
            validated[slug] = (plan, wt)

    if blocking:
        import_run.status = ImportRunStatus.VALIDATION_FAILED
        import_run.issues = all_issues
        import_run.finished_at = timezone.now()
        import_run.save()
        return import_run

    with transaction.atomic():
        city, _ = City.objects.get_or_create(name="Lübeck", defaults={"slug": slugify("Lübeck")})
        street_cache: dict[str, Street] = {}
        for slug, (plan, wt) in validated.items():
            year = plan.year
            zones = _apply_zones_and_dates(plan, wt, year, import_run, publish)
            assign_stats = _apply_assignments(plan, wt, zones, city, street_cache)
            _cleanup_orphan_zones(wt)
            stats["waste_types"][slug] = {
                "year": year,
                "dates": len(plan.calendar),
                "zones": sorted(zones),
                **assign_stats,
            }

    has_warnings = any(i["level"] == "warning" for i in all_issues)
    import_run.issues = all_issues
    import_run.stats = stats
    import_run.status = (
        ImportRunStatus.COMPLETED
        if publish and not has_warnings
        else ImportRunStatus.NEEDS_REVIEW
    )
    import_run.finished_at = timezone.now()
    import_run.save()
    return import_run


def _apply_zones_and_dates(plan, waste_type, year, import_run, publish) -> dict:
    """Write the year's collection dates onto the official letter zones."""
    zones: dict[str, CollectionZone] = {}
    for entry in plan.calendar:
        if entry.zone_code not in zones:
            zones[entry.zone_code], _ = CollectionZone.objects.get_or_create(
                waste_type=waste_type, code=entry.zone_code
            )

    schedule_year, _ = ScheduleYear.objects.get_or_create(waste_type=waste_type, year=year)
    if publish:
        schedule_year.status = ScheduleYearStatus.PUBLISHED
        schedule_year.published_at = timezone.now()
    elif schedule_year.status == ScheduleYearStatus.PUBLISHED:
        schedule_year.status = ScheduleYearStatus.NEEDS_REVIEW
    else:
        schedule_year.status = ScheduleYearStatus.NEEDS_REVIEW
    schedule_year.import_run = import_run
    if source := import_run.source_document:
        schedule_year.source_document = source
    schedule_year.save()

    # replace official dates only; manual/community records are preserved (§32)
    CollectionDate.objects.filter(
        schedule_year=schedule_year, origin=Origin.OFFICIAL_IMPORT
    ).delete()
    CollectionDate.objects.bulk_create(
        CollectionDate(
            schedule_year=schedule_year,
            zone=zones[entry.zone_code],
            date=entry.date,
            kind=entry.kind,
            note=entry.note,
            origin=Origin.OFFICIAL_IMPORT,
        )
        for entry in plan.calendar
    )
    return zones


def _apply_assignments(plan, waste_type, zones, city, street_cache) -> dict:
    """Rebuild street→zone assignments from the plan, with house ranges."""
    # drop the assignments this importer owns; keep admin/community edits
    StreetAssignment.objects.filter(
        zone__waste_type=waste_type, origin__in=_MANAGED_ORIGINS
    ).delete()

    created = pending = review = new_streets = 0
    for entry in plan.streets:
        street = _resolve_street(entry.name, city, street_cache)
        if street is None:
            new_streets += 1
            continue

        review_note = entry.note.startswith("REVIEW")
        segments = parse_house_ranges(entry.raw_range)
        if entry.raw_range and entry.raw_range != "—" and segments is None:
            # irregular range we will not guess – one PENDING row for review
            for code in entry.zone_codes:
                StreetAssignment.objects.create(
                    street=street, zone=zones.get(code) or _zone(waste_type, code),
                    raw_range=entry.raw_range, note=entry.note,
                    origin=Origin.OFFICIAL_IMPORT, status=AssignmentStatus.PENDING,
                )
                pending += 1
            continue

        status = AssignmentStatus.PENDING if review_note else AssignmentStatus.ACTIVE
        for code in entry.zone_codes:
            zone = zones.get(code) or _zone(waste_type, code)
            if segments:
                for seg in segments:
                    StreetAssignment.objects.create(
                        street=street, zone=zone,
                        house_from=seg["house_from"], house_to=seg["house_to"],
                        parity=_PARITY[seg["parity"]], raw_range=entry.raw_range,
                        note=entry.note, origin=Origin.OFFICIAL_IMPORT, status=status,
                    )
                    created += 1
            else:
                StreetAssignment.objects.create(
                    street=street, zone=zone, note=entry.note,
                    origin=Origin.OFFICIAL_IMPORT, status=status,
                )
                created += 1
        if review_note:
            review += 1

    return {
        "streets": len({e.name for e in plan.streets}),
        "assignments_created": created,
        "assignments_pending": pending,
        "assignments_review_note": review,
        "streets_not_matched": new_streets,
    }


def _resolve_street(name, city, cache) -> Street | None:
    clean = name.split("(")[0].strip()
    key = normalize_street_name(clean)
    if key in cache:
        return cache[key]
    street = (
        Street.objects.filter(city=city, normalized_name=key)
        .order_by("district_id")
        .first()
    )
    if street is None:
        street = Street.objects.create(
            city=city, name=clean, origin=Origin.OFFICIAL_IMPORT
        )
    cache[key] = street
    return street


def _zone(waste_type, code) -> CollectionZone:
    zone, _ = CollectionZone.objects.get_or_create(waste_type=waste_type, code=code)
    return zone


def _cleanup_orphan_zones(waste_type) -> None:
    """Remove zones left without any dates or assignments (old BMS scheme)."""
    CollectionZone.objects.filter(
        waste_type=waste_type, dates__isnull=True, assignments__isnull=True
    ).delete()
