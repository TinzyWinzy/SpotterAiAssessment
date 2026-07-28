"""Seed demo fleet: organisation, vehicles, drivers, admin user, sample trips."""
from datetime import date, timedelta
from random import choice, randint, uniform

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from trip.models import Organisation, Vehicle, Driver, Trip, CommodityCategory, Commodity

User = get_user_model()

ALL_ROUTES = [
    # Southern Africa
    ("Harare, Zimbabwe", "Beitbridge, Zimbabwe", 580),
    ("Beitbridge, Zimbabwe", "Johannesburg, South Africa", 540),
    ("Harare, Zimbabwe", "Mutare, Zimbabwe", 260),
    ("Harare, Zimbabwe", "Bulawayo, Zimbabwe", 440),
    ("Lusaka, Zambia", "Harare, Zimbabwe", 500),
    ("Johannesburg, South Africa", "Durban, South Africa", 570),
    ("Bulawayo, Zimbabwe", "Francistown, Botswana", 200),
    ("Harare, Zimbabwe", "Chirundu, Zimbabwe", 350),
    ("Beitbridge, Zimbabwe", "Harare, Zimbabwe", 580),
    ("Johannesburg, South Africa", "Beitbridge, Zimbabwe", 540),
    # US Interstate
    # Cross-border Zim-centric
    ("Harare, Zimbabwe", "Johannesburg, South Africa", 1120),
    ("Harare, Zimbabwe", "Lusaka, Zambia", 500),
    ("Harare, Zimbabwe", "Gaborone, Botswana", 1000),
    ("Harare, Zimbabwe", "Maputo, Mozambique", 1100),
    ("Bulawayo, Zimbabwe", "Johannesburg, South Africa", 820),
    ("Bulawayo, Zimbabwe", "Gaborone, Botswana", 580),
    ("Mutare, Zimbabwe", "Beira, Mozambique", 550),
    ("Beitbridge, Zimbabwe", "Bulawayo, Zimbabwe", 320),
    ("Chirundu, Zimbabwe", "Lusaka, Zambia", 150),
    ("Victoria Falls, Zimbabwe", "Livingstone, Zambia", 20),
    ("Harare, Zimbabwe", "Kariba, Zimbabwe", 370),
    ("Masvingo, Zimbabwe", "Harare, Zimbabwe", 290),
    ("Gweru, Zimbabwe", "Bulawayo, Zimbabwe", 290),
    ("Johannesburg, South Africa", "Durban, South Africa", 570),
    ("Johannesburg, South Africa", "Cape Town, South Africa", 1400),
    ("Lusaka, Zambia", "Ndola, Zambia", 320),
    # US Interstate
    ("New York, NY", "Philadelphia, PA", 150),
    ("Philadelphia, PA", "Baltimore, MD", 160),
    ("Baltimore, MD", "Washington, DC", 60),
    ("New York, NY", "Boston, MA", 340),
    ("Los Angeles, CA", "Phoenix, AZ", 590),
    ("Phoenix, AZ", "El Paso, TX", 430),
    ("El Paso, TX", "San Antonio, TX", 550),
    ("San Antonio, TX", "Houston, TX", 310),
    ("Houston, TX", "Dallas, TX", 390),
    ("Dallas, TX", "Oklahoma City, OK", 320),
    ("Oklahoma City, OK", "Kansas City, MO", 350),
    ("Kansas City, MO", "St. Louis, MO", 390),
    ("St. Louis, MO", "Indianapolis, IN", 390),
    ("Indianapolis, IN", "Columbus, OH", 290),
    ("Columbus, OH", "Pittsburgh, PA", 280),
    ("Pittsburgh, PA", "Harrisburg, PA", 320),
    ("Harrisburg, PA", "New York, NY", 270),
    ("Chicago, IL", "Indianapolis, IN", 290),
    ("Chicago, IL", "Detroit, MI", 470),
    ("Detroit, MI", "Cleveland, OH", 270),
    ("Cleveland, OH", "Buffalo, NY", 300),
    ("Buffalo, NY", "Rochester, NY", 120),
    ("Rochester, NY", "Syracuse, NY", 150),
    ("Syracuse, NY", "Albany, NY", 240),
    ("Albany, NY", "New York, NY", 230),
    ("Los Angeles, CA", "San Diego, CA", 190),
    ("San Francisco, CA", "Los Angeles, CA", 550),
    ("Portland, OR", "Seattle, WA", 280),
    ("Seattle, WA", "Spokane, WA", 460),
    ("Denver, CO", "Salt Lake City, UT", 840),
    ("Salt Lake City, UT", "Boise, ID", 550),
    ("Boise, ID", "Portland, OR", 720),
    ("Atlanta, GA", "Charlotte, NC", 390),
    ("Charlotte, NC", "Raleigh, NC", 260),
    ("Raleigh, NC", "Richmond, VA", 280),
    ("Richmond, VA", "Washington, DC", 180),
    ("Miami, FL", "Orlando, FL", 380),
    ("Orlando, FL", "Jacksonville, FL", 240),
    ("Jacksonville, FL", "Savannah, GA", 220),
    ("Savannah, GA", "Atlanta, GA", 400),
    ("Memphis, TN", "Nashville, TN", 340),
    ("Nashville, TN", "Knoxville, TN", 290),
    ("Knoxville, TN", "Asheville, NC", 180),
    ("Minneapolis, MN", "Milwaukee, WI", 540),
    ("Milwaukee, WI", "Chicago, IL", 150),
    ("New Orleans, LA", "Baton Rouge, LA", 130),
    ("Baton Rouge, LA", "Houston, TX", 460),
    ("Albuquerque, NM", "Santa Fe, NM", 100),
    ("Santa Fe, NM", "Denver, CO", 630),
    ("Las Vegas, NV", "Los Angeles, CA", 430),
    ("Reno, NV", "Sacramento, CA", 220),
    ("Sacramento, CA", "San Francisco, CA", 140),
]

