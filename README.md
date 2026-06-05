# Spotter Trip Planner

A full-stack trip planner that takes a driver's current location, pickup, dropoff, and remaining 70-hour cycle, then produces an FMCSA-compliant route plus one or more filled-in **Driver's Daily Log** sheets — the same paper form every US commercial driver fills out by hand.

![Cross-country trip — Los Angeles to Chicago](docs/screenshots/01-cross-country-hero.png)

> Live demo: **[frontend-three-sage-11.vercel.app](https://frontend-three-sage-11.vercel.app/)**
> API: **[spotteraiassessment.onrender.com/api/health/](https://spotteraiassessment.onrender.com/api/health/)**

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
| HOS engine | Pure Python (no numpy, no external deps) — **30 unit tests** |
| Geocoding | Nominatim (OSM) → Photon (Komoot) fallback, in-memory LRU + circuit breaker |
| Routing | OSRM public demo server |
| Frontend | Vite + React 19 + TypeScript + Tailwind 4 |
| Map | Leaflet 1.9 + OpenStreetMap tiles |
| PDF | jsPDF (vector) |
| Tests | `unittest` (engine) + `pytest` (backend) + Playwright (e2e) — **165 total** |

No paid services, no API keys, no secrets. Runs on Render + Vercel free tiers.

---

## HOS rules implemented (FMCSA-HOS-395, April 2022)

- **11-hour driving limit** per shift
- **14-hour on-duty window** starting at first on-duty
- **30-minute break** after 8 cumulative driving hours
- **10-hour reset** between shifts (off-duty *or* sleeper berth)
- **70-hour / 8-day rolling** cycle cap
- **34-hour restart** to reset the 70/8 clock
- **Fueling stop** every 1,000 mi
- **1 hr on-duty** for pickup + dropoff
- **Pre-trip + post-trip inspection** (0.25 hr each)
- **24-hour invariant** — every daily log sums to exactly 24 hr
- **Midnight day boundary** — pre-shift off-duty fills the morning of the first day
- **Per-leg mileage split** — deadhead (current→pickup) vs loaded (pickup→dropoff) tagged on every DRIVING event

Assumptions per spec: property-carrying CMV, 70hr/8day schedule, no adverse conditions, 55 mph average.

---

## Architecture

```
                 ┌─────────────────────┐
   React form ──▶│  POST /api/trip/   │──▶ OSRM (route) ──▶ geometry
                 │  (DRF view)         │
                 │                     │──▶ Nominatim/Photon (3× geocode)
                 │                     │──▶ hos_engine.generate_trip
                 │                     │     (pure-Python HOS simulator)
                 │                     │──▶ compute_recap_with_history (real
                 │                     │     per-day recap when driver_id given)
                 │                     │──▶ persist Trip + DayHistory
                 └──────────┬──────────┘
                           ▼
              JSON: { stops, rest_stops, route, days[i] {events, totals, status_quarters, recap, deadhead_mi, loaded_mi, on_duty_today} }
                           │
                           ▼
                ┌─────────────────────┐
                │  React UI           │
                │  ├─ TripForm        │  ← /#/  hash route
                │  ├─ RouteMap        │
                │  ├─ Stops & Rests   │
                │  ├─ DailyLog (SVG)  │
                │  └─ jsPDF export    │
                │                     │
                │  /#/admin           │
                │  ├─ Login (token)   │
                │  ├─ KPI cards       │
                │  ├─ 30-day sparkline│
                │  ├─ Top routes      │
                │  ├─ Cycle histogram │
                │  └─ Recent trips    │
                └─────────────────────┘

   Token auth:    POST /api/auth/login/    → { token, user }
                  GET  /api/auth/me/       (Token: ...)
                  GET  /api/admin/metrics/ (Token: ..., staff only)
                  GET  /api/admin/trips/   (Token: ..., staff only)
```

The HOS engine is the heart of the system. It's a pure-Python event simulator: given a `TripInput` (three `Point`s, cycle used, speed, start time), it walks the timeline and emits a list of `Event`s with status, duration, location, and remark. Then `group_by_day` partitions them into `DayLog`s, and `compute_recap_with_history` attaches the FMCSA-form recap using real per-day on-duty history when a driver is supplied (or the approximate version otherwise).

See **[docs/architecture.md](docs/architecture.md)** for the full write-up.

---

## Project structure

```
assessments/spotterAI/
├── backend/
│   ├── hos_engine.py            ← pure-Python HOS engine (30 unit tests)
│   ├── test_hos_engine.py       ← 30 HOS engine unit tests
│   ├── geocoding.py             ← Nominatim + Photon, LRU cache + circuit breaker
│   ├── routing.py               ← OSRM client
│   ├── spotter_backend/         ← Django project (settings, urls, wsgi)
│   ├── trip/
│   │   ├── models.py            ← Driver, DayHistory, Trip (+ User OneToOne)
│   │   ├── views.py             ← trip plan + driver CRUD
│   │   ├── auth_views.py        ← register, login, logout, me
│   │   ├── admin_views.py       ← metrics + trips list (staff only)
│   │   ├── serializers.py
│   │   ├── permissions.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── migrations/
│   │   └── management/commands/seed_demo.py
│   ├── tests/                   ← 108 pytest tests (mocked + live)
│   ├── requirements.txt
│   ├── Procfile
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── App.tsx              ← hash router (/#/ vs /#/admin)
│   │   ├── components/
│   │   │   ├── TripForm.tsx
│   │   │   ├── RouteMap.tsx
│   │   │   ├── DailyLog.tsx     ← 900×940 SVG paper-form replica
│   │   │   └── AdminPage.tsx    ← login + dashboard
│   │   └── lib/
│   │       ├── api.ts           ← planTrip + auth + admin helpers
│   │       ├── types.ts
│   │       └── pdfExport.ts
│   ├── tests/e2e/               ← 27 Playwright tests (incl. admin flow)
│   └── scripts/
│       └── take-fresh-shots.ts
├── docs/
│   ├── architecture.md
│   ├── video-script.md
│   ├── references/
│   ├── screenshots/
│   └── sample-pdfs/
├── .github/workflows/ci.yml
├── run-all-tests.sh
├── LICENSE                      ← ISC
└── README.md
```

---

## Testing

**165 tests** across three suites, all green in CI.

| Suite | Runner | Count | What it covers |
|---|---|---|---|
| HOS engine | `unittest` | 30 | Pure-Python engine: every FMCSA rule, 24-hr invariant, edge cases, recap math, mileage split, history-aware recap |
| Backend API | `pytest` | 108 | DRF endpoints: trip planning, driver CRUD, history, auth, admin RBAC, metrics math, trip persistence, mocked + live network |
| Frontend e2e | Playwright | 27 | Form, presets, full submit flow, multi-day results, rest stops, recap table, PDF download, admin login + dashboard, RBAC enforcement |

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

### Backend
```bash
cd backend
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8001   # http://127.0.0.1:8001
```

### Frontend
```bash
cd frontend
npm install
npm run dev                       # http://127.0.0.1:5173 (proxies /api to :8001)
```

### Both at once
```bash
./run-all-tests.sh                # boots both, runs both test suites
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

Returns the full plan including the route geometry, the day-by-day log with 96 quarter-hour status buckets per day, the per-leg mileage split, and the recap table for the FMCSA form. With `driver_id`, each trip day's on-duty is appended to the driver's `DayHistory` so subsequent calls produce an exact (non-approximate) recap.

### Auth
| Endpoint | Method | Auth | Purpose |
|---|---|---|---|
| `/api/auth/register/` | POST | — | Create a user + auto-create a driver profile |
| `/api/auth/login/` | POST | — | Return `{ token, user }` |
| `/api/auth/logout/` | POST | Token | Delete the caller's token |
| `/api/auth/me/` | GET | Token | Return the current user |

### Admin (staff only)
| Endpoint | Method | Purpose |
|---|---|---|
| `/api/admin/metrics/` | GET | KPIs (trips, miles, on-duty), 30-day sparkline, top routes, cycle-usage histogram, top drivers |
| `/api/admin/trips/` | GET | Paginated recent trips, `?page=N&page_size=M` |

---

## Deploy

Both free-tier, no secrets.

- **Backend** → [Render](https://render.com) Web Service, `gunicorn spotter_backend.wsgi:application`
- **Frontend** → [Vercel](https://vercel.com) static site, `npm run build`, env `VITE_API_URL` points at Render

Live URLs at the top of this README. Admin demo login: **admin / admin** (Render) or `tino / 12345` (driver account).

---

## What I'd add with more time

- **Map clustering for rest stops** — Leaflet supercluster for very long trips with many breaks.
- **Frontend driver selector** — dropdown of saved drivers in `TripForm`, auto-fills cycle, persists selection.
- **Per-day mileage display in the log + PDF** — the data is computed; just needs UI surfacing.
- **Postgres + persistent disk on Render** so driver records survive redeploys.
- **WebSocket push for live HOS-clock** when the planner is left open.
- **ELD-format import** for `DayHistory` (`.eld` files) so the recap math is sourced from real records, not manual entry.

---

Built for the Spotter AI Full-Stack Developer coding assessment. ~20 hours of work, 4 days.
