from django.core.management.base import BaseCommand

from apps.data_sources.models import DataSource, SourceKind
from apps.imports.services import run_import
from apps.notifications.services import notify_admins


class Command(BaseCommand):
    help = "Prüft aktive Datenquellen auf neue Versionen und archiviert sie (§14)."

    def add_arguments(self, parser):
        parser.add_argument("--source-id", type=int, help="Nur diese Datenquelle prüfen.")
        parser.add_argument("--force", action="store_true", help="Cache-Header ignorieren.")
        parser.add_argument(
            "--import", action="store_true", dest="run_import",
            help="Neue Dokumente direkt parsen und zur Prüfung bereitstellen.",
        )

    def handle(self, *args, **options):
        from apps.data_sources.services import fetch_source

        sources = DataSource.objects.filter(is_active=True, kind=SourceKind.PDF_URL)
        if options["source_id"]:
            sources = sources.filter(pk=options["source_id"])
        if not sources.exists():
            self.stdout.write(self.style.WARNING("Keine aktiven PDF-Datenquellen gefunden."))
            return

        for source in sources:
            result = fetch_source(source, force=options["force"])
            if result.error:
                self.stderr.write(f"{source}: FEHLER – {result.error}")
                continue
            if result.unchanged:
                self.stdout.write(f"{source}: unverändert.")
                continue
            document = result.new_document
            self.stdout.write(self.style.SUCCESS(f"{source}: neue Version archiviert ({document})."))
            notify_admins(
                f"Neue Abfuhrplan-Version: {source.name}",
                f"Es wurde eine neue Version der Quelle „{source.name}“ archiviert.\n"
                f"SHA-256: {document.sha256}\nBitte im Adminbereich prüfen und freigeben.",
            )
            if options["run_import"]:
                if source.parser_key == "luebeck_ebl":
                    # one PDF → all four waste types; staged for review
                    from apps.imports.ebl_import import run_ebl_import

                    import_run = run_ebl_import(document.file.path, source_document=document)
                else:
                    import_run = run_import(document, source.waste_type)
                self.stdout.write(f"  Importlauf #{import_run.pk}: {import_run.get_status_display()}")
