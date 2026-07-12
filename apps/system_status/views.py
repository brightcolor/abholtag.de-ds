from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render

from .checks import check_database, run_all_checks


def health(request):
    checks = run_all_checks()
    ok = all(c["ok"] for c in checks)
    return JsonResponse(
        {"status": "ok" if ok else "degraded", "checks": {c["name"]: c["ok"] for c in checks}},
        status=200 if ok else 503,
    )


def health_live(request):
    return JsonResponse({"status": "alive"})


def health_ready(request):
    db = check_database()
    return JsonResponse({"status": "ready" if db["ok"] else "unavailable"}, status=200 if db["ok"] else 503)


def public_status(request):
    """Minimal public status page – no internal metrics (§17)."""
    from apps.schedules.services import data_status

    return render(request, "status.html", {"status": data_status()})


@staff_member_required
def admin_status(request):
    from apps.data_sources.models import DataSource, SourceDocument
    from apps.imports.models import ImportRun

    return render(
        request,
        "system_status/status.html",
        {
            "title": "Systemstatus",
            "checks": run_all_checks(),
            "sources": DataSource.objects.filter(is_active=True),
            "documents": SourceDocument.objects.order_by("-fetched_at")[:10],
            "import_runs": ImportRun.objects.order_by("-started_at")[:10],
        },
    )
