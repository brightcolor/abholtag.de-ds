from datetime import date as date_cls

from django.shortcuts import get_object_or_404, redirect, render

from apps.addresses.models import AddressKey, Street
from apps.addresses.services import resolve_address
from apps.analytics.services import record_event
from apps.core.text import parse_house_number
from apps.waste_types.models import WasteType

from .services import data_status, published_dates_for_address


def home(request):
    record_event(request, "page_view")
    return render(
        request,
        "home.html",
        {
            "status": data_status(),
            "waste_types": WasteType.objects.filter(is_active=True),
        },
    )


def resolve(request):
    """Resolves street + house number and redirects to the address page."""
    street_id = request.GET.get("street_id")
    house_raw = request.GET.get("house_number", "")
    waste_slug = request.GET.get("waste_type", "")

    street = Street.objects.filter(pk=street_id, is_active=True).first() if street_id else None
    if street is None:
        record_event(request, "street_search_no_result", status="no_street")
        return render(request, "resolve_failed.html", {"error": "Bitte wählen Sie eine Straße aus der Vorschlagsliste aus."}, status=400)

    number, suffix = parse_house_number(house_raw)
    waste_type = WasteType.objects.filter(slug=waste_slug, is_active=True).first()
    result = resolve_address(street, number, suffix, waste_type=waste_type)

    if result.needs_house_number:
        return render(
            request,
            "resolve_failed.html",
            {"error": result.error, "street": street, "needs_house_number": True},
            status=200,
        )
    if not result.ok:
        record_event(request, "street_search_no_result", street=street, status="no_assignment")
        return render(request, "resolve_failed.html", {"error": result.error, "street": street}, status=200)

    record_event(request, "address_resolved", street=street, address_key=result.address_key)
    url = f"/a/{result.address_key.public_id}/"
    if waste_type:
        url += f"?abfallart={waste_type.slug}"
    return redirect(url)


def address_schedule(request, public_id):
    address_key = get_object_or_404(
        AddressKey.objects.select_related("street", "street__district", "street__city"),
        public_id=public_id,
    )
    waste_slug = request.GET.get("abfallart", "")
    waste_type = WasteType.objects.filter(slug=waste_slug, is_active=True).first()

    all_dates = list(published_dates_for_address(address_key, waste_type))
    today = date_cls.today()
    upcoming = [d for d in all_dates if d.date >= today]
    next_date = upcoming[0] if upcoming else None
    zones = sorted({d.zone for d in all_dates}, key=lambda z: z.code)
    years = sorted({d.schedule_year.year for d in all_dates})

    record_event(
        request,
        "schedule_view",
        street=address_key.street,
        address_key=address_key,
        waste_type=waste_type,
    )
    return render(
        request,
        "schedule.html",
        {
            "address_key": address_key,
            "waste_type": waste_type,
            "waste_types": WasteType.objects.filter(is_active=True),
            "zones": zones,
            "next_date": next_date,
            "days_until_next": (next_date.date - today).days if next_date else None,
            "upcoming": upcoming[:10],
            "all_dates": all_dates,
            "years": years,
            "today": today,
            "status": data_status(),
        },
    )


def address_schedule_print(request, public_id):
    address_key = get_object_or_404(AddressKey, public_id=public_id)
    all_dates = list(published_dates_for_address(address_key))
    return render(
        request,
        "schedule_print.html",
        {"address_key": address_key, "all_dates": all_dates, "today": date_cls.today()},
    )
