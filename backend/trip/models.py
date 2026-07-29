import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models


class CommodityCategory(models.Model):
    """Grouping for commodity types (Agriculture, Mining, Fuel, etc.)."""
    name = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        verbose_name_plural = "commodity categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Commodity(models.Model):
    """A specific cargo type with pricing rules."""
    name = models.CharField(max_length=100)
    category = models.ForeignKey(
        CommodityCategory, on_delete=models.PROTECT,
        related_name="commodities",
    )
    unit = models.CharField(max_length=20, default="tonne")
    rate_per_km = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    rate_per_kg = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    flat_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "commodities"
        ordering = ["category__name", "name"]

    def __str__(self):
        return self.name


def estimate_revenue(commodity, distance_km, weight_tonnes):
    """Compute estimated revenue from commodity pricing rules."""
    if not commodity:
        return None
    total = Decimal("0.00")
    if commodity.rate_per_km and distance_km:
        total += commodity.rate_per_km * Decimal(str(distance_km))
    if commodity.rate_per_kg and weight_tonnes:
        total += commodity.rate_per_kg * Decimal(str(weight_tonnes)) * Decimal("1000")
    if commodity.flat_fee:
        total += commodity.flat_fee
    return round(total, 2) if total else None


class OrganisationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class Organisation(models.Model):
    """Fleet owner organisation."""
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100, unique=True)
    license_key = models.CharField(max_length=100, blank=True, default="")
    licensed_vehicles = models.IntegerField(default=50)
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = OrganisationQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save(update_fields=["is_deleted"])


