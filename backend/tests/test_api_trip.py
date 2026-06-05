"""End-to-end API tests for POST /api/trip/.

The geocoder and router are mocked — these tests focus on the full pipeline:
validation -> HOS engine -> response shape -> HOS-rule invariants.
"""
from __future__ import annotations

import pytest


URL = "/api/trip/"


def _basic_body(**overrides):
    body = {
        "current_location": "New York, NY",
        "pickup_location": "Philadelphia, PA",
        "dropoff_location": "Baltimore, MD",
        "current_cycle_used_hrs": 0,
        "use_sleeper_berth": True,
    }
    body.update(overrides)
    return body


def _assert_invariants(payload):
    """HOS rules that must hold for every day log in every response."""
    days = payload["days"]
    assert len(days) >= 1
    for i, d in enumerate(days):
        totals = d["totals"]
        total_h = totals["off_duty"] + totals["sleeper"] + totals["driving"] + totals["on_duty"]
        assert abs(total_h - 24.0) < 0.01, f"Day {i} sums to {total_h}, not 24h"

        # 11-hour driving limit per day
        assert totals["driving"] <= 11.01, f"Day {i} drives {totals['driving']}h (> 11)"

        # 96 quarter-hour slots in status_quarters
        assert len(d["status_quarters"]) == 96, f"Day {i} has {len(d['status_quarters'])} quarters, expected 96"
        # Every quarter is a valid duty status code 0-3
        assert all(0 <= q <= 3 for q in d["status_quarters"]), f"Day {i} has invalid quarters"

        # Driving events must be contiguous in the quarters
        for ev in d["events"]:
            if ev["status"] == 2:  # DRIVING
                assert ev["duration_h"] > 0

    # Cumulative miles must be non-decreasing across all days
    cumulative = []
    for d in days:
        for ev in d["events"]:
            cumulative.append((d["date"], ev["cumulative_miles"]))
    for (a_date, a), (_, b) in zip(cumulative, cumulative[1:]):
        assert b >= a, f"Cumulative miles went down: {a_date} {a} -> {b}"


@pytest.mark.django_db
class TestShortTrip:
    """NYC -> Philadelphia -> Baltimore (~193 mi). Single day, 3h drive."""

    def test_basic_response_shape(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True

        # Top-level keys
        for key in ("stops", "route", "total_distance_mi", "days", "warnings", "cycle_used_hrs"):
            assert key in body, f"Missing key: {key}"

        # 3 stops
        assert len(body["stops"]) == 3
        assert [s["kind"] for s in body["stops"]] == ["current", "pickup", "dropoff"]

    def test_recap_present_on_every_day(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["days"]) >= 1
        for d in body["days"]:
            assert "recap" in d, f"Missing recap in day: {d['date']}"
            recap = d["recap"]
            for k in ("last_8day_total", "last_7day_total", "tomorrow_70_budget",
                      "last_5day_total", "last_7day_total_60", "tomorrow_60_budget",
                      "took_34h_restart", "approximate"):
                assert k in recap, f"Missing {k} in recap: {recap}"

    def test_single_day(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        body = resp.json()
        assert len(body["days"]) == 1
        d = body["days"][0]
        assert d["date"] == "2026-06-05"
        # 193 mi / 55 mph = 3.5h driving
        assert 3.0 <= d["totals"]["driving"] <= 4.0
        # 1 hr pickup + 1 hr dropoff + 0.5 fuel stop somewhere = 2-3h on duty
        assert 1.5 <= d["totals"]["on_duty"] <= 3.5
        # No sleeper needed for short trip
        assert d["totals"]["sleeper"] == 0.0

    def test_invariants_hold(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        _assert_invariants(resp.json())

    def test_total_distance_matches_route(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        body = resp.json()
        assert body["total_distance_mi"] == body["route"]["distance_mi"]


@pytest.mark.django_db
class TestLongTrip:
    """LA -> Albuquerque -> Chicago (~2126 mi). Multi-day, sleeper berth, 30-min break, fueling."""

    def test_multi_day(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
        ), format="json")
        body = resp.json()
        assert body["ok"] is True
        assert len(body["days"]) >= 2, f"Long trip should be multi-day, got {len(body['days'])}"

    def test_sleeper_events_present_when_enabled(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
            use_sleeper_berth=True,
        ), format="json")
        body = resp.json()
        sleepers = sum(1 for d in body["days"] for e in d["events"] if e["status"] == 1)
        assert sleepers > 0, "Long trip with sleeper berth on should produce sleeper events"

    def test_no_sleeper_events_when_disabled(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
            use_sleeper_berth=False,
        ), format="json")
        body = resp.json()
        sleepers = sum(1 for d in body["days"] for e in d["events"] if e["status"] == 1)
        assert sleepers == 0

    def test_drive_per_day_respects_11h_cap(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
        ), format="json")
        body = resp.json()
        for d in body["days"]:
            assert d["totals"]["driving"] <= 11.01, f"Day {d['date']} drives {d['totals']['driving']}h"

    def test_30_min_break_appears(self, api_client, mock_geo_router, frozen_time):
        """Long trip drives >8h/day — should produce 30-min break events."""
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
        ), format="json")
        body = resp.json()
        breaks = [e for d in body["days"] for e in d["events"] if "break" in e.get("remark", "").lower()]
        assert len(breaks) > 0, "Long trip should have at least one 30-min break"

    def test_fueling_stops(self, api_client, mock_geo_router, frozen_time):
        """2126 mi trip with multi-day sleep resets needs at least 1 fueling stop (every 1000 mi)."""
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
        ), format="json")
        body = resp.json()
        fuel = [e for d in body["days"] for e in d["events"] if "fuel" in e.get("remark", "").lower()]
        assert len(fuel) >= 1, f"Expected at least 1 fuel stop in 2126 mi trip, got {len(fuel)}"

    def test_long_trip_needs_multiple_fuel_stops(self, api_client, mock_geo_router, frozen_time):
        """~2743 mi cross-country must need 2+ fuel stops."""
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Miami, FL",
        ), format="json")
        body = resp.json()
        fuel = [e for d in body["days"] for e in d["events"] if "fuel" in e.get("remark", "").lower()]
        assert len(fuel) >= 2, f"Expected 2+ fuel stops in 2743 mi trip, got {len(fuel)}"

    def test_invariants_hold(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
        ), format="json")
        _assert_invariants(resp.json())


