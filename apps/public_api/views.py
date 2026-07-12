"""Versioned public JSON API (§33).

Design: no internal IDs (streets expose an opaque `id` only for follow-up
requests within the API, addresses expose the stable public_id), no
statistics, no reporter contact data, rate limited, paginated.
"""

import json

from django.http import HttpResponseNotAllowed, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from apps.addresses.models import AddressKey, Street
from apps.addresses.services import resolve_address, search_streets
from apps.community.models import (
    CorrectionProposal,
    ErrorReport,
    ProposalStatus,
    ProposalVote,
    ReportCategory,
)
from apps.core.http import session_hash
from apps.core.ratelimit import is_rate_limited
from apps.core.text import parse_house_number
from apps.schedules.models import CollectionDate, ScheduleYearStatus
from apps.schedules.services import published_dates_for_address
from apps.waste_types.models import WasteType


def _error(message: str, status: int = 400, code: str = "bad_request") -> JsonResponse:
    return JsonResponse({"error": {"code": code, "message": message}}, status=status)


def _paginate(request, queryset, serializer, default_limit=50, max_limit=200):
    try:
        limit = min(int(request.GET.get("limit", default_limit)), max_limit)
        offset = max(int(request.GET.get("offset", 0)), 0)
    except ValueError:
        limit, offset = default_limit, 0
    total = queryset.count() if hasattr(queryset, "count") else len(queryset)
    items = [serializer(obj) for obj in queryset[offset : offset + limit]]
    return {"count": total, "limit": limit, "offset": offset, "results": items}


def _rate_limited(request) -> JsonResponse | None:
    if is_rate_limited(request, "api"):
        return _error("Zu viele Anfragen.", status=429, code="rate_limited")
    return None


def waste_types(request):
    if limited := _rate_limited(request):
        return limited
    data = [
        {"slug": wt.slug, "name": wt.name, "icon": wt.icon, "color": wt.color}
        for wt in WasteType.objects.filter(is_active=True)
    ]
    return JsonResponse({"results": data})


def streets(request):
    if limited := _rate_limited(request):
        return limited
    query = request.GET.get("q", "")
    if len(query.strip()) < 2:
        return _error("Parameter q (mindestens 2 Zeichen) erforderlich.")
    results = search_streets(query, limit=25)
    return JsonResponse(
        {
            "results": [
                {
                    "id": street.pk,
                    "name": street.name,
                    "district": street.district.name if street.district else None,
                    "city": street.city.name,
                }
                for street in results
            ]
        }
    )


def resolve(request):
    if limited := _rate_limited(request):
        return limited
    street_name = request.GET.get("street", "")
    street_id = request.GET.get("street_id")
    if street_id:
        street = Street.objects.filter(pk=street_id, is_active=True).first()
    elif street_name:
        matches = list(search_streets(street_name, limit=2))
        if len(matches) > 1 and not request.GET.get("district"):
            district = request.GET.get("district")
            matches = [m for m in matches if m.district and m.district.name == district] or matches
        street = matches[0] if len(matches) == 1 else None
        if street is None and matches:
            return _error(
                "Straße ist mehrdeutig – bitte street_id oder district angeben.", code="ambiguous"
            )
    else:
        return _error("Parameter street oder street_id erforderlich.")
    if street is None:
        return _error("Straße nicht gefunden.", status=404, code="not_found")

    number, suffix = parse_house_number(request.GET.get("house_number", ""))
    result = resolve_address(street, number, suffix)
    if result.needs_house_number:
        return _error("Für diese Straße wird eine Hausnummer benötigt.", code="house_number_required")
    if not result.ok:
        return _error(result.error, status=404, code="no_assignment")
    return JsonResponse(
        {
            "public_id": result.address_key.public_id,
            "address": result.address_key.full_label,
            "zones": [
                {"code": zone.code, "waste_type": zone.waste_type.slug} for zone in result.zones
            ],
        }
    )


def collections(request, public_id):
    if limited := _rate_limited(request):
        return limited
    address_key = AddressKey.objects.filter(public_id=public_id).first()
    if address_key is None:
        return _error("Adresse nicht gefunden.", status=404, code="not_found")
    year = None
    if request.GET.get("year"):
        try:
            year = int(request.GET["year"])
        except ValueError:
            return _error("Ungültiges Jahr.")
    waste_type = None
    if request.GET.get("waste_type"):
        waste_type = WasteType.objects.filter(slug=request.GET["waste_type"]).first()
        if waste_type is None:
            return _error("Abfallart nicht gefunden.", status=404, code="not_found")
    dates = published_dates_for_address(address_key, waste_type=waste_type, year=year)
    payload = _paginate(
        request,
        dates,
        lambda record: {
            "date": record.date.isoformat(),
            "waste_type": record.zone.waste_type.slug,
            "zone": record.zone.code,
            "kind": record.kind,
            "note": record.note,
        },
    )
    payload["public_id"] = address_key.public_id
    return JsonResponse(payload)


