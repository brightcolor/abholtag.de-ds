"""Import the official EBL "Wegweiser" PDF (all four waste streams at once).

Usage:
    python manage.py import_ebl --path data/samples/abfuhrplan-ebl-2026.pdf
    python manage.py import_ebl --source-id 3            # archived document
    python manage.py import_ebl --path <pdf> --publish   # go live immediately

Without --publish the schedule years are staged as "Prüfung erforderlich" and
must be released with `publish_waste_schedule` (or in the admin).
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.data_sources.models import SourceDocument
from apps.imports.ebl_import import run_ebl_import
from apps.imports.models import ImportRunStatus


class Command(BaseCommand):
    help = "Importiert den EBL-Abfuhrplan (Restabfall, Bioabfall, Papier, Gelber Sack)."

    def add_arguments(self, parser):
        parser.add_argument("--path", help="Pfad zur EBL-PDF-Datei.")
        parser.add_argument("--source-id", type=int, help="Archiviertes Quelldokument (ID).")
        parser.add_argument(
            "--publish", action="store_true",
            help="Jahrespläne direkt veröffentlichen (sonst zur Prüfung stellen).",
        )

    def handle(self, *args, **options):
        source_document = None
        if options["source_id"]:
            source_document = SourceDocument.objects.filter(pk=options["source_id"]).first()
            if not source_document:
                raise CommandError(f"Quelldokument #{options['source_id']} nicht gefunden.")
            path = source_document.file.path
        elif options["path"]:
            path = options["path"]
            if not Path(path).exists():
                raise CommandError(f"Datei nicht gefunden: {path}")
        else:
            raise CommandError("Bitte --path ODER --source-id angeben.")

        self.stdout.write(f"Verarbeite EBL-Plan: {path} …")
        run = run_ebl_import(path, source_document=source_document, publish=options["publish"])

        if run.status == ImportRunStatus.PARSE_FAILED:
            raise CommandError(f"Parserlauf fehlgeschlagen: {run.log}")
        if run.status == ImportRunStatus.VALIDATION_FAILED:
            for issue in run.blocking_issues:
                self.stderr.write(f"  FEHLER [{issue.get('waste_type', '')}] {issue['message']}")
            raise CommandError("Validierung fehlgeschlagen – nichts geschrieben.")

        for slug, s in run.stats.get("waste_types", {}).items():
            self.stdout.write(
                f"  {slug}: {s['dates']} Termine, {len(s['zones'])} Touren, "
                f"{s['assignments_created']} Zuordnungen "
                f"({s['assignments_pending']} zur Prüfung, "
                f"{s['streets_not_matched']} Straßen ohne Treffer)"
            )
        for issue in run.warning_issues:
            self.stdout.write(
                self.style.WARNING(f"  Hinweis [{issue.get('waste_type', '')}] {issue['message']}")
            )

        style = self.style.SUCCESS if run.status == ImportRunStatus.COMPLETED else self.style.WARNING
        self.stdout.write(style(f"EBL-Import abgeschlossen: {run.get_status_display()}"))
        if not options["publish"]:
            self.stdout.write(
                "Zum Veröffentlichen: python manage.py publish_waste_schedule "
                "--waste-type <slug> --year <jahr>  (für jede Abfallart)"
            )
