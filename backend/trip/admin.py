from django.contrib import admin
from .models import Driver, DayHistory, Trip


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ("name", "carrier", "current_cycle_used_hrs", "user", "created_at")
    list_filter = ("carrier",)
    search_fields = ("name", "carrier", "home_terminal", "user__username")


@admin.register(DayHistory)
class DayHistoryAdmin(admin.ModelAdmin):
    list_display = ("driver", "date", "on_duty_hrs", "driving_hrs", "source")
    list_filter = ("source", "date")
    search_fields = ("driver__name",)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("__str__", "total_miles", "total_days", "final_cycle_used", "recap_approximate", "created_at")
    list_filter = ("recap_approximate", "use_sleeper_berth")
    search_fields = ("current_location", "pickup_location", "dropoff_location", "driver__name")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
