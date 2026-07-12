import csv
import json
import sys

from django.core.management.base import BaseCommand, CommandError

from apps.schedules.models import ScheduleYear


class Command(BaseCommand):
    help = "Exportiert einen Jahresplan als JSON oder CSV (Backup/Weitergabe, §38)."

    def add_arguments(self, parser):
        parser.add_argument("--waste-type", required=True)
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--format", choices=["json", "csv"], default="json")

    def handle(self, *args, **options):
        try:
            schedule_year = ScheduleYear.objects.get(
                waste_type__slug=options["waste_type"], year=options["year"]
            )
        except ScheduleYear.DoesNotExist as exc:
            raise CommandError("Jahresplan nicht gefunden.") from exc

        rows = [
            {
                "date": record.date.isoformat(),
                "zone": record.zone.code,
                "kind": record.kind,
                "note": record.note,
                "origin": record.origin,
                "cancelled": record.is_cancelled,
            }
            for record in schedule_year.dates.select_related("zone").order_by("date", "zone__code")
        ]
        if options["format"] == "json":
            payload = {
                "waste_type": schedule_year.waste_type.slug,
                "year": schedule_year.year,
                "status": schedule_year.status,
                "dates": rows,
            }
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()) if rows else ["date"])
            writer.writeheader()
            writer.writerows(rows)
