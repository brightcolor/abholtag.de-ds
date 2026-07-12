from django.core.management.base import BaseCommand, CommandError

from apps.imports.models import ImportKind
from apps.imports.services import run_import
from apps.waste_types.models import WasteType


class Command(BaseCommand):
    help = (
        "Importiert die Straßenliste. Bei leerem Straßenstamm wird initial befüllt, "
        "ansonsten wird nur ein Diff erzeugt (§16 – kein automatisches Überschreiben)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--waste-type", required=True)
        parser.add_argument("--file", help="Pfad zu einer lokalen PDF-Datei.")
        parser.add_argument("--document-id", type=int)

    def handle(self, *args, **options):
        from apps.data_sources.models import DataSource, SourceDocument, SourceKind

        try:
            waste_type = WasteType.objects.get(slug=options["waste_type"])
        except WasteType.DoesNotExist as exc:
            raise CommandError(f"Abfallart {options['waste_type']!r} nicht gefunden.") from exc

        if options["document_id"]:
            document = SourceDocument.objects.get(pk=options["document_id"])
        elif options["file"]:
            from apps.data_sources.services import archive_local_file

            source, _ = DataSource.objects.get_or_create(
                waste_type=waste_type,
                kind=SourceKind.MANUAL,
                name=f"Manueller Import {waste_type.name}",
                defaults={"parser_key": "luebeck_gelber_sack"},
            )
            document = archive_local_file(options["file"], source)
        else:
            raise CommandError("Entweder --document-id oder --file angeben.")

        import_run = run_import(document, waste_type, kind=ImportKind.STREETS)
        self.stdout.write(f"Importlauf #{import_run.pk}: {import_run.get_status_display()}")
        self.stdout.write(f"  Statistik: {import_run.stats}")
        if import_run.diff.get("summary"):
            self.stdout.write(f"  Diff: {import_run.diff['summary']}")
            self.stdout.write("  Änderungen bitte im Adminbereich prüfen und übernehmen.")
