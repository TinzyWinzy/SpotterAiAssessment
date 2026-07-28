"""Unit tests for the trip cost calculator."""
from __future__ import annotations

from trip.cost_calculator import (
    estimate_trip_cost,
    calculate_fuel_cost,
    calculate_driver_pay,
    calculate_border_fees,
    calculate_maintenance_provision,
    estimate_days,
    VehicleSpec,
    DriverSpec,
    CostBreakdown,
    DEFAULT_FUEL_PRICE_USD_PER_L,
)


class TestFuelCost:
    def test_zero_distance(self):
        assert calculate_fuel_cost(0, 35, 1.60) == 0.0

    def test_zero_consumption(self):
        assert calculate_fuel_cost(500, 0, 1.60) == 0.0

    def test_normal_calculation(self):
        cost = calculate_fuel_cost(580, 35.0, 1.60)
        assert cost > 0
        expected = (580 / 100) * 35 * 1.60
        assert cost == round(expected, 2)

    def test_harare_to_beitbridge(self):
        cost = calculate_fuel_cost(580, 35.0, 1.60)
        assert 300 < cost < 350

    def test_long_haul(self):
        cost = calculate_fuel_cost(2000, 32.0, 1.60)
        assert 1000 < cost < 1100


class TestDriverPay:
    def test_no_driver(self):
        assert calculate_driver_pay(500, 2, None) == 0.0

    def test_day_rate_only(self):
        driver = DriverSpec(rate_per_day_usd=30.0, rate_per_km_usd=0.0)
        pay = calculate_driver_pay(500, 3, driver)
        assert pay == 90.0

    def test_km_rate_only(self):
        driver = DriverSpec(rate_per_day_usd=0.0, rate_per_km_usd=0.50)
        pay = calculate_driver_pay(580, 2, driver)
        assert pay == 290.0

    def test_combined_rates(self):
        driver = DriverSpec(rate_per_day_usd=30.0, rate_per_km_usd=0.50)
        pay = calculate_driver_pay(580, 2, driver)
        assert pay == 350.0


class TestBorderFees:
    def test_no_crossings(self):
        assert calculate_border_fees(0) == 0.0

    def test_one_crossing(self):
        assert calculate_border_fees(1) == 50.0

    def test_custom_fee(self):
        assert calculate_border_fees(2, fee_per_crossing_usd=75.0) == 150.0


class TestMaintenance:
    def test_default_rate(self):
        cost = calculate_maintenance_provision(580)
        assert cost == 29.0

    def test_custom_rate(self):
        cost = calculate_maintenance_provision(1000, rate_per_km_usd=0.10)
        assert cost == 100.0


class TestEstimateDays:
    def test_short_trip(self):
        days = estimate_days(480)
        assert days == 1.0

    def test_two_day_trip(self):
        days = estimate_days(960)
        assert days == 2.0

    def test_with_border(self):
        days = estimate_days(580, border_crossings=1)
        assert days == round(580 / 480 + 0.5, 1)

    def test_minimum_one_day(self):
        days = estimate_days(10)
        assert days == 1.0


class TestFullCostBreakdown:
    def test_basic_trip_no_vehicle(self):
        cb = estimate_trip_cost(580)
        assert isinstance(cb, CostBreakdown)
        assert cb.route_distance_km == 580
        assert cb.fuel_cost_usd == 0.0
        assert cb.driver_pay_usd == 0.0
        assert cb.border_fees_usd == 0.0

    def test_harare_beitbridge_full(self):
        vehicle = VehicleSpec(fuel_consumption_l_100km=35.0)
        driver = DriverSpec(rate_per_day_usd=30.0, rate_per_km_usd=0.50)

        cb = estimate_trip_cost(
            route_distance_km=580,
            vehicle=vehicle,
            driver=driver,
            border_crossings=0,
        )

        assert cb.fuel_cost_usd > 0
        assert cb.driver_pay_usd > 0
        assert cb.total_cost_usd > 0
        assert cb.recommended_revenue_usd > cb.total_cost_usd
        assert cb.profit_margin_pct == 20.0
        assert isinstance(cb.estimated_days, float)

    def test_cross_border_with_tolls(self):
        vehicle = VehicleSpec(fuel_consumption_l_100km=32.0)
        driver = DriverSpec(rate_per_day_usd=40.0, rate_per_km_usd=0.60)

        cb = estimate_trip_cost(
            route_distance_km=1200,
            vehicle=vehicle,
            driver=driver,
            border_crossings=2,
            border_fee_per_crossing_usd=60.0,
            tolls_usd=25.0,
        )

        assert cb.border_fees_usd == 120.0
        assert cb.tolls_usd == 25.0
        assert cb.total_cost_usd == round(
            cb.fuel_cost_usd + cb.driver_pay_usd + cb.border_fees_usd
            + cb.tolls_usd + cb.maintenance_provision_usd, 2
        )

    def test_custom_fuel_price(self):
        vehicle = VehicleSpec(fuel_consumption_l_100km=35.0)
        cb = estimate_trip_cost(580, vehicle=vehicle, fuel_price_per_litre_usd=2.00)

        expected_fuel = (580 / 100) * 35 * 2.00
        assert cb.fuel_cost_usd == round(expected_fuel, 2)

    def test_break_even_equals_total_cost(self):
        vehicle = VehicleSpec(fuel_consumption_l_100km=30.0)
        driver = DriverSpec(rate_per_day_usd=25.0, rate_per_km_usd=0.40)
        cb = estimate_trip_cost(800, vehicle=vehicle, driver=driver)
        assert cb.break_even_revenue_usd == cb.total_cost_usd

    def test_recommended_includes_margin(self):
        vehicle = VehicleSpec(fuel_consumption_l_100km=30.0)
        cb = estimate_trip_cost(800, vehicle=vehicle)
        assert cb.recommended_revenue_usd == round(cb.total_cost_usd * 1.20, 2)
