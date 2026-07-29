from django.contrib import admin
from .models import (
    Organisation, Vehicle, Driver, Trip, FuelRecord,
    TripStatusLog, TripPosition, CommodityCategory, Commodity,
    UserProfile, TripImage, CustomerProfile,
)


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "licensed_vehicles", "created_at")
    search_fields = ("name", "slug")


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("plate", "make", "model", "fuel_type", "status", "organisation")
    list_filter = ("status", "fuel_type", "organisation")
    search_fields = ("plate", "make", "model")


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "phone_number", "status", "organisation", "created_at")
    list_filter = ("status", "organisation")
    search_fields = ("name", "phone_number", "licence_number")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("__str__", "status", "priority", "distance_km", "commodity", "created_at")
    list_filter = ("status", "priority", "load_type", "commodity")
    search_fields = ("origin", "destination", "driver__name", "vehicle__plate")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(CommodityCategory)
class CommodityCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "icon")
    search_fields = ("name",)


@admin.register(Commodity)
class CommodityAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "rate_per_km", "rate_per_kg", "flat_fee", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name",)


@admin.register(FuelRecord)
class FuelRecordAdmin(admin.ModelAdmin):
    list_display = ("__str__", "trip", "vehicle", "created_at")
    list_filter = ("vehicle",)
    search_fields = ("location_text", "trip__origin", "trip__destination")


@admin.register(TripStatusLog)
class TripStatusLogAdmin(admin.ModelAdmin):
    list_display = ("trip", "from_status", "to_status", "timestamp")
    list_filter = ("to_status",)
    search_fields = ("trip__origin", "notes")
    readonly_fields = ("timestamp",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "organisation", "created_at")
    list_filter = ("organisation",)
    search_fields = ("user__username", "organisation__name")


@admin.register(TripImage)
class TripImageAdmin(admin.ModelAdmin):
    list_display = ("trip", "caption", "uploaded_at")
    list_filter = ("uploaded_at",)
    search_fields = ("trip__booking_reference", "caption")


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ("name", "phone", "email", "created_at")
    search_fields = ("name", "phone", "email")


@admin.register(TripPosition)
class TripPositionAdmin(admin.ModelAdmin):
    list_display = ("trip", "lat", "lon", "source", "timestamp")
    list_filter = ("source",)
    search_fields = ("trip__origin", "remark")
    readonly_fields = ("timestamp",)
