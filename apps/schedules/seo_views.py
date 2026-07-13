"""Public SEO surfaces: street landing pages and the A–Z street index.

The street pages are the long-tail entry points ("Müllabfuhr <Straße> Lübeck")
and show street-level schedules where the assignment is unambiguous.
"""

from datetime import date as date_cls

from django.shortcuts import get_object_or_404, render

from apps.addresses.models import AssignmentStatus, Street, StreetAssignment
from apps.analytics.services import record_event

from .models import CollectionDate, ScheduleYearStatus
from .services import data_status


def street_index(request):
    """A–Z directory of all supported streets (crawl path + search target)."""
    query = request.GET.get("q", "").strip()
    streets = (
        Street.objects.filter(is_active=True, assignments__status=AssignmentStatus.ACTIVE)
        .select_related("district")
        .distinct()
        .order_by("name")
    )
    if query:
        from apps.addresses.services import search_streets

        streets = search_streets(query, limit=100)

    groups: dict[str, list] = {}
    for street in streets:
        groups.setdefault(street.name[0].upper(), []).append(street)

    return render(
        request,
        "streets_index.html",
        {
            "groups": sorted(groups.items()),
            "query": query,
            "total": sum(len(v) for v in groups.values()),
            "status": data_status(),
        },
    )


def street_page(request, slug):
    """Landing page per street: schedules per waste type at street level."""
    street = get_object_or_404(Street.objects.select_related("district", "city"), slug=slug, is_active=True)
    today = date_cls.today()

    assignments = StreetAssignment.objects.filter(
        street=street, status=AssignmentStatus.ACTIVE
    ).select_related("zone", "zone__waste_type")
    street_wide = [a for a in assignments if a.house_from is None]
    house_dependent = len(street_wide) != len(list(assignments))

    zones = sorted({a.zone for a in street_wide}, key=lambda z: z.code)
    dates = (
        CollectionDate.objects.filter(
            zone__in=zones,
            schedule_year__status=ScheduleYearStatus.PUBLISHED,
            is_cancelled=False,
        )
        .select_related("zone", "zone__waste_type")
        .order_by("date")
    )

    per_type: dict = {}
    for record in dates:
        waste_type = record.zone.waste_type
        entry = per_type.setdefault(
            waste_type.slug,
            {"waste_type": waste_type, "zone": record.zone, "next": None, "upcoming": [], "total": 0},
        )
        entry["total"] += 1
        if record.date >= today:
            if entry["next"] is None:
                entry["next"] = record
            if len(entry["upcoming"]) < 5:
                entry["upcoming"].append(record)

    record_event(request, "schedule_view", street=street)
    years = sorted({d.schedule_year.year for d in dates})
    return render(
        request,
        "street.html",
        {
            "street": street,
            "per_type": sorted(per_type.values(), key=lambda e: e["waste_type"].sort_order),
            "house_dependent": house_dependent,
            "years": years,
            "today": today,
            "status": data_status(),
        },
    )
