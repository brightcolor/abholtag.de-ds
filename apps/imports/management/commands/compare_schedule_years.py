from django.core.management.base import BaseCommand, CommandError

from apps.schedules.models import ScheduleYear


class Command(BaseCommand):
    help = "Vergleicht zwei Jahrespläne einer Abfallart (Terminanzahl je Bezirk)."

    def add_arguments(self, parser):
        parser.add_argument("--waste-type", required=True)
        parser.add_argument("--year-a", type=int, required=True)
        parser.add_argument("--year-b", type=int, required=True)

    def handle(self, *args, **options):
        years = {}
        for key in ("year_a", "year_b"):
            try:
                years[key] = ScheduleYear.objects.get(
                    waste_type__slug=options["waste_type"], year=options[key]
                )
            except ScheduleYear.DoesNotExist as exc:
                raise CommandError(f"Jahresplan {options[key]} nicht gefunden.") from exc

        def counts(schedule_year):
            result: dict[str, int] = {}
            for record in schedule_year.dates.filter(is_cancelled=False).select_related("zone"):
                result[record.zone.code] = result.get(record.zone.code, 0) + 1
            return result

        counts_a, counts_b = counts(years["year_a"]), counts(years["year_b"])
        self.stdout.write(f"Bezirk | {options['year_a']} | {options['year_b']}")
        for code in sorted(set(counts_a) | set(counts_b)):
            a, b = counts_a.get(code, 0), counts_b.get(code, 0)
            marker = "" if a == b else "  <-- Abweichung"
            self.stdout.write(f"{code:6} | {a:4} | {b:4}{marker}")
