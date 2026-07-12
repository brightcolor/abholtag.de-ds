"""Admin for waste types."""
from django.contrib import admin
from .models import WasteType

@admin.register(WasteType)
class WasteTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "color_hex", "is_active", "sort_order"]
    list_editable = ["sort_order", "is_active"]
    prepopulated_fields = {"slug": ["name"]}