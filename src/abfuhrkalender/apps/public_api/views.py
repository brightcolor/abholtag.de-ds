"""Public JSON API v1 views."""
from django.http import JsonResponse
from django.views.generic import View
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from ..waste_types.models import WasteType
from ..addresses.models import Street, AddressKey, StreetAssignment
from ..schedules.models import CollectionDate, ScheduleYear
from ..community.models import ErrorReport, CorrectionProposal


class WasteTypeListAPI(View):
    def get(self, request, *args, **kwargs):
        types = WasteType.objects.filter(is_active=True).values("slug", "name", "color_hex", "icon_name")
        return JsonResponse(list(types), safe=False)


class StreetSearchAPI(View):
    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return JsonResponse({"results": []})
        search = Street.normalize_name(q)
        streets = Street.objects.filter(search_name__icontains=search, is_active=True)[:20]
        return JsonResponse({
            "results": [
                {"id": str(s.id), "name": s.name, "district": str(s.district) if s.district else None}
                for s in streets
            ]
        })


class AddressResolveAPI(View):
    def get(self, request, *args, **kwargs):
        street_id = request.GET.get("street")
        house_number = request.GET.get("house_number", "")
        waste_type = request.GET.get("waste_type", "gelber-sack")
        if not street_id:
            return JsonResponse({"error": "street required"}, status=400)
        return JsonResponse({"status": "not_implemented"}, status=501)


class AddressCollectionsAPI(View):
    def get(self, request, public_id, *args, **kwargs):
        return JsonResponse({"status": "not_implemented"}, status=501)


class ZoneCollectionsAPI(View):
    def get(self, request, letter, *args, **kwargs):
        return JsonResponse({"status": "not_implemented"}, status=501)


class CreateReportAPI(View):
    def post(self, request, *args, **kwargs):
        return JsonResponse({"status": "not_implemented"}, status=501)


class CreateCorrectionAPI(View):
    def post(self, request, *args, **kwargs):
        return JsonResponse({"status": "not_implemented"}, status=501)
