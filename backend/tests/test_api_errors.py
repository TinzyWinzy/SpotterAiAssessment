"""Error handling tests for trip API."""
from __future__ import annotations

import pytest
from unittest.mock import patch

URL = "/api/trip/"


@pytest.mark.django_db(transaction=True)
class TestTripErrors:
    def test_routing_failure_returns_502(self, api_client):
        with patch("trip.views.routing.route", return_value=None), \
             patch("trip.views.geocoding.geocode", return_value={"lat": 10, "lon": 20, "label": "X"}):
            resp = api_client.post(URL, {
                "origin": "A", "destination": "B",
            }, format="json")
            assert resp.status_code == 502
            assert "Routing failed" in resp.json()["error"]

    def test_geocoding_failure_returns_400(self, api_client, mock_geo_router):
        resp = api_client.post(URL, {
            "origin": "Unknown City, ZZ",
            "destination": "Unknown City, ZZ",
        }, format="json")
        assert resp.status_code == 400
