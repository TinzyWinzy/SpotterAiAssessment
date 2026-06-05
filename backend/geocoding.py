"""
Geocoding via Nominatim (OpenStreetMap) with Photon (Komoot) as a fallback.

Both are free, no API key required. Nominatim has a strict 1 req/sec rate limit
and is known to block shared-IP hosting providers (Render, Vercel, etc.).
Photon is more permissive and serves the same OSM data.
"""
import time
import requests
from typing import Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "SpotterAssessment/1.0 (https://github.com/TinzyWinzy/spotter-assessment)"

_last_call = 0.0


def _rate_limit():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_call = time.time()


def _extract_label(r: dict, fallback: str) -> str:
    addr = r.get("address", {}) or {}
    city = (
        addr.get("city")
        or addr.get("town")
        or addr.get("village")
        or addr.get("hamlet")
        or addr.get("county")
        or r.get("name")
        or fallback
    )
    state = addr.get("state", "")
    if state and state not in city:
        return f"{city}, {state}"
    return city


def _geocode_nominatim(query: str) -> Optional[dict]:
    _rate_limit()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        r = results[0]
        return {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r.get("display_name", query),
            "label": _extract_label(r, query),
        }
    except Exception as e:
        print(f"[geocoding:nominatim] {query!r} -> {type(e).__name__}: {e}")
        return None


def _geocode_photon(query: str) -> Optional[dict]:
    try:
        resp = requests.get(
            PHOTON_URL,
            params={"q": query, "limit": 1, "lang": "en"},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json().get("features", [])
        if not results:
            return None
        f = results[0]
        coords = f.get("geometry", {}).get("coordinates", [])
        if len(coords) < 2:
            return None
        props = f.get("properties", {})
        return {
            "lat": float(coords[1]),
            "lon": float(coords[0]),
            "display_name": props.get("name", query) or query,
            "label": _extract_label({"address": props}, query),
        }
    except Exception as e:
        print(f"[geocoding:photon] {query!r} -> {type(e).__name__}: {e}")
        return None


def geocode(query: str) -> Optional[dict]:
    """Return {lat, lon, display_name, label} or None.

    Tries Nominatim first, then Photon. Both free, no API key.
    """
    result = _geocode_nominatim(query)
    if result is not None:
        return result
    result = _geocode_photon(query)
    return result
