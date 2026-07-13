import json
from datetime import date as date_cls

from django.shortcuts import get_object_or_404, redirect, render

from apps.addresses.models import AddressKey, Street
from apps.addresses.services import resolve_address
from apps.analytics.services import record_event
from apps.core.text import parse_house_number
from apps.waste_types.models import WasteType

from .services import data_status, published_dates_for_address


def selected_waste_types(request):
    """Parse the multi-select waste type filter.

    Sources (in order): repeated ``arten`` values (checkboxes), a comma
    separated ``arten`` value (links/feeds), legacy single ``abfallart``.
    Returns (queryset, slugs) – empty slugs means "all active types".
    """
    raw: list[str] = []
    for value in request.GET.getlist("arten"):
        raw += [part.strip() for part in value.split(",") if part.strip()]
    if not raw and request.GET.get("abfallart"):
        raw = [request.GET["abfallart"]]
    active = WasteType.objects.filter(is_active=True)
    selected = active.filter(slug__in=raw) if raw else active.none()
    slugs = sorted(wt.slug for wt in selected)
    if slugs and len(slugs) == active.count():
        return active, []  # alle ausgewählt = kein Filter
    if not slugs:
        return active, []
    return selected, slugs


def home(request):
    record_event(request, "page_view")
    # random real street names for the search field typewriter demo
    demo_streets = list(
        Street.objects.filter(is_active=True).order_by("?").values_list("name", flat=True)[:12]
    )
    return render(
        request,
        "home.html",
        {
            "status": data_status(),
            "waste_types": WasteType.objects.filter(is_active=True),
            "demo_streets_json": json.dumps(demo_streets, ensure_ascii=False),
        },
    )


def resolve(request):
    """Resolves street + house number and redirects to the address page."""
    street_id = request.GET.get("street_id")
    house_raw = request.GET.get("house_number", "")

    street = Street.objects.filter(pk=street_id, is_active=True).first() if street_id else None
    if street is None:
        record_event(request, "street_search_no_result", status="no_street")
        return render(request, "resolve_failed.html", {"error": "Bitte wählen Sie eine Straße aus der Vorschlagsliste aus."}, status=400)

    number, suffix = parse_house_number(house_raw)

    # Bereichstexte aus der Vorschlagsliste ("21-31") exakt akzeptieren:
    # für die Tourenzuordnung zählt die erste Nummer des Bereichs.
    if number is None and house_raw.strip():
        import re as _re

        exact_row = street.house_numbers.filter(text__iexact=house_raw.strip()).first()
        if exact_row:
            first_int = _re.match(r"(\d+)", exact_row.text)
            number = int(first_int.group(1)) if first_int else None
            suffix = ""

    # Hausnummern-Abgleich gegen den offiziellen BMS-Bestand: existiert die
    # Nummer laut EBL nicht, zeigen wir Vorschläge statt falscher Termine.
    from apps.addresses.services import find_house_number, house_number_suggestions

    if number is not None and street.house_numbers.exists():
        if find_house_number(street, number, suffix) is None:
            record_event(request, "street_search_no_result", street=street, status="no_house_number")
            return render(
                request,
                "resolve_failed.html",
                {
                    "unknown_house_number": True,
                    "entered_number": house_raw.strip(),
                    "street": street,
                    "suggestions": house_number_suggestions(street, number),
                    "arten_query": ",".join(request.GET.getlist("arten")),
                },
                status=200,
            )

    waste_types, selected_slugs = selected_waste_types(request)
    result = resolve_address(street, number, suffix, waste_types=waste_types if selected_slugs else None)

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
    if selected_slugs:
        url += "?arten=" + ",".join(selected_slugs)
    return redirect(url)


BMS_CALENDAR_URL = "https://insert-it.de/BMSAbfallkalenderLuebeck"


def _official_calendar_url(address_key, years) -> str:
    """Direct link to the EBL online calendar for a resolved address (BMS ids)."""
    street = address_key.street
    if not street.bms_street_id or address_key.house_number is None:
        return ""
    house = street.house_numbers.filter(
        number=address_key.house_number, suffix=address_key.suffix or ""
    ).first()
    if house is None:
        return ""
    year = years[-1] if years else date_cls.today().year
    return (
        f"{BMS_CALENDAR_URL}?bmsStreetId={street.bms_street_id}"
        f"&bmsLocationId={house.bms_location_id}&year={year}"
    )


def address_schedule(request, public_id):
    address_key = get_object_or_404(
        AddressKey.objects.select_related("street", "street__district", "street__city"),
        public_id=public_id,
    )
    # Self-healing: fehlt einer BMS-Abfallart die Zuordnung dieser Straße,
    # wird sie einmalig live geholt und dauerhaft übernommen (tagesweise
    # gedrosselt; Seitenaufbau bleibt bei Upstream-Problemen unberührt).
    try:
        from apps.imports.bms_schedule import ensure_bms_schedule_for_street

        ensure_bms_schedule_for_street(address_key.street)
    except Exception:  # noqa: BLE001
        pass

    waste_types, selected_slugs = selected_waste_types(request)
    filter_types = waste_types if selected_slugs else None

    all_dates = list(published_dates_for_address(address_key, filter_types))
    today = date_cls.today()
    upcoming = [d for d in all_dates if d.date >= today]
    next_date = upcoming[0] if upcoming else None
    zones = sorted({d.zone for d in all_dates}, key=lambda z: z.code)
    years = sorted({d.schedule_year.year for d in all_dates})

    # Filter-Chips: Klick schaltet die jeweilige Abfallart um
    active_types = list(WasteType.objects.filter(is_active=True))
    current = set(selected_slugs) if selected_slugs else {wt.slug for wt in active_types}
    chips = []
    for wt in active_types:
        toggled = sorted(current - {wt.slug} if wt.slug in current else current | {wt.slug})
        if not toggled:
            toggled = [wt.slug]  # mindestens eine Art bleibt aktiv
        param = "" if len(toggled) == len(active_types) else "?arten=" + ",".join(toggled)
        chips.append({
            "waste_type": wt,
            "active": wt.slug in current,
            "url": f"/a/{address_key.public_id}/{param}",
        })
    arten_param = ",".join(selected_slugs)

    # Hinweis, falls eine früher aufgelöste Adresse laut BMS-Bestand nicht existiert
    from apps.addresses.services import find_house_number

    house_unknown = bool(
        address_key.house_number is not None
        and address_key.street.house_numbers.exists()
        and find_house_number(address_key.street, address_key.house_number, address_key.suffix) is None
    )

    record_event(
        request,
        "schedule_view",
        street=address_key.street,
        address_key=address_key,
        waste_type=waste_types.first() if selected_slugs else None,
    )
    return render(
        request,
        "schedule.html",
        {
            "address_key": address_key,
            "selected_slugs": selected_slugs,
            "arten_param": arten_param,
            "chips": chips,
            "zones": zones,
            "next_date": next_date,
            "days_until_next": (next_date.date - today).days if next_date else None,
            "upcoming": upcoming[:10],
            "all_dates": all_dates,
            "years": years,
            "today": today,
            "status": data_status(),
            "official_calendar_url": _official_calendar_url(address_key, years),
            "house_unknown": house_unknown,
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