class UserProfile(models.Model):
    """Profile linking a User to an Organisation."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    organisation = models.ForeignKey(
        Organisation, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="members",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["user__username"]

    def __str__(self):
        return f"{self.user.username} @ {self.organisation or 'unaffiliated'}"


class VehicleQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class Vehicle(models.Model):
    """A vehicle in the fleet."""
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="vehicles",
    )
    plate = models.CharField(max_length=20)
    make = models.CharField(max_length=50, blank=True, default="")
    model = models.CharField(max_length=50, blank=True, default="")
    year = models.IntegerField(null=True, blank=True)
    fuel_type = models.CharField(
        max_length=20,
        choices=[
            ("diesel", "Diesel"),
            ("petrol", "Petrol"),
        ],
        default="diesel",
    )
    fuel_consumption_rate_l_100km = models.FloatField(default=0.0)
    tank_capacity_l = models.FloatField(default=0.0)
    service_interval_km = models.FloatField(default=5000.0)
    last_service_km = models.FloatField(default=0.0)
    current_odometer_km = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=20,
        choices=[
            ("active", "Active"),
            ("maintenance", "In Maintenance"),
            ("retired", "Retired"),
        ],
        default="active",
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VehicleQuerySet.as_manager()

    class Meta:
        ordering = ["plate"]
        unique_together = [("organisation", "plate")]
        indexes = [
            models.Index(fields=["organisation", "status"]),
            models.Index(fields=["plate"]),
        ]

    def __str__(self):
        return f"{self.plate} ({self.make} {self.model})"

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])


class DriverQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_deleted=False)


class Driver(models.Model):
    """Persistent driver profile.

    Linked to Organisation. Optional OneToOne to auth.User for login.
    """
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="drivers",
        null=True, blank=True,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="driver_profile",
    )
    name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=30, blank=True, default="")
    licence_number = models.CharField(max_length=50, blank=True, default="")
    licence_expiry = models.DateField(null=True, blank=True)
    rate_per_day_usd = models.FloatField(default=0.0)
    rate_per_km_usd = models.FloatField(default=0.0)
    status = models.CharField(
        max_length=20,
        choices=[("active", "Active"), ("inactive", "Inactive")],
        default="active",
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = DriverQuerySet.as_manager()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["organisation", "status"]),
            models.Index(fields=["phone_number"]),
        ]

    def __str__(self):
        return self.name

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])


class Trip(models.Model):
    """A planned trip with cost and revenue tracking.

    Booking statuses:
      inquiry    – customer submitted a booking request
      quoted     – admin sent a quote
      confirmed  – customer accepted the quote / booking confirmed
      assigned   – admin assigned driver + vehicle
      dispatched – driver en route to pickup
      ...
    """
    organisation = models.ForeignKey(
        Organisation, on_delete=models.CASCADE, related_name="trips",
        null=True, blank=True,
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="trips",
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="trips",
    )
    origin = models.CharField(max_length=200)
    destination = models.CharField(max_length=200)
    waypoints = models.JSONField(default=list, blank=True)
    distance_km = models.FloatField(default=0.0)

    scheduled_start = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)

    origin_address = models.CharField(max_length=500, blank=True, default="")
    destination_address = models.CharField(max_length=500, blank=True, default="")
    pickup_notes = models.TextField(blank=True, default="")
    delivery_notes = models.TextField(blank=True, default="")

    estimated_fuel_cost_usd = models.FloatField(default=0.0)
    estimated_driver_pay_usd = models.FloatField(default=0.0)
    estimated_border_fees_usd = models.FloatField(default=0.0)
    estimated_tolls_usd = models.FloatField(default=0.0)
    estimated_total_cost_usd = models.FloatField(default=0.0)
    actual_fuel_cost_usd = models.FloatField(null=True, blank=True)
    actual_driver_pay_usd = models.FloatField(null=True, blank=True)
    actual_border_fees_usd = models.FloatField(null=True, blank=True)
    actual_total_cost_usd = models.FloatField(null=True, blank=True)
    revenue_usd = models.FloatField(null=True, blank=True)

    service_type = models.CharField(
        max_length=30,
        blank=True, default="",
        choices=[
            ("household", "Household Removal"),
            ("grocery", "Grocery Delivery"),
            ("construction", "Construction Materials"),
            ("furniture", "Furniture Delivery"),
            ("office", "Office Relocation"),
            ("long_distance", "Long Distance"),
            ("custom", "Custom Transport"),
        ],
    )
    booking_reference = models.CharField(
        max_length=20, unique=True, null=True, blank=True,
    )
    customer_name = models.CharField(max_length=200, blank=True, default="")
    customer_phone = models.CharField(max_length=30, blank=True, default="")
    customer_email = models.EmailField(blank=True, default="")
    customer_token = models.UUIDField(default=uuid.uuid4, null=True, blank=True)
    booking_time_preference = models.JSONField(null=True, blank=True)
    cargo_items = models.JSONField(null=True, blank=True)
    truck_recommendation = models.JSONField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ("inquiry", "Inquiry"),
            ("quoted", "Quoted"),
            ("confirmed", "Confirmed"),
            ("assigned", "Assigned"),
            ("dispatched", "Dispatched"),
            ("at_border", "At Border"),
            ("in_transit", "In Transit"),
            ("delivered", "Delivered"),
            ("paid", "Paid"),
            ("cancelled", "Cancelled"),
        ],
        default="inquiry",
    )
    priority = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("normal", "Normal"),
            ("high", "High"),
            ("urgent", "Urgent"),
        ],
        default="normal",
    )
    load_type = models.CharField(
        max_length=50, blank=True, default="general",
        choices=[
            ("general", "General"),
            ("fuel", "Fuel"),
            ("containers", "Containers"),
            ("grains", "Grains"),
            ("mining", "Mining"),
            ("other", "Other"),
        ],
    )
    load_weight_tonnes = models.FloatField(null=True, blank=True)
    commodity = models.ForeignKey(
        Commodity, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="trips",
    )
    estimated_revenue = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
    )
    route_geometry = models.JSONField(null=True, blank=True)
    sos_triggered_at = models.DateTimeField(null=True, blank=True)
    sos_acknowledged_at = models.DateTimeField(null=True, blank=True)
    sos_message = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    cycle_used_hrs = models.FloatField(default=0.0)
    hos_daily_logs = models.JSONField(null=True, blank=True)
    waypoints_geocoded = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["organisation", "status"]),
            models.Index(fields=["driver", "status"]),
            models.Index(fields=["vehicle", "status"]),
        ]

    def __str__(self):
        who = self.driver.name if self.driver else "anonymous"
        return f"{who}: {self.origin} -> {self.destination} ({self.distance_km:.0f}km)"


class FuelRecord(models.Model):
    """Fuel purchase logged against a trip."""
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="fuel_records",
    )
    vehicle = models.ForeignKey(
        Vehicle, on_delete=models.CASCADE, related_name="fuel_records",
    )
    litres = models.FloatField()
    price_per_litre_usd = models.FloatField()
    total_cost_usd = models.FloatField()
    location_text = models.CharField(max_length=200, blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="fuel_records",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.litres}L @ ${self.price_per_litre_usd}/L ({self.created_at.date()})"


class TripStatusLog(models.Model):
    """Audit log of trip status changes."""
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="status_logs",
    )
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20)
    location_text = models.CharField(max_length=200, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="status_logs",
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.trip} {self.from_status} -> {self.to_status}"


class TripPosition(models.Model):
    """A GPS position reported during a trip."""
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="positions",
    )
    lat = models.FloatField()
    lon = models.FloatField()
    accuracy = models.FloatField(null=True, blank=True)
    source = models.CharField(
        max_length=20,
        choices=[
            ("manual", "Manual Entry"),
            ("gps", "Browser GPS"),
            ("whatsapp", "WhatsApp Share"),
        ],
        default="manual",
    )
    remark = models.CharField(max_length=200, blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reported_positions",
    )

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"Trip {self.trip_id} @ {self.lat:.4f},{self.lon:.4f} ({self.source})"


class TripImage(models.Model):
    """An image attached to a trip/booking."""
    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, related_name="images",
    )
    image = models.ImageField(upload_to="uploads/bookings/%Y/%m/%d/")
    caption = models.CharField(max_length=255, blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="uploaded_trip_images",
    )

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Image for Trip {self.trip_id}: {self.caption or '(no caption)'}"


class CustomerProfile(models.Model):
    """Optional customer account linked to bookings via phone number."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, null=True, blank=True,
        related_name="customer_profile",
    )
    phone = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name or self.phone}"
