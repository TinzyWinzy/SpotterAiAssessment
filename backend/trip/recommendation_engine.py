"""Truck recommendation engine — rule-based, no AI needed."""

from dataclasses import dataclass
from typing import Optional

from .services import get_service

TRUCK_CAPACITIES = {
    "1.5 Ton": 1.5,
    "2 Ton": 2.0,
    "3 Ton": 3.0,
    "5 Ton": 5.0,
    "7.5 Ton": 7.5,
}

TRUCK_SIZES = sorted(TRUCK_CAPACITIES.keys(), key=lambda k: TRUCK_CAPACITIES[k])


@dataclass
class TruckRecommendation:
    recommended_size: str
    capacity_tonnes: float
    explanation: str
    alternatives: list[str]


def estimate_total_weight(cargo_items: list[dict]) -> float:
    """Estimate total cargo weight in tonnes from item descriptions."""
    total = 0.0
    for item in cargo_items or []:
        weight = item.get("estimated_weight_kg", 0) or 0
        qty = item.get("quantity", 1) or 1
        total += weight * qty
    return total / 1000.0  # kg to tonnes


def recommend_truck(
    service_type: str = "",
    cargo_items: Optional[list[dict]] = None,
    total_weight_tonnes: Optional[float] = None,
) -> TruckRecommendation:
    """Recommend the appropriate truck size based on cargo and service type."""
    total_t = total_weight_tonnes if total_weight_tonnes is not None else estimate_total_weight(cargo_items or [])

    svc = get_service(service_type)
    default_sizes = svc.default_truck_sizes if svc else TRUCK_SIZES

    chosen = None
    for size in TRUCK_SIZES:
        if size in default_sizes and TRUCK_CAPACITIES[size] >= total_t * 1.2:
            chosen = size
            break

    if not chosen:
        chosen = default_sizes[-1] if default_sizes else TRUCK_SIZES[-1]

    alternatives = [s for s in default_sizes if s != chosen]

    capacity = TRUCK_CAPACITIES.get(chosen, 0)
    if total_t <= 0:
        explanation = f"Recommended: {chosen} — no cargo entered yet, based on {svc.name.lower() if svc else 'custom'} service."
    else:
        pct = (total_t / capacity * 100) if capacity > 0 else 0
        explanation = f"Recommended: {chosen} ({pct:.0f}% capacity used for ~{total_t:.1f}t of cargo)."

    return TruckRecommendation(
        recommended_size=chosen,
        capacity_tonnes=capacity,
        explanation=explanation,
        alternatives=alternatives,
    )
