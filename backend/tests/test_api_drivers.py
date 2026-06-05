"""Driver profile API + trip-with-driver-id integration tests."""
from __future__ import annotations
from datetime import date, timedelta

import pytest

from trip.models import Driver, DayHistory

URL_LIST = "/api/drivers/"
URL_TRIP = "/api/trip/"


def _basic_body(driver_id=None, cycle=None):
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


@pytest.mark.django_db
class TestDriverList:
    def test_list_returns_200_with_drivers_array(self, api_client):
        resp = api_client.get(URL_LIST)
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert isinstance(body["drivers"], list)
        for d in body["drivers"]:
            assert "id" in d and "name" in d and "day_history" in d

    def test_create_then_list(self, api_client):
        body = {
            "name": "Alex Trucker",
            "carrier": "Spotter Logistics",
            "home_terminal": "Dallas, TX",
            "current_cycle_used_hrs": 25.0,
        }
        resp = api_client.post(URL_LIST, body, format="json")
        assert resp.status_code == 201
        created = resp.json()["driver"]
        assert created["name"] == "Alex Trucker"
        assert created["id"] > 0

        resp = api_client.get(URL_LIST)
        names = [d["name"] for d in resp.json()["drivers"]]
        assert "Alex Trucker" in names

    def test_create_validation_missing_name(self, api_client):
        resp = api_client.post(URL_LIST, {"carrier": "X"}, format="json")
        assert resp.status_code == 400
        assert "name" in resp.json()["errors"]


@pytest.mark.django_db
class TestDriverDetail:
    def test_get_existing(self, api_client):
        d = Driver.objects.create(name="Bo Driver", carrier="Xpress")
        resp = api_client.get(f"/api/drivers/{d.id}/")
        assert resp.status_code == 200
        assert resp.json()["driver"]["name"] == "Bo Driver"

    def test_get_missing_404(self, api_client):
        resp = api_client.get("/api/drivers/99999/")
        assert resp.status_code == 404

    def test_patch_updates_fields(self, api_client):
        d = Driver.objects.create(name="Patch Me", carrier="Old")
        resp = api_client.patch(
            f"/api/drivers/{d.id}/",
            {"carrier": "New", "home_terminal": "Phoenix, AZ"},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["driver"]["carrier"] == "New"
        assert resp.json()["driver"]["home_terminal"] == "Phoenix, AZ"

    def test_delete_removes(self, api_client):
        d = Driver.objects.create(name="Delete Me")
        resp = api_client.delete(f"/api/drivers/{d.id}/")
        assert resp.status_code == 200
        assert not Driver.objects.filter(pk=d.id).exists()


@pytest.mark.django_db
class TestDriverHistory:
    def test_add_history(self, api_client):
        d = Driver.objects.create(name="Hist Driver")
        resp = api_client.post(
            f"/api/drivers/{d.id}/history/",
            {"date": "2026-05-30", "on_duty_hrs": 10.0, "driving_hrs": 8.0},
            format="json",
        )
        assert resp.status_code == 200
        assert resp.json()["record"]["on_duty_hrs"] == 10.0
        assert DayHistory.objects.filter(driver=d).count() == 1

    def test_add_history_invalid_date(self, api_client):
        d = Driver.objects.create(name="Bad Date Driver")
        resp = api_client.post(
            f"/api/drivers/{d.id}/history/",
            {"date": "not-a-date", "on_duty_hrs": 8.0},
            format="json",
        )
        assert resp.status_code == 400

    def test_upsert_replaces_existing(self, api_client):
        d = Driver.objects.create(name="Upsert Driver")
        api_client.post(
            f"/api/drivers/{d.id}/history/",
            {"date": "2026-05-30", "on_duty_hrs": 8.0},
            format="json",
        )
        api_client.post(
            f"/api/drivers/{d.id}/history/",
            {"date": "2026-05-30", "on_duty_hrs": 12.0},
            format="json",
        )
        rec = DayHistory.objects.get(driver=d, date=date(2026, 5, 30))
        assert rec.on_duty_hrs == 12.0


@pytest.mark.django_db
class TestTripWithDriver:
    def test_trip_uses_driver_history_for_recap(self, api_client, mock_geo_router, frozen_time):
        # Build a driver with 5 days of skewed history (heavy on day-5, light otherwise).
        d = Driver.objects.create(name="Recap Driver", current_cycle_used_hrs=30.0)
        for offset, hrs in {5: 30.0, 4: 0, 3: 0, 2: 0, 1: 0}.items():
            DayHistory.objects.create(
                driver=d, source=DayHistory.SOURCE_MANUAL,
                date=(frozen_time.date() - timedelta(days=offset)),
                on_duty_hrs=hrs, driving_hrs=max(0, hrs - 1),
            )

        resp = api_client.post(URL_TRIP, _basic_body(driver_id=d.id), format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["driver_id"] == d.id
        assert body["recap_approximate"] is False
        # Day 1 last_7day_total should reflect real history: just today's on-duty
        # (since prior 7 days are 30 + 0*4 + 0*0 = 30, but the 7-day window
        # includes only days -4..0, which has 0+0+0+0+today ≈ small)
        d1_recap = body["days"][0]["recap"]
        assert d1_recap["approximate"] is False

    def test_trip_persists_generated_history(self, api_client, mock_geo_router, frozen_time):
        d = Driver.objects.create(name="Persist Driver")
        resp = api_client.post(URL_TRIP, _basic_body(driver_id=d.id), format="json")
        assert resp.status_code == 200
        # 1 day trip → 1 generated history record
        generated = DayHistory.objects.filter(driver=d, source=DayHistory.SOURCE_GENERATED)
        assert generated.count() == 1
        rec = generated.first()
        assert rec.on_duty_hrs > 0
        assert rec.driving_hrs > 0

    def test_trip_with_invalid_driver_id(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL_TRIP, _basic_body(driver_id=99999), format="json")
        assert resp.status_code == 400
        assert "not found" in resp.json()["error"]

    def test_trip_without_driver_still_works(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL_TRIP, _basic_body(cycle=0.0), format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["recap_approximate"] is True
        assert body["driver_id"] is None


@pytest.mark.django_db
class TestMileageInTripResponse:
    def test_deadhead_and_loaded_present(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL_TRIP, _basic_body(cycle=0.0), format="json")
        body = resp.json()
        d = body["days"][0]
        assert "deadhead_mi" in d
        assert "loaded_mi" in d
        assert abs(d["deadhead_mi"] + d["loaded_mi"] - d["total_miles"]) < 0.5
        assert d["deadhead_mi"] > 0
        assert d["loaded_mi"] > 0

    def test_events_have_leg_kind(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL_TRIP, _basic_body(cycle=0.0), format="json")
        body = resp.json()
        driving = [e for e in body["days"][0]["events"] if e["status"] == 2]
        assert all(e["leg_kind"] in ("deadhead", "loaded") for e in driving)
        assert any(e["leg_kind"] == "deadhead" for e in driving)
        assert any(e["leg_kind"] == "loaded" for e in driving)
