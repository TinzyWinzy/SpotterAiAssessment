"""
Trip cost calculator — pure functions for estimating trip profitability.

All calculations in USD. No external dependencies beyond math.
Supports service-aware pricing for customer-facing quotes.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


DEFAULT_FUEL_PRICE_USD_PER_L = 1.60
DEFAULT_BORDER_FEE_USD = 50.0
DEFAULT_MAINTENANCE_USD_PER_KM = 0.05
DEFAULT_AVG_SPEED_KPH = 60.0
DEFAULT_DRIVING_HOURS_PER_DAY = 8.0
DEFAULT_PROFIT_MARGIN = 0.20
KM_PER_DAY = DEFAULT_AVG_SPEED_KPH * DEFAULT_DRIVING_HOURS_PER_DAY  # 480


@dataclass
class VehicleSpec:
    fuel_consumption_l_100km: float = 0.0
    fuel_type: str = "diesel"


@dataclass
class DriverSpec:
    rate_per_day_usd: float = 0.0
    rate_per_km_usd: float = 0.0


@dataclass
class CostBreakdown:
    route_distance_km: float
    estimated_days: float
    fuel_cost_usd: float
    driver_pay_usd: float
    border_fees_usd: float
    tolls_usd: float
    maintenance_provision_usd: float
    total_cost_usd: float
    break_even_revenue_usd: float
    recommended_revenue_usd: float
    profit_margin_pct: float


@dataclass
class BookingCostBreakdown:
    """Customer-facing quote breakdown with service-specific line items."""
    route_distance_km: float
    base_fee_usd: float
    distance_fee_usd: float
    loading_fee_usd: float
    packing_fee_usd: float
    fragile_surcharge_usd: float
    floor_fee_usd: float
    fuel_surcharge_usd: float
    total_estimated_usd: float
    truck_recommendation: Optional[str] = None


def estimate_days(
    route_distance_km: float,
    border_crossings: int = 0,
    km_per_day: float = KM_PER_DAY,
) -> float:
    """Estimate trip duration in days. Adds 0.5 day per border crossing."""
    driving_days = route_distance_km / km_per_day if km_per_day > 0 else 0
    border_days = border_crossings * 0.5
    return round(max(1.0, driving_days + border_days), 1)


def calculate_fuel_cost(
    distance_km: float,
    consumption_l_100km: float,
    price_per_litre_usd: float,
) -> float:
    """Fuel cost = (distance / 100) * consumption_rate * fuel_price."""
    if consumption_l_100km <= 0 or distance_km <= 0:
        return 0.0
    litres = (distance_km / 100.0) * consumption_l_100km
    return round(litres * price_per_litre_usd, 2)


def calculate_driver_pay(
    distance_km: float,
    days: float,
    driver: Optional[DriverSpec] = None,
) -> float:
    """Driver pay = (days * daily_rate) + (km * per_km_rate)."""
    if driver is None:
        return 0.0
    day_pay = days * driver.rate_per_day_usd
    km_pay = distance_km * driver.rate_per_km_usd
    return round(day_pay + km_pay, 2)


def calculate_border_fees(
    border_crossings: int,
    fee_per_crossing_usd: float = DEFAULT_BORDER_FEE_USD,
) -> float:
    return round(border_crossings * fee_per_crossing_usd, 2)


def calculate_maintenance_provision(
    distance_km: float,
    rate_per_km_usd: float = DEFAULT_MAINTENANCE_USD_PER_KM,
) -> float:
    return round(distance_km * rate_per_km_usd, 2)


def estimate_trip_cost(
    route_distance_km: float,
    vehicle: Optional[VehicleSpec] = None,
    driver: Optional[DriverSpec] = None,
    fuel_price_per_litre_usd: float = DEFAULT_FUEL_PRICE_USD_PER_L,
    border_crossings: int = 0,
    border_fee_per_crossing_usd: float = DEFAULT_BORDER_FEE_USD,
    tolls_usd: float = 0.0,
    maintenance_rate_usd_per_km: float = DEFAULT_MAINTENANCE_USD_PER_KM,
    profit_margin: float = DEFAULT_PROFIT_MARGIN,
) -> CostBreakdown:
    """Calculate the complete trip cost breakdown.

    Returns a CostBreakdown with all cost components and revenue targets.
    """
    days = estimate_days(route_distance_km, border_crossings)

    fuel_cost = 0.0
    if vehicle and vehicle.fuel_consumption_l_100km > 0:
        fuel_cost = calculate_fuel_cost(
            route_distance_km,
            vehicle.fuel_consumption_l_100km,
            fuel_price_per_litre_usd,
        )

    driver_pay = 0.0
    if driver:
        driver_pay = calculate_driver_pay(route_distance_km, days, driver)

    border_fees = calculate_border_fees(border_crossings, border_fee_per_crossing_usd)
    maintenance = calculate_maintenance_provision(route_distance_km, maintenance_rate_usd_per_km)

    total_cost = round(fuel_cost + driver_pay + border_fees + tolls_usd + maintenance, 2)
    recommended = round(total_cost * (1.0 + profit_margin), 2)

    return CostBreakdown(
        route_distance_km=route_distance_km,
        estimated_days=days,
        fuel_cost_usd=fuel_cost,
        driver_pay_usd=driver_pay,
        border_fees_usd=border_fees,
        tolls_usd=tolls_usd,
        maintenance_provision_usd=maintenance,
        total_cost_usd=total_cost,
        break_even_revenue_usd=total_cost,
        recommended_revenue_usd=recommended,
        profit_margin_pct=profit_margin * 100,
    )


def calculate_booking_estimate(
    distance_km: float,
    service_type: str = "custom",
    cargo_items: Optional[list[dict]] = None,
    has_fragile: bool = False,
    needs_packing: bool = False,
    needs_labour: bool = False,
    floor_count: int = 0,
) -> BookingCostBreakdown:
    """Calculate a customer-facing booking estimate with service-specific pricing."""
    from .services import get_service
    svc = get_service(service_type)

    base_fee = svc.base_fee_usd if svc else 30.0
    distance_rate = svc.distance_rate_per_km_usd if svc else 1.40
    fragile_pct = svc.fragile_surcharge_pct if svc else 5.0
    floor_fee = svc.floor_fee_usd if svc else 5

    distance_fee = round(distance_km * distance_rate, 2)
    loading_fee = 20.0 if needs_labour else 0.0
    packing_fee = 25.0 if needs_packing else 0.0
    fragile_surcharge = round((base_fee + distance_fee) * fragile_pct / 100.0, 2) if has_fragile else 0.0
    floor_charges = round(floor_count * floor_fee, 2)
    fuel_surcharge = round(distance_fee * 0.15, 2)

    total = round(base_fee + distance_fee + loading_fee + packing_fee + fragile_surcharge + floor_charges + fuel_surcharge, 2)

    return BookingCostBreakdown(
        route_distance_km=distance_km,
        base_fee_usd=base_fee,
        distance_fee_usd=distance_fee,
        loading_fee_usd=loading_fee,
        packing_fee_usd=packing_fee,
        fragile_surcharge_usd=fragile_surcharge,
        floor_fee_usd=floor_charges,
        fuel_surcharge_usd=fuel_surcharge,
        total_estimated_usd=total,
    )
