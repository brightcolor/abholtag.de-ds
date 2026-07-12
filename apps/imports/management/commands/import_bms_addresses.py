"""Import of streets + house numbers from the EBL online calendar (BMS/insert-it.de).

Data source (public JSON endpoints, no auth):
  GET {base}/Main/GetStreets?text=<prefix>      – startsWith match on the name
  GET {base}/Main/GetLocations?streetId=<id>&houseNumber=  – all house numbers

Known quirks (verified server-side, see task description in docs/ANALYSE.md):
  * street 3713 ("Geniner Ufer") returns HTTP 404 on GetLocations → treat as
    "no house numbers", do not abort
  * ~861 streets legitimately have no house numbers (motorways, ramps, …)
  * location IDs are NOT unique – several house numbers may share one ID
"""

import concurrent.futures
import json
import string
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.addresses.models import City, HouseNumber, Street
from apps.core.models import Origin
from apps.core.text import normalize_street_name, parse_house_number
from apps.imports.models import ImportKind, ImportRun, ImportRunStatus

BMS_BASE = "https://insert-it.de/BMSAbfallkalenderLuebeck"
USER_AGENT = "abholtag.de/1.0 (Open-Source-Projekt; Kontakt siehe Impressum)"
SCRAPE_PREFIXES = list(string.ascii_lowercase) + list(string.digits) + list("äöüß")


