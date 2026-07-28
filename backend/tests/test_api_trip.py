"""Integration tests for POST /api/trip/"""
from __future__ import annotations

import pytest

from trip.models import Organisation, Driver, Trip

URL = "/api/trip/"


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


def _basic_body(**overrides):
    body = {
        "origin": "Harare, Zimbabwe",
        "destination": "Beitbridge, Zimbabwe",
    }
    body.update(overrides)
    return body


@pytest.mark.django_db
class TestSimpleTrip:
    def test_basic_trip_returns_route_and_stops(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _basic_body(), format="json")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["ok"] is True
        assert "route" in payload
        assert "stops" in payload
        assert payload["route"]["distance_km"] > 0
        assert payload["route"]["duration_h"] > 0
        assert len(payload["stops"]) == 2

    def test_route_geometry_is_valid_linestring(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _basic_body(), format="json")
        geo = resp.json()["route"]["geometry"]
        assert geo["type"] == "LineString"
        assert len(geo["coordinates"]) >= 2

    def test_trip_persists_summary_record(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _basic_body(), format="json")
        assert resp.status_code == 200

        trip = Trip.objects.last()
        assert trip is not None
        assert trip.origin == "Harare, Zimbabwe"
        assert trip.destination == "Beitbridge, Zimbabwe"
        assert trip.distance_km > 0

    def test_trip_with_driver(self, api_client, mock_geo_router, org):
        driver = Driver.objects.create(name="TripDriverTest", organisation=org)

        resp = api_client.post(
            URL,
            _basic_body(driver_id=driver.id),
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["driver_id"] == driver.id

        trip = Trip.objects.filter(driver=driver).last()
        assert trip is not None
        assert trip.driver == driver

    def test_driver_not_found(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _basic_body(driver_id=99999), format="json")
        assert resp.status_code == 400
        assert "not found" in resp.json()["error"]

    def test_trip_with_waypoint(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _basic_body(
            waypoints=["Bulawayo, Zimbabwe"],
        ), format="json")
        assert resp.status_code == 200
        payload = resp.json()
        assert len(payload["stops"]) == 3
