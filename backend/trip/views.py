"""Trip API views — POST /api/trip/ returns HOS logs + route geometry."""
from datetime import datetime, date
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    TripRequestSerializer, DriverSerializer, DriverCreateSerializer,
    DayHistorySerializer,
)
from .models import Driver, DayHistory, Trip
import geocoding
import routing
import hos_engine
from hos_engine import (
    TripInput, Point, generate_trip, compute_recap, compute_recap_with_history,
    OFF_DUTY, SLEEPER, DRIVING, ON_DUTY,
)


@api_view(["POST"])
def trip_plan(request):
    """Plan an HOS-compliant trip.

    Body: {
      current_location, pickup_location, dropoff_location,
      current_cycle_used_hrs (0-70, optional when driver_id given),
      avg_speed_mph (default 55),
      use_sleeper_berth (default true),
      start_time (ISO8601, optional),
      driver_id (optional): if given, the driver's real per-day on-duty
        history is used for the recap table (no approximation), and each
        trip day's on-duty is appended to the driver's history.
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

    driver = None
    if data.get("driver_id"):
        try:
            driver = Driver.objects.get(pk=data["driver_id"])
        except Driver.DoesNotExist:
            return Response(
                {"ok": False, "error": f"driver_id {data['driver_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    cycle_used_hrs = data.get("current_cycle_used_hrs")
    if cycle_used_hrs is None and driver is not None:
        cycle_used_hrs = driver.current_cycle_used_hrs

    trip = TripInput(
        current=Point(lat=current["lat"], lon=current["lon"], label=current["label"]),
        pickup=Point(lat=pickup["lat"], lon=pickup["lon"], label=pickup["label"]),
        dropoff=Point(lat=dropoff["lat"], lon=dropoff["lon"], label=dropoff["label"]),
        cycle_used_hrs=cycle_used_hrs or 0.0,
        avg_speed_mph=data["avg_speed_mph"],
        start_time=data.get("start_time") or datetime.utcnow().replace(hour=6, minute=0, second=0, microsecond=0),
        use_sleeper_berth=data["use_sleeper_berth"],
    )

    days = generate_trip(trip)

    # Use real per-day history when a driver is supplied; otherwise
    # fall back to the approximate recap from cycle_used_hrs.
    history_records = []
    if driver is not None:
        history_records = [
            {"date": h.date, "on_duty_hrs": h.on_duty_hrs}
            for h in driver.day_history.all()
        ]
        compute_recap_with_history(days, history_records, cycle_used_hrs or 0.0)
    else:
        compute_recap(days, cycle_used_hrs or 0.0)

    def fmt_event(ev):
        return {
            "start": ev.start.isoformat(),
            "duration_h": round(ev.duration_h, 3),
            "status": ev.status,
            "status_name": hos_engine.STATUS_NAMES[ev.status],
            "location": {"lat": ev.location.lat, "lon": ev.location.lon, "label": ev.location.label},
            "remark": ev.remark,
            "cumulative_miles": round(ev.cumulative_miles, 1),
            "leg_kind": ev.leg_kind,
        }

    days_payload = []
    for d in days:
        totals = d.totals()
        days_payload.append({
            "date": d.date.date().isoformat(),
            "total_miles": round(d.total_miles, 1),
            "deadhead_mi": round(d.deadhead_mi, 1),
            "loaded_mi": round(d.loaded_mi, 1),
            "on_duty_today": round(d.on_duty_today, 2),
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

    # Persist each trip day's on-duty back to the driver's history so
    # the next plan call sees an accurate 8-day window.
    if driver is not None:
        for d in days:
            d_date = d.date.date()
            DayHistory.objects.update_or_create(
                driver=driver,
                date=d_date,
                source=DayHistory.SOURCE_GENERATED,
                defaults={
                    "on_duty_hrs": round(d.on_duty_today, 2),
                    "driving_hrs": round(
                        sum(ev.duration_h for ev in d.events if ev.status == DRIVING), 2
                    ),
                },
            )

    # Persist a summary record for the admin dashboard. The full event
    # stream stays in the response; this is the bookkeeping copy.
    total_miles = round(sum(d.total_miles for d in days), 1)
    total_driving = round(sum(d.deadhead_mi + d.loaded_mi for d in days) / max(trip.avg_speed_mph, 1), 2)
    total_on_duty = round(sum(d.on_duty_today for d in days), 2)
    final_cycle = days[-1].recap.get("last_8day_total", 0) if days else 0
    Trip.objects.create(
        driver=driver,
        current_location=current["label"],
        pickup_location=pickup["label"],
        dropoff_location=dropoff["label"],
        current_cycle_used_hrs=cycle_used_hrs or 0.0,
        use_sleeper_berth=trip.use_sleeper_berth,
        total_miles=total_miles,
        total_days=len(days),
        total_driving_hrs=total_driving,
        total_on_duty_hrs=total_on_duty,
        final_cycle_used=round(final_cycle, 2),
        recap_approximate=driver is None,
    )

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
        "cycle_used_hrs": cycle_used_hrs or 0.0,
        "recap_approximate": days[0].recap.get("approximate", True) if days else True,
        "driver_id": driver.id if driver else None,
        "warnings": [],
    })


@api_view(["GET"])
def health(request):
    return Response({"ok": True, "service": "spotter-trip-planner"})


@api_view(["GET", "POST"])
def drivers_list(request):
    if request.method == "GET":
        qs = Driver.objects.prefetch_related("day_history").all()
        return Response({"ok": True, "drivers": DriverSerializer(qs, many=True).data})
    s = DriverCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    driver = s.save()
    return Response({"ok": True, "driver": DriverSerializer(driver).data},
                    status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def driver_detail(request, pk):
    try:
        driver = Driver.objects.prefetch_related("day_history").get(pk=pk)
    except Driver.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response({"ok": True, "driver": DriverSerializer(driver).data})
    if request.method == "DELETE":
        driver.delete()
        return Response({"ok": True})
    s = DriverCreateSerializer(driver, data=request.data, partial=True)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    s.save()
    return Response({"ok": True, "driver": DriverSerializer(driver).data})


@api_view(["POST"])
def driver_add_history(request, pk):
    """Add or replace a DayHistory record for a driver.

    Body: {date: YYYY-MM-DD, on_duty_hrs: float, driving_hrs?: float, source?: "manual"|"generated"}
    """
    try:
        driver = Driver.objects.get(pk=pk)
    except Driver.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)
    try:
        d = date.fromisoformat(request.data["date"])
    except (KeyError, ValueError):
        return Response({"ok": False, "error": "date must be YYYY-MM-DD"},
                        status=status.HTTP_400_BAD_REQUEST)
    on_duty = float(request.data.get("on_duty_hrs", 0))
    driving = float(request.data.get("driving_hrs", 0))
    source = request.data.get("source", DayHistory.SOURCE_MANUAL)
    if source not in (DayHistory.SOURCE_MANUAL, DayHistory.SOURCE_GENERATED):
        return Response({"ok": False, "error": "invalid source"},
                        status=status.HTTP_400_BAD_REQUEST)
    rec, _ = DayHistory.objects.update_or_create(
        driver=driver, date=d, source=source,
        defaults={"on_duty_hrs": on_duty, "driving_hrs": driving},
    )
    return Response({"ok": True, "record": DayHistorySerializer(rec).data})
