# Architecture

## Big picture

The system is a small but complete web app: a single DRF endpoint turns four strings and a number into a multi-day HOS plan + route geometry + filled-in log sheets. The interesting work is in the **HOS engine**, which is a pure-Python event simulator. Everything else is plumbing.

```
                          Internet
                             │
                             ▼
   ┌──────────────────────────────────────────────────────┐
   │  Vercel (static SPA)         Render (Django + DRF)   │
   │  ┌─────────────────┐         ┌─────────────────────┐ │
   │  │ React 19 + Vite │ ──────▶ │ POST /api/trip/     │ │
   │  │  ├─ TripForm    │  JSON   │  ├─ geocoding       │ │
   │  │  ├─ RouteMap    │ ◀────── │  ├─ routing (OSRM)  │ │
   │  │  ├─ DailyLog    │         │  ├─ hos_engine      │ │
   │  │  └─ jsPDF       │         │  └─ compute_recap   │ │
   │  └─────────────────┘         └─────────────────────┘ │
   │                                       │              │
   └───────────────────────────────────────┼──────────────┘
                                           │
                       ┌───────────────────┴────────────────┐
                       ▼                                    ▼
              ┌─────────────────┐                ┌──────────────────┐
              │  Nominatim/Photon │                │  OSRM demo server │
              │  (geocode)         │                │  (route geometry) │
              └─────────────────┘                └──────────────────┘
```

## The HOS engine

`backend/hos_engine.py` — ~400 lines, zero external deps, 20 unit tests.

### Data model

```
TripInput ──┬── current: Point
            ├── pickup: Point
            ├── dropoff: Point
            ├── cycle_used_hrs: float
            ├── avg_speed_mph: float (default 55)
            ├── start_time: datetime
            └── use_sleeper_berth: bool

Point     — lat, lon, label
Event     — start, duration_h, status (0/1/2/3), location, remark, cumulative_miles
DayLog    — date, events[], total_miles, recap{}
State     — now, window_start, drive_today, drive_since_break,
             on_duty_today, cycle_used, total_miles, miles_since_fuel, last_loc

compute_recap(days, cycle_used_hrs) — mutates each DayLog.recap dict
```

### The drive loop

The core is `drive_leg(events, state, leg)`, a `while miles_remaining > 0` loop that walks the timeline one chunk at a time. At each step it checks all the limits in priority order:

1. **Cycle cap** (`cycle_used >= 70`) → take a 34-hr restart, continue
2. **30-min break** (`drive_since_break >= 8`) → take it, continue
3. **Fuel stop** (`miles_since_fuel >= 1000`) → take it at an interpolated point, continue
4. **11-hr drive / 14-hr window cap** → take a 10-hr reset (off-duty or sleeper), continue
5. Otherwise: drive for the smallest of `(11 - drive_today, 8 - drive_since_break, 14 - window, miles_remaining / speed, miles_to_fuel / speed)` hours

Each iteration either consumes a required stop *or* drives a chunk. The loop terminates when the leg is complete.

This priority order matters. A 30-min break is preferred over a fueling stop is preferred over a 10-hr reset, because the break is a minor disruption and the reset puts the driver off-duty for 10 hours.

### The day log

`generate_trip(trip)` emits a flat list of events:

```
0. Pre-shift off-duty (from midnight to start_time, if any)
1. Pre-trip inspection (0.25 hr on-duty)         ← 14-hr window starts here
2. Drive current → pickup
3. Pickup (1 hr on-duty)
4. Drive pickup → dropoff
5. Dropoff (1 hr on-duty)
6. Post-trip inspection (0.25 hr on-duty)
7. Either 10-hr reset (if 11/14 cap hit) or fill to midnight as off-duty
```

Then `group_by_day(events)` partitions by date. `compute_recap(days, cycle_used_hrs)` attaches the FMCSA recap to each day.

### The 24-hour invariant

Every `DayLog` has a `status_quarters` property: 96 quarter-hour slots, one per 15-min slot in a day. The UI fills these with the duty status at each slot and the graph on the paper form reads them. The `totals()` method counts the quarters per status and returns hours.

The invariant: `off_duty + sleeper + driving + on_duty = 24.0` for every day. This is enforced by a unit test and checked in every API test. It's the most basic correctness property: if the log doesn't sum to 24 hours, it's wrong.

The invariant holds because:
- `group_by_day` partitions events with no gaps
- The pre-shift off-duty event fills the morning of the first day
- `fill_to_midnight` fills the evening of every day the engine touches
- `take_10hr_reset` calls `fill_to_midnight` before adding the 10-hr off-duty/sleeper

### The recap table

The recap table on the FMCSA paper form has six cells across two driver schedules:

| 70 hr / 8 day | 60 hr / 7 day |
|---|---|
| A. Total hrs on duty last 7 days | C. Total hrs on duty last 5 days |
| B. Available tomorrow (70 - A) | D. Total hrs on duty last 7 days |
| F. Total hrs on duty last 8 days | E. Available tomorrow (60 - C) |

The math:

```
F = cycle_used_hrs + sum(day_on_duty for day in days)
A = F * 7/8   (assumes prior on-duty was evenly spread)
B = 70 - A
C = F * 5/8
D = C + day_on_duty  (last 2 days of the 7-day window)
E = 60 - C
```

