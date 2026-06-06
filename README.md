# Spotter Trip Planner

A full-stack trip planner that takes a driver's current location, pickup, dropoff, and remaining 70-hour cycle, then produces an FMCSA-compliant route plus one or more filled-in **Driver's Daily Log** sheets — the same paper form every US commercial driver fills out by hand.

![Cross-country trip — Los Angeles to Chicago](docs/screenshots/01-cross-country-hero.png)

> Live demo: **[frontend-three-sage-11.vercel.app](https://frontend-three-sage-11.vercel.app/)**
> API: **[spotteraiassessment.onrender.com/api/health/](https://spotteraiassessment.onrender.com/api/health/)**
> Admin: **[frontend-three-sage-11.vercel.app/#/admin](https://frontend-three-sage-11.vercel.app/#/admin)** — login `admin / admin`

---

## What it does

| Input | Output |
|---|---|
| Current location, pickup, dropoff (free-text cities) | OSRM driving route on a Leaflet map |
| Current cycle used (0-70 hr) | One or more daily log sheets (multi-day for long trips) |
| Use sleeper berth? (default on) | Sleeper-berth 10-hr reset / 30-min break variant |
| Optional: pick a saved driver profile | Real per-day on-duty history → exact (non-approximate) recap math |
| | HOS-compliant timeline (driving + on-duty + sleeper + off-duty) |
| | Filled-in SVG daily log matching the canonical FMCSA paper form |
| | Per-day deadhead vs loaded mileage split |
| | Fuel, break, and rest stops extracted on the map and in a list |
| | Vector PDF export (jsPDF) — one page per daily log |
| | Admin dashboard (`/#/admin`) with token auth, KPIs, sparkline, top routes, cycle-usage histogram, recent-trips table |

The most distinctive output is the daily log: a 900×940 SVG that matches the canonical FMCSA paper form cell-for-cell, including the recap table (A./B./C./D./E./F. cells for the 70hr/8day and 60hr/7day driver schedules).

![Daily log close-up — recap table visible](docs/screenshots/02-daily-log-recap.png)

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Django 6.0 + Django REST Framework 3.17 + gunicorn |
| Auth | DRF `TokenAuthentication`, custom `IsAdmin` permission, OneToOne `User ↔ Driver` |
| HOS engine | Pure Python (no numpy, no external deps) |
| Geocoding | Nominatim (OSM) → Photon (Komoot) fallback, in-memory LRU + circuit breaker |
| Routing | OSRM public demo server |
| Frontend | Vite + React 19 + TypeScript + Tailwind 4 |
| Map | Leaflet 1.9 + OpenStreetMap tiles |
| PDF | jsPDF (vector) |

No paid services, no API keys, no secrets. Runs on Render + Vercel free tiers.

---

## HOS rules implemented (FMCSA-HOS-395, April 2022)

11-hour driving limit, 14-hour on-duty window, 30-minute break after 8 cumulative driving hours, 10-hour reset (off-duty or sleeper berth), 70-hour / 8-day rolling cycle cap, 34-hour restart, fuel stop every 1,000 mi, 1-hr on-duty for pickup + dropoff, 0.25-hr pre- and post-trip inspection, 24-hour invariant (every log sums to exactly 24 hr), midnight day boundary, per-leg mileage split (deadhead vs loaded).

Assumptions per spec: property-carrying CMV, 70hr/8day schedule, no adverse conditions, 55 mph average. See **[docs/architecture.md](docs/architecture.md)** for the engine design and recap math.

---

## Architecture

```
                 ┌─────────────────────┐
   React form ──▶│  POST /api/trip/   │──▶ OSRM (route)
                 │  (DRF view)         │──▶ Nominatim/Photon (3× geocode)
                 │                     │──▶ hos_engine.generate_trip
                 │                     │──▶ compute_recap_with_history
                 │                     │──▶ persist Trip + DayHistory
                 └──────────┬──────────┘
                           ▼
              JSON: { stops, rest_stops, route, days[i] {events, totals, status_quarters, recap, deadhead_mi, loaded_mi, on_duty_today} }
                           │
                           ▼
                ┌─────────────────────┐
                │  React UI  (/#/)    │  trip planner
                │  React UI  (/#/admin)│ token auth + dashboard
                └─────────────────────┘
```

The HOS engine is a pure-Python event simulator. Given a `TripInput` (three `Point`s, cycle used, speed, start time), it walks the timeline and emits a list of `Event`s with status, duration, location, and remark. `group_by_day` partitions them into `DayLog`s, and `compute_recap_with_history` attaches the FMCSA-form recap using real per-day on-duty history when a driver is supplied (or the approximate version otherwise).

---

## Project structure

```
backend/
├── hos_engine.py            ← pure-Python HOS engine
├── geocoding.py             ← Nominatim + Photon, LRU + circuit breaker
├── routing.py               ← OSRM client
├── spotter_backend/         ← Django project (settings, urls, wsgi)
├── trip/                    ← views, serializers, models, migrations, seed_demo
└── tests/                   ← pytest tests (mocked + live)

frontend/
├── src/components/          ← TripForm, RouteMap, DailyLog, AdminPage
├── src/lib/                 ← api, types, pdfExport
└── tests/e2e/               ← Playwright tests

docs/                        ← architecture, video-script, screenshots, sample-pdfs
.github/workflows/ci.yml     ← CI: pytest + Playwright
run-all-tests.sh             ← local dual-suite runner
LICENSE                      ← ISC
```

---

## Testing

165 tests across three suites, all green in CI.

| Suite | Runner | Count | What it covers |
|---|---|---|---|
| HOS engine | `unittest` | 30 | Every FMCSA rule, 24-hr invariant, edge cases, recap math, mileage split, history-aware recap |
| Backend API | `pytest` | 108 | Trip planning, driver CRUD, history, auth, admin RBAC, metrics math, trip persistence, mocked + live network |
| Frontend e2e | Playwright | 27 | Form, presets, submit flow, multi-day results, rest stops, recap table, PDF download, admin login + dashboard, RBAC enforcement |

```bash
cd backend
python manage.py seed_demo                  # admin/admin + tino/12345 + 8 days history
python -m pytest tests/ -m "not live"       # ~3s, 108 tests
python -m pytest tests/                     # includes live OSRM/Nominatim (slow)

cd ../frontend
npx playwright test                          # 27 tests, ~2 min
```

CI: GitHub Actions runs both suites on every push — see `.github/workflows/ci.yml`.

---

## Running locally

```bash
# Backend
cd backend
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8001   # http://127.0.0.1:8001

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                       # http://127.0.0.1:5173 (proxies /api to :8001)
```

---

## API

### `POST /api/trip/`
```json
{
  "current_location": "New York, NY",
  "pickup_location": "Philadelphia, PA",
  "dropoff_location": "Baltimore, MD",
  "current_cycle_used_hrs": 0,
  "use_sleeper_berth": true,
  "driver_id": 1
}
```

With `driver_id`, each trip day's on-duty is appended to the driver's `DayHistory` so subsequent calls produce an exact (non-approximate) recap.

### Auth + Admin
| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/auth/{register,login,logout,me}/` | POST/GET | varies | User lifecycle + token issuance |
| `/api/admin/metrics/` | GET | staff | KPIs, 30-day sparkline, top routes, cycle histogram, top drivers |
| `/api/admin/trips/?page=N&page_size=M` | GET | staff | Paginated recent trips |

---

## Deploy

- **Backend** → [Render](https://render.com) Web Service
- **Frontend** → [Vercel](https://vercel.com) static site, env `VITE_API_URL` points at Render

Live URLs at the top of this README. Admin demo login: `admin / admin`.
