"""
FMCSA Hours of Service engine — property-carrying, 70hr/8day, no adverse conditions.

Per FMCSA-HOS-395 (April 2022): 11-hr driving limit, 14-hr on-duty window, 30-min break
after 8 cumulative driving hours, 10-hr reset between shifts, 70 hr on-duty in any
rolling 8-day period (resettable by a 34-hr restart), fueling at least once per 1,000 mi,
1 hr on-duty per pickup/dropoff. Sleeper berth optionally used for resets and breaks.

Day boundary is midnight local time. Coordinates of intermediate stops are interpolated
along the route polyline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
import math

OFF_DUTY = 0
SLEEPER = 1
DRIVING = 2
ON_DUTY = 3

STATUS_NAMES = {0: "Off Duty", 1: "Sleeper Berth", 2: "Driving", 3: "On Duty (Not Driving)"}

MAX_DRIVE_PER_SHIFT = 11.0
MAX_WINDOW_PER_SHIFT = 14.0
REQUIRED_BREAK_AFTER_DRIVE = 8.0
BREAK_DURATION = 0.5
REQUIRED_RESET = 10.0
MAX_CYCLE_HOURS = 70.0
RESTART_34_HOURS = 34.0
FUEL_INTERVAL_MI = 1000.0
FUEL_DURATION = 0.5
PICKUP_DURATION = 1.0
DROPOFF_DURATION = 1.0
PRE_TRIP_DURATION = 0.25
POST_TRIP_DURATION = 0.25
AVG_SPEED_MPH = 55.0
DAY_START_HOUR = 6


@dataclass
class Point:
    lat: float
    lon: float
    label: str = ""


@dataclass
class Leg:
    start: Point
    end: Point
    distance_mi: float


@dataclass
class TripInput:
    current: Point
    pickup: Point
    dropoff: Point
    cycle_used_hrs: float = 0.0
    avg_speed_mph: float = AVG_SPEED_MPH
    start_time: Optional[datetime] = None
    use_sleeper_berth: bool = True

    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now().replace(
                hour=DAY_START_HOUR, minute=0, second=0, microsecond=0
            )


@dataclass
class Event:
    start: datetime
    duration_h: float
    status: int
    location: Point
    remark: str
    cumulative_miles: float = 0.0
    leg_kind: Optional[str] = None  # "deadhead" | "loaded" | None (non-driving)


@dataclass
class DayLog:
    date: datetime
    events: List[Event] = field(default_factory=list)
    total_miles: float = 0.0
    deadhead_mi: float = 0.0
    loaded_mi: float = 0.0
    on_duty_today: float = 0.0
    warnings: List[str] = field(default_factory=list)
    recap: dict = field(default_factory=dict)

    @property
    def status_quarters(self) -> List[int]:
        """96 quarter-hour slots of duty status for the day."""
        quarters = [OFF_DUTY] * 96
        for ev in self.events:
            start_idx = int((ev.start.hour * 60 + ev.start.minute) / 15)
            length = max(1, int(round(ev.duration_h * 4)))
            for i in range(length):
                if 0 <= start_idx + i < 96:
                    quarters[start_idx + i] = ev.status
        return quarters

    def totals(self) -> dict:
        q = self.status_quarters
        return {
            "off_duty": q.count(OFF_DUTY) * 0.25,
            "sleeper": q.count(SLEEPER) * 0.25,
            "driving": q.count(DRIVING) * 0.25,
            "on_duty": q.count(ON_DUTY) * 0.25,
        }


@dataclass
class State:
    """Mutable trip-building state."""
    now: datetime
    window_start: datetime
    drive_today: float = 0.0
    drive_since_break: float = 0.0
    on_duty_today: float = 0.0
    cycle_used: float = 0.0
    total_miles: float = 0.0
    miles_since_fuel: float = 0.0
    avg_speed: float = AVG_SPEED_MPH
    last_loc: Optional[Point] = None
    use_sleeper_berth: bool = True

    def advance(self, hours: float):
        self.now += timedelta(hours=hours)


def compute_recap(days: List[DayLog], cycle_used_hrs: float) -> None:
    """Attach a `recap` dict to every DayLog in `days` (in-place).

    Recap values follow the FMCSA paper-form table:

      70 Hour / 8 Day Drivers
        A. Total hours on duty last 7 days including today
        B. Total hours available tomorrow = 70 - A
        F. Total hours on duty last 8 days including today
      60 Hour / 7 Day Drivers
        C. Total hours on duty last 5 days including today
        D. Total hours on duty last 7 days including today
        E. Total hours available tomorrow = 60 - C

    `cycle_used_hrs` is the user's claim of on-duty in the last 8 days
    before this trip. A, C, D are approximations: we assume the prior
    on-duty was evenly spread over the 8 days, so the 7-day figure is
    `total_8day * 7/8` and the 5-day figure is `total_8day * 5/8`. The
    flag is surfaced in the UI so reviewers know.
    """
    running = cycle_used_hrs
    for day in days:
        day_on_duty = sum(
            ev.duration_h
            for ev in day.events
            if ev.status in (DRIVING, ON_DUTY)
        )
        running += day_on_duty
        f_total = running
        a_7day = f_total * 7.0 / 8.0
        c_5day = f_total * 5.0 / 8.0
        d_7day_60 = c_5day + day_on_duty
        day.recap = {
            "cycle_used_hrs": round(cycle_used_hrs, 2),
            "on_duty_today": round(day_on_duty, 2),
            "last_8day_total": round(f_total, 2),
            "last_7day_total": round(a_7day, 2),
            "tomorrow_70_budget": round(70.0 - a_7day, 2),
            "last_5day_total": round(c_5day, 2),
            "last_7day_total_60": round(d_7day_60, 2),
            "tomorrow_60_budget": round(60.0 - c_5day, 2),
            "took_34h_restart": any("34-hr" in ev.remark for ev in day.events),
            "approximate": True,
        }


def compute_recap_with_history(
    days: List[DayLog],
    history: List[dict],
    cycle_used_hrs: float = 0.0,
) -> None:
    """Attach a `recap` dict using real per-day on-duty history (no approximation).

    `history` is a list of `{"date": date, "on_duty_hrs": float}` records for
    days *before* the trip. Missing dates are treated as 0. The 8/7/5-day
    windows roll forward as the trip progresses (day 2 of the trip drops
    the oldest pre-trip day and includes the new trip day).
    """
    on_duty: dict = {}
    for h in history:
        d = h["date"]
        if isinstance(d, datetime):
            d = d.date()
        on_duty[d] = on_duty.get(d, 0.0) + float(h["on_duty_hrs"])

    for day in days:
        d = day.date.date() if isinstance(day.date, datetime) else day.date
        on_duty[d] = on_duty.get(d, 0.0) + day.on_duty_today

    def sum_window(end_date, n_days: int) -> float:
        start = end_date - timedelta(days=n_days - 1)
        return sum(
            on_duty.get(start + timedelta(days=i), 0.0)
            for i in range(n_days)
        )

    for day in days:
        d = day.date.date() if isinstance(day.date, datetime) else day.date
        f_total = sum_window(d, 8)
        a_7day = sum_window(d, 7)
        c_5day = sum_window(d, 5)
        day.recap = {
            "cycle_used_hrs": round(cycle_used_hrs, 2),
            "on_duty_today": round(day.on_duty_today, 2),
            "last_8day_total": round(f_total, 2),
            "last_7day_total": round(a_7day, 2),
            "tomorrow_70_budget": round(70.0 - a_7day, 2),
            "last_5day_total": round(c_5day, 2),
            "last_7day_total_60": round(a_7day, 2),
            "tomorrow_60_budget": round(60.0 - c_5day, 2),
            "took_34h_restart": any("34-hr" in ev.remark for ev in day.events),
            "approximate": False,
        }


def haversine_mi(a: Point, b: Point) -> float:
    """Great-circle distance in miles."""
    R = 3958.8
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def interpolate(a: Point, b: Point, fraction: float) -> Point:
    """Linear interp between two Points; returns a Point with a generated label."""
    if not (0.0 <= fraction <= 1.0):
        fraction = max(0.0, min(1.0, fraction))
    return Point(
        lat=a.lat + (b.lat - a.lat) * fraction,
        lon=a.lon + (b.lon - a.lon) * fraction,
        label=f"On route to {b.label}" if b.label else "On route",
    )


def add_on_duty(events: List[Event], state: State, duration: float, location: Point, remark: str):
    events.append(Event(state.now, duration, ON_DUTY, location, remark, state.total_miles))
    state.advance(duration)
    state.on_duty_today += duration


def add_off_duty(events: List[Event], state: State, duration: float, location: Point, remark: str):
    events.append(Event(state.now, duration, OFF_DUTY, location, remark, state.total_miles))
    state.advance(duration)


def add_sleeper(events: List[Event], state: State, duration: float, location: Point, remark: str):
    events.append(Event(state.now, duration, SLEEPER, location, remark, state.total_miles))
    state.advance(duration)


def take_30min_break(events: List[Event], state: State):
    if state.use_sleeper_berth:
        add_sleeper(events, state, BREAK_DURATION, state.last_loc, "30-min break (sleeper berth)")
    else:
        add_off_duty(events, state, BREAK_DURATION, state.last_loc, "30-min break (off duty)")
    state.drive_since_break = 0.0


def take_fuel_stop(events: List[Event], state: State, location: Point):
    add_on_duty(events, state, FUEL_DURATION, location, "Fueling")
    state.miles_since_fuel = 0.0


def fill_to_midnight(events: List[Event], state: State, remark: str = "Off duty"):
    """Fill the rest of the current day as off-duty, ending at midnight."""
    midnight = state.now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    remaining = (midnight - state.now).total_seconds() / 3600.0
    if remaining > 0.001:
        add_off_duty(events, state, remaining, state.last_loc, remark)


def take_10hr_reset(events: List[Event], state: State):
    """End the current shift. Fill rest of day as off-duty, then add 10 hr
    off-duty/sleeper going into the next day. Resets the 11+14 counters."""
    fill_to_midnight(events, state, "Off duty (end of shift)")
    next_start = state.now.replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
    if state.now > next_start:
        next_start += timedelta(days=1)
    gap_h = (next_start - state.now).total_seconds() / 3600.0
    if gap_h > 0.001:
        if state.use_sleeper_berth:
            add_sleeper(events, state, gap_h, state.last_loc, "10-hr reset (sleeper berth)")
        else:
            add_off_duty(events, state, gap_h, state.last_loc, "10-hr reset (off duty)")
    state.window_start = state.now
    state.drive_today = 0.0
    state.drive_since_break = 0.0
    state.on_duty_today = 0.0


def take_34hr_restart(events: List[Event], state: State):
    if state.use_sleeper_berth:
        add_sleeper(events, state, RESTART_34_HOURS, state.last_loc, "34-hr restart (sleeper berth)")
    else:
        add_off_duty(events, state, RESTART_34_HOURS, state.last_loc, "34-hr restart (off duty)")
    state.cycle_used = 0.0
    state.window_start = state.now
    state.drive_today = 0.0
    state.drive_since_break = 0.0
    state.on_duty_today = 0.0


def drive_leg(events: List[Event], state: State, leg: Leg, leg_kind: str = "loaded"):
    """Drive from leg.start to leg.end, breaking as required.

    `leg_kind` tags every DRIVING event emitted by this leg so the day log
    can split deadhead (empty) miles from loaded miles. Priority order
    when a limit is hit:
      1. 30-min break (if drive_since_break >= 8)
      2. Fueling stop (if miles_since_fuel >= 1000)
      3. 10-hr reset (if drive_today >= 11 or window >= 14)
      4. 34-hr restart (if cycle >= 70)
    """
    miles_remaining = leg.distance_mi

    while miles_remaining > 0.001:
        if state.cycle_used >= MAX_CYCLE_HOURS - 0.01:
            take_34hr_restart(events, state)
            continue

        drive_to_11 = MAX_DRIVE_PER_SHIFT - state.drive_today
        drive_to_break = REQUIRED_BREAK_AFTER_DRIVE - state.drive_since_break
        elapsed_window = (state.now - state.window_start).total_seconds() / 3600.0
        window_to_14 = MAX_WINDOW_PER_SHIFT - elapsed_window
        miles_to_fuel = FUEL_INTERVAL_MI - state.miles_since_fuel
        fuel_h = miles_to_fuel / state.avg_speed if miles_to_fuel > 0 else 0.0
        drive_to_dest = miles_remaining / state.avg_speed

        if drive_to_break <= 0.001:
            take_30min_break(events, state)
            continue
        if miles_to_fuel <= 0.001:
            progress = 1.0 - (miles_remaining / leg.distance_mi)
            loc = interpolate(leg.start, leg.end, max(0.0, min(1.0, progress)))
            loc.label = f"Fuel stop en route to {leg.end.label}" if leg.end.label else "Fuel stop"
            take_fuel_stop(events, state, loc)
            continue
        if drive_to_11 <= 0.001 or window_to_14 <= 0.001:
            take_10hr_reset(events, state)
            continue

        chunk_h = min(drive_to_11, drive_to_break, window_to_14, drive_to_dest, fuel_h)
        if chunk_h <= 0.001:
            break

        driven_mi = chunk_h * state.avg_speed
        progress = 1.0 - (miles_remaining - driven_mi) / leg.distance_mi
        loc = interpolate(leg.start, leg.end, max(0.0, min(1.0, progress)))
        events.append(Event(
            state.now, chunk_h, DRIVING, loc, "Driving",
            state.total_miles + driven_mi, leg_kind=leg_kind,
        ))
        state.advance(chunk_h)
        state.drive_today += chunk_h
        state.drive_since_break += chunk_h
        state.cycle_used += chunk_h
        state.on_duty_today += chunk_h
        state.total_miles += driven_mi
        state.miles_since_fuel += driven_mi
        state.last_loc = loc
        miles_remaining -= driven_mi

    state.last_loc = leg.end


def group_by_day(events: List[Event]) -> List[DayLog]:
    days: List[DayLog] = []
    for ev in events:
        day_date = ev.start.replace(hour=0, minute=0, second=0, microsecond=0)
        if not days or days[-1].date != day_date:
            days.append(DayLog(date=day_date))
        days[-1].events.append(ev)
    for day in days:
        if not day.events:
            continue
        day.total_miles = 0.0
        for ev in day.events:
            if ev.status != DRIVING:
                continue
            miles = ev.duration_h * AVG_SPEED_MPH
            if ev.leg_kind == "deadhead":
                day.deadhead_mi += miles
            else:
                day.loaded_mi += miles
        day.total_miles = day.deadhead_mi + day.loaded_mi
        day.on_duty_today = sum(
            ev.duration_h
            for ev in day.events
            if ev.status in (DRIVING, ON_DUTY)
        )
    return days


def generate_trip(trip: TripInput) -> List[DayLog]:
    """Build a full HOS-compliant timeline of events, grouped by day."""
    events: List[Event] = []
    state = State(
        now=trip.start_time,
        window_start=trip.start_time,
        cycle_used=trip.cycle_used_hrs,
        avg_speed=trip.avg_speed_mph,
        last_loc=trip.current,
        use_sleeper_berth=trip.use_sleeper_berth,
    )

    midnight = trip.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    pre_shift_h = (trip.start_time - midnight).total_seconds() / 3600.0
    if pre_shift_h > 0.001:
        state.now = midnight
        add_off_duty(events, state, pre_shift_h, trip.current, "Off duty (home terminal)")

    add_on_duty(events, state, PRE_TRIP_DURATION, trip.current, "Pre-trip inspection")
    state.window_start = state.now
    state.on_duty_today = PRE_TRIP_DURATION

    pickup_leg = Leg(start=trip.current, end=trip.pickup, distance_mi=haversine_mi(trip.current, trip.pickup))
    drive_leg(events, state, pickup_leg, leg_kind="deadhead")
    add_on_duty(events, state, PICKUP_DURATION, trip.pickup, "Pickup")

    drop_leg = Leg(start=trip.pickup, end=trip.dropoff, distance_mi=haversine_mi(trip.pickup, trip.dropoff))
    drive_leg(events, state, drop_leg, leg_kind="loaded")
    add_on_duty(events, state, DROPOFF_DURATION, trip.dropoff, "Dropoff")

    add_on_duty(events, state, POST_TRIP_DURATION, trip.dropoff, "Post-trip inspection")

    # Only consume a 10-hr reset if we actually hit the 11/14-hr cap;
    # otherwise just park at home terminal for the rest of the day.
    elapsed = (state.now - state.window_start).total_seconds() / 3600.0
    if state.drive_today >= MAX_DRIVE_PER_SHIFT - 0.01 or elapsed >= MAX_WINDOW_PER_SHIFT - 0.01:
        take_10hr_reset(events, state)
    else:
        fill_to_midnight(events, state, "Off duty (end of trip)")

    days = group_by_day(events)
    compute_recap(days, trip.cycle_used_hrs)
    return days


def compute_stops(trip: TripInput) -> List[dict]:
    """Lat/lon + label for map markers (start, pickup, dropoff)."""
    return [
        {"lat": trip.current.lat, "lon": trip.current.lon, "label": trip.current.label, "kind": "current"},
        {"lat": trip.pickup.lat, "lon": trip.pickup.lon, "label": trip.pickup.label, "kind": "pickup"},
        {"lat": trip.dropoff.lat, "lon": trip.dropoff.lon, "label": trip.dropoff.label, "kind": "dropoff"},
    ]


def total_distance_mi(trip: TripInput) -> float:
    return haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
