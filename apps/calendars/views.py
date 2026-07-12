from datetime import date as date_cls

from django.http import Http404, HttpResponse, HttpResponseNotModified
from django.shortcuts import get_object_or_404, render
from django.utils.http import http_date

from apps.addresses.models import AddressKey
from apps.analytics.services import record_event
from apps.schedules.services import feed_dates_for_address, upcoming_dates_for_address
from apps.waste_types.models import WasteType

from .ics import build_calendar, calendar_etag


def _feed_response(request, address_key, waste_type, event: str):
    dates = feed_dates_for_address(address_key, waste_type)
    if waste_type:
        name = f"{waste_type.name} – {address_key.label}"
    else:
        name = f"Abfuhrtermine – {address_key.label}"
    with_alarm = request.GET.get("erinnerung") == "1"
    content = build_calendar(address_key, dates, name, with_alarm=with_alarm)
    etag = calendar_etag(content)

    last_modified = max((d.updated_at for d in dates), default=None)

    if request.headers.get("If-None-Match") == etag:
        record_event(request, event, address_key=address_key, waste_type=waste_type, status="304")
        return HttpResponseNotModified()

    response = HttpResponse(content, content_type="text/calendar; charset=utf-8")
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=3600"
    if last_modified:
        response.headers["Last-Modified"] = http_date(last_modified.timestamp())
    filename = f"abfuhrkalender-{address_key.public_id}.ics"
    response.headers["Content-Disposition"] = f'inline; filename="{filename}"'
    record_event(request, event, address_key=address_key, waste_type=waste_type, status="200")
    return response


def address_feed(request, public_id, waste_slug):
    address_key = get_object_or_404(
        AddressKey.objects.select_related("street", "street__city"), public_id=public_id
    )
    if waste_slug == "all":
        waste_type = None
    else:
        waste_type = WasteType.objects.filter(slug=waste_slug).first()
        if waste_type is None:
            raise Http404
    event = "calendar_downloaded" if "download" in request.GET else "calendar_feed_requested"
    return _feed_response(request, address_key, waste_type, event)


def subscribe_page(request, public_id):
    address_key = get_object_or_404(
        AddressKey.objects.select_related("street", "street__district", "street__city"),
        public_id=public_id,
    )
    waste_slug = request.GET.get("abfallart", "")
    waste_type = WasteType.objects.filter(slug=waste_slug, is_active=True).first()
    slug = waste_type.slug if waste_type else "all"

    record_event(request, "calendar_subscription_page_view", address_key=address_key, waste_type=waste_type)
    feed_path = f"/calendar/address/{address_key.public_id}/{slug}.ics"
    return render(
        request,
        "subscribe.html",
        {
            "address_key": address_key,
            "waste_type": waste_type,
            "feed_path": feed_path,
            "upcoming": upcoming_dates_for_address(address_key, waste_type, limit=5),
            "today": date_cls.today(),
        },
    )
