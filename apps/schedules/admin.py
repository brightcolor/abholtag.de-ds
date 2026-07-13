from django.contrib import admin

from .models import CollectionDate, CollectionZone, ScheduleYear

STATUS_BADGE_COLORS = {
    "published": "success", "completed": "success", "approved": "success",
    "resolved": "success", "accepted": "success", "active": "success",
    "needs_review": "warning", "parsed": "warning", "in_review": "warning",
    "awaiting_confirmation": "warning", "quorum_reached": "warning",
    "pending": "warning", "running": "info", "new": "info", "submitted": "info",
    "discovered": "info", "downloaded": "info",
}


def status_badge(obj):
    """Farbiges Status-Badge statt nacktem Text in den Listen."""
    from django.utils.html import format_html

    color = STATUS_BADGE_COLORS.get(obj.status, "danger" if "fail" in obj.status or obj.status in (
        "rejected", "withdrawn", "duplicate", "retired", "expired") else "secondary")
    return format_html('<span class="badge badge-{}">{}</span>', color, obj.get_status_display())


status_badge.short_description = "Status"
status_badge.admin_order_field = "status"



@admin.register(CollectionZone)
class CollectionZoneAdmin(admin.ModelAdmin):
    list_display = ("code", "waste_type", "name", "is_active")
    list_filter = ("waste_type", "is_active")
    search_fields = ("code", "name", "waste_type__name")


@admin.register(ScheduleYear)
class ScheduleYearAdmin(admin.ModelAdmin):
    list_display = ("waste_type", "year", status_badge, "published_at", "source_document")
    list_filter = ("waste_type", "status", "year")
    readonly_fields = ("published_at",)


@admin.register(CollectionDate)
class CollectionDateAdmin(admin.ModelAdmin):
    list_display = ("date", "zone", "kind", "origin", "is_cancelled", "note")
    list_filter = ("zone__waste_type", "zone", "kind", "origin", "is_cancelled", "schedule_year__year")
    search_fields = ("note",)
    date_hierarchy = "date"
    autocomplete_fields = ("zone",)
