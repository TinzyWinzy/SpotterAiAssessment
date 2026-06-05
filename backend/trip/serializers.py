"""Trip serializer — validates and normalizes incoming API requests."""
from rest_framework import serializers


class TripRequestSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=200)
    pickup_location = serializers.CharField(max_length=200)
    dropoff_location = serializers.CharField(max_length=200)
    current_cycle_used_hrs = serializers.FloatField(min_value=0, max_value=70, default=0)
    avg_speed_mph = serializers.FloatField(min_value=20, max_value=80, default=55)
    use_sleeper_berth = serializers.BooleanField(default=True)
    start_time = serializers.DateTimeField(required=False, allow_null=True)
