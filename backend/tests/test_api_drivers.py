"""Driver API tests."""
from __future__ import annotations

import pytest

from trip.models import Organisation, Driver

URL = "/api/drivers/"


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


@pytest.mark.django_db
class TestDriverCRUD:
    def test_list_drivers_empty(self, api_client, org):
        Driver.objects.all().delete()
        resp = api_client.get(URL)
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_create_driver(self, api_client, org):
        resp = api_client.post(URL, {
            "name": "Tinotenda Duma",
            "phone_number": "+263712345678",
            "rate_per_day_usd": 30.0,
            "rate_per_km_usd": 0.50,
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()["driver"]
        assert data["name"] == "Tinotenda Duma"

    def test_list_drivers_after_create(self, api_client, org):
        Driver.objects.create(name="Driver 1", organisation=org)
        Driver.objects.create(name="Driver 2", organisation=org)
        resp = api_client.get(URL)
        assert len(resp.json()["drivers"]) >= 2

    def test_get_single_driver(self, api_client, org):
        d = Driver.objects.create(name="Driver X", organisation=org)
        resp = api_client.get(f"{URL}{d.id}/")
        assert resp.status_code == 200
        assert resp.json()["driver"]["name"] == "Driver X"

    def test_patch_driver(self, api_client, org):
        d = Driver.objects.create(name="Old Name", organisation=org)
        resp = api_client.patch(f"{URL}{d.id}/", {"name": "New Name"}, format="json")
        assert resp.status_code == 200
        assert resp.json()["driver"]["name"] == "New Name"

    def test_delete_driver(self, api_client, org):
        d = Driver.objects.create(name="Delete Me", organisation=org)
        resp = api_client.delete(f"{URL}{d.id}/")
        assert resp.status_code == 200
        assert not Driver.objects.filter(pk=d.id).exists()

    def test_get_non_existent_returns_404(self, api_client, org):
        resp = api_client.get(f"{URL}99999/")
        assert resp.status_code == 404
