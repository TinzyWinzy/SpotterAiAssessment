"""Auth and admin endpoint tests."""
from __future__ import annotations

import pytest

from django.contrib.auth import get_user_model
from trip.models import Organisation, Driver, Trip

User = get_user_model()


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


@pytest.mark.django_db
class TestAuth:
    def test_register(self, api_client, org):
        resp = api_client.post("/api/auth/register/", {
            "username": "new_test_user",
            "password": "testpass123",
            "name": "Test Driver",
        }, format="json")
        assert resp.status_code == 201
        data = resp.json()
        assert data["ok"] is True
        assert data["token"]
        assert data["user"]["username"] == "new_test_user"

    def test_login(self, api_client, org):
        User.objects.create_user(username="login_test_user", password="testpass123")
        resp = api_client.post("/api/auth/login/", {
            "username": "login_test_user",
            "password": "testpass123",
        }, format="json")
        assert resp.status_code == 200
        assert resp.json()["token"]

    def test_login_invalid(self, api_client, org):
        resp = api_client.post("/api/auth/login/", {
            "username": "noone", "password": "wrong",
        }, format="json")
        assert resp.status_code == 401


@pytest.mark.django_db
class TestAdmin:
    def _login_admin(self, api_client):
        user, _ = User.objects.get_or_create(
            username="admin",
            defaults={"password": "admin", "is_staff": True},
        )
        if not user.check_password("admin"):
            user.set_password("admin")
            user.save()
        resp = api_client.post("/api/auth/login/", {
            "username": "admin", "password": "admin",
        }, format="json")
        token = resp.json()["token"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return user

    def test_metrics_requires_auth(self, api_client, org):
        resp = api_client.get("/api/admin/metrics/")
        assert resp.status_code == 401

    def test_metrics_returns_kpi_structure(self, api_client, mock_geo_router, org):
        self._login_admin(api_client)

        driver = Driver.objects.create(name="Test Driver", organisation=org)
        Trip.objects.create(
            organisation=org,
            driver=driver,
            origin="Harare, Zimbabwe",
            destination="Beitbridge, Zimbabwe",
            distance_km=580.0,
        )

        resp = api_client.get("/api/admin/metrics/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert data["totals"]["trips"] >= 1
        assert data["totals"]["km"] > 0
        assert data["totals"]["drivers"] >= 1
        assert "top_vehicles" in data

    def test_trips_list_paginated(self, api_client, mock_geo_router, org):
        self._login_admin(api_client)

        for i in range(5):
            Trip.objects.create(
                organisation=org,
                origin=f"City {i}",
                destination=f"City {i + 1}",
                distance_km=100.0,
            )

        resp = api_client.get("/api/admin/trips/?page=1&page_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 5
        assert len(data["trips"]) == 3

    def test_metrics_non_admin_rejected(self, api_client, org):
        user = User.objects.create_user(username="non_admin_driver", password="pass", is_staff=False)
        resp = api_client.post("/api/auth/login/", {
            "username": "non_admin_driver", "password": "pass",
        }, format="json")
        token = resp.json()["token"]
        api_client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        resp = api_client.get("/api/admin/metrics/")
        assert resp.status_code in (401, 403)
