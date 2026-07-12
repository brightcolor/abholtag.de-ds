from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError

from apps.schedules.models import ScheduleYear


class Command(BaseCommand):
    help = "Validiert einen gespeicherten Jahresplan (Rhythmus, Lücken, Duplikate) – §32."

    def add_arguments(self, parser):
        parser.add_argument("--waste-type", required=True)
        parser.add_argument("--year", type=int, required=True)

    def handle(self, *args, **options):
        try:
            schedule_year = ScheduleYear.objects.get(
                waste_type__slug=options["waste_type"], year=options["year"]
            )
        except ScheduleYear.DoesNotExist as exc:
            raise CommandError("Jahresplan nicht gefunden.") from exc

        problems = 0
        dates = schedule_year.dates.filter(is_cancelled=False).select_related("zone").order_by(
            "zone__code", "date"
        )
        per_zone: dict[str, list] = {}
        for record in dates:
            per_zone.setdefault(record.zone.code, []).append(record.date)

        if not per_zone:
            raise CommandError("Der Jahresplan enthält keine Termine.")

        for code, zone_dates in sorted(per_zone.items()):
            for a, b in zip(zone_dates, zone_dates[1:], strict=False):
                gap = (b - a).days
                if gap == 0:
                    self.stderr.write(f"Bezirk {code}: Duplikat am {a}.")
                    problems += 1
                elif not 6 <= gap <= 22:
                    self.stderr.write(f"Bezirk {code}: unplausibler Abstand {gap} Tage ({a} → {b}).")
                    problems += 1
            first, last = zone_dates[0], zone_dates[-1]
            if first > schedule_year_start(schedule_year) + timedelta(days=31):
                self.stderr.write(f"Bezirk {code}: erster Termin erst am {first}.")
                problems += 1
            if last < schedule_year_end(schedule_year) - timedelta(days=31):
                self.stderr.write(f"Bezirk {code}: letzter Termin bereits am {last}.")
                problems += 1

        if problems:
            self.stdout.write(self.style.WARNING(f"{problems} Auffälligkeiten gefunden."))
        else:
            self.stdout.write(self.style.SUCCESS("Keine Auffälligkeiten gefunden."))


def schedule_year_start(schedule_year):
    from datetime import date

    return date(schedule_year.year, 1, 1)


def schedule_year_end(schedule_year):
    from datetime import date

    return date(schedule_year.year, 12, 31)
