"""Trip + Driver + Auth serializers."""
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from .models import Driver, DayHistory, Trip

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(max_length=120)
    carrier = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    home_terminal = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")

    def validate_username(self, v):
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("username already taken")
        return v

    def create(self, validated):
        user = User.objects.create_user(
            username=validated["username"],
            password=validated["password"],
        )
        Driver.objects.create(
            user=user,
            name=validated["name"],
            carrier=validated.get("carrier", ""),
            home_terminal=validated.get("home_terminal", ""),
        )
        token, _ = Token.objects.get_or_create(user=user)
        return {"user": user, "token": token}


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_staff", read_only=True)
    driver_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "is_admin", "driver_id", "date_joined"]

    def get_driver_id(self, obj):
        try:
            return obj.driver_profile.id
        except Driver.DoesNotExist:
            return None


class DayHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DayHistory
        fields = ["id", "date", "on_duty_hrs", "driving_hrs", "source"]


class DriverSerializer(serializers.ModelSerializer):
    day_history = DayHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id", "name", "carrier", "default_truck_number",
            "home_terminal", "main_office", "current_cycle_used_hrs",
            "created_at", "updated_at", "day_history",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "day_history"]


class DriverCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = [
            "name", "carrier", "default_truck_number",
            "home_terminal", "main_office", "current_cycle_used_hrs",
        ]


class TripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=200)
    pickup_location = serializers.CharField(max_length=200)
    dropoff_location = serializers.CharField(max_length=200)
    current_cycle_used_hrs = serializers.FloatField(min_value=0, max_value=70, default=0)
    avg_speed_mph = serializers.FloatField(min_value=20, max_value=80, default=55)
    use_sleeper_berth = serializers.BooleanField(default=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
    driver_id = serializers.IntegerField(required=False, allow_null=True)


class TripSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source="driver.name", read_only=True, default=None)

    class Meta:
        model = Trip
        fields = [
            "id", "driver", "driver_name",
            "current_location", "pickup_location", "dropoff_location",
            "current_cycle_used_hrs", "use_sleeper_berth",
            "total_miles", "total_days", "total_driving_hrs", "total_on_duty_hrs",
            "final_cycle_used", "recap_approximate", "created_at",
        ]
        read_only_fields = fields
