from datetime import date as date_cls

from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.shortcuts import get_object_or_404, render
from django.utils.http import http_date

from apps.addresses.models import AddressKey
from apps.analytics.services import record_event
from apps.schedules.services import feed_dates_for_address, upcoming_dates_for_address
from apps.schedules.views import selected_waste_types
from apps.waste_types.models import WasteType

from .ics import build_calendar, calendar_etag


def _feed_response(request, address_key, waste_types, name: str, event: str):
    dates = feed_dates_for_address(address_key, waste_types)
    with_alarm = request.GET.get("erinnerung") == "1"
    content = build_calendar(address_key, dates, name, with_alarm=with_alarm)
    etag = calendar_etag(content)

    last_modified = max((d.updated_at for d in dates), default=None)
    first_type = waste_types[0] if waste_types and len(waste_types) == 1 else None

    if request.headers.get("If-None-Match") == etag:
        record_event(request, event, address_key=address_key, waste_type=first_type, status="304")
        return HttpResponseNotModified()

    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=3600"
    if last_modified:
        response.headers["Last-Modified"] = http_date(last_modified.timestamp())
    filename = f"abfuhrkalender-{address_key.public_id}.ics"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    record_event(request, event, address_key=address_key, waste_type=first_type, status="200")
    return response


def address_feed(request, public_id, waste_slug):
    address_key = get_object_or_404(
        AddressKey.objects.select_related("street", "street__city"), public_id=public_id
    )
    if waste_slug == "all":
        # optional: ?arten=slug1,slug2 filtert den Kombi-Feed
        selected, slugs = selected_waste_types(request)
        waste_types = list(selected) if slugs else None
        if slugs:
            name = f"Abfuhrtermine ({len(slugs)} Arten) – {address_key.label}"
        else:
            name = f"Abfuhrtermine – {address_key.label}"
    else:
        waste_type = WasteType.objects.filter(slug=waste_slug).first()
        if waste_type is None:
            raise Http404
        waste_types = [waste_type]
        name = f"{waste_type.name} – {address_key.label}"
    event = "calendar_downloaded" if "download" in request.GET else "calendar_feed_requested"
    return _feed_response(request, address_key, waste_types, name, event)


def subscribe_page(request, public_id):
    address_key = get_object_or_404(
        AddressKey.objects.select_related("street", "street__district", "street__city"),
        public_id=public_id,
    )
    selected, slugs = selected_waste_types(request)
    waste_types = list(selected) if slugs else None

    if slugs and len(slugs) == 1:
        feed_path = f"/calendar/address/{address_key.public_id}/{slugs[0]}.ics"
    elif slugs:
        feed_path = f"/calendar/address/{address_key.public_id}/all.ics?arten=" + ",".join(slugs)
    else:
        feed_path = f"/calendar/address/{address_key.public_id}/all.ics"

    record_event(
        request, "calendar_subscription_page_view", address_key=address_key,
        waste_type=waste_types[0] if waste_types and len(waste_types) == 1 else None,
    )

    # Ein-Klick-Abo fürs Smartphone: webcal:// (Apple) und Google-Kalender-Link
    from urllib.parse import quote

    from django.conf import settings

    host = settings.SITE_BASE_URL.replace("https://", "").replace("http://", "").rstrip("/")
    webcal_url = f"webcal://{host}{feed_path}"
    # Google bekommt die https-URL direkt: webcal wird von Google zu http://
    # normalisiert und der Redirect auf https lässt den Kalender leer bleiben.
    https_url = f"{settings.SITE_BASE_URL.rstrip('/')}{feed_path}"
    google_url = "https://calendar.google.com/calendar/render?cid=" + quote(https_url, safe="")

    return render(
        request,
        "subscribe.html",
        {
            "address_key": address_key,
            "selected_types": waste_types,
            "feed_path": feed_path,
            "webcal_url": webcal_url,
            "google_url": google_url,
            "upcoming": upcoming_dates_for_address(address_key, waste_types, limit=5),
            "today": date_cls.today(),
        },
    )
