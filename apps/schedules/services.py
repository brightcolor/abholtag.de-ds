"""Query services around published collection dates."""

from datetime import date as date_cls

from django.db.models import Max

from apps.addresses.models import AddressKey
from apps.addresses.services import zones_for_address_key

from .models import CollectionDate, ScheduleYear, ScheduleYearStatus


def published_dates_for_address(address_key: AddressKey, waste_type=None, year: int | None = None):
    """All published, non-cancelled dates for an address (all matching zones)."""
    zones = zones_for_address_key(address_key, waste_type=waste_type)
    qs = (
        CollectionDate.objects.filter(
            zone__in=zones,
            schedule_year__status=ScheduleYearStatus.PUBLISHED,
            is_cancelled=False,
        )
        .select_related("zone", "zone__waste_type", "schedule_year")
        .order_by("date")
    )
    if year:
        qs = qs.filter(schedule_year__year=year)
    return qs


def feed_dates_for_address(address_key: AddressKey, waste_type=None):
    """Dates for ICS feeds – includes cancelled dates so clients remove them."""
    zones = zones_for_address_key(address_key, waste_type=waste_type)
    return (
        CollectionDate.objects.filter(
            zone__in=zones, schedule_year__status=ScheduleYearStatus.PUBLISHED
        )
        .select_related("zone", "zone__waste_type", "schedule_year")
        .order_by("date")
    )


def upcoming_dates_for_address(address_key: AddressKey, waste_type=None, limit: int = 10):
    today = date_cls.today()
    return list(published_dates_for_address(address_key, waste_type).filter(date__gte=today)[:limit])


def data_status():
    """Aggregate data freshness info for the public start page (§9)."""
    from apps.addresses.models import Street
    from apps.waste_types.models import WasteType

    published_years = ScheduleYear.objects.filter(status=ScheduleYearStatus.PUBLISHED)
    return {
        "street_count": Street.objects.filter(is_active=True).count(),
        "waste_type_count": WasteType.objects.filter(is_active=True).count(),
        "published_years": sorted({sy.year for sy in published_years}),
        "date_count": CollectionDate.objects.filter(
            schedule_year__status=ScheduleYearStatus.PUBLISHED, is_cancelled=False
        ).count(),
        "last_update": published_years.aggregate(m=Max("updated_at"))["m"],
    }
