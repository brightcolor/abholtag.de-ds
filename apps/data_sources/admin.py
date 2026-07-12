from django.contrib import admin

from .models import DataSource, SourceDocument


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "waste_type", "kind", "is_active", "last_checked_at", "last_status")
    list_filter = ("kind", "is_active", "waste_type")
    readonly_fields = (
        "last_checked_at",
        "last_status",
        "last_etag",
        "last_modified_header",
        "last_sha256",
    )


@admin.register(SourceDocument)
class SourceDocumentAdmin(admin.ModelAdmin):
    list_display = ("data_source", "fetched_at", "detected_year", "page_count", "status", "sha256_short")
    list_filter = ("data_source", "status", "detected_year")
    readonly_fields = ("sha256", "size_bytes", "content_type", "etag", "last_modified_header")

    @admin.display(description="SHA-256")
    def sha256_short(self, obj):
        return obj.sha256[:12]
