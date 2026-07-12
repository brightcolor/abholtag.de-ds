"""Admin for data sources."""
from django.contrib import admin
from .models import DataSource, ImportRun

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ["name", "source_type", "is_active"]
    list_filter = ["source_type", "is_active"]

@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ["data_source", "status", "detected_year", "file_hash", "created_at"]
    list_filter = ["status", "data_source"]
    readonly_fields = ["file_hash", "file_size", "started_at", "completed_at"]