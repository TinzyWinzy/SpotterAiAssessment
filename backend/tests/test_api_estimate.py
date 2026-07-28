"""Integration tests for POST /api/trip/estimate/."""
from __future__ import annotations

import pytest

from trip.models import Organisation, Vehicle, Driver

URL = "/api/trip/estimate/"


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


def _body(**overrides):
    body = {
        "origin": "Harare, Zimbabwe",
        "destination": "Beitbridge, Zimbabwe",
    }
    body.update(overrides)
    return body


@pytest.mark.django_db
class TestTripEstimate:
    def test_basic_estimate(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _body(), format="json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert "route" in data
        assert "cost_estimate" in data
        ce = data["cost_estimate"]
        assert ce["route_distance_km"] > 0
        assert "fuel_cost_usd" in ce
        assert "driver_pay_usd" in ce
        assert "total_cost_usd" in ce

    def test_estimate_with_vehicle(self, api_client, mock_geo_router, org):
        vehicle = Vehicle.objects.create(
            plate="EST 001", organisation=org,
            fuel_consumption_rate_l_100km=35.0,
        )
        resp = api_client.post(URL, _body(vehicle_id=vehicle.id), format="json")
        assert resp.status_code == 200
        ce = resp.json()["cost_estimate"]
        assert ce["fuel_cost_usd"] > 0

    def test_estimate_with_vehicle_and_driver(self, api_client, mock_geo_router, org):
        vehicle = Vehicle.objects.create(
            plate="EST 002", organisation=org,
            fuel_consumption_rate_l_100km=32.0,
        )
        driver = Driver.objects.create(
            name="Est Driver", organisation=org,
            rate_per_day_usd=30.0, rate_per_km_usd=0.50,
        )
        resp = api_client.post(URL, _body(
            vehicle_id=vehicle.id,
            driver_id=driver.id,
        ), format="json")
        assert resp.status_code == 200
        ce = resp.json()["cost_estimate"]
        assert ce["fuel_cost_usd"] > 0
        assert ce["driver_pay_usd"] > 0

    def test_estimate_with_border_and_tolls(self, api_client, mock_geo_router, org):
        vehicle = Vehicle.objects.create(
            plate="EST 003", organisation=org,
            fuel_consumption_rate_l_100km=30.0,
        )
        resp = api_client.post(URL, _body(
            vehicle_id=vehicle.id,
            border_crossings=2,
            tolls_usd=25.0,
        ), format="json")
        assert resp.status_code == 200
        ce = resp.json()["cost_estimate"]
        assert ce["border_fees_usd"] == 100.0
        assert ce["tolls_usd"] == 25.0

    def test_estimate_custom_fuel_price(self, api_client, mock_geo_router, org):
        vehicle = Vehicle.objects.create(
            plate="EST 004", organisation=org,
            fuel_consumption_rate_l_100km=35.0,
        )
        resp = api_client.post(URL, _body(
            vehicle_id=vehicle.id,
            fuel_price_per_litre_usd=1.80,
        ), format="json")
        assert resp.status_code == 200
        ce = resp.json()["cost_estimate"]
        assert ce["fuel_cost_usd"] > 0

    def test_vehicle_not_found(self, api_client, mock_geo_router, org):
        resp = api_client.post(URL, _body(vehicle_id=99999), format="json")
        assert resp.status_code == 400
        assert "not found" in resp.json()["error"]
