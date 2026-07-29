"""Serializers for all models."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import (
    Organisation, Vehicle, Driver, Trip, FuelRecord, TripStatusLog, TripPosition,
    CommodityCategory, Commodity, UserProfile, estimate_revenue,
)

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(max_length=120)

    def validate_username(self, v):
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("username already taken")
        return v

    def create(self, validated):
        user = User.objects.create_user(
            username=validated["username"],
            password=validated["password"],
        )
        org, _ = Organisation.objects.get_or_create(
            slug="default",
            defaults={"name": user.username},
        )
        UserProfile.objects.get_or_create(user=user, defaults={"organisation": org})
        Driver.objects.create(user=user, name=validated["name"], organisation=org)
        token, _ = Token.objects.get_or_create(user=user)
        return {"user": user, "token": token}


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_staff", read_only=True)
    driver_id = serializers.SerializerMethodField()
    organisation_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "is_admin", "driver_id", "organisation_id", "date_joined"]

    def get_driver_id(self, obj):
        try:
            return obj.driver_profile.id
        except Driver.DoesNotExist:
            return None

    def get_organisation_id(self, obj):
        if hasattr(obj, "profile") and obj.profile.organisation_id:
            return obj.profile.organisation_id
        try:
            if obj.driver_profile and obj.driver_profile.organisation_id:
                return obj.driver_profile.organisation_id
        except Driver.DoesNotExist:
            pass
        return None


class CommodityCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CommodityCategory
        fields = ["id", "name", "icon"]


class CommoditySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_icon = serializers.CharField(source="category.icon", read_only=True)

    class Meta:
        model = Commodity
        fields = [
            "id", "name", "category", "category_name", "category_icon",
            "unit", "rate_per_km", "rate_per_kg", "flat_fee", "is_active",
        ]


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = [
            "id", "name", "slug", "license_key", "licensed_vehicles",
            "contact_phone", "contact_email", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VehicleSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="organisation.name", read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id", "organisation", "organisation_name",
            "plate", "make", "model", "year", "fuel_type",
            "fuel_consumption_rate_l_100km", "tank_capacity_l",
            "service_interval_km", "last_service_km", "current_odometer_km",
            "status", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VehicleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "plate", "make", "model", "year", "fuel_type",
            "fuel_consumption_rate_l_100km", "tank_capacity_l",
            "service_interval_km", "last_service_km", "current_odometer_km",
            "status",
        ]


class DriverSerializer(serializers.ModelSerializer):
    organisation_name = serializers.CharField(source="organisation.name", read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id", "organisation", "organisation_name", "user",
            "name", "phone_number", "licence_number", "licence_expiry",
            "rate_per_day_usd", "rate_per_km_usd", "status",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DriverCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            "name", "phone_number", "licence_number",
            "licence_expiry", "rate_per_day_usd", "rate_per_km_usd",
        ]


class TripRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    waypoints = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False, default=list,
    )
    driver_id = serializers.IntegerField(required=False, allow_null=True)
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    commodity_id = serializers.IntegerField(required=False, allow_null=True)
    load_weight_tonnes = serializers.FloatField(required=False, allow_null=True)
    estimated_revenue = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True,
    )
    cycle_used_hrs = serializers.FloatField(required=False, default=0.0)
    use_sleeper_berth = serializers.BooleanField(required=False, default=True)


class TripEstimateSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    waypoints = serializers.ListField(
        child=serializers.CharField(max_length=200),
        required=False, default=list,
    )
    vehicle_id = serializers.IntegerField(required=False, allow_null=True)
    driver_id = serializers.IntegerField(required=False, allow_null=True)
    fuel_price_per_litre_usd = serializers.FloatField(default=1.60)
    border_crossings = serializers.IntegerField(default=0)
    tolls_usd = serializers.FloatField(default=0.0)
    cycle_used_hrs = serializers.FloatField(required=False, default=0.0)
    use_sleeper_berth = serializers.BooleanField(required=False, default=True)


class TripStatusLogSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source="updated_by.username", read_only=True)

    class Meta:
        model = TripStatusLog
        fields = [
            "id", "trip", "from_status", "to_status",
            "location_text", "notes", "timestamp",
            "updated_by", "updated_by_name",
        ]
        read_only_fields = ["id", "timestamp"]


class TripSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.name", read_only=True, default=None)
    vehicle_plate = serializers.CharField(source="vehicle.plate", read_only=True, default=None)
    status_logs = TripStatusLogSerializer(many=True, read_only=True, source="tripstatuslog_set")
    commodity_data = CommoditySerializer(source="commodity", read_only=True)

    class Meta:
        model = Trip
        fields = [
            "id", "organisation", "vehicle", "vehicle_plate",
            "driver", "driver_name",
            "origin", "destination", "waypoints", "distance_km",
            "scheduled_start", "actual_start", "actual_end",
            "estimated_fuel_cost_usd", "estimated_driver_pay_usd",
            "estimated_border_fees_usd", "estimated_tolls_usd",
            "estimated_total_cost_usd",
            "actual_fuel_cost_usd", "actual_driver_pay_usd",
            "actual_border_fees_usd", "actual_total_cost_usd",
            "revenue_usd", "estimated_revenue",
            "route_geometry",
            "status", "priority", "load_type", "load_weight_tonnes",
            "commodity", "commodity_data",
            "sos_triggered_at", "sos_acknowledged_at", "sos_message",
            "notes", "cycle_used_hrs", "hos_daily_logs",
            "waypoints_geocoded",
            "created_at", "updated_at",
            "status_logs",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "commodity_data", "sos_triggered_at", "sos_acknowledged_at", "hos_daily_logs", "waypoints_geocoded"]


class TripUpdateSerializer(serializers.ModelSerializer):
    """Used for PATCH — status changes, cost updates, notes, commodity."""
    class Meta:
        model = Trip
        fields = [
            "status", "priority", "notes",
            "actual_fuel_cost_usd", "actual_driver_pay_usd",
            "actual_border_fees_usd", "actual_total_cost_usd",
            "revenue_usd", "estimated_revenue",
            "load_type", "load_weight_tonnes", "commodity",
            "sos_message", "cycle_used_hrs",
        ]


class FuelRecordSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.username", read_only=True)

    class Meta:
        model = FuelRecord
        fields = [
            "id", "trip", "vehicle", "litres",
            "price_per_litre_usd", "total_cost_usd",
            "location_text", "recorded_by", "recorded_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class FuelRecordCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelRecord
        fields = [
            "trip", "vehicle", "litres",
            "price_per_litre_usd", "total_cost_usd", "location_text",
        ]


class TripPositionSerializer(serializers.ModelSerializer):
    reported_by_name = serializers.CharField(source="reported_by.username", read_only=True)

    class Meta:
        model = TripPosition
        fields = [
            "id", "trip", "lat", "lon", "accuracy",
            "source", "remark", "timestamp",
            "reported_by", "reported_by_name",
        ]
        read_only_fields = ["id", "timestamp"]


class TripPositionCreateSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lon = serializers.FloatField()
    accuracy = serializers.FloatField(required=False)
    source = serializers.CharField(required=False, default="manual")
    remark = serializers.CharField(required=False, allow_blank=True, default="")