STATUSES = ["delivered", "paid", "in_transit", "dispatched", "at_border"]

COMMODITY_SEED = [
    ("General Freight", [
        ("General Cargo", "tonne", 0.50, 0.05, 0),
        ("Parcel Freight", "kg", None, 0.15, 5),
        ("Less-than-Truckload", "tonne", 0.60, 0.08, 10),
    ]),
    ("Fuel & Chemicals", [
        ("Diesel", "litre", 0.20, None, 0),
        ("Petrol", "litre", 0.22, None, 0),
        ("Chemicals (Hazmat)", "tonne", 0.90, 0.06, 25),
    ]),
    ("Containers", [
        ("20ft Container", "unit", 1.20, None, 50),
        ("40ft Container", "unit", 1.80, None, 75),
        ("Reefer Container", "unit", 2.00, None, 100),
    ]),
    ("Agriculture", [
        ("Grains (Maize/Wheat)", "tonne", 0.40, 0.03, 0),
        ("Fresh Produce", "tonne", 0.70, 0.08, 10),
        ("Livestock", "head", 2.50, None, 50),
        ("Fertiliser", "tonne", 0.45, 0.04, 0),
    ]),
    ("Mining & Minerals", [
        ("Coal", "tonne", 0.35, 0.02, 0),
        ("Gold Ore", "tonne", 2.00, 0.15, 50),
        ("Copper", "tonne", 1.50, 0.10, 30),
        ("Chromite", "tonne", 0.55, 0.04, 0),
        ("Lithium Ore", "tonne", 1.80, 0.12, 40),
        ("Granite / Marble", "tonne", 0.60, 0.05, 20),
    ]),
    ("Construction", [
        ("Cement", "tonne", 0.30, 0.02, 0),
        ("Steel / Rebar", "tonne", 0.50, 0.03, 10),
        ("Sand / Aggregate", "tonne", 0.25, 0.01, 0),
        ("Bricks", "pallet", 0.40, None, 5),
    ]),
    ("Perishables", [
        ("Frozen Goods", "tonne", 0.80, 0.10, 15),
        ("Dairy Products", "tonne", 0.75, 0.09, 10),
        ("Pharmaceuticals", "kg", None, 1.50, 25),
    ]),
    ("Vehicles & Machinery", [
        ("Passenger Vehicle", "unit", 2.00, None, 0),
        ("Light Truck", "unit", 2.50, None, 0),
        ("Heavy Equipment", "unit", 5.00, None, 0),
    ]),
]


