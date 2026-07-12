from django.core.management.base import BaseCommand, CommandError

from apps.imports.services import publish_schedule_year
from apps.schedules.models import ScheduleYear, ScheduleYearStatus


class Command(BaseCommand):
    help = "Veröffentlicht einen geprüften Jahresplan (§31)."

    def add_arguments(self, parser):
        parser.add_argument("--waste-type", required=True)
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument(
            "--force", action="store_true",
            help="Auch veröffentlichen, wenn der Status nicht „geprüft/freigegeben“ ist.",
        )

    def handle(self, *args, **options):
        try:
            schedule_year = ScheduleYear.objects.get(
                waste_type__slug=options["waste_type"], year=options["year"]
            )
        except ScheduleYear.DoesNotExist as exc:
            raise CommandError("Jahresplan nicht gefunden.") from exc

        if schedule_year.status == ScheduleYearStatus.PUBLISHED:
            self.stdout.write("Jahresplan ist bereits veröffentlicht.")
            return

        allowed = {ScheduleYearStatus.PARSED, ScheduleYearStatus.APPROVED, ScheduleYearStatus.NEEDS_REVIEW}
        if schedule_year.status not in allowed and not options["force"]:
            raise CommandError(
                f"Status ist {schedule_year.get_status_display()!r} – Veröffentlichung nur mit --force."
            )
        if schedule_year.status == ScheduleYearStatus.NEEDS_REVIEW and not options["force"]:
            raise CommandError(
                "Der Jahresplan hat offene Prüfhinweise. Bitte im Adminbereich prüfen "
                "oder mit --force veröffentlichen."
            )

        publish_schedule_year(schedule_year)
        self.stdout.write(self.style.SUCCESS(f"Veröffentlicht: {schedule_year}"))
