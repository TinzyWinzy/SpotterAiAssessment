"""Vehicle API tests."""
from __future__ import annotations

import pytest

from trip.models import Organisation, Vehicle

URL = "/api/vehicles/"


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


@pytest.mark.django_db
class TestVehicleCRUD:
    def test_list_vehicles_empty(self, api_client, org):
        Vehicle.objects.all().delete()
        resp = api_client.get(URL)
        assert resp.status_code == 200
        assert isinstance(resp.json()["vehicles"], list)

    def test_create_vehicle(self, api_client, org):
        resp = api_client.post(URL, {
            "plate": "VEH-TEST-001",
            "make": "MAN",
            "model": "TGS",
            "fuel_type": "diesel",
            "fuel_consumption_rate_l_100km": 35.0,
            "tank_capacity_l": 400.0,
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()["vehicle"]
        assert data["plate"] == "VEH-TEST-001"
        assert data["organisation"] == org.id

    def test_list_vehicles_after_create(self, api_client, org):
        Vehicle.objects.create(plate="AAA 001", organisation=org)
        Vehicle.objects.create(plate="AAA 002", organisation=org)
        resp = api_client.get(URL)
        assert len(resp.json()["vehicles"]) >= 2

    def test_get_single_vehicle(self, api_client, org):
        v = Vehicle.objects.create(plate="XYZ 999", organisation=org)
        resp = api_client.get(f"{URL}{v.id}/")
        assert resp.status_code == 200
        assert resp.json()["vehicle"]["plate"] == "XYZ 999"

    def test_patch_vehicle(self, api_client, org):
        v = Vehicle.objects.create(plate="OLD 111", organisation=org)
        resp = api_client.patch(f"{URL}{v.id}/", {
            "current_odometer_km": 50000,
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["vehicle"]["current_odometer_km"] == 50000

    def test_patch_vehicle_status(self, api_client, org):
        v = Vehicle.objects.create(plate="MNT 222", organisation=org)
        resp = api_client.patch(f"{URL}{v.id}/", {"status": "maintenance"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["vehicle"]["status"] == "maintenance"

    def test_delete_vehicle(self, api_client, org):
        v = Vehicle.objects.create(plate="DEL 000", organisation=org)
        resp = api_client.delete(f"{URL}{v.id}/")
        assert resp.status_code == 200
        assert not Vehicle.objects.filter(pk=v.id).exists()

    def test_get_non_existent_returns_404(self, api_client, org):
        resp = api_client.get(f"{URL}99999/")
        assert resp.status_code == 404

    def test_duplicate_plate_same_org_fails(self, api_client, org):
        Vehicle.objects.create(plate="DUP-VEH-001", organisation=org)
        resp = api_client.post(URL, {
            "plate": "DUP-VEH-001",
            "fuel_consumption_rate_l_100km": 30.0,
        }, format="json")
        assert resp.status_code == 400
