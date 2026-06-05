"""Auth + admin RBAC + metrics tests."""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

from trip.models import Trip, Driver, DayHistory

User = get_user_model()


def _basic_trip_body(driver_id=None, cycle=None):
    body = {
        "current_location": "New York, NY",
        "pickup_location": "Philadelphia, PA",
        "dropoff_location": "Baltimore, MD",
        "use_sleeper_berth": True,
    }
    if driver_id is not None:
        body["driver_id"] = driver_id
    if cycle is not None:
        body["current_cycle_used_hrs"] = cycle
    return body


@pytest.fixture(autouse=True)
def _isolate_metrics_db():
    """Wipe Trip + Driver + DayHistory + User + Token at the start of each test
    in this module so metrics + auth counts are deterministic when pytest-django
    shares the dev DB. The Playwright setup script re-seeds the admin user
    before its own tests run, so this is safe across the full test run."""
    from trip.models import Trip, DayHistory, Driver
    from rest_framework.authtoken.models import Token
    Trip.objects.all().delete()
    DayHistory.objects.all().delete()
    Driver.objects.all().delete()
    Token.objects.all().delete()
    User.objects.all().delete()
    yield


@pytest.mark.django_db
class TestAuth:
    def test_register_creates_user_and_token(self, api_client):
        resp = api_client.post(
            "/api/auth/register/",
            {"username": "alice", "password": "abc12345", "name": "Alice"},
            format="json",
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["ok"] is True
        assert len(body["token"]) > 20
        assert body["user"]["username"] == "alice"
        assert body["user"]["is_admin"] is False
        # A driver profile was auto-created
        assert Driver.objects.filter(name="Alice").exists()

    def test_register_validates_password_length(self, api_client):
        resp = api_client.post(
            "/api/auth/register/",
            {"username": "bob", "password": "x", "name": "Bob"},
            format="json",
        )
        assert resp.status_code == 400

    def test_register_rejects_duplicate_username(self, api_client):
        api_client.post(
            "/api/auth/register/",
            {"username": "carol", "password": "abcdef", "name": "Carol"},
            format="json",
        )
        resp = api_client.post(
            "/api/auth/register/",
            {"username": "carol", "password": "abcdef", "name": "Carol 2"},
            format="json",
        )
        assert resp.status_code == 400
        assert "username" in resp.json()["errors"]

    def test_login_returns_token(self, api_client):
        User.objects.create_user(username="dave", password="secret123")
        resp = api_client.post(
            "/api/auth/login/",
            {"username": "dave", "password": "secret123"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["token"]

    def test_login_rejects_bad_password(self, api_client):
        User.objects.create_user(username="eve", password="rightpass")
        resp = api_client.post(
            "/api/auth/login/",
            {"username": "eve", "password": "wrongpass"},
            format="json",
        )
        assert resp.status_code == 401

    def test_me_requires_token(self, api_client):
        resp = api_client.get("/api/auth/me/")
        assert resp.status_code in (401, 403)

    def test_me_returns_user(self, api_client):
        u = User.objects.create_user(username="frank", password="abcdef")
        Token.objects.create(user=u)
        resp = api_client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Token {u.auth_token.key}")
        assert resp.status_code == 200
        assert resp.json()["user"]["username"] == "frank"

    def test_logout_deletes_token(self, api_client):
        u = User.objects.create_user(username="gina", password="abcdef")
        Token.objects.create(user=u)
        token = u.auth_token.key
        resp = api_client.post("/api/auth/logout/", HTTP_AUTHORIZATION=f"Token {token}")
        assert resp.status_code == 200
        assert not Token.objects.filter(user=u).exists()


@pytest.mark.django_db
class TestAdminRBAC:
    def test_metrics_requires_admin(self, api_client):
        u = User.objects.create_user(username="normie", password="abcdef")
        Token.objects.create(user=u)
        resp = api_client.get(
            "/api/admin/metrics/",
            HTTP_AUTHORIZATION=f"Token {u.auth_token.key}",
        )
        assert resp.status_code == 403

    def test_metrics_rejects_anonymous(self, api_client):
        resp = api_client.get("/api/admin/metrics/")
        assert resp.status_code in (401, 403)

    def test_metrics_works_for_staff(self, api_client):
        admin = User.objects.create_user(username="root", password="abcdef", is_staff=True)
        Token.objects.create(user=admin)
        resp = api_client.get(
            "/api/admin/metrics/",
            HTTP_AUTHORIZATION=f"Token {admin.auth_token.key}",
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "totals" in body
        assert "window" in body
        assert "top_routes" in body
        assert "cycle_histogram" in body
        assert "top_drivers" in body
        assert len(body["window"]["sparkline_30d"]) == 30

    def test_trips_list_requires_admin(self, api_client):
        u = User.objects.create_user(username="normie2", password="abcdef")
        Token.objects.create(user=u)
        resp = api_client.get(
            "/api/admin/trips/",
            HTTP_AUTHORIZATION=f"Token {u.auth_token.key}",
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTripPersistence:
    def test_trip_creates_trip_row(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post("/api/trip/", _basic_trip_body(cycle=0.0), format="json")
        assert resp.status_code == 200
        assert Trip.objects.count() == 1
        t = Trip.objects.first()
        assert t.total_miles > 0
        assert t.total_days >= 1
        assert t.recap_approximate is True

    def test_trip_with_driver_persists_approximate_false(self, api_client, mock_geo_router, frozen_time):
        d = Driver.objects.create(name="Persisted Driver")
        resp = api_client.post("/api/trip/", _basic_trip_body(driver_id=d.id), format="json")
        assert resp.status_code == 200
        t = Trip.objects.first()
        assert t.driver_id == d.id
        assert t.recap_approximate is False


@pytest.mark.django_db
class TestMetricsMath:
    def _login(self, api_client, username, password):
        resp = api_client.post(
            "/api/auth/login/",
            {"username": username, "password": password},
            format="json",
        )
        return resp.json()["token"]

    def _seed_trips(self, driver):
        for i in range(3):
            Trip.objects.create(
                driver=driver,
                current_location=f"Origin {i}",
                pickup_location=f"Pickup {i}",
                dropoff_location=f"Dest {i}",
                total_miles=100.0 * (i + 1),
                total_days=1,
                total_driving_hrs=2.0 * (i + 1),
                total_on_duty_hrs=4.0 * (i + 1),
                final_cycle_used=20.0 + i * 15,
                recap_approximate=False,
            )

    def test_metrics_aggregates_totals(self, api_client, mock_geo_router, frozen_time):
        admin = User.objects.create_user(username="root2", password="abcdef", is_staff=True)
        Token.objects.create(user=admin)
        token = admin.auth_token.key

        d = Driver.objects.create(name="M Driver")
        self._seed_trips(d)

        resp = api_client.get(
            "/api/admin/metrics/", HTTP_AUTHORIZATION=f"Token {token}",
        )
        body = resp.json()
        assert body["totals"]["trips"] == 3
        assert body["totals"]["miles"] == 600.0
        assert body["totals"]["avg_miles_per_trip"] == 200.0
        assert body["totals"]["drivers_with_trips"] == 1

    def test_cycle_histogram_buckets(self, api_client):
        admin = User.objects.create_user(username="root3", password="abcdef", is_staff=True)
        Token.objects.create(user=admin)
        d = Driver.objects.create(name="H Driver")
        self._seed_trips(d)

        resp = api_client.get(
            "/api/admin/metrics/", HTTP_AUTHORIZATION=f"Token {admin.auth_token.key}",
        )
        buckets = {b["label"]: b["count"] for b in resp.json()["cycle_histogram"]}
        # Three trips at 20, 35, 50 hours → 0-10, 30-50, 50-60 each get 1
        assert buckets.get("30-50h", 0) == 1
        assert buckets.get("50-60h", 0) == 1

    def test_top_routes(self, api_client):
        admin = User.objects.create_user(username="root4", password="abcdef", is_staff=True)
        Token.objects.create(user=admin)
        d = Driver.objects.create(name="R Driver")
        # Two trips on the same route, one on a different
        for _ in range(2):
            Trip.objects.create(
                driver=d, current_location="A", pickup_location="B",
                dropoff_location="C", total_miles=100, total_days=1,
                total_driving_hrs=2, total_on_duty_hrs=4, final_cycle_used=10,
            )
        Trip.objects.create(
            driver=d, current_location="X", pickup_location="Y",
            dropoff_location="Z", total_miles=50, total_days=1,
            total_driving_hrs=1, total_on_duty_hrs=2, final_cycle_used=5,
        )

        resp = api_client.get(
            "/api/admin/metrics/", HTTP_AUTHORIZATION=f"Token {admin.auth_token.key}",
        )
        top = resp.json()["top_routes"]
        assert top[0]["origin"] == "A"
        assert top[0]["count"] == 2

    def test_trips_list_pagination(self, api_client):
        admin = User.objects.create_user(username="root5", password="abcdef", is_staff=True)
        Token.objects.create(user=admin)
        d = Driver.objects.create(name="P Driver")
        for i in range(5):
            Trip.objects.create(
                driver=d, current_location=f"O{i}", pickup_location=f"P{i}",
                dropoff_location=f"D{i}", total_miles=10, total_days=1,
                total_driving_hrs=1, total_on_duty_hrs=2, final_cycle_used=5,
            )

        resp = api_client.get(
            "/api/admin/trips/?page=1&page_size=2",
            HTTP_AUTHORIZATION=f"Token {admin.auth_token.key}",
        )
        body = resp.json()
        assert body["total"] == 5
        assert len(body["trips"]) == 2
        assert body["page"] == 1