def zone_collections(request, code):
    if limited := _rate_limited(request):
        return limited
    year = request.GET.get("year")
    queryset = CollectionDate.objects.filter(
        zone__code=code.upper(),
        schedule_year__status=ScheduleYearStatus.PUBLISHED,
        is_cancelled=False,
    ).select_related("zone", "zone__waste_type")
    if request.GET.get("waste_type"):
        queryset = queryset.filter(zone__waste_type__slug=request.GET["waste_type"])
    if year:
        try:
            queryset = queryset.filter(schedule_year__year=int(year))
        except ValueError:
            return _error("Ungültiges Jahr.")
    if not queryset.exists():
        return _error("Keine Termine für diesen Bezirk gefunden.", status=404, code="not_found")
    payload = _paginate(
        request,
        queryset.order_by("date"),
        lambda record: {
            "date": record.date.isoformat(),
            "waste_type": record.zone.waste_type.slug,
            "zone": record.zone.code,
            "kind": record.kind,
        },
    )
    return JsonResponse(payload)


@csrf_exempt
def create_report(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if is_rate_limited(request, "report"):
        return _error("Zu viele Meldungen.", status=429, code="rate_limited")
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _error("Ungültiges JSON.")
    category = data.get("category")
    description = (data.get("description") or "").strip()
    if category not in ReportCategory.values:
        return _error(f"category muss eines von {ReportCategory.values} sein.")
    if len(description) < 10:
        return _error("description (mindestens 10 Zeichen) erforderlich.")
    address_key = None
    if data.get("public_id"):
        address_key = AddressKey.objects.filter(public_id=data["public_id"]).first()
    report = ErrorReport.objects.create(
        category=category,
        description=description[:5000],
        source_hint=(data.get("source") or "")[:255],
        contact_email=(data.get("contact_email") or "")[:254],
        address_key=address_key,
        street=address_key.street if address_key else None,
        session_hash=session_hash(request),
    )
    return JsonResponse({"token": report.public_token, "status": report.status}, status=201)


@csrf_exempt
def create_correction(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if is_rate_limited(request, "report"):
        return _error("Zu viele Vorschläge.", status=429, code="rate_limited")
    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return _error("Ungültiges JSON.")
    from apps.community.models import ProposalKind

    kind = data.get("kind")
    reason = (data.get("reason") or "").strip()
    if kind not in ProposalKind.values:
        return _error(f"kind muss eines von {ProposalKind.values} sein.")
    if len(reason) < 10:
        return _error("reason (mindestens 10 Zeichen) erforderlich.")
    proposal = CorrectionProposal.objects.create(
        kind=kind,
        reason=reason[:5000],
        old_value=data.get("old_value") or {},
        new_value=data.get("new_value") or {},
        source_url=(data.get("source_url") or "")[:200],
        contact_email=(data.get("contact_email") or "")[:254],
        session_hash=session_hash(request),
    )
    return JsonResponse({"id": proposal.pk, "status": proposal.status}, status=201)


@csrf_exempt
def confirm_proposal(request, pk):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    if is_rate_limited(request, "vote"):
        return _error("Zu viele Bestätigungen.", status=429, code="rate_limited")
    proposal = CorrectionProposal.objects.filter(
        pk=pk, status__in=[ProposalStatus.SUBMITTED, ProposalStatus.AWAITING_CONFIRMATION]
    ).first()
    if proposal is None:
        return _error("Vorschlag nicht gefunden oder nicht mehr offen.", status=404, code="not_found")
    _, created = ProposalVote.objects.get_or_create(
        proposal=proposal, session_hash=session_hash(request), defaults={"is_support": True}
    )
    if created:
        CorrectionProposal.objects.filter(pk=proposal.pk).update(
            confirmations=proposal.votes.filter(is_support=True).count(),
            status=ProposalStatus.AWAITING_CONFIRMATION,
        )
    return JsonResponse({"id": proposal.pk, "counted": created})


def openapi_spec(request):
    from django.conf import settings

    spec_path = settings.BASE_DIR / "docs" / "openapi.json"
    with open(spec_path, encoding="utf-8") as handle:
        return JsonResponse(json.load(handle))
