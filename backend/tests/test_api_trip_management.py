"""Trip management API tests — status updates, fuel, trip list."""
from __future__ import annotations

import pytest

from trip.models import Organisation, Vehicle, Driver, Trip

FUEL_URL = "/api/fuel/"
TRIPS_URL = "/api/trips/"


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


@pytest.fixture
def vehicle(org):
    v, _ = Vehicle.objects.get_or_create(
        plate="TST-TM-001", organisation=org,
        defaults={"fuel_consumption_rate_l_100km": 35.0},
    )
    return v


@pytest.fixture
def driver(org):
    return Driver.objects.create(name="Test Driver", organisation=org)


@pytest.fixture
def trip(org, vehicle, driver):
    return Trip.objects.create(
        organisation=org, vehicle=vehicle, driver=driver,
        origin="Harare, Zimbabwe", destination="Beitbridge, Zimbabwe",
        distance_km=580.0, status="dispatched",
    )


@pytest.mark.django_db
class TestTripStatusUpdate:
    def test_update_status_creates_log(self, api_client, trip):
        resp = api_client.post(f"{TRIPS_URL}{trip.id}/status/", {
            "status": "at_border",
            "location_text": "Beitbridge Border Post",
            "notes": "Queue is long",
        }, format="json")
        assert resp.status_code == 200
        trip.refresh_from_db()
        assert trip.status == "at_border"

        from trip.models import TripStatusLog
        log = TripStatusLog.objects.filter(trip=trip).last()
        assert log is not None
        assert log.from_status == "dispatched"
        assert log.to_status == "at_border"
        assert log.location_text == "Beitbridge Border Post"

    def test_update_status_chain(self, api_client, trip):
        api_client.post(f"{TRIPS_URL}{trip.id}/status/", {"status": "at_border"}, format="json")
        api_client.post(f"{TRIPS_URL}{trip.id}/status/", {"status": "in_transit"}, format="json")
        api_client.post(f"{TRIPS_URL}{trip.id}/status/", {"status": "delivered"}, format="json")

        trip.refresh_from_db()
        assert trip.status == "delivered"

        from trip.models import TripStatusLog
        assert TripStatusLog.objects.filter(trip=trip).count() == 3

    def test_status_requires_field(self, api_client, trip):
        resp = api_client.post(f"{TRIPS_URL}{trip.id}/status/", {}, format="json")
        assert resp.status_code == 400
        assert "status" in resp.json()["error"].lower()

    def test_nonexistent_trip_returns_404(self, api_client):
        resp = api_client.post(f"{TRIPS_URL}99999/status/", {"status": "delivered"}, format="json")
        assert resp.status_code == 404


@pytest.mark.django_db
class TestFuelLogging:
    def test_log_fuel(self, api_client, trip, vehicle):
        resp = api_client.post(FUEL_URL, {
            "trip": trip.id,
            "vehicle": vehicle.id,
            "litres": 200,
            "price_per_litre_usd": 1.60,
            "total_cost_usd": 320.0,
            "location_text": "Beitbridge Total",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()["fuel_record"]
        assert data["litres"] == 200
        assert data["trip"] == trip.id

    def test_list_fuel_records(self, api_client, trip, vehicle):
        from trip.models import FuelRecord
        FuelRecord.objects.create(
            trip=trip, vehicle=vehicle,
            litres=200, price_per_litre_usd=1.60, total_cost_usd=320.0,
        )
        FuelRecord.objects.create(
            trip=trip, vehicle=vehicle,
            litres=150, price_per_litre_usd=1.55, total_cost_usd=232.50,
        )
        resp = api_client.get(FUEL_URL)
        assert resp.status_code == 200
        assert len(resp.json()["fuel_records"]) >= 2

    def test_fuel_validation_requires_fields(self, api_client):
        resp = api_client.post(FUEL_URL, {}, format="json")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestTripList:
    def test_list_trips(self, api_client, org):
        Trip.objects.create(
            organisation=org,
            origin="A", destination="B", distance_km=100,
        )
        Trip.objects.create(
            organisation=org,
            origin="C", destination="D", distance_km=200,
        )
        resp = api_client.get(TRIPS_URL)
        assert resp.status_code == 200
        assert len(resp.json()["trips"]) >= 2

    def test_trip_detail(self, api_client, trip):
        resp = api_client.get(f"{TRIPS_URL}{trip.id}/")
        assert resp.status_code == 200
        data = resp.json()["trip"]
        assert data["origin"] == "Harare, Zimbabwe"
        assert data["status"] == "dispatched"

    def test_patch_trip_costs(self, api_client, trip):
        resp = api_client.patch(f"{TRIPS_URL}{trip.id}/", {
            "actual_fuel_cost_usd": 280.0,
            "revenue_usd": 800.0,
        }, format="json")
        assert resp.status_code == 200
        data = resp.json()["trip"]
        assert data["actual_fuel_cost_usd"] == 280.0
        assert data["revenue_usd"] == 800.0
