from django.shortcuts import render


def error_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def error_500(request):
    return render(request, "errors/500.html", status=500)


def error_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def imprint(request):
    return render(request, "pages/impressum.html")


def privacy(request):
    return render(request, "pages/datenschutz.html")


def api_docs(request):
    from apps.addresses.models import AddressKey
    from apps.waste_types.models import WasteType

    # a real, resolvable example address for copy-paste examples (fallback: none)
    example = AddressKey.objects.filter(house_number__isnull=False).order_by("pk").first()
    return render(
        request,
        "pages/api.html",
        {
            "waste_types": WasteType.objects.filter(is_active=True),
            "example_public_id": example.public_id if example else "<public_id>",
        },
    )


def admin_dashboard(request):
    """Custom /admin/ start page: KPIs, quick actions and an explainer for
    every admin area ("was ist das und wozu brauche ich das?")."""
    from django.contrib.admin.views.decorators import staff_member_required

    @staff_member_required
    def _view(request):
        from datetime import date, timedelta

        from apps.analytics.models import AnalyticsEvent, EventType
        from apps.community.models import CorrectionProposal, ErrorReport
        from apps.imports.models import ImportRun
        from apps.schedules.services import data_status
        from apps.system_status.checks import run_all_checks

        week_ago = date.today() - timedelta(days=7)
        status = data_status()
        checks = run_all_checks()
        open_reports = ErrorReport.objects.filter(status__in=["new", "in_review"]).count()
        open_proposals = CorrectionProposal.objects.filter(
            status__in=["submitted", "awaiting_confirmation", "quorum_reached", "under_review"]
        ).count()
        review_imports = ImportRun.objects.filter(
            status__in=["needs_review", "validation_failed", "parse_failed"]
        ).count()

        sections = [
            {
                "title": "Termine & Jahrespläne",
                "icon": "fas fa-calendar-alt",
                "color": "teal",
                "text": "Das Herzstück: die veröffentlichten Abfuhrtermine. Ein Jahresplan "
                        "durchläuft Import, Prüfung und Veröffentlichung; erst dann erscheinen "
                        "seine Termine öffentlich und in den Kalender-Feeds. Einzelne Termine "
                        "korrigieren Sie hier (Hinweis setzen, absagen) – die Feeds der "
                        "Abonnenten aktualisieren sich automatisch.",
                "links": [
                    ("Jahrespläne", "/admin/schedules/scheduleyear/"),
                    ("Termine", "/admin/schedules/collectiondate/"),
                    ("Abfuhrbezirke", "/admin/schedules/collectionzone/"),
                ],
            },
            {
                "title": "Adress-Stammdaten",
                "icon": "fas fa-road",
                "color": "blue",
                "text": "Straßen, Hausnummern und ihre Zuordnung zu Abfuhrbezirken. Diese Daten "
                        "bleiben über Jahre stabil und werden von Importen nie automatisch "
                        "überschrieben. Zuordnungen mit Status „in Prüfung“ (mehrdeutige "
                        "Hausnummernbereiche aus dem PDF) warten hier auf Ihre Freigabe.",
                "links": [
                    ("Straßen", "/admin/addresses/street/"),
                    ("Tourenzuordnungen", "/admin/addresses/streetassignment/"),
                    ("Hausnummern", "/admin/addresses/housenumber/"),
                    ("Ortsteile", "/admin/addresses/district/"),
                ],
            },
            {
                "title": "Abfallarten",
                "icon": "fas fa-recycle",
                "color": "amber",
                "text": "Gelber Sack, Restabfall, Bioabfall, Papier – mit Farbe, Icon und den "
                        "Texten für die Kalendereinträge. Nur aktive Abfallarten erscheinen in "
                        "Suche, Terminlisten und Feeds.",
                "links": [("Abfallarten", "/admin/waste_types/wastetype/")],
            },
            {
                "title": "Datenquellen & Importe",
                "icon": "fas fa-file-import",
                "color": "violet",
                "text": "Woher die Daten kommen: der offizielle Gelber-Sack-PDF (täglich "
                        "automatisch geprüft) und der EBL-Online-Kalender. Jeder Importlauf "
                        "protokolliert Statistik, Warnungen und Diffs – nichts geht ungeprüft "
                        "live. Neue Planversionen erscheinen hier zur Freigabe.",
                "links": [
                    ("Importläufe", "/admin/imports/importrun/"),
                    ("Datenquellen", "/admin/data_sources/datasource/"),
                    ("Archivierte Dokumente", "/admin/data_sources/sourcedocument/"),
                ],
            },
            {
                "title": "Community & Moderation",
                "icon": "fas fa-comments",
                "color": "red",
                "text": "Fehlermeldungen und Korrekturvorschläge aus der Bürgerschaft. Die "
                        "Moderationsqueue bündelt alles, was Aufmerksamkeit braucht; "
                        "Quorum-Regeln steuern das Gewicht von Bestätigungen "
                        "(Community-Modus ist standardmäßig aus).",
                "links": [
                    ("Moderationsqueue", "/intern/moderation/"),
                    ("Fehlermeldungen", "/admin/community/errorreport/"),
                    ("Korrekturvorschläge", "/admin/community/correctionproposal/"),
                    ("Quorum-Regeln", "/admin/community/quorumrule/"),
                ],
            },
            {
                "title": "Statistik",
                "icon": "fas fa-chart-line",
                "color": "green",
                "text": "Datenschutzfreundliche Nutzungszahlen (keine IP-Adressen, täglich "
                        "rotierende Hashes): Suchen, Terminaufrufe, Feed-Abrufe, geschätzte "
                        "Abonnements, erfolglose Suchbegriffe. Nur intern sichtbar.",
                "links": [("Statistik-Dashboard", "/intern/statistik/")],
            },
            {
                "title": "System & Sicherheit",
                "icon": "fas fa-shield-halved",
                "color": "slate",
                "text": "Benutzer und Rollen (Datenmanager, Moderator, Analyst, Auditor), das "
                        "unveränderliche Audit-Log aller Datenänderungen und der technische "
                        "Systemstatus (Quellen-Freshness, Speicher, offene Prüfungen).",
                "links": [
                    ("Systemstatus", "/intern/status/"),
                    ("Benutzer", "/admin/accounts/user/"),
                    ("Gruppen/Rollen", "/admin/auth/group/"),
                    ("Audit-Log", "/admin/audit/auditlog/"),
                ],
            },
        ]

        from django.contrib import admin as django_admin

        context = {
            **django_admin.site.each_context(request),
            "title": "Dashboard",
            "status": status,
            "checks": checks,
            "checks_ok": all(c["ok"] for c in checks),
            "open_reports": open_reports,
            "open_proposals": open_proposals,
            "review_imports": review_imports,
            "feed_week": AnalyticsEvent.objects.filter(
                event_type=EventType.CALENDAR_FEED_REQUESTED, created_at__date__gte=week_ago
            ).count(),
            "views_week": AnalyticsEvent.objects.filter(
                event_type=EventType.PAGE_VIEW, created_at__date__gte=week_ago
            ).count(),
            "recent_imports": ImportRun.objects.order_by("-started_at")[:5],
            "recent_reports": ErrorReport.objects.order_by("-created_at")[:5],
            "sections": sections,
        }
        return render(request, "admin/dashboard.html", context)

    return _view(request)
