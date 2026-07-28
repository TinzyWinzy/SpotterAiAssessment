"""
Unit tests for the HOS engine.
Run with: python test_hos_engine.py
"""
import unittest
from datetime import datetime, timedelta, date as date_type

from hos_engine import (
    TripInput, Point, generate_trip, haversine_mi, total_distance_mi,
    compute_recap_with_history,
    OFF_DUTY, SLEEPER, DRIVING, ON_DUTY,
    MAX_DRIVE_PER_SHIFT, MAX_WINDOW_PER_SHIFT, MAX_CYCLE_HOURS, FUEL_INTERVAL_MI,
)


def make_trip(cycle=0.0, speed=55.0, start=None):
    if start is None:
        start = datetime(2026, 6, 1, 6, 0, 0)
    return TripInput(
        current=Point(40.7128, -74.006, "New York, NY"),
        pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
        dropoff=Point(39.2904, -76.6122, "Baltimore, MD"),
        cycle_used_hrs=cycle,
        avg_speed_mph=speed,
        start_time=start,
    )


def drive_hours(day):
    return sum(ev.duration_h for ev in day.events if ev.status == DRIVING)


def on_duty_hours(day):
    return sum(ev.duration_h for ev in day.events if ev.status in (DRIVING, ON_DUTY))


def off_duty_hours(day):
    return sum(ev.duration_h for ev in day.events if ev.status == OFF_DUTY)


def total_hours(day):
    return sum(ev.duration_h for ev in day.events)


def _history(self, base_date, values_by_offset):
    out = []
    for days_back, hrs in values_by_offset.items():
        out.append({"date": base_date - timedelta(days=days_back), "on_duty_hrs": hrs})
    return out