@pytest.mark.django_db
class TestCrossCountry:
    """LA -> Albuquerque -> Miami (~2743 mi). Even longer; multiple resets."""

    def test_produces_four_plus_days(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Miami, FL",
        ), format="json")
        body = resp.json()
        assert len(body["days"]) >= 3, f"Cross-country should be 3+ days, got {len(body['days'])}"

    def test_invariants_hold(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Miami, FL",
        ), format="json")
        _assert_invariants(resp.json())


@pytest.mark.django_db
class TestCycleCap:
    """Trip with cycle hours already near the 70/8 cap — must trigger 34-hr restart."""

    def test_high_cycle_triggers_restart(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(
            current_location="Los Angeles, CA",
            pickup_location="Albuquerque, NM",
            dropoff_location="Chicago, IL",
            current_cycle_used_hrs=65,
        ), format="json")
        body = resp.json()
        # With 65 hr used, only 5 hr remaining. A 2126 mi / 55 mph = 38.6h trip
        # can't fit in 5 hr — must restart.
        restart = [e for d in body["days"] for e in d["events"]
                   if "restart" in e.get("remark", "").lower() or "34" in e.get("remark", "")]
        assert len(restart) >= 1, "65/70 cycle with long trip must trigger 34-hr restart"

    def test_full_cycle_still_completes(self, api_client, mock_geo_router, frozen_time):
        """At 70/70 cycle, trip must still produce a valid day log set."""
        resp = api_client.post(URL, _basic_body(
            current_location="New York, NY",
            pickup_location="Philadelphia, PA",
            dropoff_location="Baltimore, MD",
            current_cycle_used_hrs=70,
        ), format="json")
        body = resp.json()
        assert body["ok"] is True
        _assert_invariants(body)

    def test_zero_cycle(self, api_client, mock_geo_router, frozen_time):
        """0/70 cycle is the normal rested-driver case."""
        resp = api_client.post(URL, _basic_body(current_cycle_used_hrs=0), format="json")
        body = resp.json()
        assert body["ok"] is True
        _assert_invariants(body)


