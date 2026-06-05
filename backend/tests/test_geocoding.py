"""Geocoder client unit tests — Nominatim + Photon fallback."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import geocoding


class _FakeResp:
    def __init__(self, status, json_data=None, text=""):
        self.status_code = status
        self._json = json_data
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        if self._json is None:
            raise ValueError("no json")
        return self._json


class TestNominatimSuccess:
    def test_returns_parsed_result(self):
        body = [{
            "lat": "40.7128",
            "lon": "-74.0060",
            "display_name": "New York, United States",
            "address": {"city": "New York", "state": "New York"},
        }]
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(200, body)):
            result = geocoding._geocode_nominatim("New York, NY")
        assert result is not None
        assert result["lat"] == 40.7128
        assert result["lon"] == -74.0060
        assert "New York" in result["label"]

    def test_falls_back_to_town(self):
        body = [{
            "lat": "40.0", "lon": "-75.0",
            "display_name": "Somewhere",
            "address": {"town": "Smalltown", "state": "PA"},
        }]
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(200, body)):
            result = geocoding._geocode_nominatim("Smalltown, PA")
        assert result["label"] == "Smalltown, PA"

    def test_empty_results_returns_none(self):
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(200, [])):
            assert geocoding._geocode_nominatim("Atlantis") is None

    def test_http_error_returns_none(self):
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(500)):
            assert geocoding._geocode_nominatim("X") is None

    def test_network_exception_returns_none(self):
        with patch.object(geocoding.requests, "get", side_effect=ConnectionError("nope")):
            assert geocoding._geocode_nominatim("X") is None


class TestPhotonSuccess:
    def test_returns_parsed_result(self):
        body = {
            "features": [{
                "geometry": {"coordinates": [-74.006, 40.7128]},
                "properties": {"name": "New York", "state": "New York", "country": "United States"},
            }]
        }
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(200, body)):
            result = geocoding._geocode_photon("New York, NY")
        assert result is not None
        assert result["lat"] == 40.7128
        assert result["lon"] == -74.006
        assert "New York" in result["label"]

    def test_empty_features_returns_none(self):
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(200, {"features": []})):
            assert geocoding._geocode_photon("X") is None

    def test_bad_geometry_returns_none(self):
        body = {"features": [{"geometry": {"coordinates": []}, "properties": {}}]}
        with patch.object(geocoding.requests, "get", return_value=_FakeResp(200, body)):
            assert geocoding._geocode_photon("X") is None


class TestFallbackLogic:
    def test_nominatim_success_skips_photon(self):
        """If Nominatim returns a result, Photon must NOT be called."""
        geocoding.cache_clear()
        with patch.object(geocoding, "_geocode_nominatim", return_value={"lat": 1, "lon": 2, "label": "X", "display_name": "X"}) as nom, \
             patch.object(geocoding, "_geocode_photon") as phot:
            result = geocoding.geocode("X")
        assert result == {"lat": 1, "lon": 2, "label": "X", "display_name": "X"}
        nom.assert_called_once_with("X")
        phot.assert_not_called()

    def test_nominatim_fail_uses_photon(self):
        """If Nominatim returns None, Photon should be tried."""
        geocoding.cache_clear()
        with patch.object(geocoding, "_geocode_nominatim", return_value=None) as nom, \
             patch.object(geocoding, "_geocode_photon", return_value={"lat": 3, "lon": 4, "label": "Y", "display_name": "Y"}) as phot:
            result = geocoding.geocode("Y")
        assert result["lat"] == 3
        nom.assert_called_once()
        phot.assert_called_once_with("Y")

    def test_both_fail_returns_none(self):
        geocoding.cache_clear()
        with patch.object(geocoding, "_geocode_nominatim", return_value=None), \
             patch.object(geocoding, "_geocode_photon", return_value=None):
            assert geocoding.geocode("X") is None


class TestCacheAndCircuitBreaker:
    def setup_method(self):
        geocoding.cache_clear()
        geocoding._cb_consecutive_429 = 0
        geocoding._cb_open_until = 0.0

    def test_cache_hit_avoids_http(self):
        """A second call with the same query must not hit the network."""
        with patch.object(geocoding, "_geocode_nominatim", return_value={"lat": 1, "lon": 2, "label": "X", "display_name": "X"}) as nom:
            r1 = geocoding.geocode("New York, NY")
            r2 = geocoding.geocode("new york, ny")  # case-insensitive
        assert r1 == r2
        assert nom.call_count == 1  # only first call goes to network

    def test_two_consecutive_429s_open_circuit(self):
        """2 raw 429 responses from Nominatim → circuit opens → next call skips Nominatim."""
        import time as _t
        fake_429 = _FakeResp(429)
        with patch.object(geocoding.requests, "get", return_value=fake_429), \
             patch.object(geocoding, "_geocode_photon", return_value={"lat": 1, "lon": 2, "label": "Z", "display_name": "Z"}) as phot:
            geocoding.geocode("A")
            geocoding.geocode("B")
            assert geocoding._cb_consecutive_429 == 2
            assert geocoding._cb_open_until > _t.time()  # circuit now open
            geocoding.geocode("C")  # this one should skip Nominatim
        # Photon should have been called for all 3 (Nominatim was the path, but
        # once the circuit is open Nominatim is skipped, so Photon does the work)
        assert phot.call_count == 3

    def test_circuit_skips_nominatim_entirely_when_open(self):
        geocoding._cb_open_until = time.time() + 60
        with patch.object(geocoding, "_geocode_nominatim") as nom, \
             patch.object(geocoding, "_geocode_photon", return_value={"lat": 1, "lon": 2, "label": "X", "display_name": "X"}):
            result = geocoding.geocode("X")
        assert result is not None
        nom.assert_not_called()

    def test_successful_call_resets_429_counter(self):
        geocoding._cb_consecutive_429 = 2
        fake_200 = _FakeResp(200, [{
            "lat": "40.0", "lon": "-75.0",
            "display_name": "X",
            "address": {"city": "X", "state": "PA"},
        }])
        with patch.object(geocoding.requests, "get", return_value=fake_200):
            geocoding.geocode("X-city")
        assert geocoding._cb_consecutive_429 == 0


import time  # needed for the breaker tests