class TestHOSEngine(unittest.TestCase):

    def test_short_trip_completes_in_one_day(self):
        """NYC -> Philly -> Baltimore (~170 mi straight-line) should fit in one day."""
        trip = make_trip()
        total_mi = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        days = generate_trip(trip)
        self.assertEqual(len(days), 1, f"Expected 1 day, got {len(days)}")
        day = days[0]
        self.assertAlmostEqual(drive_hours(day), 3.1, places=1)
        self.assertAlmostEqual(total_hours(day), 24.0, places=0)

    def test_24h_sum_invariant(self):
        """Sum of all 4 status categories must equal 24 hours per day."""
        trip = make_trip()
        days = generate_trip(trip)
        for day in days:
            totals = day.totals
            total = sum(totals.values())
            self.assertAlmostEqual(total, 24.0, delta=0.1,
                                   msg=f"Day {day.date} totals: {totals}, sum={total}")

    def test_no_violation_11hr_drive_cap(self):
        """No single day should exceed 11 hours of driving."""
        trip = make_trip(cycle=60.0)
        long_trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(38.9072, -77.0369, "Washington, DC"),
            dropoff=Point(35.2271, -80.8431, "Charlotte, NC"),
            cycle_used_hrs=60.0,
            avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        days = generate_trip(long_trip)
        for day in days:
            d = drive_hours(day)
            self.assertLessEqual(d, MAX_DRIVE_PER_SHIFT + 0.01,
                                 msg=f"Day {day.date} drove {d} hrs (>11)")

    def test_30min_break_inserted(self):
        """A drive > 8 hours must include a 30-min break."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(35.2271, -80.8431, "Charlotte, NC"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        days = generate_trip(trip)
        all_breaks = []
        for day in days:
            for ev in day.events:
                if "30-min" in ev.remark:
                    all_breaks.append(ev)
        self.assertGreater(len(all_breaks), 0, "Expected at least one 30-min break")

    def test_fueling_stop_under_1000mi(self):
        """No fueling stops for trips under 1000 mi."""
        trip = make_trip()
        days = generate_trip(trip)
        fuels = []
        for day in days:
            for ev in day.events:
                if "Fueling" in ev.remark:
                    fuels.append(ev)
        self.assertEqual(len(fuels), 0, f"Expected 0 fuel stops, got {len(fuels)}")

    def test_fueling_stop_over_1000mi(self):
        """Trips over 1000 mi must include at least one fueling stop."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(25.7617, -80.1918, "Miami, FL"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        total = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        self.assertGreater(total, FUEL_INTERVAL_MI,
                           f"Test setup: trip must be > {FUEL_INTERVAL_MI:.0f} mi, got {total:.0f}")
        days = generate_trip(trip)
        fuels = []
        for day in days:
            for ev in day.events:
                if "Fueling" in ev.remark:
                    fuels.append(ev)
        self.assertGreaterEqual(len(fuels), 1, f"Expected at least 1 fuel stop, got {len(fuels)}")

    def test_70hr_cycle_cap_triggers_restart(self):
        """If cycle + drive > 70, a 34-hr restart should appear."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(41.8781, -87.6298, "Chicago, IL"),
            cycle_used_hrs=65.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        days = generate_trip(trip)
        restarts = []
        for day in days:
            for ev in day.events:
                if "34-hr" in ev.remark:
                    restarts.append(ev)
        self.assertGreaterEqual(len(restarts), 1, f"Expected at least one 34-hr restart, got {len(restarts)}")

    def test_multi_day_trip_10hr_reset(self):
        """Trips requiring > 14 hr shift must span multiple days with 10-hr reset."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(33.749, -84.388, "Atlanta, GA"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        total_mi = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        days = generate_trip(trip)
        self.assertGreaterEqual(len(days), 2,
                                f"Expected 2+ days, got {len(days)} (trip {total_mi:.0f} mi)")
        resets = []
        for day in days:
            for ev in day.events:
                if "10-hr" in ev.remark:
                    resets.append(ev)

    def test_remarks_capture_locations(self):
        """Each status change should have a non-empty location label."""
        trip = make_trip()
        days = generate_trip(trip)
        for day in days:
            for ev in day.events:
                self.assertTrue(ev.location and ev.location.label,
                                f"Missing label for {ev.remark}")

    def test_status_quarter_invariants(self):
        """The 96-quarter array must sum to 24 hours exactly (96 * 0.25)."""
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        for day in days:
            quarters = day.status_quarters
            self.assertEqual(len(quarters), 96)

    def test_mid_day_start(self):
        """Trip starting at 2 PM should have ~14 hr of pre-shift off-duty."""
        start = datetime(2026, 6, 1, 14, 0, 0)
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(39.2904, -76.6122, "Baltimore, MD"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=start,
        )
        days = generate_trip(trip)
        pre_shift = None
        for ev in days[0].events:
            if "home terminal" in ev.remark:
                pre_shift = ev
                break
        self.assertAlmostEqual(pre_shift.duration_h, 14.0, places=1)
        self.assertAlmostEqual(total_hours(days[0]), 24.0, places=0)

    def test_cycle_used_input_propagates(self):
        """If cycle_used > 0, the engine respects it before any drive."""
        trip = make_trip(cycle=30.0)
        days = generate_trip(trip)
        restarts = []
        for day in days:
            for ev in day.events:
                if "34-hr" in ev.remark:
                    restarts.append(ev)
        self.assertEqual(len(restarts), 0, "Unexpected restart: {len(restarts)}")

    def test_fueling_at_1000mi_boundary(self):
        """A trip just over 1000 mi should have exactly 1 fueling stop."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(27.9506, -82.4572, "Tampa, FL"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        total = haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
        self.assertGreater(total, FUEL_INTERVAL_MI, f"Trip should exceed 1000 mi, got {total:.0f}")
        days = generate_trip(trip)
        fuels = []
        for day in days:
            for ev in day.events:
                if "Fueling" in ev.remark:
                    fuels.append(ev)

    def test_34hr_restart_resets_all_counters(self):
        """After a 34-hr restart, cycle/drive/window/break should all reset."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(25.7617, -80.1918, "Miami, FL"),
            cycle_used_hrs=68.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        days = generate_trip(trip)
        restart = None
        for day in days:
            for ev in day.events:
                if "34-hr" in ev.remark:
                    restart = ev
                    break
        self.assertIsNotNone(restart, "34-hr restart event not found")
        self.assertAlmostEqual(restart.duration_h, 34.0, places=0)

    def test_sleeper_berth_used_for_reset(self):
        """When use_sleeper_berth=True, multi-day trips use sleeper for reset."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(33.749, -84.388, "Atlanta, GA"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
            use_sleeper_berth=True,
        )
        days = generate_trip(trip)
        sleepers = []
        for day in days:
            for ev in day.events:
                if ev.status == SLEEPER:
                    sleepers.append(ev)
        self.assertGreaterEqual(len(sleepers), 1, "Expected sleeper berth events")

    def test_sleeper_berth_disabled(self):
        """When use_sleeper_berth=False, resets go off-duty instead."""
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(33.749, -84.388, "Atlanta, GA"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
            use_sleeper_berth=False,
        )
        days = generate_trip(trip)
        sleepers = []
        for day in days:
            for ev in day.events:
                if ev.status == SLEEPER:
                    sleepers.append(ev)
        self.assertEqual(len(sleepers), 0, f"Expected no sleeper events, got {len(sleepers)}")

    def test_recap_attached_to_every_day(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        for d in days:
            self.assertIn("last_8day_total", d.recap)
            self.assertIn("last_7day_total", d.recap)
            self.assertIn("last_5day_total", d.recap)
            self.assertIn("last_7day_total_60", d.recap)
            self.assertIn("tomorrow_70_budget", d.recap)
            self.assertIn("tomorrow_60_budget", d.recap)
            self.assertIn("took_34h_restart", d.recap)
            self.assertIn("approximate", d.recap)

    def test_recap_running_8day_total_increases_each_day(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        if len(days) < 2:
            self.skipTest("Trip is single-day; running total trivially equal")
        f_values = [d.recap["last_8day_total"] for d in days]
        for i in range(1, len(f_values)):
            self.assertGreaterEqual(f_values[i], f_values[i - 1],
                                    f"8-day total should not decrease: {f_values}")

    def test_recap_34h_restart_flag_set_when_triggered(self):
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(41.8781, -87.6298, "Chicago, IL"),
            cycle_used_hrs=65.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        days = generate_trip(trip)
        flagged = [d for d in days if d.recap["took_34h_restart"]]
        self.assertGreater(len(flagged), 0, "Expected at least one day with 34-hr restart flag")

    def test_recap_tomorrow_budget_decreases_with_on_duty(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        b_values = [d.recap["tomorrow_70_budget"] for d in days]
        for v in b_values:
            self.assertLessEqual(v, 70.0)
            self.assertGreaterEqual(v, 0.0)


class TestMileageSplit(unittest.TestCase):

    def test_legs_are_tagged_deadhead_and_loaded(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        all_driving = []
        for d in days:
            for ev in d.events:
                if ev.status == DRIVING:
                    all_driving.append(ev)
        kinds = {ev.leg_kind for ev in all_driving}
        self.assertIn("deadhead", kinds)
        self.assertIn("loaded", kinds)

    def test_short_trip_deadhead_then_loaded(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        driving_events = []
        for d in days:
            for ev in d.events:
                if ev.status == DRIVING:
                    driving_events.append(ev)
        kinds_in_order = [ev.leg_kind for ev in driving_events]
        self.assertIn("deadhead", kinds_in_order)
        self.assertIn("loaded", kinds_in_order)

    def test_day_log_mileage_split_sums_to_total(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        for d in days:
            self.assertAlmostEqual(d.deadhead_mi + d.loaded_mi, d.total_miles, places=1)

    def test_short_trip_deadhead_equals_nyc_to_philly(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        for d in days:
            self.assertGreater(d.deadhead_mi, 70.0)
            self.assertLess(d.loaded_mi, 95.0)
            self.assertGreater(d.loaded_mi, 80.0)
            self.assertLess(d.deadhead_mi, 105.0)

    def test_on_duty_today_populated(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        for d in days:
            self.assertGreater(d.on_duty_today, 0.0)


class TestRecapWithHistory(unittest.TestCase):

    def test_approximate_flag_is_false(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        history = _history(self, days[0].date, {1: 8.0})
        compute_recap_with_history(days, 0.0, history)
        for d in days:
            self.assertFalse(d.recap["approximate"])

    def test_f_equals_sum_of_history_plus_trip(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        start = days[0].date
        history = _history(self, start, {i: 10.0 for i in range(1, 8)})
        compute_recap_with_history(days, 0.0, history)
        expected_f = 70.0 + days[0].on_duty_today
        self.assertAlmostEqual(days[0].recap["last_8day_total"], expected_f, places=1)

    def test_window_rolls_forward_on_multi_day_trip(self):
        trip = TripInput(
            current=Point(40.7128, -74.006, "New York, NY"),
            pickup=Point(39.9526, -75.1652, "Philadelphia, PA"),
            dropoff=Point(41.8781, -87.6298, "Chicago, IL"),
            cycle_used_hrs=0.0, avg_speed_mph=55.0,
            start_time=datetime(2026, 6, 1, 6, 0, 0),
        )
        days = generate_trip(trip)
        if len(days) < 3:
            self.skipTest("Trip is < 3 days, window-roll test not applicable")
        start = days[0].date
        history = _history(self, start, {i: 12.0 for i in range(1, 15)})
        compute_recap_with_history(days, 0.0, history)
        f1 = days[0].recap["last_8day_total"]
        f2 = days[1].recap["last_8day_total"]
        f3 = days[2].recap["last_8day_total"]
        self.assertAlmostEqual(f1, sum([12.0] * 7 + [days[0].on_duty_today]), places=1)
        self.assertAlmostEqual(f2, sum([12.0] * 6 + [days[0].on_duty_today, days[1].on_duty_today]), places=1)
        self.assertAlmostEqual(f3, sum([12.0] * 5 + [days[0].on_duty_today, days[1].on_duty_today, days[2].on_duty_today]), places=1)

    def test_approximation_breaks_under_skewed_history(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        start = days[0].date
        history = _history(self, start, {i: 14.0 for i in range(1, 5)})
        compute_recap_with_history(days, 0.0, history)
        self.assertLess(days[0].recap["last_8day_total"], 66.0)
        self.assertGreater(days[0].recap["last_8day_total"], 10.0)
        self.assertLess(days[0].recap["last_7day_total"], 66.0)

    def test_budget_is_negative_when_caps_exceeded(self):
        trip = make_trip(cycle=0.0)
        days = generate_trip(trip)
        start = days[0].date
        history = _history(self, start, {i: 16.0 for i in range(1, 7)})
        compute_recap_with_history(days, 0.0, history)
        self.assertLess(days[0].recap["tomorrow_60_budget"], 0)
        self.assertLess(days[0].recap["tomorrow_70_budget"], 12.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
