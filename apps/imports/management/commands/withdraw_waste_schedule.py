from django.core.management.base import BaseCommand, CommandError

from apps.imports.services import withdraw_schedule_year
from apps.schedules.models import ScheduleYear


class Command(BaseCommand):
    help = "Zieht einen veröffentlichten Jahresplan zurück (§31)."

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
        withdraw_schedule_year(schedule_year)
        self.stdout.write(self.style.SUCCESS(f"Zurückgezogen: {schedule_year}"))
