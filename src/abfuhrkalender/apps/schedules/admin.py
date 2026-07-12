"""Admin for schedules."""
from django.contrib import admin
from .models import ScheduleYear, CollectionDate

@admin.register(ScheduleYear)
class ScheduleYearAdmin(admin.ModelAdmin):
    list_display = ["waste_type", "year", "status", "published_at"]
    list_filter = ["status", "waste_type"]
    search_fields = ["year"]

@admin.register(CollectionDate)
class CollectionDateAdmin(admin.ModelAdmin):
    list_display = ["collection_date", "zone", "schedule_year", "is_special", "source"]
    list_filter = ["is_special", "source", "schedule_year__year"]
    search_fields = ["zone__letter"]
    date_hierarchy = "collection_date"