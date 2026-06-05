"""
FMCSA Hours of Service Engine — Property-Carrying, 70hr/8day, No Adverse Conditions.

Rules implemented (per FMCSA-HOS-395, April 2022):
  - 11-hour driving limit
  - 14-hour driving window (starts at first on-duty after 10+ hr off)
  - 30-minute break after 8 cumulative driving hours (off-duty/on-duty/sleeper)
  - 10 consecutive hours off-duty between shifts (resets 11+14)
  - 70 hours on-duty in 8 consecutive days (rolling)
  - 34-hour restart (resets 70/8 clock)
  - Fueling stop at least once per 1,000 mi (on-duty not driving)
  - 1 hr on-duty for pickup and dropoff
  - Sleeper berth supported (used for 10-hr reset by default)

Assumptions:
  - Property-carrying CMV
  - No adverse driving conditions
  - 70hr/8day schedule
  - Driver begins rested (10+ hr off before pre-trip)
  - Sleeper berth optionally used for 10-hr reset and 30-min break
  - Fueling stop = 0.5 hr on-duty not driving
  - Pre-trip inspection = 0.25 hr on-duty
  - Post-trip inspection = 0.25 hr on-duty
  - Average speed 55 mph
  - Day boundary = midnight local time
  - Coordinates of intermediate stops are interpolated along the route polyline
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta, time
from typing import List, Tuple
import math

# Duty status codes
OFF_DUTY = 0
SLEEPER = 1
DRIVING = 2
ON_DUTY = 3

STATUS_NAMES = {0: "Off Duty", 1: "Sleeper Berth", 2: "Driving", 3: "On Duty (Not Driving)"}

# Rule constants
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
DAY_START_HOUR = 6  # start shifts at 6 AM local


@dataclass
class Point:
    lat: float
    lon: float
    label: str = ""  # "City, ST" or "On route"


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
    start_time: datetime = None  # if None, today 6:00 AM
    use_sleeper_berth: bool = True  # 10-hr reset & 30-min break go to sleeper

    def __post_init__(self):
        if self.start_time is None:
            now = datetime.now().replace(hour=DAY_START_HOUR, minute=0, second=0, microsecond=0)
            self.start_time = now


@dataclass
class Event:
    start: datetime
    duration_h: float
    status: int
    location: Point
    remark: str
    cumulative_miles: float = 0.0  # total miles driven up to end of this event


@dataclass
class DayLog:
    date: datetime  # midnight of the day
    events: List[Event] = field(default_factory=list)
    total_miles: float = 0.0
    warnings: List[str] = field(default_factory=list)
    recap: dict = field(default_factory=dict)  # F, A, B, C, D, E, took_34h_restart, ...


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
    BEFORE this trip. We add the trip's on-duty (driving + on-duty) on top.

    Note: A, C, D are approximations because we don't have the user's prior
    day-by-day breakdown. We assume the prior on-duty was evenly spread over
    the 8 days, so the 7-day figure is `total_8day * 7/8` and the 5-day
    figure is `total_8day * 5/8`. These are labelled in the UI as
    "approximate" so reviewers know.
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
        d_7day_60 = c_5day + day_on_duty  # last 2 days of the 7-day window
        day.recap = {
            "cycle_used_hrs": round(cycle_used_hrs, 2),
            "on_duty_today": round(day_on_duty, 2),
            "last_8day_total": round(f_total, 2),       # F
            "last_7day_total": round(a_7day, 2),         # A
            "tomorrow_70_budget": round(70.0 - a_7day, 2),  # B
            "last_5day_total": round(c_5day, 2),         # C
            "last_7day_total_60": round(d_7day_60, 2),   # D
            "tomorrow_60_budget": round(60.0 - c_5day, 2),  # E
            "took_34h_restart": any("34-hr" in ev.remark for ev in day.events),
            "approximate": True,
        }


@dataclass
class DayLog:
    date: datetime  # midnight of the day
    events: List[Event] = field(default_factory=list)
    total_miles: float = 0.0
    warnings: List[str] = field(default_factory=list)
    recap: dict = field(default_factory=dict)  # F, A, B, C, D, E, took_34h_restart, ...

    @property
    def status_quarters(self) -> List[int]:
        """Return 96 entries (15-min each) of duty status for the day."""
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
    drive_today: float = 0.0  # hours driven since last 10-hr reset
    drive_since_break: float = 0.0  # hours driven since last 30-min break
    on_duty_today: float = 0.0
    cycle_used: float = 0.0
    total_miles: float = 0.0
    miles_since_fuel: float = 0.0
    avg_speed: float = AVG_SPEED_MPH
    last_loc: Point = None
    use_sleeper_berth: bool = True

    def advance(self, hours: float):
        self.now += timedelta(hours=hours)


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


# ──────────────────────────────────────────────────────────────────────
# Event builders (append to events + mutate state)
# ──────────────────────────────────────────────────────────────────────

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
    """Fill remaining hours of the current day as off-duty, ending at midnight."""
    midnight = state.now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    remaining = (midnight - state.now).total_seconds() / 3600.0
    if remaining > 0.001:
        add_off_duty(events, state, remaining, state.last_loc, remark)


def take_10hr_reset(events: List[Event], state: State):
    """End the current shift. Fill rest of day as off-duty, then add 10 hr
    off-duty/sleeper going into the next day. Resets 11+14 counters."""
    fill_to_midnight(events, state, "Off duty (end of shift)")
    # New shift starts at DAY_START_HOUR the next day
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
    # Also resets the daily shift
    state.window_start = state.now
    state.drive_today = 0.0
    state.drive_since_break = 0.0
    state.on_duty_today = 0.0


# ──────────────────────────────────────────────────────────────────────
# Main drive loop
# ──────────────────────────────────────────────────────────────────────

def drive_leg(events: List[Event], state: State, leg: Leg):
    """Drive from leg.start to leg.end, breaking as required.

    Priority order when limits hit:
      1. 30-min break (if drive_since_break >= 8)
      2. Fueling stop (if miles_since_fuel >= 1000)
      3. 10-hr reset (if drive_today >= 11 OR window >= 14)
      4. 34-hr restart (if cycle >= 70)
    """
    miles_remaining = leg.distance_mi

    while miles_remaining > 0.001:
        # 34-hr restart if cycle cap hit
        if state.cycle_used >= MAX_CYCLE_HOURS - 0.01:
            take_34hr_restart(events, state)
            continue

        # Compute remaining allowances (in hours of driving)
        drive_to_11 = MAX_DRIVE_PER_SHIFT - state.drive_today
        drive_to_break = REQUIRED_BREAK_AFTER_DRIVE - state.drive_since_break
        elapsed_window = (state.now - state.window_start).total_seconds() / 3600.0
        window_to_14 = MAX_WINDOW_PER_SHIFT - elapsed_window
        miles_to_fuel = FUEL_INTERVAL_MI - state.miles_since_fuel
        fuel_h = miles_to_fuel / state.avg_speed if miles_to_fuel > 0 else 0.0
        drive_to_dest = miles_remaining / state.avg_speed

        # Handle forced stops FIRST (priority order)
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

        # Drive the chunk limited by all positive limits
        chunk_h = min(drive_to_11, drive_to_break, window_to_14, drive_to_dest, fuel_h)
        if chunk_h <= 0.001:
            break  # safety

        driven_mi = chunk_h * state.avg_speed
        progress = 1.0 - (miles_remaining - driven_mi) / leg.distance_mi
        loc = interpolate(leg.start, leg.end, max(0.0, min(1.0, progress)))
        events.append(Event(state.now, chunk_h, DRIVING, loc, "Driving", state.total_miles + driven_mi))
        state.advance(chunk_h)
        state.drive_today += chunk_h
        state.drive_since_break += chunk_h
        state.cycle_used += chunk_h
        state.on_duty_today += chunk_h
        state.total_miles += driven_mi
        state.miles_since_fuel += driven_mi
        state.last_loc = loc
        miles_remaining -= driven_mi

    # Update last_loc to leg.end for the stop event
    state.last_loc = leg.end


# ──────────────────────────────────────────────────────────────────────
# Day grouping
# ──────────────────────────────────────────────────────────────────────

def group_by_day(events: List[Event]) -> List[DayLog]:
    days: List[DayLog] = []
    for ev in events:
        day_date = ev.start.replace(hour=0, minute=0, second=0, microsecond=0)
        if not days or days[-1].date != day_date:
            days.append(DayLog(date=day_date))
        days[-1].events.append(ev)
        if ev.status == DRIVING:
            # Account only this event's miles
            # (cumulative_miles field tracks end-of-event miles)
            pass
    # Compute per-day miles by differencing cumulative
    for day in days:
        prev = 0.0
        max_m = 0.0
        for ev in day.events:
            if ev.cumulative_miles > max_m:
                max_m = ev.cumulative_miles
        # Each day's miles = end-of-day cumulative - start-of-day cumulative
        # We approximate by max - min cumulative
        if day.events:
            start_cum = day.events[0].cumulative_miles
            # subtract driving-only events
            driving_miles = sum(
                ev.duration_h * AVG_SPEED_MPH
                for ev in day.events
                if ev.status == DRIVING
            )
            day.total_miles = driving_miles
    return days


# ──────────────────────────────────────────────────────────────────────
# Trip generation (public entry)
# ──────────────────────────────────────────────────────────────────────

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

    # 0. Pre-shift off-duty from midnight (so the day log sums to 24h)
    midnight = trip.start_time.replace(hour=0, minute=0, second=0, microsecond=0)
    pre_shift_h = (trip.start_time - midnight).total_seconds() / 3600.0
    if pre_shift_h > 0.001:
        state.now = midnight
        add_off_duty(events, state, pre_shift_h, trip.current, "Off duty (home terminal)")

    # 1. Pre-trip inspection
    add_on_duty(events, state, PRE_TRIP_DURATION, trip.current, "Pre-trip inspection")
    state.window_start = state.now  # 14-hr window starts at first on-duty
    state.on_duty_today = PRE_TRIP_DURATION

    # 2. Drive current → pickup
    pickup_leg = Leg(start=trip.current, end=trip.pickup, distance_mi=haversine_mi(trip.current, trip.pickup))
    drive_leg(events, state, pickup_leg)
    add_on_duty(events, state, PICKUP_DURATION, trip.pickup, "Pickup")

    # 3. Drive pickup → dropoff
    drop_leg = Leg(start=trip.pickup, end=trip.dropoff, distance_mi=haversine_mi(trip.pickup, trip.dropoff))
    drive_leg(events, state, drop_leg)
    add_on_duty(events, state, DROPOFF_DURATION, trip.dropoff, "Dropoff")

    # 4. Post-trip inspection
    add_on_duty(events, state, POST_TRIP_DURATION, trip.dropoff, "Post-trip inspection")

    # 5. End of trip: only take a 10-hr reset if we hit the 11-hr or 14-hr cap.
    # Otherwise, just fill the rest of the current day as off-duty (the driver
    # is done working and resting at home terminal).
    elapsed = (state.now - state.window_start).total_seconds() / 3600.0
    if state.drive_today >= MAX_DRIVE_PER_SHIFT - 0.01 or elapsed >= MAX_WINDOW_PER_SHIFT - 0.01:
        take_10hr_reset(events, state)
    else:
        fill_to_midnight(events, state, "Off duty (end of trip)")

    days = group_by_day(events)
    compute_recap(days, trip.cycle_used_hrs)
    return days


# ──────────────────────────────────────────────────────────────────────
# Public helpers
# ──────────────────────────────────────────────────────────────────────

def compute_stops(trip: TripInput) -> List[dict]:
    """Compute approximate lat/lon + label for map markers (start, pickup, dropoff)."""
    return [
        {"lat": trip.current.lat, "lon": trip.current.lon, "label": trip.current.label, "kind": "current"},
        {"lat": trip.pickup.lat, "lon": trip.pickup.lon, "label": trip.pickup.label, "kind": "pickup"},
        {"lat": trip.dropoff.lat, "lon": trip.dropoff.lon, "label": trip.dropoff.label, "kind": "dropoff"},
    ]


def total_distance_mi(trip: TripInput) -> float:
    return haversine_mi(trip.current, trip.pickup) + haversine_mi(trip.pickup, trip.dropoff)
