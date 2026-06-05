"""Pytest fixtures for backend integration tests.

Provides:
  - `api_client`   — DRF APIClient
  - `mock_geo_router` — patches `geocoding.geocode` + `routing.route` to return synthetic data
  - `freezer`      — pins datetime so 14h-window tests are deterministic
  - `live_network` — fixture that requires a real backend to be running (used by test_live_*.py)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

# Make the backend root importable so `import views, geocoding, routing, hos_engine` works.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Configure Django before any app imports.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "spotter_backend.settings")

import django  # noqa: E402

django.setup()

from rest_framework.test import APIClient  # noqa: E402


# ---------- city coords used by mocked geocoder (miles apart, see test_hos_engine.py) ----------
CITY_COORDS = {
    "New York, NY":         (40.7128, -74.0060),
    "Philadelphia, PA":     (39.9526, -75.1652),
    "Baltimore, MD":        (39.2904, -76.6122),
    "Washington, D.C.":     (38.9072, -77.0369),
    "Indianapolis, IN":     (39.7684, -86.1581),
    "Columbus, OH":         (39.9612, -82.9988),
    "Chicago, IL":          (41.8781, -87.6298),
    "Los Angeles, CA":      (34.0522, -118.2437),
    "Albuquerque, NM":      (35.0844, -106.6504),
    "Miami, FL":            (25.7617, -80.1918),
    "Atlanta, GA":          (33.7490, -84.3880),
    "Charlotte, NC":        (35.2271, -80.8431),
    "Tampa, FL":            (27.9506, -82.4572),
    "Unknown City, ZZ":     (None, None),
}


def _synthetic_route(coords):
    """Mimics OSRM: a straight-line geometry between waypoints.

    Distance/duration computed in `routing.py` style, so tests can compare
    against the same haversine math.
    """
    import math

    R_MI = 3958.8
    total = 0.0
    for i in range(1, len(coords)):
        lat1, lon1 = coords[i - 1]
        lat2, lon2 = coords[i]
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lon2 - lon1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        total += R_MI * c
    return {
        "distance_mi": total,
        "duration_seconds": total / 55.0 * 3600,  # 55 mph
        "geometry": {
            "type": "LineString",
            "coordinates": [[lon, lat] for (lat, lon) in coords],
        },
    }


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def mock_geo_router():
    """Patch geocoding.geocode + routing.route with deterministic synthetic data.

    The patched geocoder looks up coords from CITY_COORDS, returns None for unknowns.
    The patched router returns a straight-line geometry between the geocoded coords.
    """
    def fake_geocode(query):
        if query in CITY_COORDS:
            lat, lon = CITY_COORDS[query]
            if lat is None:
                return None
            return {"lat": lat, "lon": lon, "display_name": query, "label": query}
        return None

    def fake_route(lonlat_pairs):
        # lonlat_pairs is a list of (lon, lat) — convert to (lat, lon) for our helper.
        coords_latlon = [(lat, lon) for (lon, lat) in lonlat_pairs]
        return _synthetic_route(coords_latlon)

    with patch("trip.views.geocoding.geocode", side_effect=fake_geocode) as geo_patch, \
         patch("trip.views.routing.route", side_effect=fake_route) as route_patch:
        yield {
            "geocode": geo_patch,
            "route": route_patch,
        }


@pytest.fixture
def frozen_time():
    """Pin datetime.utcnow() to a known moment so trips start deterministically."""
    fixed = datetime(2026, 6, 5, 6, 0, 0)
    with patch("trip.views.datetime") as dt_patch:
        dt_patch.utcnow.return_value = fixed
        yield fixed


@pytest.fixture
def live_network():
    """Skip test if the live backend isn't reachable."""
    import socket
    from urllib.parse import urlparse

    url = os.environ.get("SPOTTER_LIVE_URL", "http://127.0.0.1:8001")
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=3):
            return url
    except OSError:
        pytest.skip(f"Live backend not reachable at {url}")