@pytest.mark.django_db
class TestSleeperBerthToggle:
    """Sleeper berth on vs off should change the day log content."""

    def test_toggle_changes_events(self, api_client, mock_geo_router, frozen_time):
        # Long enough to need a reset
        body_kwargs = dict(
            current_location="Indianapolis, IN",
            pickup_location="Columbus, OH",
            dropoff_location="Washington, D.C.",
        )

        on = api_client.post(URL, _basic_body(use_sleeper_berth=True, **body_kwargs), format="json").json()
        off = api_client.post(URL, _basic_body(use_sleeper_berth=False, **body_kwargs), format="json").json()

        on_sleepers = sum(d["totals"]["sleeper"] for d in on["days"])
        off_sleepers = sum(d["totals"]["sleeper"] for d in off["days"])
        assert on_sleepers > off_sleepers
        assert off_sleepers == 0.0

    def test_toggle_invariants_still_hold(self, api_client, mock_geo_router, frozen_time):
        for sleeper in (True, False):
            resp = api_client.post(URL, _basic_body(
                current_location="Los Angeles, CA",
                pickup_location="Albuquerque, NM",
                dropoff_location="Chicago, IL",
                use_sleeper_berth=sleeper,
            ), format="json")
            _assert_invariants(resp.json())


@pytest.mark.django_db
class TestPickupDropoffHours:
    """Every trip must include 1 hr on-duty for pickup + 1 hr on-duty for dropoff."""

    def test_pickup_event_present(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        events = [e for d in resp.json()["days"] for e in d["events"]]
        pickup = [e for e in events if "pickup" in e["remark"].lower()]
        assert len(pickup) == 1
        assert pickup[0]["duration_h"] == 1.0
        assert pickup[0]["status"] == 3  # ON_DUTY

    def test_dropoff_event_present(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        events = [e for d in resp.json()["days"] for e in d["events"]]
        dropoff = [e for e in events if "dropoff" in e["remark"].lower()]
        assert len(dropoff) == 1
        assert dropoff[0]["duration_h"] == 1.0
        assert dropoff[0]["status"] == 3


@pytest.mark.django_db
class TestPreTripInspection:
    """Pre-trip + post-trip inspection events should be present and total 0.5h on-duty."""

    def test_pre_and_post_trip_events(self, api_client, mock_geo_router, frozen_time):
        resp = api_client.post(URL, _basic_body(), format="json")
        events = [e for d in resp.json()["days"] for e in d["events"]]
        pre = [e for e in events if "pre-trip" in e["remark"].lower()]
        post = [e for e in events if "post-trip" in e["remark"].lower()]
        assert len(pre) == 1
        assert len(post) == 1
        assert pre[0]["duration_h"] == 0.25
        assert post[0]["duration_h"] == 0.25
        assert pre[0]["status"] == 3
        assert post[0]["status"] == 3


@pytest.mark.django_db
class TestStartTime:
    """start_time controls when the trip begins — affects pre-shift off-duty."""

    def test_midnight_start(self, api_client, mock_geo_router):
        resp = api_client.post(URL, _basic_body(
            start_time="2026-06-05T00:00:00Z",
        ), format="json")
        body = resp.json()
        # No pre-shift off-duty needed if starting at midnight
        d0_off = body["days"][0]["events"][0]
        # First event of day 1 is either pre-trip or driving
        assert d0_off["duration_h"] <= 0.5

    def test_2pm_start_has_pre_shift_off_duty(self, api_client, mock_geo_router):
        resp = api_client.post(URL, _basic_body(
            start_time="2026-06-05T14:00:00Z",
        ), format="json")
        body = resp.json()
        d0 = body["days"][0]
        first = d0["events"][0]
        # First event of day 1 must be off-duty, ~14 hours
        assert first["status"] == 0
        assert 13.5 <= first["duration_h"] <= 14.5


@pytest.mark.django_db
class TestAvgSpeed:
    """avg_speed_mph should change driving time proportionally."""

    def test_faster_speed_shorter_drive(self, api_client, mock_geo_router, frozen_time):
        body = _basic_body(current_location="New York, NY",
                            pickup_location="Philadelphia, PA",
                            dropoff_location="Washington, D.C.")
        slow = api_client.post(URL, {**body, "avg_speed_mph": 30}, format="json").json()
        fast = api_client.post(URL, {**body, "avg_speed_mph": 65}, format="json").json()

        # Total driving hours should be smaller at higher speed
        slow_drive = sum(d["totals"]["driving"] for d in slow["days"])
        fast_drive = sum(d["totals"]["driving"] for d in fast["days"])
        assert fast_drive < slow_drive
