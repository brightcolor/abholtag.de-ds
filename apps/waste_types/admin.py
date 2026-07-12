from django.contrib import admin

from .models import WasteType


@admin.register(WasteType)
class WasteTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "sort_order", "reminder_hours_before")
    list_editable = ("is_active", "sort_order")
    prepopulated_fields = {"slug": ("name",)}
