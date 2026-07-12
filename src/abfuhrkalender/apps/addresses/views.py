"""Addresses views - street search, autocomplete, address resolution."""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.views.generic import TemplateView, View
from django.db.models import Q
from .models import Street, StreetAssignment, AddressKey
from ..schedules.models import CollectionDate, ScheduleYear


class StreetSearchView(View):
    """HTMX-Autocomplete für Straßensuche."""

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "").strip()
        if len(q) < 2:
            return render(request, "addresses/_street_results.html", {"results": [], "query": q})

        from .models import Street
        search = Street.normalize_name(q)
        results = Street.objects.filter(
            Q(search_name__icontains=search) | Q(search_name__startswith=search),
            is_active=True,
        ).select_related("district").order_by("name")[:15]

        return render(request, "addresses/_street_results.html", {
            "results": results,
            "query": q,
        })


class AddressResolveView(View):
    """Löst eine Adresse auf und zeigt die Terminübersicht."""

    def get(self, request, *args, **kwargs):
        street_id = request.GET.get("street")
        house_number = request.GET.get("house_number", "").strip()
        waste_type_slug = request.GET.get("waste_type", "gelber-sack")

        if not street_id:
            return JsonResponse({"error": "Straße erforderlich"}, status=400)

        street = get_object_or_404(Street, id=street_id, is_active=True)

        # Find matching assignment
        assignments = StreetAssignment.objects.filter(
            street=street,
            zone__waste_type__slug=waste_type_slug,
        ).select_related("zone")

        if not assignments.exists():
            return render(request, "addresses/_no_assignment.html", {"street": street})

        # If only one assignment and no house number needed, use it
        if assignments.count() == 1 and not street.has_number_ranges:
            assignment = assignments.first()
        elif assignments.count() == 1 and street.has_number_ranges and house_number:
            assignment = assignments.first()
        elif assignments.count() > 1:
            # Multiple zones - try to match by house number
            if house_number:
                assignment = self._match_house_number(assignments, house_number)
            else:
                return render(request, "addresses/_number_required.html", {
                    "street": street,
                    "assignments": assignments,
                })
        else:
            assignment = assignments.first()

        if not assignment:
            return render(request, "addresses/_no_assignment.html", {"street": street})

        # Get or create address key
        addr_key, _ = AddressKey.objects.get_or_create(
            street=street,
            house_number=house_number,
            house_number_suffix="",
        )

        # Get upcoming dates
        current_year = ScheduleYear.objects.filter(
            waste_type__slug=waste_type_slug,
            status="published",
        ).order_by("-year").first()

        dates = []
        if current_year:
            dates = CollectionDate.objects.filter(
                schedule_year=current_year,
                zone=assignment.zone,
                collection_date__gte="2026-01-01",
            ).order_by("collection_date")[:10]

        next_date = dates[0] if dates else None

        return render(request, "addresses/_schedule_result.html", {
            "street": street,
            "assignment": assignment,
            "address_key": addr_key,
            "dates": dates,
            "next_date": next_date,
            "waste_type_slug": waste_type_slug,
            "calendar_year": current_year.year if current_year else None,
        })

    def _match_house_number(self, assignments, house_number):
        """Finde passende Zuordnung anhand der Hausnummer."""
        # Strip suffix for comparison
        import re
        num_match = re.match(r"(\d+)([a-zA-Z]?)", house_number)
        if not num_match:
            return assignments.first()

        num = int(num_match.group(1))
        suffix = num_match.group(2)

        for a in assignments:
            start = int(a.house_number_start) if a.house_number_start else 0
            end = int(a.house_number_end) if a.house_number_end else float("inf")

            if a.house_number_parity == "even" and num % 2 != 0:
                continue
            if a.house_number_parity == "odd" and num % 2 != 1:
                continue
            if a.house_number_suffix and suffix != a.house_number_suffix:
                continue

            if start <= num <= end:
                return a

        return assignments.first()