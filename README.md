# Spotter Trip Planner — Full-Stack Coding Assessment

A Django + React web app that takes a trip's start/pickup/dropoff locations plus the driver's current 70-hour cycle usage, and produces:

1. An interactive **route map** with markers and the OSRM-rendered driving path
2. One or more **HOS-compliant Driver's Daily Log** sheets (FMCSA format) drawn as vector SVG, exact replica of the blank paper log
3. A **multi-page PDF export** of the summary + every daily log sheet

Built for the Spotter AI Full-Stack Developer coding assessment.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.0, Django REST Framework 3.17, django-cors-headers, gunicorn |
| HOS engine | Pure Python (no external deps) — 16 unit tests passing |
| Geocoding | Nominatim (OpenStreetMap, free, no key) |
| Routing | OSRM public demo server (free, no key) |
| Frontend | Vite + React 19 + TypeScript + Tailwind CSS 4 |
| Map | Leaflet 1.9 + react-leaflet + OpenStreetMap tiles |
| PDF export | jsPDF (vector) |
| Tests | `unittest` (Python) |

No paid services, no API keys required. Runs on free tiers of Render + Vercel.

---

## HOS rules implemented (per FMCSA-HOS-395, April 2022)

- **11-hour driving limit** per shift
- **14-hour driving window** starting at first on-duty
- **30-minute break** after 8 cumulative driving hours (configurable: off-duty or sleeper berth)
- **10-hour reset** between shifts (configurable: off-duty or sleeper berth)
- **70-hour / 8-day rolling** cycle cap with **34-hour restart** to reset
- **Fueling stop** every 1,000 mi (0.5 hr on-duty not driving)
- **1 hour** on-duty for pickup + **1 hour** on-duty for dropoff
- **Pre-trip + post-trip inspection** (0.25 hr each, on-duty)
- **Sleeper berth provision** — used for 10-hr reset and 30-min break when toggled on
- **24-hour log invariant** — every daily log sums to exactly 24 hours

Assumptions (per spec):
- Property-carrying CMV
- 70hr/8day schedule
- No adverse driving conditions
- Average speed 55 mph

---

## Project structure

```
assessments/spotterAI/
├── backend/
│   ├── manage.py
│   ├── hos_engine.py          # Pure-Python HOS logic (16 unit tests)
│   ├── test_hos_engine.py     # unittest suite
│   ├── geocoding.py           # Nominatim client
│   ├── routing.py             # OSRM client
│   ├── spotter_backend/       # Django project (settings, urls, wsgi)
│   ├── trip/                  # Django app (views, serializers, urls)
│   ├── requirements.txt
│   ├── runtime.txt
│   ├── Procfile               # Render entry point
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── TripForm.tsx
│   │   │   ├── RouteMap.tsx
│   │   │   └── DailyLog.tsx
│   │   └── lib/
│   │       ├── api.ts
│   │       ├── types.ts
│   │       └── pdfExport.ts
│   ├── vite.config.ts
│   ├── vercel.json
│   └── package.json
└── README.md
```

---

## Run locally

### Backend

```bash
cd backend
python -m pip install -r requirements.txt
python manage.py runserver
```

Server runs on `http://127.0.0.1:8001`.

Run unit tests:

```bash
python test_hos_engine.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dev server on `http://127.0.0.1:5173` (proxies `/api/*` to Django).

For prod build:

```bash
npm run build
# Output in dist/
```

---

## API

### `GET /api/health/`

Returns `{ok: true, service: "spotter-trip-planner"}`.

### `POST /api/trip/`

**Request body:**

```json
{
  "current_location": "New York, NY",
  "pickup_location": "Philadelphia, PA",
  "dropoff_location": "Baltimore, MD",
  "current_cycle_used_hrs": 0,
  "use_sleeper_berth": true
}
```

**Response:**

```json
{
  "ok": true,
  "stops": [{"lat": 40.71, "lon": -74.0, "label": "New York, NY", "kind": "current"}, ...],
  "route": {
    "distance_mi": 192.5,
    "duration_h": 3.84,
    "geometry": {"type": "LineString", "coordinates": [[lon, lat], ...]}
  },
  "total_distance_mi": 192.5,
  "days": [
    {
      "date": "2026-06-05",
      "total_miles": 170.0,
      "events": [
        {"start": "2026-06-05T00:00:00", "duration_h": 6.0, "status": 0,
         "status_name": "Off Duty", "location": {...}, "remark": "Off duty (home terminal)", ...},
        ...
      ],
      "totals": {"off_duty": 18.5, "sleeper": 0.0, "driving": 3.0, "on_duty": 2.5},
      "status_quarters": [0, 0, 0, 0, 0, 0, ...]  // 96 quarter-hour buckets
    }
  ],
  "cycle_used_hrs": 0,
  "warnings": []
}
```

---

## Deploy

### Backend (Render)

1. Push the repo to GitHub.
2. On Render, create a new **Web Service** pointing at the `backend/` directory.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn spotter_backend.wsgi:application --bind 0.0.0.0:$PORT`
5. Set env: `ALLOWED_HOSTS=*`, `DEBUG=False`, `PYTHON_VERSION=3.14.2`

### Frontend (Vercel)

1. Import the GitHub repo into Vercel.
2. Set **Root Directory** to `frontend`.
3. Add env: `VITE_API_URL=https://<your-render-app>.onrender.com`
4. Build command: `npm run build` (Vercel auto-detects)
5. Output: `dist/`

---

## Test scenarios verified

| Scenario | Result |
|---|---|
| Short trip (170 mi, NYC→Philly→Baltimore) | 1 day, 3.0 hr drive, 1 page log |
| Long trip (2126 mi, LA→Albuquerque→Chicago) | 3 days, 605 mi/day, sleeper-berth reset, 30-min break, fueling stops |
| Trip with cycle near 70-hr cap | 34-hr restart inserted |
| Sleeper berth on vs off | Toggle respected — sleeper berth events appear/disappear in the log |
| Trip starting at 2 PM | 14 hr of pre-shift off-duty fills the day |
| 24-hour invariant | Every day log sums to exactly 24 hr |

---

## License

ISC. Built for the Spotter AI coding assessment.
