"""Calendar feeds and subscription pages."""
from django.http import HttpResponse, Http404
from django.views.generic import TemplateView, View
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ..addresses.models import AddressKey
from ..schedules.models import ScheduleYear, CollectionDate


class CalendarFeedView(View):
    """iCalendar (ICS) Feed für eine Adresse und Abfallart."""

    def get(self, request, address_key_id, waste_type_slug, *args, **kwargs):
        addr_key = get_object_or_404(AddressKey, id=address_key_id)
        schedule = ScheduleYear.objects.filter(
            waste_type__slug=waste_type_slug,
            status="published",
        ).order_by("-year").first()

        if not schedule:
            raise Http404("Kein aktueller Jahresplan vorhanden")

        dates = CollectionDate.objects.filter(
            schedule_year=schedule,
            zone__assignments__street=addr_key.street,
            collection_date__gte=timezone.now().date(),
        ).order_by("collection_date")[:50]

        ics = self._build_ics(addr_key, waste_type_slug, schedule, dates)
        response = HttpResponse(ics, content_type="text/calendar; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{waste_type_slug}-{addr_key.public_id}.ics"'
        response["ETag"] = f'"{abs(hash(ics))}"'
        response["Cache-Control"] = "max-age=3600, public"
        return response

    def _build_ics(self, addr_key, waste_type_slug, schedule, dates):
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Abfuhrkalender Lübeck//DE",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:{} - {}".format(
                waste_type_slug.replace("-", " ").title(),
                str(addr_key),
            ),
        ]
        for i, date in enumerate(dates):
            date_str = date.collection_date.strftime("%Y%m%d")
            uid = f"{addr_key.public_id}-{waste_type_slug}-{date.id}@abfuhrkalender.luebeck"
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uid}",
                f"DTSTART;VALUE=DATE:{date_str}",
                f"DTEND;VALUE=DATE:{date_str}",
                f"SUMMARY:{schedule.waste_type.name}",
                f"DESCRIPTION:Abholung des {schedule.waste_type.name} fuer "
                f"{addr_key.street.name} {addr_key.house_number} in Luebeck.",
                f"LOCATION:{addr_key.street.name} {addr_key.house_number}, 23552 Luebeck",
                f"DTSTAMP:{timezone.now().strftime('%Y%m%dT%H%M%SZ')}",
                "SEQUENCE:0",
                "END:VEVENT",
            ])
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)


class CalendarFeedAllView(View):
    def get(self, request, address_key_id, *args, **kwargs):
        return HttpResponse("Not implemented yet", status=501)


class CalendarSubscribeView(TemplateView):
    template_name = "calendars/subscribe.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        addr_key = get_object_or_404(AddressKey, id=self.kwargs["address_key_id"])
        context["address_key"] = addr_key
        return context