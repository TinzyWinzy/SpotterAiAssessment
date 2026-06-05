# Video Walkthrough Script — 3 minutes

**Target pace**: ~140 words per minute. Read the VO aloud; the B-roll and on-screen text do the rest of the work.

**Format**: screen recording with voiceover. No face-cam needed.

**Goal**: in 3 minutes, show the working app, name the interesting engineering, prove it's a real product, and end with the URLs.

---

## 0:00 – 0:20  ·  HOOK  (20 sec)

| | |
|---|---|
| **VO** | "Truck drivers in the US have to log every minute of their day — driving, on-duty, sleeper, off-duty — on a paper form, by hand, every day. I built a trip planner that does it for them." |
| **B-roll** | `docs/screenshots/01-cross-country-hero.png` (the full cross-country flow: form + summary + map + 3 daily log sheets) |
| **On-screen text** | Lower-left: "Spotter Trip Planner — HOS-compliant route + daily log generator" |
| **Energy** | Calm, confident. The image does the work. Don't oversell. |

---

## 0:20 – 1:00  ·  LIVE DEMO  (40 sec)

| | |
|---|---|
| **VO** | "Here's the live app. I'm going to plan a 2,126-mile cross-country run from Los Angeles to Chicago with zero cycle used. Click Cross-country, click Plan Trip." |
| **B-roll** | Screen-record the deployed app. Click the **Cross-country** preset (already on the form). Click **Plan Trip**. The page renders the summary, map, stops list, and 3 daily log sheets. |
| **On-screen text** | (none — let the UI speak) |
| **Energy** | Confident, narrative. "And there it is — three days, six rest stops, three log sheets, ready to print." |
| **Note** | The cross-country preset takes ~10 sec to compute on Render's free tier (cold start). That's fine. Use the pause to underline the next sentence: "The whole pipeline is geocoding → OSRM routing → HOS simulation → SVG render, end to end." |

---

## 1:00 – 1:40  ·  TECH HIGHLIGHT 1: HOS ENGINE  (40 sec)

| | |
|---|---|
| **VO** | "The interesting part is the engine. It's a pure-Python event simulator — no numpy, no external deps. It walks the timeline one chunk at a time and checks every FMCSA rule in priority order: 11-hour drive cap, 14-hour window, 30-minute break, fueling every 1,000 miles, and the 70-hour 8-day cycle with a 34-hour restart." |
| **B-roll** | Cut to `hos_engine.py` open in an editor. Scroll slowly to the `drive_leg` function. Highlight the `while miles_remaining > 0:` loop. |
| **On-screen text** | Right-side overlay, monospace:<br>`11 hr drive cap`<br>`14 hr on-duty window`<br>`30 min break after 8 hr drive`<br>`70 hr / 8 day cycle`<br>`34 hr restart` |
| **Energy** | Engineer-explaining-engineer. Don't read the rules — name them, point at the loop, move on. |

---

## 1:40 – 2:10  ·  TECH HIGHLIGHT 2: RECAP TABLE  (30 sec)

| | |
|---|---|
| **VO** | "Each day gets a recap table that matches the canonical FMCSA paper form — six cells, A through F, for both the 70-hour-8-day and 60-hour-7-day driver schedules. It's drawn as vector SVG, and the PDF export uses the same layout — so the printed log is byte-for-byte the same as the on-screen log." |
| **B-roll** | Scroll to Day 1 or Day 2 in the demo, zoom into the recap section. Numbers visible: A 9.84, B 60.16, F 11.25, C 7.03, D 18.28, E 52.97. |
| **On-screen text** | Lower-right: "Vector SVG + vector PDF · mirrors the paper form cell-for-cell" |
| **Energy** | Specific. The numbers on screen are the proof — point at F=11.25, say "that's the 8-day total including the cycle used," move on. |

---

## 2:10 – 2:40  ·  TECH HIGHLIGHT 3: QUALITY SIGNALS  (30 sec)

| | |
|---|---|
| **VO** | "One hundred and fifteen tests — twenty on the engine, seventy-four on the API, twenty-one end-to-end in Playwright. Geocoding has a circuit breaker because Render's shared IP gets rate-limited by Nominatim. The whole thing runs on free tiers, no API keys." |
| **B-roll** | Cut to `docs/architecture.md` (or the test count line of the README). Then to `geocoding.py` showing the circuit breaker constants. |
| **On-screen text** | Stamp graphic: "115 tests · 0 API keys · free tier" |
| **Energy** | Quick hits, three sentences, three numbers. Don't dwell. |

---

## 2:40 – 3:00  ·  CLOSE  (20 sec)

| | |
|---|---|
| **VO** | "Live on Vercel, source on GitHub. Thanks for watching." |
| **B-roll** | Final shot: the live app on the cross-country preset, with the URLs overlaid. |
| **On-screen text** | Centered, large:<br>`frontend-three-sage-11.vercel.app`<br>`github.com/TinzyWinzy/SpotterAiAssessment` |
| **Energy** | Out. No "any questions?" — that eats time. End clean. |

---

## Recording tips

- **Resolution**: 1920×1080 minimum. Vercel at 1400 wide looks soft at 1080p; if you can, set the browser zoom to 110% in DevTools.
- **Audio**: quiet room, USB headset or close-mic. No background music — distracts from the technical content.
- **Pace**: ~140 wpm. If you finish early, the rule is "stop at 2:55, not stretch to 3:00." Better to leave 5 sec of silence than to talk past the end.
- **Retake strategy**: the Playwright harness in `frontend/scripts/record-demo.ts` records the full demo as an MP4. Re-record the screen portion as many times as you want; the VO is a separate audio track — record them, drop them in a free editor (DaVinci Resolve, Kdenlive, CapCut), align to the B-roll timestamps above, and ship.
- **No face-cam is fine.** Screen + voice is the dominant format for tech-assesment videos and is less risky than talking to camera in a noisy room.

## Word count

The VO total is 374 words. At 140 wpm that's ~2:40 spoken, plus ~20 sec of pause for the API call to land. Right at the 3-min cap.
