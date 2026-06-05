"""Geocoding via Nominatim (OpenStreetMap). Free, no key, 1 req/sec rate limit."""
import time
import requests
from typing import Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SpotterAssessment/1.0 (https://github.com/TinzyWinzy/spotter-assessment)"

_last_call = 0.0


def _rate_limit():
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_call = time.time()


def geocode(query: str) -> Optional[dict]:
    """Return {lat, lon, display_name} or None."""
    _rate_limit()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        r = results[0]
        addr = r.get("address", {})
        city = (
            addr.get("city")
            or addr.get("town")
            or addr.get("village")
            or addr.get("hamlet")
            or addr.get("county")
            or query
        )
        state = addr.get("state", "")
        label = f"{city}, {state}" if state else city
        return {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r.get("display_name", query),
            "label": label,
        }
    except Exception as e:
        print(f"[geocoding] error for {query!r}: {e}")
        return None
