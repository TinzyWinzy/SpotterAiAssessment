"""Routing via OSRM public demo server. Free, no key, returns polyline + distance."""
import requests
from typing import Optional

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"


def route(coords: list[tuple[float, float]]) -> Optional[dict]:
    """coords: [(lon, lat), (lon, lat), ...] — note OSRM uses lon,lat order.

    Returns {distance_meters, duration_seconds, geometry (GeoJSON LineString)} or None.
    """
    if len(coords) < 2:
        return None
    path = ";".join(f"{lon},{lat}" for lon, lat in coords)
    try:
        resp = requests.get(
            f"{OSRM_URL}/{path}",
            params={"overview": "full", "geometries": "geojson"},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data.get("routes"):
            return None
        r = data["routes"][0]
        return {
            "distance_meters": r["distance"],
            "duration_seconds": r["duration"],
            "distance_mi": r["distance"] / 1609.344,
            "geometry": r["geometry"],  # GeoJSON LineString
        }
    except Exception as e:
        print(f"[routing] error: {e}")
        return None
