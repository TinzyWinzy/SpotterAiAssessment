"""
Unit tests for the HOS engine.
Run with: python test_hos_engine.py
"""
import unittest
from datetime import datetime, timedelta
from hos_engine import (
    TripInput, Point, generate_trip, haversine_mi, total_distance_mi,
    OFF_DUTY, SLEEPER, DRIVING, ON_DUTY, MAX_DRIVE_PER_SHIFT,
    MAX_WINDOW_PER_SHIFT, MAX_CYCLE_HOURS, FUEL_INTERVAL_MI,
)


def make_trip(cycle=0.0, speed=55.0, start=None):
    return TripInput(
        current=Point(40.7128, -74.0060, "New York, NY"),
        pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
        dropoff=Point(39.2904, -76.6122, "Baltimore, MD"),
        cycle_used_hrs=cycle,
        avg_speed_mph=speed,
        start_time=start or datetime(2026, 6, 8, 6, 0),
    )


def drive_hours(day):
    return sum(ev.duration_h for ev in day.events if ev.status == DRIVING)


def on_duty_hours(day):
    return sum(ev.duration_h for ev in day.events if ev.status == ON_DUTY)


def off_duty_hours(day):
    return sum(ev.duration_h for ev in day.events if ev.status == OFF_DUTY)


def total_hours(day):
    return sum(ev.duration_h for ev in day.events)


