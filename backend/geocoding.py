"""
Geocoding via Nominatim (OpenStreetMap) with Photon (Komoot) as a fallback.

Both are free, no API key required. Nominatim has a strict 1 req/sec rate limit
and is known to block shared-IP hosting providers (Render, Vercel, etc.).
Photon is more permissive and serves the same OSM data.

Optimisations:
  - In-memory LRU cache (1 hr TTL) so the same city is only geocoded once.
  - Circuit breaker: after 2 consecutive 429s, skip Nominatim for 5 min and
    go straight to Photon (the typical Render-on-shared-IP scenario).
  - Demoted log line: noisy `print` replaced with `logging.warning` so prod
    logs stay clean. Nominatim 429s are expected on Render — they no longer
    look like a bug.
"""
from __future__ import annotations
import logging
import time
from threading import Lock
from typing import Optional

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
USER_AGENT = "SpotterAssessment/1.0 (https://github.com/TinzyWinzy/spotter-assessment)"

# --------------------------------------------------------------------------- #
# Cache
# --------------------------------------------------------------------------- #
_CACHE: dict[str, tuple[float, Optional[dict]]] = {}
_CACHE_TTL_S = 3600.0
_CACHE_LOCK = Lock()

# --------------------------------------------------------------------------- #
# Rate limit (Nominatim: 1 req/sec, process-wide)
# --------------------------------------------------------------------------- #
_last_nominatim_call = 0.0
_NOMINATIM_MIN_INTERVAL_S = 1.0

# --------------------------------------------------------------------------- #
# Circuit breaker: open after N consecutive 429s, stay open for T seconds
# --------------------------------------------------------------------------- #
_CB_FAIL_THRESHOLD = 2
_CB_OPEN_DURATION_S = 300.0
_cb_consecutive_429 = 0
_cb_open_until = 0.0
_CB_LOCK = Lock()


def _cache_get(query: str) -> Optional[dict]:
    with _CACHE_LOCK:
        entry = _CACHE.get(query)
    if not entry:
        return None
    stored_at, value = entry
    if time.time() - stored_at > _CACHE_TTL_S:
        with _CACHE_LOCK:
            _CACHE.pop(query, None)
        return None
    return value


def _cache_put(query: str, value: Optional[dict]) -> None:
    with _CACHE_LOCK:
        _CACHE[query] = (time.time(), value)


def cache_clear() -> None:
    """Clear the in-memory geocode cache (test helper)."""
    with _CACHE_LOCK:
        _CACHE.clear()


def _cb_is_open() -> bool:
    return time.time() < _cb_open_until


def _cb_record_success() -> None:
    global _cb_consecutive_429, _cb_open_until
    with _CB_LOCK:
        _cb_consecutive_429 = 0
        _cb_open_until = 0.0


def _cb_record_429() -> None:
    global _cb_consecutive_429, _cb_open_until
    with _CB_LOCK:
        _cb_consecutive_429 += 1
        if _cb_consecutive_429 >= _CB_FAIL_THRESHOLD:
            _cb_open_until = time.time() + _CB_OPEN_DURATION_S
            logger.warning(
                "nominatim circuit OPEN — skipping for %ds after %d consecutive 429s",
                _CB_OPEN_DURATION_S, _cb_consecutive_429,
            )


def _rate_limit_nominatim() -> None:
    global _last_nominatim_call
    elapsed = time.time() - _last_nominatim_call
    if elapsed < _NOMINATIM_MIN_INTERVAL_S:
        time.sleep(_NOMINATIM_MIN_INTERVAL_S - elapsed)
    _last_nominatim_call = time.time()


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
    _rate_limit_nominatim()
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "addressdetails": 1},
            headers={"User-Agent": USER_AGENT, "Accept-Language": "en"},
            timeout=10,
        )
        if resp.status_code == 429:
            _cb_record_429()
            logger.info("nominatim 429 for %r (consecutive=%d, circuit_open=%s)",
                        query, _cb_consecutive_429, _cb_is_open())
            return None
        resp.raise_for_status()
        results = resp.json()
        if not results:
            return None
        r = results[0]
        _cb_record_success()
        return {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r.get("display_name", query),
            "label": _extract_label(r, query),
        }
    except Exception as e:
        logger.info("nominatim error for %r: %s: %s", query, type(e).__name__, e)
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
        logger.info("photon error for %r: %s: %s", query, type(e).__name__, e)
        return None


def geocode(query: str) -> Optional[dict]:
    """Return {lat, lon, display_name, label} or None.

    Order: cache → Nominatim (if circuit closed) → Photon.
    Negative results (None) are also cached briefly to avoid hammering.
    """
    query_norm = query.strip().lower()
    cached = _cache_get(query_norm)
    if cached is not None or query_norm in {k for k, _ in _CACHE.items()}:
        # Re-check the negative-cache sentinel: a stored None
        with _CACHE_LOCK:
            entry = _CACHE.get(query_norm)
        if entry is not None and entry[1] is None and time.time() - entry[0] < 60:
            return None
        if cached is not None:
            return cached

    result: Optional[dict] = None
    if not _cb_is_open():
        result = _geocode_nominatim(query)
    if result is None:
        result = _geocode_photon(query)

    _cache_put(query_norm, result)
    return result