class Command(BaseCommand):
    help = (
        "Importiert Straßen und Hausnummern des EBL-Online-Abfallkalenders (insert-it.de). "
        "Standard: aus data/bms/*.json; mit --scrape werden die Daten frisch abgerufen."
    )

    def add_arguments(self, parser):
        parser.add_argument("--streets", default="data/bms/streets.json")
        parser.add_argument("--locations", default="data/bms/locations.json")
        parser.add_argument(
            "--scrape", action="store_true",
            help="Daten live von insert-it.de abrufen und in die JSON-Dateien schreiben.",
        )
        parser.add_argument(
            "--no-create", action="store_true",
            help="Keine neuen Straßen anlegen, nur bestehende verknüpfen.",
        )

    # ------------------------------------------------------------------
    # scraping (per task spec: UA header, ≤4 parallel, retries, 404 → [])
    # ------------------------------------------------------------------
    def _get_json(self, url: str, retries: int = 3):
        import requests

        for attempt in range(retries):
            try:
                response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json()
            except requests.RequestException:
                if attempt == retries - 1:
                    raise
                time.sleep(1.5 * (attempt + 1))
        return None

    def scrape(self, streets_path: Path, locations_path: Path) -> None:
        self.stdout.write("Rufe Straßenliste ab (Präfixe a–z, 0–9, äöüß) …")
        streets: dict[int, str] = {}
        for prefix in SCRAPE_PREFIXES:
            rows = self._get_json(f"{BMS_BASE}/Main/GetStreets?text={prefix}") or []
            for row in rows:
                streets[int(row["ID"])] = row["Name"]
        street_list = [{"id": sid, "name": name} for sid, name in sorted(streets.items())]
        streets_path.write_text(json.dumps(street_list, ensure_ascii=False, indent=1), encoding="utf-8")
        self.stdout.write(f"  {len(street_list)} Straßen gespeichert.")

        self.stdout.write("Rufe Hausnummern ab (max. 4 parallel) …")

        def fetch_locations(entry):
            rows = self._get_json(
                f"{BMS_BASE}/Main/GetLocations?streetId={entry['id']}&houseNumber="
            )
            return {
                "street_id": entry["id"],
                "street_name": entry["name"],
                "locations": [
                    {"id": int(r["ID"]), "house_number": r["Text"]} for r in (rows or [])
                ],
            }

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for index, result in enumerate(pool.map(fetch_locations, street_list), 1):
                results.append(result)
                if index % 250 == 0:
                    self.stdout.write(f"  {index}/{len(street_list)} Straßen …")
        locations_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        total = sum(len(r["locations"]) for r in results)
        self.stdout.write(f"  {total} Hausnummern gespeichert.")

    # ------------------------------------------------------------------
    # import
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        streets_path = Path(options["streets"])
        locations_path = Path(options["locations"])

        if options["scrape"]:
            streets_path.parent.mkdir(parents=True, exist_ok=True)
            self.scrape(streets_path, locations_path)

        if not streets_path.exists() or not locations_path.exists():
            raise CommandError(
                f"Datendateien fehlen ({streets_path}, {locations_path}) – "
                "mit --scrape abrufen oder Pfade angeben."
            )

        bms_streets = json.loads(streets_path.read_text(encoding="utf-8"))
        bms_locations = json.loads(locations_path.read_text(encoding="utf-8"))
        locations_by_street = {entry["street_id"]: entry["locations"] for entry in bms_locations}

        import_run = ImportRun.objects.create(
            parser_key="bms_insert_it", kind=ImportKind.STREETS
        )

        city, _ = City.objects.get_or_create(name="Lübeck", defaults={"slug": slugify("Lübeck")})

        # existing streets by normalized name (may map to several district rows)
        existing: dict[str, list[Street]] = {}
        for street in Street.objects.filter(city=city):
            existing.setdefault(street.normalized_name, []).append(street)

        matched = created = ambiguous = 0
        unmatched_names: list[str] = []
        street_rows_by_bms: dict[int, list[Street]] = {}

        with transaction.atomic():
            for entry in bms_streets:
                bms_id, name = int(entry["id"]), entry["name"].strip()
                candidates = existing.get(normalize_street_name(name), [])
                if candidates:
                    # district variants of the same physical street share the BMS id
                    for street in candidates:
                        street.bms_street_id = bms_id
                        street.save(update_fields=["bms_street_id", "updated_at"])
                    street_rows_by_bms[bms_id] = candidates
                    matched += 1
                    ambiguous += int(len(candidates) > 1)
                elif not options["no_create"]:
                    has_locations = bool(locations_by_street.get(bms_id))
                    street = Street.objects.create(
                        city=city,
                        name=name,
                        origin=Origin.EXTERNAL_API,
                        bms_street_id=bms_id,
                        # streets without any house number (motorways etc.) stay
                        # out of the public autocomplete until curated
                        is_active=has_locations,
                    )
                    street_rows_by_bms[bms_id] = [street]
                    created += 1
                else:
                    unmatched_names.append(name)

            # house numbers: replace external records per street
            house_count = 0
            for bms_id, streets in street_rows_by_bms.items():
                rows = locations_by_street.get(bms_id) or []
                for street in streets:
                    street.house_numbers.filter(origin=Origin.EXTERNAL_API).delete()
                    objects = []
                    seen_texts = set()
                    for row in rows:
                        text = row["house_number"].strip()
                        if not text or text in seen_texts:
                            continue
                        seen_texts.add(text)
                        number, suffix = parse_house_number(text)
                        objects.append(
                            HouseNumber(
                                street=street,
                                text=text,
                                number=number,
                                suffix=suffix,
                                bms_location_id=int(row["id"]),
                            )
                        )
                    HouseNumber.objects.bulk_create(objects)
                    house_count += len(objects)

        import_run.status = ImportRunStatus.COMPLETED
        import_run.finished_at = timezone.now()
        import_run.stats = {
            "bms_streets": len(bms_streets),
            "matched": matched,
            "matched_multi_district": ambiguous,
            "created": created,
            "unmatched": len(unmatched_names),
            "house_numbers": house_count,
        }
        import_run.save()

        self.stdout.write(self.style.SUCCESS(
            f"BMS-Import abgeschlossen: {matched} Straßen verknüpft "
            f"({ambiguous} mit Ortsteil-Varianten), {created} neu angelegt, "
            f"{house_count} Hausnummern übernommen."
        ))
        if unmatched_names:
            self.stdout.write(f"  Nicht verknüpft: {len(unmatched_names)} (siehe Importlauf #{import_run.pk})")
            import_run.diff = {"unmatched": unmatched_names}
            import_run.save(update_fields=["diff"])
