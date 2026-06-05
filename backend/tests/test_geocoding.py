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
        with patch.object(geocoding, "_geocode_nominatim", return_value={"lat": 1, "lon": 2, "label": "X", "display_name": "X"}) as nom, \
             patch.object(geocoding, "_geocode_photon") as phot:
            result = geocoding.geocode("X")
        assert result == {"lat": 1, "lon": 2, "label": "X", "display_name": "X"}
        nom.assert_called_once_with("X")
        phot.assert_not_called()

    def test_nominatim_fail_uses_photon(self):
        """If Nominatim returns None, Photon should be tried."""
        with patch.object(geocoding, "_geocode_nominatim", return_value=None) as nom, \
             patch.object(geocoding, "_geocode_photon", return_value={"lat": 3, "lon": 4, "label": "Y", "display_name": "Y"}) as phot:
            result = geocoding.geocode("Y")
        assert result["lat"] == 3
        nom.assert_called_once()
        phot.assert_called_once_with("Y")

    def test_both_fail_returns_none(self):
        with patch.object(geocoding, "_geocode_nominatim", return_value=None), \
             patch.object(geocoding, "_geocode_photon", return_value=None):
            assert geocoding.geocode("X") is None
