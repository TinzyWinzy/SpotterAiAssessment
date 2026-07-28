"""API views — trip planning, vehicles, drivers, fuel, status tracking."""
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .serializers import (
    TripRequestSerializer, TripSerializer, TripUpdateSerializer,
    TripEstimateSerializer,
    DriverSerializer, DriverCreateSerializer,
    VehicleSerializer, VehicleCreateSerializer,
    FuelRecordSerializer, FuelRecordCreateSerializer,
    TripStatusLogSerializer, TripPositionSerializer, TripPositionCreateSerializer,
    CommoditySerializer, CommodityCategorySerializer,
)
from .models import (
    Organisation, Vehicle, Driver, Trip, FuelRecord,
    TripStatusLog, TripPosition, Commodity, CommodityCategory,
)
from .cost_calculator import (
    estimate_trip_cost, CostBreakdown, VehicleSpec, DriverSpec,
    DEFAULT_FUEL_PRICE_USD_PER_L, DEFAULT_BORDER_FEE_USD,
)
from .notifications import send_trip_status_sms
import geocoding
import routing
from trip_engine import Point, compute_stops


# ---------------------------------------------------------------------------
# Trip planning
# ---------------------------------------------------------------------------

def _build_cost_estimate(distance_km, vehicle, driver, border_crossings=0, tolls_usd=0.0):
    """Build a cost estimate dict from a vehicle and driver."""
    vspec = None
    dspec = None
    if vehicle:
        vspec = VehicleSpec(
            fuel_consumption_l_100km=vehicle.fuel_consumption_rate_l_100km,
            fuel_type=vehicle.fuel_type,
        )
    if driver:
        dspec = DriverSpec(
            rate_per_day_usd=driver.rate_per_day_usd,
            rate_per_km_usd=driver.rate_per_km_usd,
        )
    cb = estimate_trip_cost(
        route_distance_km=distance_km,
        vehicle=vspec,
        driver=dspec,
        border_crossings=border_crossings,
        tolls_usd=tolls_usd,
    )
    return {
        "route_distance_km": cb.route_distance_km,
        "estimated_days": cb.estimated_days,
        "fuel_cost_usd": cb.fuel_cost_usd,
        "driver_pay_usd": cb.driver_pay_usd,
        "border_fees_usd": cb.border_fees_usd,
        "tolls_usd": cb.tolls_usd,
        "maintenance_provision_usd": cb.maintenance_provision_usd,
        "total_cost_usd": cb.total_cost_usd,
        "break_even_revenue_usd": cb.break_even_revenue_usd,
        "recommended_revenue_usd": cb.recommended_revenue_usd,
        "profit_margin_pct": cb.profit_margin_pct,
    }


