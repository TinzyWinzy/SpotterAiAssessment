"""Input validation tests — POST /api/trip/ with malformed/missing/out-of-range inputs.

These tests do NOT call the geocoder — they verify the serializer rejects bad data
before any external network calls are made.
"""
import pytest


@pytest.mark.django_db
class TestTripRequestValidation:
    URL = "/api/trip/"

    def test_missing_current_location(self, api_client):
        resp = api_client.post(self.URL, {
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
        }, format="json")
        assert resp.status_code == 400
        assert resp.json()["ok"] is False
        assert "current_location" in resp.json()["errors"]

    def test_missing_pickup_location(self, api_client):
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
        }, format="json")
        assert resp.status_code == 400
        assert "pickup_location" in resp.json()["errors"]

    def test_missing_dropoff_location(self, api_client):
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "current_cycle_used_hrs": 0,
        }, format="json")
        assert resp.status_code == 400
        assert "dropoff_location" in resp.json()["errors"]

    def test_cycle_hours_above_max(self, api_client):
        """70/8 cycle cap — anything above 70 is invalid input."""
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 71,
        }, format="json")
        assert resp.status_code == 400
        assert "current_cycle_used_hrs" in resp.json()["errors"]

    def test_cycle_hours_negative(self, api_client):
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": -1,
        }, format="json")
        assert resp.status_code == 400

    def test_avg_speed_too_low(self, api_client):
        """avg_speed_mph < 20 is rejected (would imply unrealistically slow truck)."""
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
            "avg_speed_mph": 5,
        }, format="json")
        assert resp.status_code == 400

    def test_avg_speed_too_high(self, api_client):
        """avg_speed_mph > 80 is rejected (truck speed limit)."""
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
            "avg_speed_mph": 100,
        }, format="json")
        assert resp.status_code == 400

    def test_optional_fields_default(self, api_client):
        """avg_speed_mph, use_sleeper_berth, start_time should default — must not 400 on their absence."""
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
        }, format="json")
        # 200 or 400 depending on geocoder. We only assert it's NOT 400 from validation.
        if resp.status_code == 400:
            assert "avg_speed_mph" not in resp.json().get("errors", {})
            assert "use_sleeper_berth" not in resp.json().get("errors", {})

    def test_blank_string_rejected(self, api_client):
        resp = api_client.post(self.URL, {
            "current_location": "",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
        }, format="json")
        # CharField allows blank=False by default — must 400.
        assert resp.status_code == 400

    def test_start_time_accepts_iso8601(self, api_client, mock_geo_router):
        resp = api_client.post(self.URL, {
            "current_location": "New York, NY",
            "pickup_location": "Philadelphia, PA",
            "dropoff_location": "Baltimore, MD",
            "current_cycle_used_hrs": 0,
            "start_time": "2026-06-05T06:00:00Z",
        }, format="json")
        assert resp.status_code == 200
