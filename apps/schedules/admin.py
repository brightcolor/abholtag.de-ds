from django.contrib import admin

from .models import CollectionDate, CollectionZone, ScheduleYear


@admin.register(CollectionZone)
class CollectionZoneAdmin(admin.ModelAdmin):
    list_display = ("code", "waste_type", "name", "is_active")
    list_filter = ("waste_type", "is_active")
    search_fields = ("code", "name", "waste_type__name")


@admin.register(ScheduleYear)
class ScheduleYearAdmin(admin.ModelAdmin):
    list_display = ("waste_type", "year", "status", "published_at", "source_document")
    list_filter = ("waste_type", "status", "year")
    readonly_fields = ("published_at",)


@admin.register(CollectionDate)
class CollectionDateAdmin(admin.ModelAdmin):
    list_display = ("date", "zone", "kind", "origin", "is_cancelled", "note")
    list_filter = ("zone__waste_type", "zone", "kind", "origin", "is_cancelled", "schedule_year__year")
    search_fields = ("note",)
    date_hierarchy = "date"
    autocomplete_fields = ("zone",)
