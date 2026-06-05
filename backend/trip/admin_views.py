"""Admin dashboard endpoints — staff-only.

Returns aggregate metrics over all persisted Trip + Driver records.
Computes everything in-process from the database; no extra pipeline.
"""
from collections import Counter
from datetime import timedelta

from django.db.models import Count, F, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import Driver, Trip
from .permissions import IsAdmin
from .serializers import TripSerializer


@api_view(["GET"])
@permission_classes([IsAdmin])
def metrics(request):
    """Top-level KPIs for the admin dashboard."""
    trips = Trip.objects.all()
    drivers = Driver.objects.all()
    now = timezone.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    totals = trips.aggregate(
        total=Count("id"),
        total_miles=Sum("total_miles"),
        total_driving=Sum("total_driving_hrs"),
        total_on_duty=Sum("total_on_duty_hrs"),
    )

    trips_7d = trips.filter(created_at__gte=seven_days_ago).count()
    trips_30d = trips.filter(created_at__gte=thirty_days_ago).count()

    # Per-day trip count for the last 30 days, zero-filled for missing days.
    per_day = (
        trips.filter(created_at__gte=thirty_days_ago)
        .extra(select={"day": "date(created_at)"})
        .values("day")
        .annotate(count=Count("id"))
    )
    counts_by_day = {row["day"]: row["count"] for row in per_day}
    sparkline = []
    for offset in range(29, -1, -1):
        day = (now - timedelta(days=offset)).date()
        sparkline.append({"date": day.isoformat(), "count": counts_by_day.get(day, 0)})

    # Top origin → destination routes.
    top_routes_qs = (
        trips.values("current_location", "pickup_location", "dropoff_location")
        .annotate(count=Count("id"), miles=Sum("total_miles"))
        .order_by("-count")[:5]
    )
    top_routes = [
        {
            "origin": r["current_location"],
            "pickup": r["pickup_location"],
            "destination": r["dropoff_location"],
            "count": r["count"],
            "miles": round(r["miles"] or 0, 1),
        }
        for r in top_routes_qs
    ]

    # Cycle-usage histogram (final_cycle_used bucket).
    buckets = [(0, 10), (10, 30), (30, 50), (50, 60), (60, 70), (70, 100)]
    histogram = []
    for lo, hi in buckets:
        n = trips.filter(final_cycle_used__gte=lo, final_cycle_used__lt=hi).count()
        histogram.append({"label": f"{lo}-{hi}h", "count": n})
    over_70 = trips.filter(final_cycle_used__gte=70).count()
    if over_70:
        histogram.append({"label": "70h+", "count": over_70})

    # Drivers with history (i.e. realistic recap), and total generated vs manual days.
    drivers_with_history = drivers.annotate(h=Count("day_history")).filter(h__gt=0).count()
    drivers_with_trips = drivers.annotate(t=Count("trips")).filter(t__gt=0).count()

    # Per-driver cumulative miles, top 5.
    per_driver = (
        drivers.annotate(trips_count=Count("trips"), miles_sum=Sum("trips__total_miles"))
        .order_by(F("miles_sum").desc(nulls_last=True))[:5]
    )
    top_drivers = [
        {
            "id": d.id,
            "name": d.name,
            "trips": d.trips_count,
            "miles": round(d.miles_sum or 0, 1),
        }
        for d in per_driver
    ]

    return Response({
        "ok": True,
        "generated_at": now.isoformat(),
        "totals": {
            "trips": totals["total"] or 0,
            "drivers": drivers.count(),
            "drivers_with_trips": drivers_with_trips,
            "drivers_with_history": drivers_with_history,
            "miles": round(totals["total_miles"] or 0, 1),
            "driving_hrs": round(totals["total_driving"] or 0, 1),
            "on_duty_hrs": round(totals["total_on_duty"] or 0, 1),
            "avg_miles_per_trip": round(
                (totals["total_miles"] or 0) / max(1, totals["total"] or 1), 1
            ),
        },
        "window": {
            "trips_7d": trips_7d,
            "trips_30d": trips_30d,
            "sparkline_30d": sparkline,
        },
        "top_routes": top_routes,
        "cycle_histogram": histogram,
        "top_drivers": top_drivers,
    })


@api_view(["GET"])
@permission_classes([IsAdmin])
def trips_list(request):
    """Paginated list of recent trips, newest first."""
    try:
        page = int(request.GET.get("page", "1"))
        page_size = min(int(request.GET.get("page_size", "20")), 100)
    except ValueError:
        return Response(
            {"ok": False, "error": "page and page_size must be integers"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    qs = Trip.objects.select_related("driver").order_by("-created_at")
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
