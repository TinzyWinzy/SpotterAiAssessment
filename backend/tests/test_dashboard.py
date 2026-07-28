"""Admin dashboard tests — enhanced metrics, summary, filters."""
from __future__ import annotations

import pytest

from django.contrib.auth import get_user_model
from trip.models import Organisation, Driver, Trip, Vehicle

User = get_user_model()


@pytest.fixture
def org():
    return Organisation.objects.get_or_create(
        slug="default", defaults={"name": "Test Fleet"},
    )[0]


@pytest.mark.django_db
class TestDashboardEnhanced:
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

    def test_metrics_returns_fuel_efficiency(self, api_client, org, mock_geo_router):
        self._login_admin(api_client)
        vehicle = Vehicle.objects.create(
            plate="DASH-001", organisation=org,
            fuel_consumption_rate_l_100km=35.0,
        )
        driver = Driver.objects.create(name="Dash Driver", organisation=org)
        Trip.objects.create(
            organisation=org, vehicle=vehicle, driver=driver,
            origin="Harare, Zimbabwe", destination="Beitbridge, Zimbabwe",
            distance_km=580.0, revenue_usd=800.0,
            estimated_total_cost_usd=565.0, estimated_fuel_cost_usd=267.0,
            status="delivered",
        )

        resp = api_client.get("/api/admin/metrics/")
        assert resp.status_code == 200
        data = resp.json()
        assert "fuel" in data
        assert "status_distribution" in data
        assert data["totals"]["revenue_usd"] >= 800.0

    def test_metrics_with_date_filter(self, api_client, org):
        self._login_admin(api_client)
        resp = api_client.get("/api/admin/metrics/?from_date=2026-01-01&to_date=2026-12-31")
        assert resp.status_code == 200
        data = resp.json()
        assert data["date_range"]["from"] is not None
        assert data["date_range"]["to"] is not None

    def test_fleet_summary_text(self, api_client, org):
        self._login_admin(api_client)
        resp = api_client.get("/api/admin/summary/")
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        text = data["text"]
        assert "TruckLedger Fleet Summary" in text
        assert "Revenue:" in text or "$" in text

    def test_comparison_data_present(self, api_client, org):
        self._login_admin(api_client)
        resp = api_client.get("/api/admin/metrics/")
        assert resp.status_code == 200
        data = resp.json()
        assert "comparison" in data
        comp = data["comparison"]
        assert "trips_this_month" in comp
        assert "trips_last_month" in comp
        assert "revenue_this_month_usd" in comp

    def test_trips_list_with_status_filter(self, api_client, org):
        self._login_admin(api_client)
        Trip.objects.create(
            organisation=org, origin="A", destination="B",
            distance_km=100, status="delivered",
        )
        Trip.objects.create(
            organisation=org, origin="C", destination="D",
            distance_km=200, status="in_transit",
        )
        resp = api_client.get("/api/admin/trips/?status=in_transit")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for trip in data["trips"]:
            assert trip["status"] == "in_transit"

    def test_trips_list_with_date_filter(self, api_client, org):
        self._login_admin(api_client)
        resp = api_client.get("/api/admin/trips/?from_date=2026-01-01")
        assert resp.status_code == 200
