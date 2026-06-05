"""Live network tests — opt-in via --runslow.

These hit real OSRM, Nominatim, and the deployed backend. Useful for
verifying the integration end-to-end against public services.

Run: pytest tests/test_live_*.py --runslow
"""
from __future__ import annotations

import pytest


@pytest.mark.live
class TestLiveGeocoder:
    def test_nominatim_new_york(self):
        import geocoding
        result = geocoding._geocode_nominatim("New York, NY")
        assert result is not None
        assert 40.0 < result["lat"] < 41.5
        assert -75.0 < result["lon"] < -73.0

    def test_photon_new_york(self):
        import geocoding
        result = geocoding._geocode_photon("New York, NY")
        assert result is not None
        assert 40.0 < result["lat"] < 41.5
        assert -75.0 < result["lon"] < -73.0

    def test_photon_falls_back_for_unknown(self):
        """Nominatim should fail on a nonsense query; Photon should also fail."""
        import geocoding
        assert geocoding.geocode("ZZZQXQXQXQXQX") is None


@pytest.mark.live
class TestLiveRouter:
    def test_osrm_nyc_to_baltimore(self):
        import routing
        result = routing.route([
            (-74.0060, 40.7128),  # NYC
            (-76.6122, 39.2904),  # Baltimore
        ])
        assert result is not None
        # Driving distance NYC -> Baltimore is ~190 mi
        assert 150 < result["distance_mi"] < 250
        # At ~55 mph, ~3.5h
        assert 3.0 < result["duration_seconds"] / 3600 < 5.0


@pytest.mark.live
class TestLiveAPI:
    """Hit the deployed backend (Render) end-to-end.

    These tests exercise the full Django -> Nominatim/Photon -> OSRM -> HOS pipeline
    against the production deployment.
    """

    BASE = "https://spotteraiassessment.onrender.com"

    def test_health(self):
        import requests
        r = requests.get(f"{self.BASE}/api/health/", timeout=60)
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_short_trip_end_to_end(self):
        import requests
        r = requests.post(
            f"{self.BASE}/api/trip/",
            json={
                "current_location": "New York, NY",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Baltimore, MD",
                "current_cycle_used_hrs": 0,
                "use_sleeper_berth": True,
            },
            timeout=120,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        # ~190 mi via road
        assert 150 < body["total_distance_mi"] < 250
        assert len(body["days"]) == 1
        d = body["days"][0]
        assert 3.0 <= d["totals"]["driving"] <= 4.5

    def test_long_trip_multi_day(self):
        import requests
        r = requests.post(
            f"{self.BASE}/api/trip/",
            json={
                "current_location": "Los Angeles, CA",
                "pickup_location": "Albuquerque, NM",
                "dropoff_location": "Chicago, IL",
                "current_cycle_used_hrs": 0,
                "use_sleeper_berth": True,
            },
            timeout=120,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["ok"] is True
        assert len(body["days"]) >= 2
        # 24h invariant on every day
        for d in body["days"]:
            total = d["totals"]["off_duty"] + d["totals"]["sleeper"] + d["totals"]["driving"] + d["totals"]["on_duty"]
            assert abs(total - 24.0) < 0.01

    def test_geocoding_failure_returns_400(self):
        import requests
        r = requests.post(
            f"{self.BASE}/api/trip/",
            json={
                "current_location": "ZZZQXQXQXQXQX",
                "pickup_location": "Philadelphia, PA",
                "dropoff_location": "Baltimore, MD",
                "current_cycle_used_hrs": 0,
            },
            timeout=60,
        )
        assert r.status_code == 400
        assert "Geocoding failed" in r.json()["error"]
