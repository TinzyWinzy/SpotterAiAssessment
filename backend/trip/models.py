from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Driver(models.Model):
    """Persistent driver profile.

    `current_cycle_used_hrs` is a cached convenience for the API
    fallback path (when the driver has no DayHistory records it matches
    the input shape of the legacy `current_cycle_used_hrs` field).
    The authoritative value is the rolling sum of `DayHistory.on_duty_hrs`.

    Optional OneToOne to a Django `auth.User` (set on register/login)
    so drivers can authenticate and the admin dashboard can scope by
    account.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name="driver_profile",
    )
    name = models.CharField(max_length=120)
    carrier = models.CharField(max_length=200, blank=True, default="")
    default_truck_number = models.CharField(max_length=40, blank=True, default="")
    home_terminal = models.CharField(max_length=120, blank=True, default="")
    main_office = models.CharField(max_length=200, blank=True, default="")
    current_cycle_used_hrs = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0), MaxValueValidator(70)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.carrier})" if self.carrier else self.name


class DayHistory(models.Model):
    """One day of a driver's on-duty history, used to compute the real
    recap table (no approximation) on the FMCSA paper form.

    `source='generated'` records are created automatically when a trip
    is planned for the driver, so each trip extends the rolling 8-day
    window. `source='manual'` records are imported from another system
    (ELD export, payroll, etc.) and never overwritten.
    """
    SOURCE_MANUAL = "manual"
    SOURCE_GENERATED = "generated"
    SOURCE_CHOICES = [
        (SOURCE_MANUAL, "Manual"),
        (SOURCE_GENERATED, "Generated"),
    ]

    driver = models.ForeignKey(Driver, on_delete=models.CASCADE, related_name="day_history")
    date = models.DateField()
    on_duty_hrs = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(24)])
    driving_hrs = models.FloatField(default=0.0, validators=[MinValueValidator(0), MaxValueValidator(24)])
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date"]
        unique_together = [("driver", "date", "source")]

    def __str__(self):
        return f"{self.driver.name} {self.date} {self.on_duty_hrs:.1f}h ({self.source})"


class Trip(models.Model):
    """A planned trip, persisted for the admin dashboard.

    Stores the input the user submitted plus a compact summary of the
    output (totals + first-day recap). The full day-by-day event list is
    not persisted here; the response payload is the source of truth
    while the user has it open.
    """
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="trips",
    )
    current_location = models.CharField(max_length=200)
    pickup_location = models.CharField(max_length=200)
    dropoff_location = models.CharField(max_length=200)
    current_cycle_used_hrs = models.FloatField(default=0.0)
    use_sleeper_berth = models.BooleanField(default=True)

    total_miles = models.FloatField()
    total_days = models.IntegerField()
    total_driving_hrs = models.FloatField()
    total_on_duty_hrs = models.FloatField()
    final_cycle_used = models.FloatField()
    recap_approximate = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["-created_at"])]

    def __str__(self):
        who = self.driver.name if self.driver else "anonymous"
        return f"{who}: {self.current_location} → {self.dropoff_location} ({self.total_miles:.0f}mi, {self.total_days}d)"
