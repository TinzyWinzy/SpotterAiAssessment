"""OSRM routing client tests."""
from __future__ import annotations

from unittest.mock import patch

import routing


class _FakeResp:
    def __init__(self, status, json_data=None):
        self.status_code = status
        self._json = json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._json


class TestOSRMSuccess:
    def test_returns_route(self):
        body = {
            "routes": [{
                "distance": 193000,  # meters
                "duration": 11000,  # seconds
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[-74.0, 40.7], [-75.1, 39.9], [-76.6, 39.3]],
                },
            }]
        }
        with patch.object(routing.requests, "get", return_value=_FakeResp(200, body)):
            result = routing.route([(-74.0, 40.7), (-75.1, 39.9), (-76.6, 39.3)])
        assert result is not None
        # 193000 m -> 119.9 mi
        assert 115 < result["distance_mi"] < 125
        # 11000 s -> 3.06 h
        assert 3.0 < result["duration_seconds"] / 3600 < 3.2
        assert result["geometry"]["type"] == "LineString"
        assert len(result["geometry"]["coordinates"]) == 3

    def test_no_routes_returns_none(self):
        with patch.object(routing.requests, "get", return_value=_FakeResp(200, {"routes": []})):
            assert routing.route([(-74, 40), (-75, 39)]) is None

    def test_http_error_returns_none(self):
        with patch.object(routing.requests, "get", return_value=_FakeResp(500)):
            assert routing.route([(-74, 40), (-75, 39)]) is None

    def test_network_exception_returns_none(self):
        with patch.object(routing.requests, "get", side_effect=ConnectionError):
            assert routing.route([(-74, 40), (-75, 39)]) is None

    def test_url_contains_lonlat_pairs(self):
        """OSRM requires `lng,lat;lng,lat` coord order — verify our format."""
        with patch.object(routing.requests, "get", return_value=_FakeResp(200, {
            "routes": [{
                "distance": 0, "duration": 0,
                "geometry": {"type": "LineString", "coordinates": []},
            }]
        })) as m:
            routing.route([(-74.0, 40.7), (-75.1, 39.9)])
        called_url = m.call_args[0][0]
        assert "-74.0,40.7" in called_url
        assert "-75.1,39.9" in called_url
        # OSRM uses ; as coord separator in the URL path
        assert ";" in called_url