class Command(BaseCommand):
    help = "Create demo fleet with vehicles, drivers, admin, and sample trips."

    def add_arguments(self, parser):
        parser.add_argument("--admin-username", default="admin")
        parser.add_argument("--admin-password", default="admin")
        parser.add_argument("--driver-username", default="tino")
        parser.add_argument("--driver-password", default="12345")
        parser.add_argument("--trip-count", type=int, default=25)

    def _ensure_user(self, username, password, is_staff=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"is_staff": is_staff},
        )
        user.set_password(password)
        if is_staff:
            user.is_staff = True
        user.save()
        return user

    def handle(self, *args, **opts):
        admin = self._ensure_user(opts["admin_username"], opts["admin_password"], is_staff=True)
        driver_user = self._ensure_user(opts["driver_username"], opts["driver_password"], is_staff=False)

        org, _ = Organisation.objects.get_or_create(
            slug="mhofu-logistics",
            defaults={
                "name": "Mhofu Logistics",
                "contact_phone": "+263772000000",
                "contact_email": "ops@mhofu.co.zw",
                "licensed_vehicles": 20,
            },
        )

        vehicle_specs = [
            {"plate": "AFC 4512", "make": "MAN", "model": "TGS 26.440", "fuel_consumption_rate_l_100km": 35.0, "tank_capacity_l": 400.0},
            {"plate": "AFC 4513", "make": "Volvo", "model": "FH16", "fuel_consumption_rate_l_100km": 32.0, "tank_capacity_l": 450.0},
            {"plate": "ADH 7890", "make": "Scania", "model": "R500", "fuel_consumption_rate_l_100km": 30.0, "tank_capacity_l": 500.0},
        ]
        vehicles = []
        for v in vehicle_specs:
            obj, _ = Vehicle.objects.get_or_create(
                organisation=org, plate=v["plate"],
                defaults={k: v[k] for k in v if k != "plate"},
            )
            vehicles.append(obj)

        driver_names = ["Tinotenda Duma", "Tawanda Moyo", "Simba Chirwa", "Farai Ncube",
                          "Chido Madzima", "Tanaka Mufambi", "Rumbidzai Sithole"]
        drivers = []
        for name in driver_names:
            d, _ = Driver.objects.get_or_create(
                name=name,
                defaults={
                    "organisation": org,
                    "phone_number": f"+26371{randint(1000000, 9999999)}",
                    "rate_per_day_usd": uniform(25, 40),
                    "rate_per_km_usd": uniform(0.30, 0.60),
                },
            )
            if name == "Tinotenda Duma":
                d.user = driver_user
                d.save()
            drivers.append(d)

        # Seed commodity categories and commodities
        all_commodities = []
        for cat_name, items in COMMODITY_SEED:
            cat, _ = CommodityCategory.objects.get_or_create(
                name=cat_name,
                defaults={"icon": cat_name.lower().replace(" & ", "-").replace(" ", "-")},
            )
            for c_name, unit, rate_km, rate_kg, flat in items:
                com, _ = Commodity.objects.get_or_create(
                    name=c_name,
                    defaults={
                        "category": cat,
                        "unit": unit,
                        "rate_per_km": rate_km if rate_km else None,
                        "rate_per_kg": rate_kg if rate_kg else None,
                        "flat_fee": flat if flat else None,
                        "is_active": True,
                    },
                )
                all_commodities.append(com)

        # Seed sample trips across the last 60 days
        existing_count = Trip.objects.filter(organisation=org).count()
        to_create = max(0, opts["trip_count"] - existing_count)

        for i in range(to_create):
            route = choice(ALL_ROUTES)
            origin, destination, base_km = route
            distance = base_km + randint(-30, 30)
            days_ago = randint(0, 60)
            trip_date = date.today() - timedelta(days=days_ago)
            status = choice(STATUSES)
            driver = choice(drivers)
            vehicle = choice(vehicles)

            fuel_price = uniform(1.50, 1.75)
            fuel_litres = (distance / 100) * vehicle.fuel_consumption_rate_l_100km
            est_fuel = round(fuel_litres * fuel_price, 2)
            est_driver = round(distance * driver.rate_per_km_usd + 2 * driver.rate_per_day_usd, 2)
            est_total = round(est_fuel + est_driver + uniform(25, 100) + distance * 0.05, 2)
            revenue = round(est_total * uniform(1.15, 1.35), 2)
            actual_fuel = round(est_fuel * uniform(0.90, 1.10), 2) if status in ("delivered", "paid") else None
            commodity = choice(all_commodities) if all_commodities else None
            rev = uniform(1.15, 1.35)
            if commodity and commodity.rate_per_km:
                est_rev = round(
                    float(commodity.rate_per_km) * distance +
                    (float(commodity.rate_per_kg or 0) * uniform(5, 20) * 1000) +
                    float(commodity.flat_fee or 0),
                    2,
                )
            else:
                est_rev = round(est_total * rev, 2)
            load_weight = round(uniform(5, 25), 1) if commodity else None

            Trip.objects.create(
                organisation=org,
                vehicle=vehicle,
                driver=driver,
                commodity=commodity,
                origin=origin,
                destination=destination,
                distance_km=distance,
                load_weight_tonnes=load_weight,
                estimated_revenue=est_rev,
                estimated_fuel_cost_usd=est_fuel,
                estimated_driver_pay_usd=est_driver,
                estimated_total_cost_usd=est_total,
                actual_fuel_cost_usd=actual_fuel,
                actual_total_cost_usd=round(est_total * uniform(0.90, 1.05), 2) if status in ("delivered", "paid") else None,
                revenue_usd=revenue if status in ("delivered", "paid") else None,
                status=status,
                created_at=trip_date,
                updated_at=trip_date,
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {org.name}: {len(vehicles)} vehicles, {len(drivers)} drivers, "
            f"{Trip.objects.filter(organisation=org).count()} trips. "
            f"Admin={admin.username}, Driver={driver_user.username}"
        ))
