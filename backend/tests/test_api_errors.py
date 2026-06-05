"""Error-path tests — geocoding failures, routing failures, partial failures."""
from __future__ import annotations

from unittest.mock import patch

import pytest


URL = "/api/trip/"


def _body(**overrides):
    body = {
        "current_location": "New York, NY",
        "pickup_location": "Philadelphia, PA",
        "dropoff_location": "Baltimore, MD",
        "current_cycle_used_hrs": 0,
    }
    body.update(overrides)
    return body


@pytest.mark.django_db
class TestGeocodingFailures:
    def test_current_location_unknown(self, api_client, mock_geo_router):
        """Mocked geocoder returns None for unknowns."""
        resp = api_client.post(URL, _body(current_location="Unknown City, ZZ"), format="json")
        assert resp.status_code == 400
        body = resp.json()
        assert body["ok"] is False
        assert "Geocoding failed" in body["error"]
        assert "current_location" in body["error"]

    def test_pickup_location_unknown(self, api_client, mock_geo_router):
        resp = api_client.post(URL, _body(pickup_location="Unknown City, ZZ"), format="json")
        assert resp.status_code == 400
        assert "pickup_location" in resp.json()["error"]

    def test_dropoff_location_unknown(self, api_client, mock_geo_router):
        resp = api_client.post(URL, _body(dropoff_location="Unknown City, ZZ"), format="json")
        assert resp.status_code == 400
        assert "dropoff_location" in resp.json()["error"]

    def test_all_locations_unknown_lists_all(self, api_client, mock_geo_router):
        resp = api_client.post(URL, _body(
            current_location="Unknown City, ZZ",
            pickup_location="Unknown City, ZZ",
            dropoff_location="Unknown City, ZZ",
        ), format="json")
        assert resp.status_code == 400
        err = resp.json()["error"]
        assert "current_location" in err
        assert "pickup_location" in err
        assert "dropoff_location" in err

    def test_geocoder_returns_none_all(self, api_client):
        """A network exception during geocoding should bubble up as 400 (graceful)."""
        with patch("trip.views.geocoding.geocode", return_value=None):
            resp = api_client.post(URL, _body(), format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestRoutingFailures:
    def test_osrm_returns_none(self, api_client, mock_geo_router):
        """If OSRM is unreachable, return 502."""
        with patch("trip.views.routing.route", return_value=None):
            resp = api_client.post(URL, _body(), format="json")
        assert resp.status_code == 502
        assert "Routing failed" in resp.json()["error"]

    def test_routing_raises_exception(self, api_client):
        with patch("trip.views.geocoding.geocode", side_effect=[
            {"lat": 40.7, "lon": -74.0, "display_name": "x", "label": "x"},
            {"lat": 39.9, "lon": -75.1, "display_name": "y", "label": "y"},
            {"lat": 39.3, "lon": -76.6, "display_name": "z", "label": "z"},
        ]), patch("trip.views.routing.route", side_effect=Exception("timeout")):
            with pytest.raises(Exception):
                api_client.post(URL, _body(), format="json")