These are flagged `approximate: true` because we only have the user's *total* `cycle_used_hrs` — not the per-day breakdown. A real product would track 8 days of driver history.

### The `34-hr restart` flag

A `took_34h_restart: bool` on each day's recap indicates that the engine took a 34-hr restart *on that day*. Computed by looking for any event with `"34-hr"` in its remark. The UI uses this to render an amber banner on the recap table.

## The API

`POST /api/trip/` is the only non-trivial endpoint. ~120 lines.

1. Validate request body via `TripRequestSerializer`
2. Geocode all three locations (cached, circuit-breaker-protected)
3. Fetch OSRM route for the three-point path
4. Build `TripInput`
5. Call `generate_trip(trip)` → `List[DayLog]`
6. Serialize the response: stops, rest_stops, route, days (with status_quarters and recap), warnings
7. Return 200 or 400/502 with a specific error

The `rest_stops` extraction walks every event in every day, classifies by remark text, dedupes by `(lat, lon, kind)`, and filters out the three main stops.

## The frontend

Three significant components:

- **`TripForm.tsx`** — controlled form with 4 location inputs + cycle hours + sleeper toggle + 4 quick presets (short, long, cross-country, 70hr at limit). All inputs have proper `htmlFor`/`id` bindings.
- **`RouteMap.tsx`** — Leaflet map with the route polyline from OSRM, the three main stop markers, and rest-stop markers (fuel/break/rest) with a legend.
- **`DailyLog.tsx`** — the showcase. 900×940 SVG that draws the canonical FMCSA paper form cell-for-cell: title bar, From/To, Total Miles, Name of Carrier, Main Office, Original/Duplicates banner, Truck/Trailer, Home Terminal, 24-hr graph with 15-min subdivisions, Total Hours column, Remarks (left 2/3), Shipping Documents (right 1/3), italic captions, and the full Recap table.

State management is React 19's `useState` + prop drilling — no Redux, no Zustand. The whole thing is small enough that prop drilling is clearer than introducing a state library.

## Why these design choices

### Pure-Python HOS engine
No numpy, no pandas, no sympy. Just `math` and `datetime`. The HOS rules are simple enough that scalar math reads better than vector math, and the test suite runs in milliseconds. The only "data structure" is the 96-element `status_quarters` array, which doesn't justify a heavy dep.

### Free public services
- **OSRM** demo server: zero-key, zero-cost, generous rate limits
- **Nominatim** for geocoding: zero-key, but known to 429-block shared-IP hosting providers
- **Photon** (Komoot) as fallback: same OSM data, no rate limit on Render

The geocoding module has a 1-hour in-memory LRU cache and a 2-strikes-then-300s circuit breaker for Nominatim. After two consecutive 429s, all calls go straight to Photon. This was added after seeing the deployed backend hit Nominatim rate limits constantly.

### jsPDF over html2canvas
Vector PDF. The same `DailyLog.tsx` layout is mirrored in `pdfExport.ts` as a series of `doc.text`/`doc.rect` calls. Output is selectable text, scales infinitely, and is ~50 KB per day.

### One endpoint, one view
The trip-planning surface is one POST; auth + admin are separate. This keeps the happy path trivial. The admin / driver / history surface uses Token auth + role checks so a non-admin driver token can be rejected at the permission layer without custom view logic.

## Why event list, not FSM library

A "real" HOS engine is often modeled as a finite state machine with states like `OFF_DUTY → ON_DUTY → DRIVING → OFF_DUTY` and explicit transitions triggered by the clock and accumulated hours. Libraries like `transitions` or `sismic` make this declarative. We deliberately did **not** go that way, for these reasons:

1. **The 96 quarter-hour bucketing already gives us a state machine.** `DayLog.status_quarters` is a length-96 array of duty-status codes; a state transition is just `status_quarters[i] != status_quarters[i-1]`. No additional data structure needed.
2. **Rules overlap in ways FSMs handle awkwardly.** The 11-hour driving limit counts *cumulative driving*, the 14-hour window counts *cumulative on-duty*, the 30-min break fires after 8 hr driving — these are all *quantitative* triggers on running totals, not state-symbol transitions. An FSM with `if counter > X` guards on every transition is just a state diagram that re-implements counters.
3. **The list is a "trace" the user can read.** Drivers, auditors, and recruiters all expect to see "you drove 9.5 hr, took a 30-min break, drove another 1.5 hr, then went off-duty" as a sequence of events with timestamps. That's exactly what we emit. An FSM with self-loops is harder to narrate.
4. **The pure-Python implementation is testable in 30 unit tests** without any framework indirection. Adding a transitions library would shift coverage from "the rule is right" to "we configured the library correctly".

The pragmatic decision: the engine's data model *is* a state machine (current state, event-driven transitions) but the implementation is a straight-line simulator over that model. Adding a library would couple us to its API for marginal benefit.

## What I'd do differently with more time

- Map clustering for very long trips
- Snapshot tests on the SVG output of `DailyLog.tsx`
- Postgres + persistent disk on Render so driver records survive redeploys
- WebSocket push for live HOS-clock when the planner is left open
- ELD-format import for `DayHistory` (`.eld` files) so the recap math is sourced from real records, not manual entry
