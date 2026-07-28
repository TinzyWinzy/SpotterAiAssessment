"""Admin dashboard endpoints — fleet KPIs, P&L, trends."""
from datetime import datetime, timedelta
from collections import defaultdict

from django.db.models import Count, F, Sum, Q, Avg
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Organisation, Vehicle, Driver, Trip, FuelRecord, TripPosition
from .permissions import IsAdmin
from .serializers import TripSerializer, TripPositionSerializer


def _parse_date(param, default):
    if not param:
        return default
    try:
        return datetime.strptime(param, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default


def _date_filter(qs, from_date, to_date, field="created_at"):
    if from_date:
        qs = qs.filter(**{f"{field}__date__gte": from_date})
    if to_date:
        qs = qs.filter(**{f"{field}__date__lte": to_date})
    return qs


@api_view(["GET"])
@permission_classes([IsAdmin])
def metrics(request):
    """Fleet KPIs with optional date-range filtering.

    Query params: from_date=YYYY-MM-DD, to_date=YYYY-MM-DD
    """
    now = timezone.now()
    from_date = _parse_date(request.GET.get("from_date"), None)
    to_date = _parse_date(request.GET.get("to_date"), None)

    trips = Trip.objects.all()
    drivers = Driver.objects.all()
    vehicles = Vehicle.objects.all()
    fuel_records = FuelRecord.objects.all()

    trips_filtered = _date_filter(trips, from_date, to_date, "created_at")
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    this_month = now.replace(day=1)
    last_month = (this_month - timedelta(days=1)).replace(day=1)

    totals = trips_filtered.aggregate(
        total=Count("id"),
        total_km=Sum("distance_km"),
        total_revenue=Sum("revenue_usd"),
        total_est_cost=Sum("estimated_total_cost_usd"),
        total_fuel_est=Sum("estimated_fuel_cost_usd"),
        total_actual_fuel=Sum("actual_fuel_cost_usd"),
        total_actual_cost=Sum("actual_total_cost_usd"),
    )

    fuel_totals = fuel_records.aggregate(
        total_litres=Sum("litres"),
        total_cost=Sum("total_cost_usd"),
        records=Count("id"),
    )

    trips_7d = trips.filter(created_at__gte=seven_days_ago).count()
    trips_30d = trips.filter(created_at__gte=thirty_days_ago).count()

    # This month vs last month comparison
    trips_this_month = trips.filter(created_at__gte=this_month).count()
    trips_last_month = trips.filter(
        created_at__gte=last_month, created_at__lt=this_month,
    ).count()

    revenue_this_month = trips.filter(created_at__gte=this_month).aggregate(
        r=Sum("revenue_usd"),
    )["r"] or 0
    revenue_last_month = trips.filter(
        created_at__gte=last_month, created_at__lt=this_month,
    ).aggregate(r=Sum("revenue_usd"))["r"] or 0

    # Fleet utilization
    active_vehicles = vehicles.filter(status="active").count()
    total_vehicles = vehicles.count()
    vehicles_with_trips = vehicles.annotate(tc=Count("trips")).filter(tc__gt=0).count()

    # Status distribution
    status_counts = (
        trips_filtered.values("status")
        .annotate(count=Count("id"))
        .order_by("status")
    )
    status_distribution = {
        s["status"]: s["count"]
        for s in status_counts
    }

    # Fuel efficiency across fleet
    fuel_efficiency = 0.0
    if fuel_totals["total_litres"] and totals["total_km"]:
        fuel_efficiency = round(
            (fuel_totals["total_litres"] / totals["total_km"]) * 100, 1,
        )

    # Monthly sparkline
    per_day = (
        trips_filtered.filter(created_at__gte=thirty_days_ago)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
    )
    counts_by_day = {row["day"]: row["count"] for row in per_day}
    sparkline = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date()
        sparkline.append({"date": day.isoformat(), "count": counts_by_day.get(day, 0)})

    # Top routes
    top_routes_qs = (
        trips_filtered.values("origin", "destination")
        .annotate(count=Count("id"), km=Sum("distance_km"))
        .order_by("-count")[:5]
    )
    top_routes = [
        {"origin": r["origin"], "destination": r["destination"],
         "count": r["count"], "km": round(r["km"] or 0, 1)}
        for r in top_routes_qs
    ]

    # Top drivers
    per_driver = (
        drivers.annotate(
            trips_count=Count("trips", filter=(
                Q(trips__created_at__gte=from_date) if from_date else Q()
            ) & (
                Q(trips__created_at__lte=to_date) if to_date else Q()
            ) if (from_date or to_date) else Q(),
        ),
            km_sum=Sum("trips__distance_km"),
        )
        .order_by(F("km_sum").desc(nulls_last=True))[:5]
    )
    top_drivers = [
        {"id": d.id, "name": d.name, "trips": d.trips_count,
         "km": round(d.km_sum or 0, 1)}
        for d in per_driver
    ]

    # Top vehicles
    per_vehicle = (
        vehicles.annotate(trips_count=Count("trips"), km_sum=Sum("trips__distance_km"))
        .order_by(F("km_sum").desc(nulls_last=True))[:5]
    )
    top_vehicles = [
        {"id": v.id, "plate": v.plate, "trips": v.trips_count,
         "km": round(v.km_sum or 0, 1)}
        for v in per_vehicle
    ]

    revenue = round(totals["total_revenue"] or 0, 2)
    est_cost = round(totals["total_est_cost"] or 0, 2)
    actual_cost = round(totals["total_actual_cost"] or 0, 2)

    return Response({
        "ok": True,
        "generated_at": now.isoformat(),
        "date_range": {
            "from": from_date.isoformat() if from_date else None,
            "to": to_date.isoformat() if to_date else None,
        },
        "totals": {
            "trips": totals["total"] or 0,
            "drivers": drivers.count(),
            "vehicles": total_vehicles,
            "active_vehicles": active_vehicles,
            "vehicles_with_trips": vehicles_with_trips,
            "km": round(totals["total_km"] or 0, 1),
            "avg_km_per_trip": round(
                (totals["total_km"] or 0) / max(1, totals["total"] or 1), 1
            ),
            "revenue_usd": revenue,
            "estimated_cost_usd": est_cost,
            "actual_cost_usd": actual_cost,
            "estimated_profit_usd": round(revenue - est_cost, 2),
            "actual_profit_usd": round(revenue - actual_cost, 2) if actual_cost else None,
        },
        "fuel": {
            "total_litres": round(fuel_totals["total_litres"] or 0, 1),
            "total_cost_usd": round(fuel_totals["total_cost"] or 0, 2),
            "fleet_efficiency_l_100km": fuel_efficiency,
            "records": fuel_totals["records"] or 0,
        },
        "status_distribution": status_distribution,
        "window": {
            "trips_7d": trips_7d,
            "trips_30d": trips_30d,
            "sparkline_30d": sparkline,
        },
        "comparison": {
            "trips_this_month": trips_this_month,
            "trips_last_month": trips_last_month,
            "revenue_this_month_usd": round(revenue_this_month, 2),
            "revenue_last_month_usd": round(revenue_last_month, 2),
        },
        "top_routes": top_routes,
        "top_drivers": top_drivers,
        "top_vehicles": top_vehicles,
    })


@api_view(["GET"])
@permission_classes([IsAdmin])
def trips_list(request):
    """Paginated list of recent trips, newest first.

    Query params: page, page_size, status (filter), from_date, to_date
    """
    try:
        page = int(request.GET.get("page", "1"))
        page_size = min(int(request.GET.get("page_size", "20")), 100)
    except ValueError:
        return Response(
            {"ok": False, "error": "page and page_size must be integers"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = Trip.objects.select_related("driver", "vehicle").order_by("-created_at")

    status_filter = request.GET.get("status")
    if status_filter:
        qs = qs.filter(status=status_filter)

    from_date = _parse_date(request.GET.get("from_date"), None)
    to_date = _parse_date(request.GET.get("to_date"), None)
    qs = _date_filter(qs, from_date, to_date)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = TripSerializer(qs[start:end], many=True).data

    return Response({
        "ok": True,
        "page": page,
        "page_size": page_size,
        "total": total,
        "trips": items,
    })


@api_view(["GET"])
@permission_classes([IsAdmin])
def active_trips(request):
    """Return all active trips with their latest position."""
    active_statuses = ["dispatched", "at_border", "in_transit"]
    qs = Trip.objects.filter(
        status__in=active_statuses,
    ).select_related("driver", "vehicle").order_by("-updated_at")

    result = []
    for trip in qs:
        last_pos = TripPosition.objects.filter(trip=trip).order_by("-timestamp").first()
        trip_data = TripSerializer(trip).data
        trip_data["last_position"] = TripPositionSerializer(last_pos).data if last_pos else None
        result.append(trip_data)

    return Response({
        "ok": True,
        "active_trips": result,
        "count": len(result),
    })


@api_view(["GET"])
@permission_classes([IsAdmin])
def fleet_summary_text(request):
    """WhatsApp-friendly fleet summary as plain text."""
    now = timezone.now()
    trips = Trip.objects.all()
    vehicles = Vehicle.objects.all()
    drivers = Driver.objects.all()

    this_month = now.replace(day=1)
    trips_this_month = trips.filter(created_at__gte=this_month).count()

    totals = trips.aggregate(
        total_km=Sum("distance_km"),
        revenue=Sum("revenue_usd"),
        est_cost=Sum("estimated_total_cost_usd"),
    )

    revenue = round(totals["revenue"] or 0, 2)
    cost = round(totals["est_cost"] or 0, 2)
    profit = round(revenue - cost, 2)
    km = round(totals["total_km"] or 0, 1)

    active_statuses = ["dispatched", "at_border", "in_transit"]
    active_trips = trips.filter(status__in=active_statuses).count()

    delivered_pending = trips.filter(status="delivered").count()

    lines = [
        "*TruckLedger Fleet Summary*",
        "",
        f"Trips this month: {trips_this_month}",
        f"Active trips: {active_trips}",
        f"Delivered (unpaid): {delivered_pending}",
        f"Total distance: {km:,.0f} km",
        "",
        f"Revenue: ${revenue:,.2f}",
        f"Est. cost: ${cost:,.2f}",
        f"Est. profit: ${profit:,.2f}",
        "",
        f"Vehicles: {vehicles.count()} ({vehicles.filter(status='active').count()} active)",
        f"Drivers: {drivers.count()} ({drivers.filter(status='active').count()} active)",
        "",
        f"Generated: {now.strftime('%Y-%m-%d %H:%M')}",
    ]

    return Response({"ok": True, "text": "\n".join(lines)})
