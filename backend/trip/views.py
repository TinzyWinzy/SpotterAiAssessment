"""API views — trip planning, vehicles, drivers, fuel, status tracking."""
from datetime import datetime

from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

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
from .permissions import (
    get_user_organisation, scope_organisation, belongs_to_organisation,
    validate_status_transition, IsAdmin,
)
import geocoding
import routing
from hos_engine import TripInput, Point as HOSPoint, generate_trip as hos_generate_trip
from trip_engine import Point, compute_stops


BURST_RATE = 20
SUSTAINED_RATE = 60


class TripAnonThrottle(AnonRateThrottle):
    scope = "trip"


class TripUserThrottle(UserRateThrottle):
    scope = "trip"


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


def _serialize_hos_daily_logs(days):
    """Convert HOS DayLog objects to serializable dicts."""
    result = []
    for day in days:
        events = []
        for ev in day.events:
            events.append({
                "start": ev.start.isoformat(),
                "duration_h": ev.duration_h,
                "status": ev.status,
                "location": {
                    "lat": ev.location.lat,
                    "lon": ev.location.lon,
                    "label": ev.location.label,
                },
                "remark": ev.remark,
                "cumulative_miles": ev.cumulative_miles,
                "leg_kind": ev.leg_kind,
            })
        result.append({
            "date": day.date.isoformat(),
            "events": events,
            "total_miles": day.total_miles,
            "deadhead_mi": day.deadhead_mi,
            "loaded_mi": day.loaded_mi,
            "on_duty_today": day.on_duty_today,
            "warnings": day.warnings,
            "recap": day.recap,
            "totals": day.totals,
        })
    return result


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@throttle_classes([TripUserThrottle])
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
    user_org = get_user_organisation(request.user)
    if data.get("vehicle_id"):
        try:
            vehicle = Vehicle.objects.get(pk=data["vehicle_id"])
            if user_org and vehicle.organisation_id != user_org.id and not request.user.is_staff:
                vehicle = None
        except Vehicle.DoesNotExist:
            return Response(
                {"ok": False, "error": f"vehicle_id {data['vehicle_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    if data.get("driver_id"):
        try:
            driver = Driver.objects.get(pk=data["driver_id"])
            if user_org and driver.organisation_id != user_org.id and not request.user.is_staff:
                driver = None
        except Driver.DoesNotExist:
            return Response(
                {"ok": False, "error": f"driver_id {data['driver_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
@permission_classes([IsAuthenticated])
@throttle_classes([TripUserThrottle])
def trip_plan(request):
    """Plan a trip: geocode -> route -> HOS -> cost estimate -> persist."""
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
    waypoints_geocoded = []
    for wp_label in data.get("waypoints", []):
        wp = geocoding.geocode(wp_label)
        if not wp:
            return Response(
                {"ok": False, "error": f"Geocoding failed for waypoint: {wp_label}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        waypoints.append(wp)
        waypoints_geocoded.append(wp)

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
    user_org = get_user_organisation(request.user)
    org = user_org or Organisation.objects.filter(is_deleted=False).first()

    if data.get("driver_id"):
        try:
            driver = Driver.objects.get(pk=data["driver_id"])
            if org and driver.organisation_id != org.id and not request.user.is_staff:
                return Response(
                    {"ok": False, "error": "Driver does not belong to your organisation"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Driver.DoesNotExist:
            return Response(
                {"ok": False, "error": f"driver_id {data['driver_id']} not found"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    if data.get("vehicle_id"):
        try:
            vehicle = Vehicle.objects.get(pk=data["vehicle_id"])
            if org and vehicle.organisation_id != org.id and not request.user.is_staff:
                return Response(
                    {"ok": False, "error": "Vehicle does not belong to your organisation"},
                    status=status.HTTP_403_FORBIDDEN,
                )
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

    # -- HOS engine integration --
    hos_daily_logs = None
    try:
        distance_mi = route_result["distance_mi"]
        cycle_used = data.get("cycle_used_hrs", 0.0)
        use_sleeper = data.get("use_sleeper_berth", True)

        # Build HOS trip input using geocoded points
        # OSRM gives us the full route, but HOS needs origin -> pickup -> dropoff
        # We treat origin as current location, first waypoint (or destination) as pickup
        if waypoints_geocoded:
            pickup_pt = waypoints_geocoded[0]
            # Use last waypoint or destination as dropoff
            if len(waypoints_geocoded) > 1:
                dropoff_pt = waypoints_geocoded[-1]
            else:
                dropoff_pt = destination
        else:
            pickup_pt = destination
            dropoff_pt = destination

        hos_input = TripInput(
            current=HOSPoint(lat=origin["lat"], lon=origin["lon"], label=origin["label"]),
            pickup=HOSPoint(lat=pickup_pt["lat"], lon=pickup_pt["lon"], label=pickup_pt["label"]),
            dropoff=HOSPoint(lat=dropoff_pt["lat"], lon=dropoff_pt["lon"], label=dropoff_pt["label"]),
            cycle_used_hrs=cycle_used,
            avg_speed_mph=route_result["distance_mi"] / max(1, route_result["duration_seconds"] / 3600),
            use_sleeper_berth=use_sleeper,
        )
        hos_days = hos_generate_trip(hos_input)
        hos_daily_logs = _serialize_hos_daily_logs(hos_days)
    except Exception:
        hos_daily_logs = None

    cost_estimate = _build_cost_estimate(distance_km, vehicle, driver)

    trip = Trip.objects.create(
        organisation=org,
        vehicle=vehicle,
        driver=driver,
        commodity=commodity,
        origin=origin["label"],
        destination=destination["label"],
        waypoints=data.get("waypoints", []),
        waypoints_geocoded=waypoints_geocoded,
        distance_km=distance_km,
        route_geometry=route_result.get("geometry"),
        load_weight_tonnes=data.get("load_weight_tonnes"),
        estimated_revenue=data.get("estimated_revenue"),
        estimated_fuel_cost_usd=cost_estimate["fuel_cost_usd"],
        estimated_driver_pay_usd=cost_estimate["driver_pay_usd"],
        estimated_total_cost_usd=cost_estimate["total_cost_usd"],
        cycle_used_hrs=data.get("cycle_used_hrs", 0.0),
        hos_daily_logs=hos_daily_logs,
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
        "hos_daily_logs": hos_daily_logs,
        "driver_id": driver.id if driver else None,
        "vehicle_id": vehicle.id if vehicle else None,
        "trip_id": trip.id,
    })


# ---------------------------------------------------------------------------
# Trip CRUD + status
# ---------------------------------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trips_list(request):
    qs = Trip.objects.select_related("driver", "vehicle").order_by("-created_at")
    qs = scope_organisation(qs, request.user)

    # Pagination
    try:
        page = int(request.GET.get("page", "1"))
        page_size = min(int(request.GET.get("page_size", "20")), 100)
    except ValueError:
        page = 1
        page_size = 20

    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = TripSerializer(qs[start:end], many=True).data

    return Response({
        "ok": True,
        "trips": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def trip_detail(request, pk):
    try:
        trip = Trip.objects.select_related("driver", "vehicle").get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(trip, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    if request.method == "GET":
        return Response({"ok": True, "trip": TripSerializer(trip).data})
    s = TripUpdateSerializer(trip, data=request.data, partial=True)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    s.save()
    return Response({"ok": True, "trip": TripSerializer(trip).data})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def trip_update_status(request, pk):
    """Update trip status with transition validation."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(trip, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

    new_status = request.data.get("status")
    if not new_status:
        return Response({"ok": False, "error": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

    if not validate_status_transition(trip.status, new_status):
        return Response(
            {"ok": False, "error": f"Invalid transition from {trip.status} to {new_status}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    location = request.data.get("location_text", "")
    notes = request.data.get("notes", "")

    old_status = trip.status
    trip.status = new_status
    if new_status == "delivered" and not trip.actual_end:
        trip.actual_end = timezone.now()
    trip.save(update_fields=["status", "actual_end", "updated_at"])

    TripStatusLog.objects.create(
        trip=trip,
        from_status=old_status,
        to_status=new_status,
        location_text=location,
        notes=notes,
        updated_by=request.user if request.user.is_authenticated else None,
    )

    if trip.driver and trip.driver.phone_number:
        sent = send_trip_status_sms(
            driver_phone=trip.driver.phone_number,
            trip_id=trip.id,
            status=new_status,
            origin=trip.origin,
            destination=trip.destination,
        )
        if not sent:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("SMS notification failed for trip #%s to %s", trip.id, trip.driver.phone_number)

    return Response({
        "ok": True,
        "trip": TripSerializer(trip).data,
    })


# ---------------------------------------------------------------------------
# Vehicle CRUD
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def vehicles_list(request):
    if request.method == "GET":
        qs = Vehicle.objects.select_related("organisation").filter(is_deleted=False)
        qs = scope_organisation(qs, request.user)
        return Response({"ok": True, "vehicles": VehicleSerializer(qs, many=True).data})

    org = get_user_organisation(request.user) or Organisation.objects.filter(is_deleted=False).first()
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
@permission_classes([IsAuthenticated])
def vehicle_detail(request, pk):
    try:
        vehicle = Vehicle.objects.select_related("organisation").get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(vehicle, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
@permission_classes([IsAuthenticated])
def fuel_list(request):
    if request.method == "GET":
        qs = FuelRecord.objects.select_related("trip", "vehicle", "recorded_by").order_by("-created_at")
        qs = scope_organisation(qs, request.user, org_field="trip__organisation")
        return Response({"ok": True, "fuel_records": FuelRecordSerializer(qs, many=True).data})
    s = FuelRecordCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)

    # Verify trip belongs to user's org
    trip_id = s.validated_data.get("trip")
    if trip_id and not request.user.is_staff:
        try:
            trip = Trip.objects.get(pk=trip_id.pk if hasattr(trip_id, 'pk') else trip_id)
            if not belongs_to_organisation(trip, request.user):
                return Response(
                    {"ok": False, "error": "Trip does not belong to your organisation"},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except Trip.DoesNotExist:
            pass

    record = s.save(recorded_by=request.user if request.user.is_authenticated else None)
    return Response({"ok": True, "fuel_record": FuelRecordSerializer(record).data},
                    status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Driver CRUD
# ---------------------------------------------------------------------------

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def drivers_list(request):
    if request.method == "GET":
        qs = Driver.objects.select_related("organisation").filter(is_deleted=False)
        qs = scope_organisation(qs, request.user)
        return Response({"ok": True, "drivers": DriverSerializer(qs, many=True).data})
    org = get_user_organisation(request.user) or Organisation.objects.filter(is_deleted=False).first()
    if not org:
        return Response({"ok": False, "error": "No organisation found"}, status=status.HTTP_400_BAD_REQUEST)
    s = DriverCreateSerializer(data=request.data)
    if not s.is_valid():
        return Response({"ok": False, "errors": s.errors}, status=status.HTTP_400_BAD_REQUEST)
    driver = s.save(organisation=org)
    return Response({"ok": True, "driver": DriverSerializer(driver).data},
                    status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def driver_detail(request, pk):
    try:
        driver = Driver.objects.select_related("organisation").get(pk=pk)
    except Driver.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(driver, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
@permission_classes([IsAuthenticated])
def trip_positions(request, pk):
    """Get position history or report a new position for a trip."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(trip, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
@permission_classes([IsAuthenticated])
def trip_sos(request, pk):
    """Trigger an SOS alert for a trip."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(trip, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
@permission_classes([IsAuthenticated])
def trip_sos_acknowledge(request, pk):
    """Acknowledge an SOS alert (dispatcher action)."""
    try:
        trip = Trip.objects.get(pk=pk)
    except Trip.DoesNotExist:
        return Response({"ok": False, "error": "not found"}, status=status.HTTP_404_NOT_FOUND)

    if not belongs_to_organisation(trip, request.user) and not request.user.is_staff:
        return Response({"ok": False, "error": "forbidden"}, status=status.HTTP_403_FORBIDDEN)

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
@permission_classes([IsAuthenticated])
def commodity_list(request):
    qs = Commodity.objects.select_related("category").filter(is_active=True)
    return Response({
        "ok": True,
        "commodities": CommoditySerializer(qs, many=True).data,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def commodity_categories(request):
    qs = CommodityCategory.objects.all()
    return Response({
        "ok": True,
        "categories": CommodityCategorySerializer(qs, many=True).data,
    })
