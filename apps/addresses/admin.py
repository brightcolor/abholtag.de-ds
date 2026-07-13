from django.contrib import admin

from apps.schedules.admin import status_badge

from .models import (
    AddressKey,
    City,
    District,
    HouseNumber,
    Street,
    StreetAlias,
    StreetAssignment,
)


@admin.register(HouseNumber)
class HouseNumberAdmin(admin.ModelAdmin):
    list_display = ("street", "text", "bms_location_id", "origin")
    search_fields = ("street__name", "text", "bms_location_id")
    autocomplete_fields = ("street",)
    list_filter = ("origin",)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ("name", "city")
    list_filter = ("city",)
    prepopulated_fields = {"slug": ("name",)}


class StreetAliasInline(admin.TabularInline):
    model = StreetAlias
    extra = 0


class StreetAssignmentInline(admin.TabularInline):
    model = StreetAssignment
    extra = 0
    autocomplete_fields = ("zone",)


@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "city", "is_active", "origin", "bms_street_id")
    list_filter = ("is_active", "district", "origin")
    search_fields = ("name", "normalized_name", "aliases__name")
    inlines = [StreetAliasInline, StreetAssignmentInline]


@admin.register(StreetAssignment)
class StreetAssignmentAdmin(admin.ModelAdmin):
    list_display = ("street", "zone", "house_from", "house_to", "parity", status_badge, "origin")
    list_filter = ("zone", "status", "parity", "origin")
    search_fields = ("street__name", "raw_range")
    autocomplete_fields = ("street", "zone")


@admin.register(StreetAlias)
class StreetAliasAdmin(admin.ModelAdmin):
    list_display = ("name", "street")
    search_fields = ("name", "street__name")
    autocomplete_fields = ("street",)


@admin.register(AddressKey)
class AddressKeyAdmin(admin.ModelAdmin):
    list_display = ("public_id", "street", "house_number", "suffix", "created_at")
    search_fields = ("public_id", "street__name")
    readonly_fields = ("public_id",)
    autocomplete_fields = ("street",)
