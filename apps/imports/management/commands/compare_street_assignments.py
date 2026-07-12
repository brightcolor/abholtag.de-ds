import json

from django.core.management.base import BaseCommand, CommandError

from apps.imports.parsers.registry import get_parser
from apps.imports.services import diff_streets
from apps.waste_types.models import WasteType


class Command(BaseCommand):
    help = "Vergleicht eine PDF-Straßenliste mit dem bestehenden Straßenstamm (§16, nur lesend)."

    def add_arguments(self, parser):
        parser.add_argument("--waste-type", required=True)
        parser.add_argument("--file", required=True, help="Pfad zur PDF-Datei.")
        parser.add_argument("--parser", default="luebeck_gelber_sack")
        parser.add_argument("--json", action="store_true", help="Vollständigen Diff als JSON ausgeben.")

    def handle(self, *args, **options):
        try:
            waste_type = WasteType.objects.get(slug=options["waste_type"])
        except WasteType.DoesNotExist as exc:
            raise CommandError(f"Abfallart {options['waste_type']!r} nicht gefunden.") from exc

        plan = get_parser(options["parser"]).parse(options["file"])
        diff = diff_streets(plan, waste_type)
        if options["json"]:
            self.stdout.write(json.dumps(diff, ensure_ascii=False, indent=2))
            return
        summary = diff["summary"]
        self.stdout.write(
            f"Neu: {summary['added']}, entfernt: {summary['removed']}, "
            f"geändert: {summary['changed']}, unverändert: {summary['unchanged']}"
        )
        for street in diff["streets_added"][:20]:
            self.stdout.write(f"  + {street['name']} → {', '.join(street['zones'])}")
        for street in diff["assignments_changed"][:20]:
            self.stdout.write(
                f"  ~ {street['name']}: {', '.join(street['zones_old'])} → {', '.join(street['zones_new'])}"
            )
