"""
Trip engine — shared geometry, routing utilities, and trip timeline helpers.

Extracted from the original HOS engine. FMCSA-specific regulation logic
removed; reusable data structures and geometric utilities preserved.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
import math


@dataclass
class Point:
    lat: float
    lon: float
    label: str = ""


@dataclass
class Leg:
    start: Point
    end: Point
    distance_km: float


@dataclass
class Event:
    start: datetime
    duration_h: float
    status: str
    location: Point
    remark: str
    cumulative_km: float = 0.0
    leg_kind: Optional[str] = None


@dataclass
class DayBucket:
    date: datetime
    events: List[Event] = field(default_factory=list)
    total_km: float = 0.0
    deadhead_km: float = 0.0
    loaded_km: float = 0.0


def haversine_km(a: Point, b: Point) -> float:
    """Great-circle distance in kilometres."""
    R = 6371.0
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = lat2 - lat1
    dlon = math.radians(b.lon - a.lon)
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def interpolate(a: Point, b: Point, fraction: float) -> Point:
    """Linear interpolation between two Points; returns a Point with a generated label."""
    if not (0.0 <= fraction <= 1.0):
        fraction = max(0.0, min(1.0, fraction))
    return Point(
        lat=a.lat + (b.lat - a.lat) * fraction,
        lon=a.lon + (b.lon - a.lon) * fraction,
        label=f"On route to {b.label}" if b.label else "On route",
    )


def fill_to_midnight(
    events: List[Event],
    start_time: datetime,
    remark: str = "Off duty",
    location: Optional[Point] = None,
):
    """Fill the rest of the current day as off-duty, ending at midnight."""
    midnight = start_time.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    remaining = (midnight - start_time).total_seconds() / 3600.0
    if remaining > 0.001:
        loc = location or Point(lat=0, lon=0, label="Unknown")
        events.append(Event(start_time, remaining, "off_duty", loc, remark))


def group_events_by_day(events: List[Event]) -> List[DayBucket]:
    """Group events into daily buckets, calculating per-day totals."""
    days: List[DayBucket] = []
    for ev in events:
        day_date = ev.start.replace(hour=0, minute=0, second=0, microsecond=0)
        if not days or days[-1].date != day_date:
            days.append(DayBucket(date=day_date))
        days[-1].events.append(ev)

    for day in days:
        if not day.events:
            continue
        day.total_km = 0.0
        for ev in day.events:
            if ev.status == "driving":
                if ev.leg_kind == "deadhead":
                    day.deadhead_km += ev.cumulative_km
                else:
                    day.loaded_km += ev.cumulative_km
        day.total_km = day.deadhead_km + day.loaded_km

    return days


def compute_stops(
    origin: Point,
    destination: Point,
    waypoints: Optional[List[Point]] = None,
) -> List[dict]:
    """Lat/lon + label for map markers (origin, waypoints, destination)."""
    stops = [{"lat": origin.lat, "lon": origin.lon, "label": origin.label, "kind": "origin"}]
    if waypoints:
        for wp in waypoints:
            stops.append({"lat": wp.lat, "lon": wp.lon, "label": wp.label, "kind": "waypoint"})
    stops.append({"lat": destination.lat, "lon": destination.lon, "label": destination.label, "kind": "destination"})
    return stops


def total_crow_distance_km(
    origin: Point,
    destination: Point,
    waypoints: Optional[List[Point]] = None,
) -> float:
    """Sum of great-circle distances from origin through waypoints to destination."""
    total = 0.0
    points = [origin]
    if waypoints:
        points.extend(waypoints)
    points.append(destination)
    for i in range(len(points) - 1):
        total += haversine_km(points[i], points[i + 1])
    return total