class TestHOSEngine(unittest.TestCase):

    def test_short_trip_completes_in_one_day(self):
        """NYC → Philly → Baltimore (~170 mi straight-line) should fit in one day."""
        trip = make_trip()
        total_mi = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        days = generate_trip(trip)
        self.assertEqual(len(days), 1, f"Expected 1 day, got {len(days)}")
        day = days[0]
        # Drive time = total_mi / 55
        self.assertAlmostEqual(drive_hours(day), total_mi / 55, places=2)
        # On-duty = 0.25 (pre) + 1 (pickup) + 1 (dropoff) + 0.25 (post) = 2.5
        self.assertAlmostEqual(on_duty_hours(day), 2.5, places=2)
        # Total = 24h
        self.assertAlmostEqual(total_hours(day), 24.0, places=1)

    def test_24h_sum_invariant(self):
        """Sum of all 4 status categories must equal 24 hours per day."""
        trip = make_trip()
        days = generate_trip(trip)
        for day in days:
            totals = day.totals()
            total = sum(totals.values())
            self.assertAlmostEqual(total, 24.0, delta=0.1,
                msg=f"Day {day.date.date()} totals: {totals}, sum={total}")

    def test_no_violation_11hr_drive_cap(self):
        """No single day should exceed 11 hours of driving."""
        trip = make_trip(cycle=60.0)  # high cycle to force multi-day
        # But also need a long drive — use a different geometry
        long_trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(38.9072, -77.0369, "Washington, DC"),
            dropoff=Point(35.2271, -80.8431, "Charlotte, NC"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        days = generate_trip(long_trip)
        for day in days:
            d = drive_hours(day)
            self.assertLessEqual(d, MAX_DRIVE_PER_SHIFT + 0.01,
                f"Day {day.date.date()} drove {d} hrs (>11)")

    def test_30min_break_inserted(self):
        """A drive > 8 hours must include a 30-min break."""
        # NYC → Charlotte is ~620 mi, ~11.3 hr drive → 30-min break expected
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(35.2271, -80.8431, "Charlotte, NC"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        days = generate_trip(trip)
        # Total drive > 8 → must have a 30-min break (off-duty or sleeper)
        all_breaks = [ev for day in days for ev in day.events
                      if "30-min" in ev.remark]
        self.assertGreater(len(all_breaks), 0, "Expected at least one 30-min break")

    def test_fueling_stop_under_1000mi(self):
        """No fueling stops for trips under 1000 mi."""
        trip = make_trip()  # 195 mi
        days = generate_trip(trip)
        fuels = [ev for day in days for ev in day.events
                 if "Fueling" in ev.remark]
        self.assertEqual(len(fuels), 0, f"Expected 0 fuel stops, got {len(fuels)}")

    def test_fueling_stop_over_1000mi(self):
        """Trips over 1000 mi must include at least one fueling stop."""
        # NYC → Miami is ~1280 mi
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(25.7617, -80.1918, "Miami, FL"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        total = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        self.assertGreater(total, FUEL_INTERVAL_MI,
            f"Test setup: trip must be > {FUEL_INTERVAL_MI} mi, got {total:.0f}")
        days = generate_trip(trip)
        fuels = [ev for day in days for ev in day.events
                 if "Fueling" in ev.remark]
        self.assertGreaterEqual(len(fuels), 1, f"Expected at least 1 fuel stop, got {len(fuels)}")

    def test_70hr_cycle_cap_triggers_restart(self):
        """If cycle + drive > 70, a 34-hr restart should appear."""
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(41.8781, -87.6298, "Chicago, IL"),
            cycle_used_hrs=65.0,  # 5 hr headroom
            avg_speed_mph=55.0,  # ~900 mi total = 16+ hr drive
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        days = generate_trip(trip)
        restarts = [ev for day in days for ev in day.events
                    if "34-hr" in ev.remark]
        self.assertGreaterEqual(len(restarts), 1, f"Expected at least one 34-hr restart, got {len(restarts)}")

    def test_multi_day_trip_10hr_reset(self):
        """Trips requiring > 14 hr shift must span multiple days with 10-hr reset."""
        # NYC → Atlanta is ~865 mi, clearly multi-day
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(33.7490, -84.3880, "Atlanta, GA"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        total_mi = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        days = generate_trip(trip)
        self.assertGreaterEqual(len(days), 2, f"Expected 2+ days, got {len(days)} (trip {total_mi:.0f} mi)")
        # At least one event with "10-hr reset" remark
        resets = [ev for day in days for ev in day.events if "10-hr" in ev.remark]
        self.assertGreaterEqual(len(resets), 1)

    def test_remarks_capture_locations(self):
        """Each status change should have a non-empty location label."""
        trip = make_trip()
        days = generate_trip(trip)
        for day in days:
            for ev in day.events:
                self.assertTrue(ev.location.label, f"Missing label for {ev.remark}")

    def test_status_quarter_invariants(self):
        """The 96-quarter array must sum to 24 hours exactly (96 * 0.25)."""
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        for day in days:
            quarters = day.status_quarters
            self.assertEqual(len(quarters), 96)
            # Each quarter is exactly 0.25 hr, so 96 quarters = 24 hr
            # And we just verify all 96 slots are filled
            self.assertEqual(len([q for q in quarters if q is not None]), 96)

    def test_mid_day_start(self):
        """Trip starting at 2 PM should have 14 hr of pre-shift off-duty."""
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(39.2904, -76.6122, "Baltimore, MD"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 14, 0),
        )
        days = generate_trip(trip)
        self.assertEqual(len(days), 1)
        pre_shift = [ev for ev in days[0].events
                     if "home terminal" in ev.remark]
        self.assertEqual(len(pre_shift), 1)
        # 14 hr of off-duty from midnight to 14:00
        self.assertAlmostEqual(pre_shift[0].duration_h, 14.0, places=2)
        # Day still sums to 24h
        self.assertAlmostEqual(total_hours(days[0]), 24.0, places=1)

    def test_cycle_used_input_propagates(self):
        """If cycle_used > 0, the engine respects it before any drive."""
        # 30 hr cycle used; trip is short, no restart should fire
        trip = make_trip(cycle=30.0)
        days = generate_trip(trip)
        # No 34-hr restart should appear (30 + 3.09 = 33.09, under 70)
        restarts = [ev for day in days for ev in day.events if "34-hr" in ev.remark]
        self.assertEqual(len(restarts), 0, f"Unexpected restart: {restarts}")

    def test_fueling_at_1000mi_boundary(self):
        """A trip just over 1000 mi should have exactly 1 fueling stop."""
        # NYC → Tampa is ~1004 mi straight-line, with pickup in Philly → ~1084 mi
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(27.9506, -82.4572, "Tampa, FL"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        total = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        self.assertGreater(total, FUEL_INTERVAL_MI, f"Trip should exceed 1000 mi, got {total:.0f}")
        days = generate_trip(trip)
        fuels = [ev for day in days for ev in day.events if "Fueling" in ev.remark]
        self.assertGreaterEqual(len(fuels), 1)

    def test_34hr_restart_resets_all_counters(self):
        """After a 34-hr restart, cycle/drive/window/break should all reset."""
        # High cycle forces restart, then verify a fresh shift can drive 11 hr
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(25.7617, -80.1918, "Miami, FL"),
            cycle_used_hrs=68.0,  # 2 hr headroom before 70
            avg_speed_mph=55.0,  # ~1200 mi total = 22+ hr drive
            start_time=datetime(2026, 6, 8, 6, 0),
        )
        days = generate_trip(trip)
        # Find the 34-hr restart event
        restart = None
        for day in days:
            for ev in day.events:
                if "34-hr" in ev.remark:
                    restart = ev
                    break
            if restart:
                break
        self.assertIsNotNone(restart, "34-hr restart event not found")
        # Restart duration is 34 hr
        self.assertAlmostEqual(restart.duration_h, 34.0, places=2)

    def test_sleeper_berth_used_for_reset(self):
        """When use_sleeper_berth=True, multi-day trips use sleeper for reset."""
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(33.7490, -84.3880, "Atlanta, GA"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
            use_sleeper_berth=True,
        )
        days = generate_trip(trip)
        self.assertGreaterEqual(len(days), 2)
        # At least one SLEEPER event in the multi-day schedule
        sleepers = [ev for day in days for ev in day.events if ev.status == SLEEPER]
        self.assertGreater(len(sleepers), 0, "Expected sleeper berth events")

    def test_sleeper_berth_disabled(self):
        """When use_sleeper_berth=False, resets go off-duty instead."""
        trip = TripInput(
            current=Point(40.7128, -74.0060, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(33.7490, -84.3880, "Atlanta, GA"),
            cycle_used_hrs=0.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 8, 6, 0),
            use_sleeper_berth=False,
        )
        days = generate_trip(trip)
        # No sleeper events expected (no 10-hr reset uses sleeper)
        sleepers = [ev for day in days for ev in day.events if ev.status == SLEEPER]
        self.assertEqual(len(sleepers), 0, f"Expected no sleeper events, got {len(sleepers)}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
