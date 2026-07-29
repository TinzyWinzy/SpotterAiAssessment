"""Service type registry — defines per-service pricing, defaults, and workflows."""

from dataclasses import dataclass
from typing import Optional

SERVICE_CHOICES = [
    ("household", "Household Removal", "Truck moving household furniture and belongings"),
    ("grocery", "Grocery Delivery", "Transport of groceries and perishables"),
    ("construction", "Construction Materials", "Delivery of bricks, cement, timber, and other materials"),
    ("furniture", "Furniture Delivery", "Delivery of new or second-hand furniture items"),
    ("office", "Office Relocation", "Moving office equipment, desks, and files"),
    ("long_distance", "Long Distance", "Intercity or cross-border transport of any goods"),
    ("custom", "Custom Transport", "General goods transport not covered by other categories"),
]


@dataclass
class ServiceType:
    key: str
    name: str
    description: str
    icon: str
    base_fee_usd: float
    distance_rate_per_km_usd: float
    default_truck_sizes: list[str]
    requires_packing: bool
    requires_labour: bool
    fragile_surcharge_pct: float
    floor_fee_usd: int


SERVICES: dict[str, ServiceType] = {
    "household": ServiceType(
        key="household", name="Household Removal", description="",
        icon="truck", base_fee_usd=50.0, distance_rate_per_km_usd=1.50,
        default_truck_sizes=["3 Ton", "5 Ton", "7.5 Ton"],
        requires_packing=True, requires_labour=True,
        fragile_surcharge_pct=15.0, floor_fee_usd=10,
    ),
    "grocery": ServiceType(
        key="grocery", name="Grocery Delivery", description="",
        icon="shopping-cart", base_fee_usd=20.0, distance_rate_per_km_usd=1.00,
        default_truck_sizes=["1.5 Ton", "2 Ton", "3 Ton"],
        requires_packing=False, requires_labour=True,
        fragile_surcharge_pct=10.0, floor_fee_usd=5,
    ),
    "construction": ServiceType(
        key="construction", name="Construction Materials", description="",
        icon="hard-hat", base_fee_usd=40.0, distance_rate_per_km_usd=1.80,
        default_truck_sizes=["3 Ton", "5 Ton", "7.5 Ton"],
        requires_packing=False, requires_labour=True,
        fragile_surcharge_pct=0.0, floor_fee_usd=0,
    ),
    "furniture": ServiceType(
        key="furniture", name="Furniture Delivery", description="",
        icon="armchair", base_fee_usd=35.0, distance_rate_per_km_usd=1.20,
        default_truck_sizes=["1.5 Ton", "2 Ton", "3 Ton"],
        requires_packing=True, requires_labour=True,
        fragile_surcharge_pct=20.0, floor_fee_usd=10,
    ),
    "office": ServiceType(
        key="office", name="Office Relocation", description="",
        icon="building", base_fee_usd=60.0, distance_rate_per_km_usd=1.60,
        default_truck_sizes=["3 Ton", "5 Ton", "7.5 Ton"],
        requires_packing=True, requires_labour=True,
        fragile_surcharge_pct=10.0, floor_fee_usd=10,
    ),
    "long_distance": ServiceType(
        key="long_distance", name="Long Distance", description="",
        icon="map", base_fee_usd=80.0, distance_rate_per_km_usd=1.00,
        default_truck_sizes=["3 Ton", "5 Ton", "7.5 Ton"],
        requires_packing=False, requires_labour=False,
        fragile_surcharge_pct=10.0, floor_fee_usd=0,
    ),
    "custom": ServiceType(
        key="custom", name="Custom Transport", description="",
        icon="package", base_fee_usd=30.0, distance_rate_per_km_usd=1.40,
        default_truck_sizes=["1.5 Ton", "2 Ton", "3 Ton", "5 Ton", "7.5 Ton"],
        requires_packing=False, requires_labour=False,
        fragile_surcharge_pct=5.0, floor_fee_usd=5,
    ),
}


def get_service(key: str) -> Optional[ServiceType]:
    return SERVICES.get(key)


def list_services() -> list[dict]:
    return [
        {
            "key": s.key,
            "name": s.name,
            "description": s.description,
            "icon": s.icon,
            "default_truck_sizes": s.default_truck_sizes,
        }
        for s in SERVICES.values()
    ]
