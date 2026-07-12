"""System health checks for /health endpoints and the status page (§37)."""

import shutil
from datetime import date, timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone


def check_database() -> dict:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return {"name": "Datenbank", "ok": True, "detail": "Verbindung erfolgreich."}
    except Exception as exc:  # noqa: BLE001
        return {"name": "Datenbank", "ok": False, "detail": str(exc)}


def check_disk() -> dict:
    try:
        usage = shutil.disk_usage(settings.MEDIA_ROOT if settings.MEDIA_ROOT.exists() else ".")
        free_gb = usage.free / (1024**3)
        return {
            "name": "Speicher",
            "ok": free_gb > 1.0,
            "detail": f"{free_gb:.1f} GB frei",
        }
    except Exception as exc:  # noqa: BLE001
        return {"name": "Speicher", "ok": False, "detail": str(exc)}


def check_source_freshness() -> dict:
    from apps.data_sources.models import DataSource

    sources = DataSource.objects.filter(is_active=True, kind="pdf_url")
    if not sources.exists():
        return {"name": "PDF-Abruf", "ok": True, "detail": "Keine aktiven URL-Quellen konfiguriert."}
    stale = []
    for source in sources:
        limit = timezone.now() - timedelta(hours=source.check_interval_hours * 3)
        if source.last_checked_at is None or source.last_checked_at < limit:
            stale.append(source.name)
    if stale:
        return {"name": "PDF-Abruf", "ok": False, "detail": f"Überfällig: {', '.join(stale)}"}
    return {"name": "PDF-Abruf", "ok": True, "detail": "Alle Quellen fristgerecht geprüft."}


def check_published_year() -> dict:
    from apps.schedules.models import ScheduleYear, ScheduleYearStatus
    from apps.waste_types.models import WasteType

    today = date.today()
    missing = []
    for waste_type in WasteType.objects.filter(is_active=True):
        current = ScheduleYear.objects.filter(
            waste_type=waste_type, year=today.year, status=ScheduleYearStatus.PUBLISHED
        ).exists()
        if not current:
            missing.append(f"{waste_type.name} {today.year}")
        # From October on, warn if next year's plan is not at least in review.
        if today.month >= 10:
            upcoming = ScheduleYear.objects.filter(
                waste_type=waste_type, year=today.year + 1
            ).exists()
            if not upcoming:
                missing.append(f"{waste_type.name} {today.year + 1} (noch nicht importiert)")
    if missing:
        return {"name": "Jahrespläne", "ok": False, "detail": "Fehlt: " + ", ".join(missing)}
    return {"name": "Jahrespläne", "ok": True, "detail": "Aktuelle Pläne veröffentlicht."}


def check_moderation_backlog() -> dict:
    from apps.community.models import CorrectionProposal, ErrorReport

    open_reports = ErrorReport.objects.filter(status__in=["new", "in_review"]).count()
    open_proposals = CorrectionProposal.objects.filter(
        status__in=["submitted", "awaiting_confirmation", "quorum_reached", "under_review"]
    ).count()
    total = open_reports + open_proposals
    return {
        "name": "Moderation",
        "ok": total < 50,
        "detail": f"{open_reports} offene Meldungen, {open_proposals} offene Vorschläge",
    }


def run_all_checks() -> list[dict]:
    return [
        check_database(),
        check_disk(),
        check_source_freshness(),
        check_published_year(),
        check_moderation_backlog(),
    ]