@api_view(["POST"])
def trip_estimate(request):
    """Estimate trip cost without persisting a trip."""
    serializer = TripEstimateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    data = serializer.validated_data

    origin = geocoding.geocode(data["origin"])
    destination = geocoding.geocode(data["destination"])

    if not (origin and destination):
        missing = []
        if not origin:
            missing.append("origin")
        if not destination:
            missing.append("destination")
        return Response(
            {"ok": False, "error": f"Geocoding failed for: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    coords = [(origin["lon"], origin["lat"]), (destination["lon"], destination["lat"])]
    for wp_label in data.get("waypoints", []):
        wp = geocoding.geocode(wp_label)
        if not wp:
            return Response(
                {"ok": False, "error": f"Geocoding failed for waypoint: {wp_label}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        coords.append((wp["lon"], wp["lat"]))

    route_result = routing.route(coords)
    if not route_result:
        return Response(
            {"ok": False, "error": "Routing failed (OSRM unreachable)"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    distance_km = round(route_result["distance_mi"] * 1.60934, 1)

    vehicle = None
    driver = None
    if data.get("vehicle_id"):
        try:
            vehicle = Vehicle.objects.get(pk=data["vehicle_id"])
        except Vehicle.DoesNotExist:
            return Response(
                {"ok": False, "error": f"vehicle_id {data['vehicle_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    if data.get("driver_id"):
        try:
            driver = Driver.objects.get(pk=data["driver_id"])
        except Driver.DoesNotExist:
            pass

    cost_estimate = _build_cost_estimate(
        distance_km, vehicle, driver,
        border_crossings=data.get("border_crossings", 0),
        tolls_usd=data.get("tolls_usd", 0.0),
    )

    return Response({
        "ok": True,
        "route": {
            "distance_km": distance_km,
            "duration_h": round(route_result["duration_seconds"] / 3600, 2),
            "geometry": route_result["geometry"],
        },
        "cost_estimate": cost_estimate,
    })

@api_view(["POST"])
def trip_plan(request):
    """Plan a trip: geocode -> route -> return distance + geometry + cost estimate."""
    serializer = TripRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"ok": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    data = serializer.validated_data

    origin = geocoding.geocode(data["origin"])
    destination = geocoding.geocode(data["destination"])
    waypoints = []
    for wp_label in data.get("waypoints", []):
        wp = geocoding.geocode(wp_label)
        if not wp:
            return Response(
                {"ok": False, "error": f"Geocoding failed for waypoint: {wp_label}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        waypoints.append(wp)

    if not (origin and destination):
        missing = []
        if not origin:
            missing.append("origin")
        if not destination:
            missing.append("destination")
        return Response(
            {"ok": False, "error": f"Geocoding failed for: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    coords = [(origin["lon"], origin["lat"])]
    for wp in waypoints:
        coords.append((wp["lon"], wp["lat"]))
    coords.append((destination["lon"], destination["lat"]))

    route_result = routing.route(coords)
    if not route_result:
        return Response(
            {"ok": False, "error": "Routing failed (OSRM unreachable)"},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    driver = None
    vehicle = None
    commodity = None
    org = Organisation.objects.first()

    if data.get("driver_id"):
        try:
            driver = Driver.objects.get(pk=data["driver_id"])
        except Driver.DoesNotExist:
            return Response(
                {"ok": False, "error": f"driver_id {data['driver_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if data.get("vehicle_id"):
        try:
            vehicle = Vehicle.objects.get(pk=data["vehicle_id"])
        except Vehicle.DoesNotExist:
            return Response(
                {"ok": False, "error": f"vehicle_id {data['vehicle_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if data.get("commodity_id"):
        try:
            commodity = Commodity.objects.get(pk=data["commodity_id"])
        except Commodity.DoesNotExist:
            return Response(
                {"ok": False, "error": f"commodity_id {data['commodity_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    origin_pt = Point(lat=origin["lat"], lon=origin["lon"], label=origin["label"])
    dest_pt = Point(lat=destination["lat"], lon=destination["lon"], label=destination["label"])
    waypoint_pts = [
        Point(lat=w["lat"], lon=w["lon"], label=w["label"]) for w in waypoints
    ]

    stops = compute_stops(origin_pt, dest_pt, waypoint_pts if waypoint_pts else None)
    distance_km = round(route_result["distance_mi"] * 1.60934, 1)

    cost_estimate = _build_cost_estimate(distance_km, vehicle, driver)

    trip = Trip.objects.create(
        organisation=org,
        vehicle=vehicle,
        driver=driver,
        commodity=commodity,
        origin=origin["label"],
        destination=destination["label"],
        waypoints=data.get("waypoints", []),
        distance_km=distance_km,
        route_geometry=route_result.get("geometry"),
        load_weight_tonnes=data.get("load_weight_tonnes"),
        estimated_revenue=data.get("estimated_revenue"),
        estimated_fuel_cost_usd=cost_estimate["fuel_cost_usd"],
        estimated_driver_pay_usd=cost_estimate["driver_pay_usd"],
        estimated_total_cost_usd=cost_estimate["total_cost_usd"],
    )

    return Response({
        "ok": True,
        "stops": stops,
        "route": {
            "distance_km": distance_km,
            "duration_h": round(route_result["duration_seconds"] / 3600, 2),
            "geometry": route_result["geometry"],
        },
        "cost_estimate": cost_estimate,
        "driver_id": driver.id if driver else None,
        "vehicle_id": vehicle.id if vehicle else None,
        "trip_id": trip.id,
    })


# ---------------------------------------------------------------------------
# Trip CRUD + status
# ---------------------------------------------------------------------------

@api_view(["GET"])
def trips_list(request):
    qs = Trip.objects.select_related("driver", "vehicle").order_by("-created_at")
    return Response({
        "ok": True,
        "trips": TripSerializer(qs, many=True).data,
    })


@api_view(["GET", "PATCH"])
def trip_detail(request, pk):
    try:
        trip = Trip.objects.select_related("driver", "vehicle").get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response({"ok": True, "trip": TripSerializer(trip).data})
    s = TripUpdateSerializer(trip, data=request.data, partial=True)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    s.save()
    return Response({"ok": True, "trip": TripSerializer(trip).data})


@api_view(["POST"])
def trip_update_status(request, pk):
    """Update trip status and create a status log entry."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    new_status = request.data.get("status")
    if not new_status:
        return Response({"ok": False, "error": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

    location = request.data.get("location_text", "")
    notes = request.data.get("notes", "")

    old_status = trip.status
    trip.status = new_status
    trip.save(update_fields=["status", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=old_status,
        to_status=new_status,
        location_text=location,
        notes=notes,
        updated_by=request.user if request.user.is_authenticated else None,
    )

    if trip.driver and trip.driver.phone_number:
        send_trip_status_sms(
            driver_phone=trip.driver.phone_number,
            trip_id=trip.id,
            status=new_status,
            origin=trip.origin,
            destination=trip.destination,
        )

    return Response({
        "ok": True,
        "trip": TripSerializer(trip).data,
    })


# ---------------------------------------------------------------------------
# Vehicle CRUD
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
def vehicles_list(request):
    if request.method == "GET":
        qs = Vehicle.objects.select_related("organisation").all()
        return Response({"ok": True, "vehicles": VehicleSerializer(qs, many=True).data})
    org = Organisation.objects.first()
    if not org:
        return Response({"ok": False, "error": "No organisation found"}, status=status.HTTP_400_BAD_REQUEST)
    s = VehicleCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    try:
        vehicle = s.save(organisation=org)
    except Exception:
        return Response(
            {"ok": False, "error": "A vehicle with this plate already exists in the organisation"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response({"ok": True, "vehicle": VehicleSerializer(vehicle).data},
                    status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def vehicle_detail(request, pk):
    try:
        vehicle = Vehicle.objects.select_related("organisation").get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)
    if request.method == "GET":
        return Response({"ok": True, "vehicle": VehicleSerializer(vehicle).data})
    if request.method == "DELETE":
        vehicle.delete()
        return Response({"ok": True})
    s = VehicleCreateSerializer(vehicle, data=request.data, partial=True)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    s.save()
    return Response({"ok": True, "vehicle": VehicleSerializer(vehicle).data})


# ---------------------------------------------------------------------------
# Fuel records
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
def fuel_list(request):
    if request.method == "GET":
        qs = FuelRecord.objects.select_related("trip", "vehicle", "recorded_by").order_by("-created_at")
        return Response({"ok": True, "fuel_records": FuelRecordSerializer(qs, many=True).data})
    s = FuelRecordCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    record = s.save(recorded_by=request.user if request.user.is_authenticated else None)
    return Response({"ok": True, "fuel_record": FuelRecordSerializer(record).data},
                    status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Driver CRUD
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
def drivers_list(request):
    if request.method == "GET":
        qs = Driver.objects.select_related("organisation").all()
        return Response({"ok": True, "drivers": DriverSerializer(qs, many=True).data})
    org = Organisation.objects.first()
    if not org:
        return Response({"ok": False, "error": "No organisation found"}, status=status.HTTP_400_BAD_REQUEST)
    s = DriverCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    driver = s.save(organisation=org)
    return Response({"ok": True, "driver": DriverSerializer(driver).data},
                    status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
def driver_detail(request, pk):
    try:
        driver = Driver.objects.select_related("organisation").get(pk=pk)
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


# ---------------------------------------------------------------------------
# Position tracking
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
def trip_positions(request, pk):
    """Get position history or report a new position for a trip."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        qs = trip.positions.order_by("-timestamp")[:50]
        return Response({
            "ok": True,
            "positions": TripPositionSerializer(qs, many=True).data,
        })

    s = TripPositionCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)

    pos = TripPosition.objects.create(
        trip=trip,
        lat=s.validated_data["lat"],
        lon=s.validated_data["lon"],
        accuracy=s.validated_data.get("accuracy"),
        source=s.validated_data.get("source", "manual"),
        remark=s.validated_data.get("remark", ""),
        reported_by=request.user if request.user.is_authenticated else None,
    )
    return Response({
        "ok": True,
        "position": TripPositionSerializer(pos).data,
    }, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# SOS
# ---------------------------------------------------------------------------

@api_view(["POST"])
def trip_sos(request, pk):
    """Trigger an SOS alert for a trip."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    trip.sos_triggered_at = timezone.now()
    trip.sos_message = request.data.get("message", "")
    trip.save(update_fields=["sos_triggered_at", "sos_message", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=trip.status,
        to_status=trip.status,
        location_text=request.data.get("lat") and request.data.get("lon")
            and f"{request.data['lat']},{request.data['lon']}" or "",
        notes=f"SOS triggered: {trip.sos_message}" if trip.sos_message else "SOS triggered",
        updated_by=request.user if request.user.is_authenticated else None,
    )

    return Response({"ok": True})


@api_view(["POST"])
def trip_sos_acknowledge(request, pk):
    """Acknowledge an SOS alert (dispatcher action)."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    from django.utils import timezone
    trip.sos_acknowledged_at = timezone.now()
    trip.save(update_fields=["sos_acknowledged_at", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=trip.status,
        to_status=trip.status,
        notes="SOS acknowledged by dispatcher",
        updated_by=request.user if request.user.is_authenticated else None,
    )

    return Response({"ok": True})


@api_view(["GET"])
def health(request):
    return Response({"ok": True, "service": "truckledger"})


# ---------------------------------------------------------------------------
# Commodities
# ---------------------------------------------------------------------------

@api_view(["GET"])
def commodity_list(request):
    qs = Commodity.objects.select_related("category").filter(is_active=True)
    return Response({
        "ok": True,
        "commodities": CommoditySerializer(qs, many=True).data,
    })


@api_view(["GET"])
def commodity_categories(request):
    qs = CommodityCategory.objects.all()
    return Response({
        "ok": True,
        "categories": CommodityCategorySerializer(qs, many=True).data,
    })
