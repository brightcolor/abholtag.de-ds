"""Import Restabfall/Bioabfall/Papier schedules from the BMS ICS endpoint.

Samples one location per street, clusters date patterns into zones and stages
ScheduleYears for review (publishing stays explicit, as with the PDF import).
"""

import concurrent.futures
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.addresses.models import AssignmentStatus, Street, StreetAssignment
from apps.core.models import Origin
from apps.imports.bms_schedule import (
    ZONE_PREFIX,
    cluster_signatures,
    fetch_location_ics,
    parse_bms_ics,
    zone_codes_for,
)
from apps.imports.models import ImportKind, ImportRun, ImportRunStatus
from apps.schedules.models import (
    CollectionDate,
    CollectionZone,
    ScheduleYear,
    ScheduleYearStatus,
)
from apps.waste_types.models import WasteType


class Command(BaseCommand):
    help = "Importiert Restabfall-/Bioabfall-/Papier-Termine aus dem EBL-Online-Kalender (BMS-ICS)."

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--cache-dir", default="data/bms/ics_cache")
        parser.add_argument("--limit", type=int, help="Nur die ersten N Straßen (zum Testen).")

    def handle(self, *args, **options):
        year = options["year"]
        cache_dir = Path(options["cache_dir"])
        cache_dir.mkdir(parents=True, exist_ok=True)

        waste_types = {wt.slug: wt for wt in WasteType.objects.filter(slug__in=ZONE_PREFIX)}
        if len(waste_types) != len(ZONE_PREFIX):
            raise CommandError("BMS-Abfallarten fehlen – Migration waste_types 0003 ausführen.")

        # one sampled location per BMS street id; district variants share the id
        streets = (
            Street.objects.filter(bms_street_id__isnull=False, house_numbers__isnull=False)
            .prefetch_related("house_numbers")
            .distinct()
        )
        by_bms: dict[int, list[Street]] = {}
        for street in streets:
            by_bms.setdefault(street.bms_street_id, []).append(street)
        samples = {
            bms_id: min(
                rows[0].house_numbers.all(),
                key=lambda hn: (hn.number if hn.number is not None else 10**6, hn.text),
            ).bms_location_id
            for bms_id, rows in by_bms.items()
        }
        items = sorted(samples.items())
        if options["limit"]:
            items = items[: options["limit"]]
        self.stdout.write(f"{len(items)} Straßen (BMS-IDs) – rufe ICS für {year} ab …")

        import_run = ImportRun.objects.create(parser_key="bms_ics", kind=ImportKind.SCHEDULE)

        # ------------------------------------------------------------------
        # fetch (≤4 parallel, cached on disk)
        # ------------------------------------------------------------------
        def fetch(pair):
            bms_id, location_id = pair
            try:
                return bms_id, fetch_location_ics(location_id, year, cache_dir=cache_dir)
            except Exception as exc:  # noqa: BLE001 – one failure must not kill the run
                return bms_id, f"__ERROR__{exc}"

        results: dict[int, str] = {}
        errors = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for index, (bms_id, content) in enumerate(pool.map(fetch, items), 1):
                if content.startswith("__ERROR__"):
                    errors += 1
                    content = ""
                results[bms_id] = content
                if index % 200 == 0:
                    self.stdout.write(f"  {index}/{len(items)} …")

        # ------------------------------------------------------------------
        # parse + cluster per waste type
        # ------------------------------------------------------------------
        per_type_signatures: dict[str, dict[int, tuple]] = {slug: {} for slug in ZONE_PREFIX}
        unknown_summaries: set[str] = set()
        empty_streets = 0
        for bms_id, content in results.items():
            if not content:
                empty_streets += 1
                continue
            parsed, unknown = parse_bms_ics(content)
            unknown_summaries |= unknown
            for slug, dates in parsed.items():
                wrong_year = [d for d in dates if d.year != year]
                if wrong_year:
                    continue
                per_type_signatures[slug][bms_id] = tuple(dates)

        issues = []
        if unknown_summaries:
            issues.append({
                "level": "info", "code": "unknown_summaries",
                "message": f"Unbekannte Terminarten ignoriert: {sorted(unknown_summaries)}",
            })
        if errors:
            issues.append({
                "level": "warning", "code": "fetch_errors",
                "message": f"{errors} Straßen konnten nicht abgerufen werden.",
            })

        # ------------------------------------------------------------------
        # write zones, assignments, schedule years
        # ------------------------------------------------------------------
        stats = {"year": year, "streets_sampled": len(items), "streets_without_data": empty_streets}
        with transaction.atomic():
            for slug, street_dates in per_type_signatures.items():
                waste_type = waste_types[slug]
                clusters = cluster_signatures(street_dates)
                codes = zone_codes_for(clusters, ZONE_PREFIX[slug])

                # BMS zones/assignments are derived data: rebuild them each run
                # (zone codes depend on the clustering); manually created
                # assignments and non-official dates are preserved (§32).
                StreetAssignment.objects.filter(
                    zone__waste_type=waste_type, origin=Origin.EXTERNAL_API
                ).delete()

                schedule_year, _ = ScheduleYear.objects.get_or_create(
                    waste_type=waste_type, year=year
                )
                if schedule_year.status != ScheduleYearStatus.PUBLISHED:
                    schedule_year.status = ScheduleYearStatus.PARSED
                schedule_year.import_run = import_run
                schedule_year.save()

                date_count = 0
                for signature, bms_ids in clusters.items():
                    zone, _ = CollectionZone.objects.get_or_create(
                        waste_type=waste_type, code=codes[signature]
                    )
                    CollectionDate.objects.filter(
                        schedule_year=schedule_year, zone=zone, origin=Origin.OFFICIAL_IMPORT
                    ).delete()
                    CollectionDate.objects.bulk_create(
                        CollectionDate(
                            schedule_year=schedule_year, zone=zone, date=day,
                            origin=Origin.OFFICIAL_IMPORT,
                        )
                        for day in signature
                    )
                    date_count += len(signature)

                    for bms_id in bms_ids:
                        for street in by_bms[bms_id]:
                            StreetAssignment.objects.get_or_create(
                                street=street, zone=zone,
                                defaults={
                                    "origin": Origin.EXTERNAL_API,
                                    "status": AssignmentStatus.ACTIVE,
                                },
                            )
                # official dates of zones that vanished from the clustering
                CollectionDate.objects.filter(
                    schedule_year=schedule_year, origin=Origin.OFFICIAL_IMPORT
                ).exclude(zone__code__in=codes.values()).delete()

                stats[slug] = {
                    "zones": len(clusters),
                    "streets": len(street_dates),
                    "dates": date_count,
                }

        import_run.status = ImportRunStatus.NEEDS_REVIEW if issues else ImportRunStatus.COMPLETED
        import_run.issues = issues
        import_run.stats = stats
        import_run.finished_at = timezone.now()
        import_run.save()

        self.stdout.write(self.style.SUCCESS(f"BMS-Terminimport abgeschlossen: {stats}"))
        self.stdout.write(
            "Veröffentlichen mit: python manage.py publish_waste_schedule "
            f"--waste-type <slug> --year {year}"
        )
