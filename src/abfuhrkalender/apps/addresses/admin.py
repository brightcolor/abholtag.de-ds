"""Admin configuration for addresses."""
from django.contrib import admin
from .models import District, Street, StreetAlias, CollectionZone, StreetAssignment, AddressKey

@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ["name", "postal_codes"]
    search_fields = ["name"]

@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ["name", "district", "postal_code", "is_active", "version"]
    list_filter = ["is_active", "district"]
    search_fields = ["name", "search_name"]
    readonly_fields = ["version"]

@admin.register(StreetAlias)
class StreetAliasAdmin(admin.ModelAdmin):
    list_display = ["alias", "street"]
    search_fields = ["alias"]

@admin.register(CollectionZone)
class CollectionZoneAdmin(admin.ModelAdmin):
    list_display = ["letter", "waste_type", "is_active"]
    list_filter = ["waste_type", "is_active"]

@admin.register(StreetAssignment)
class StreetAssignmentAdmin(admin.ModelAdmin):
    list_display = ["street", "zone", "house_number_start", "house_number_end", "valid_from", "valid_until"]
    list_filter = ["zone", "zone__waste_type"]
    search_fields = ["street__name"]
    readonly_fields = ["version"]

@admin.register(AddressKey)
class AddressKeyAdmin(admin.ModelAdmin):
    list_display = ["public_id", "street", "house_number"]
    search_fields = ["public_id", "street__name"]