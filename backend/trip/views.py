"""Trip API views — POST /api/trip/ returns HOS logs + route geometry."""
from datetime import datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripRequestSerializer
import geocoding
import routing
import hos_engine
from hos_engine import (
    TripInput, Point, generate_trip, OFF_DUTY, SLEEPER, DRIVING, ON_DUTY,
)


@api_view(["POST"])
def trip_plan(request):
    """Plan an HOS-compliant trip.

    Body: {
      current_location: str,   # "New York, NY"
      pickup_location: str,
      dropoff_location: str,
      current_cycle_used_hrs: float,  # 0-70
      avg_speed_mph: float,          # default 55
      use_sleeper_berth: bool,       # default true
      start_time: ISO8601 datetime,  # optional
    }

    Returns: {
      ok: bool,
      stops: [{lat, lon, label, kind}],
      route: {distance_mi, duration_h, geometry},
      total_distance_mi: float,
      days: [{date, total_miles, events, totals, status_quarters}],
      warnings: [str],
    }
    """
    serializer = TripRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    data = serializer.validated_data

    current = geocoding.geocode(data["current_location"])
    pickup = geocoding.geocode(data["pickup_location"])
    dropoff = geocoding.geocode(data["dropoff_location"])

    if not (current and pickup and dropoff):
        missing = []
        if not current: missing.append("current_location")
        if not pickup: missing.append("pickup_location")
        if not dropoff: missing.append("dropoff_location")
        return Response(
            {"ok": False, "error": f"Geocoding failed for: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    route_result = routing.route([
        (current["lon"], current["lat"]),
        (pickup["lon"], pickup["lat"]),
        (dropoff["lon"], dropoff["lat"]),
    ])
    if not route_result:
        return Response(
            {"ok": False, "error": "Routing failed (OSRM unreachable)"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    trip = TripInput(
        current=Point(lat=current["lat"], lon=current["lon"], label=current["label"]),
        pickup=Point(lat=pickup["lat"], lon=pickup["lon"], label=pickup["label"]),
        dropoff=Point(lat=dropoff["lat"], lon=dropoff["lon"], label=dropoff["label"]),
        cycle_used_hrs=data["current_cycle_used_hrs"],
        avg_speed_mph=data["avg_speed_mph"],
        start_time=data.get("start_time") or datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0),
        use_sleeper_berth=data["use_sleeper_berth"],
    )

    days = generate_trip(trip)

    def fmt_event(ev):
        return {
            "start": ev.start.isoformat(),
            "duration_h": round(ev.duration_h, 3),
            "status": ev.status,
            "status_name": hos_engine.STATUS_NAMES[ev.status],
            "location": {"lat": ev.location.lat, "lon": ev.location.lon, "label": ev.location.label},
            "remark": ev.remark,
            "cumulative_miles": round(ev.cumulative_miles, 1),
        }

    days_payload = []
    for d in days:
        totals = d.totals()
        days_payload.append({
            "date": d.date.date().isoformat(),
            "total_miles": round(d.total_miles, 1),
            "events": [fmt_event(e) for e in d.events],
            "totals": {k: round(v, 2) for k, v in totals.items()},
            "status_quarters": d.status_quarters,
            "recap": d.recap,
        })

    stops = [
        {"lat": current["lat"], "lon": current["lon"], "label": current["label"], "kind": "current"},
        {"lat": pickup["lat"], "lon": pickup["lon"], "label": pickup["label"], "kind": "pickup"},
        {"lat": dropoff["lat"], "lon": dropoff["lon"], "label": dropoff["label"], "kind": "dropoff"},
    ]

    # Rest/fuel stops: any non-driving on-duty or break event at a location
    # other than the 3 main stops. Deduped by (lat, lon, kind).
    main_stop_labels = {current["label"], pickup["label"], dropoff["label"]}
    rest_stops = []
    seen_locs: set[tuple[float, float]] = set()
    for d in days:
        for ev in d.events:
            kind = None
            lbl = ev.remark
            low = ev.remark.lower()
            if "fuel" in low and ev.status == hos_engine.ON_DUTY:
                kind = "fuel"
            elif "30-min break" in low:
                kind = "break"
            elif "10-hr reset" in low or "34-hr restart" in low:
                kind = "rest"
            elif "pickup" in low and ev.status == hos_engine.ON_DUTY:
                kind = "pickup"
            elif "dropoff" in low and ev.status == hos_engine.ON_DUTY:
                kind = "dropoff"
            if kind is None or not ev.location or not ev.location.label:
                continue
            if ev.location.label in main_stop_labels:
                continue
            key = (round(ev.location.lat, 4), round(ev.location.lon, 4), kind)
            if key in seen_locs:
                continue
            seen_locs.add(key)
            rest_stops.append({
                "lat": ev.location.lat,
                "lon": ev.location.lon,
                "label": ev.location.label,
                "kind": kind,
                "remark": ev.remark,
                "day": d.date.date().isoformat(),
                "duration_h": round(ev.duration_h, 2),
                "cumulative_miles": round(ev.cumulative_miles, 1),
            })

    return Response({
        "ok": True,
        "stops": stops,
        "rest_stops": rest_stops,
        "route": {
            "distance_mi": round(route_result["distance_mi"], 1),
            "duration_h": round(route_result["duration_seconds"] / 3600, 2),
            "geometry": route_result["geometry"],
        },
        "total_distance_mi": round(route_result["distance_mi"], 1),
        "days": days_payload,
        "cycle_used_hrs": data["current_cycle_used_hrs"],
        "warnings": [],
    })


@api_view(["GET"])
def health(request):
    return Response({"ok": True, "service": "spotter-trip-planner"})
