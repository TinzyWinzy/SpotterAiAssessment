import { useCallback, useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { RouteInfo, StopMarker, TripPosition } from "../lib/types";
import { Maximize2, Minimize2, MapPin, Navigation } from "lucide-react";

interface Props {
  route: RouteInfo;
  stops: StopMarker[];
  restStops: never[];
  positions?: TripPosition[];
}

const STOP_COLORS: Record<StopMarker["kind"], string> = {
  origin: "#0e7c86",
  waypoint: "#f59e0b",
  destination: "#dc2626",
};

const STOP_LABELS: Record<StopMarker["kind"], string> = {
  origin: "Start",
  waypoint: "Via",
  destination: "Dest",
};

const STOP_RING: Record<StopMarker["kind"], string> = {
  origin: "#ffffff",
  waypoint: "#ffffff",
  destination: "#ffffff",
};

const DEFAULT_CENTER: L.LatLngExpression = [-19.0, 29.0];
const DEFAULT_ZOOM = 5;

const COUNTRY_FLAGS: Record<string, string> = {
  Zimbabwe: "🇿🇼",
  "South Africa": "🇿🇦",
  Zambia: "🇿🇲",
  Botswana: "🇧🇼",
  Mozambique: "🇲🇿",
};

type DistanceMarker = { lat: number; lng: number; km: number };

function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function extractCountry(label: string): string | null {
  for (const country of Object.keys(COUNTRY_FLAGS)) {
    if (label.toLowerCase().includes(country.toLowerCase())) return country;
  }
  return null;
}

function getLegDistances(stops: StopMarker[]): { from: string; to: string; km: number }[] {
  const legs: { from: string; to: string; km: number }[] = [];
  for (let i = 1; i < stops.length; i++) {
    const d = haversineKm(stops[i - 1].lat, stops[i - 1].lon, stops[i].lat, stops[i].lon);
    legs.push({ from: stops[i - 1].label, to: stops[i].label, km: Math.round(d) });
  }
  return legs;
}

function getCrossings(stops: StopMarker[]): { fromCountry: string; toCountry: string; betweenIdx: number }[] {
  const crossings: { fromCountry: string; toCountry: string; betweenIdx: number }[] = [];
  for (let i = 1; i < stops.length; i++) {
    const c1 = extractCountry(stops[i - 1].label);
    const c2 = extractCountry(stops[i].label);
    if (c1 && c2 && c1 !== c2) {
      crossings.push({ fromCountry: c1, toCountry: c2, betweenIdx: i - 1 });
    }
  }
  return crossings;
}

function getDistanceMarkers(
  coords: [number, number][],
  intervalKm = 50,
): DistanceMarker[] {
  if (coords.length < 2) return [];

  const segments: { startIdx: number; endIdx: number; startKm: number; endKm: number }[] = [];
  let cumKm = 0;

  for (let i = 1; i < coords.length; i++) {
    const [lon1, lat1] = coords[i - 1];
    const [lon2, lat2] = coords[i];
    const segKm = haversineKm(lat1, lon1, lat2, lon2);
    segments.push({ startIdx: i - 1, endIdx: i, startKm: cumKm, endKm: cumKm + segKm });
    cumKm += segKm;
  }

  const markers: DistanceMarker[] = [];
  let nextMarkerKm = intervalKm;

  for (const seg of segments) {
    while (nextMarkerKm <= seg.endKm + 0.001) {
      const t = (nextMarkerKm - seg.startKm) / (seg.endKm - seg.startKm || 1);
      const [lon1, lat1] = coords[seg.startIdx];
      const [lon2, lat2] = coords[seg.endIdx];
      markers.push({
        lat: lat1 + (lat2 - lat1) * t,
        lng: lon1 + (lon2 - lon1) * t,
        km: Math.round(nextMarkerKm),
      });
      nextMarkerKm += intervalKm;
    }
  }

  return markers;
}

function makeStopIcon(bg: string, glyph: string, ring: string): L.DivIcon {
  return L.divIcon({
    className: "tl-marker",
    html: `<div style="position:relative;width:32px;height:32px;">
      <div style="position:absolute;inset:0;border-radius:50%;background:${bg};border:3px solid ${ring};box-shadow:0 2px 6px rgba(0,0,0,0.35);"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;color:#fff;line-height:1;font-family:system-ui,sans-serif;">${glyph}</div>
    </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -18],
  });
}

function makeBorderIcon(fromFlag: string, toFlag: string): L.DivIcon {
  return L.divIcon({
    className: "tl-border-marker",
    html: `<div style="
      display:flex;align-items:center;gap:1px;
      background:#fff;border:2px solid #dc2626;border-radius:14px;
      padding:1px 6px;font-size:13px;white-space:nowrap;
      box-shadow:0 1px 4px rgba(0,0,0,0.2);
    ">${fromFlag}↔${toFlag}</div>`,
    iconSize: [0, 0],
    iconAnchor: [35, 12],
  });
}

function makeDistIcon(km: number): L.DivIcon {
  return L.divIcon({
    className: "tl-dist-marker",
    html: `<div style="
      display:flex;align-items:center;justify-content:center;
      background:rgba(14,124,134,0.15);border-radius:12px;
      padding:0 4px;font-size:9px;font-weight:600;color:#0e7c86;
      white-space:nowrap;font-family:system-ui,sans-serif;
      border:1px solid rgba(14,124,134,0.3);
    ">${km} km</div>`,
    iconSize: [0, 0],
    iconAnchor: [30, 8],
  });
}

function makeVehicleIcon(): L.DivIcon {
  return L.divIcon({
    className: "tl-vehicle-marker",
    html: `<div style="
      width:36px;height:36px;
      display:flex;align-items:center;justify-content:center;
      background:#0e7c86;border-radius:50%;
      border:3px solid #fff;
      box-shadow:0 2px 8px rgba(0,0,0,0.4);
      animation:pulse-dot 2s ease-in-out infinite;
    ">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>
      </svg>
    </div>
    <style>
      @keyframes pulse-dot {
        0%, 100% { box-shadow: 0 2px 8px rgba(14,124,134,0.4), 0 0 0 0 rgba(14,124,134,0.3); }
        50% { box-shadow: 0 2px 8px rgba(14,124,134,0.4), 0 0 0 10px rgba(14,124,134,0); }
      }
    </style>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

function computeEta(
  pos: { lat: number; lon: number },
  dest: { lat: number; lon: number },
  positions: TripPosition[],
): { remainingKm: number; etaHours: number; speedKmh: number } | null {
  const remainingKm = haversineKm(pos.lat, pos.lon, dest.lat, dest.lon);

  let speedKmh = 60;
  if (positions.length >= 2) {
    const sorted = [...positions].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    if (first.id !== last.id) {
      const distKm = haversineKm(first.lat, first.lon, last.lat, last.lon);
      const hours = (new Date(last.timestamp).getTime() - new Date(first.timestamp).getTime()) / 3600000;
      if (distKm > 1 && hours > 0.01) {
        speedKmh = Math.round(distKm / hours);
      }
    }
  }

  const etaHours = speedKmh > 5 ? remainingKm / speedKmh : remainingKm / 60;
  return { remainingKm: Math.round(remainingKm), etaHours, speedKmh };
}

export function RouteMap({ route, stops, positions = [] }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const tileRef = useRef<L.TileLayer | null>(null);
  const polylineRef = useRef<L.Polyline | null>(null);
  const markersLayer = useRef<L.LayerGroup | null>(null);
  const distLayer = useRef<L.LayerGroup | null>(null);
  const borderLayer = useRef<L.LayerGroup | null>(null);
  const trackingLayer = useRef<L.LayerGroup | null>(null);
  const [ready, setReady] = useState(false);
  const [isFullscreen, setFullscreen] = useState(false);

  const hasGeometry = !!route.geometry?.coordinates?.length;
  const legs = getLegDistances(stops);
  const crossings = getCrossings(stops);

  const latestPos = positions.length > 0
    ? positions.reduce((a, b) => new Date(a.timestamp) > new Date(b.timestamp) ? a : b)
    : null;

  const destStop = stops.find(s => s.kind === "destination");
  const eta = latestPos && destStop
    ? computeEta({ lat: latestPos.lat, lon: latestPos.lon }, { lat: destStop.lat, lon: destStop.lon }, positions)
    : null;

  const focusStop = useCallback((lat: number, lon: number) => {
    const map = mapRef.current;
    if (!map) return;
    map.setView([lat, lon], map.getZoom() < 10 ? 10 : map.getZoom(), { animate: true });
    setTimeout(() => {
      const el = document.elementFromPoint(
        containerRef.current!.getBoundingClientRect().left + 100,
        containerRef.current!.getBoundingClientRect().top + 100,
      );
      if (el) {
        const markerEl = el.closest(".tl-marker");
        if (markerEl) markerEl.dispatchEvent(new Event("click"));
      }
    }, 300);
  }, []);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: true,
    }).setView(DEFAULT_CENTER, DEFAULT_ZOOM);

    mapRef.current = map;

    const tile = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);
    tileRef.current = tile;

    markersLayer.current = L.layerGroup().addTo(map);
    distLayer.current = L.layerGroup().addTo(map);
    borderLayer.current = L.layerGroup().addTo(map);
    trackingLayer.current = L.layerGroup().addTo(map);

    map.whenReady(() => setReady(true));
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersLayer.current?.clearLayers();
    distLayer.current?.clearLayers();
    borderLayer.current?.clearLayers();

    if (hasGeometry) {
      if (polylineRef.current) {
        map.removeLayer(polylineRef.current);
        polylineRef.current = null;
      }

      const latlngs: [number, number][] = route.geometry.coordinates.map(
        ([lon, lat]) => [lat, lon],
      );
      const poly = L.polyline(latlngs, {
        color: "#0e7c86",
        weight: 5,
        opacity: 0.75,
        lineCap: "round",
        lineJoin: "round",
      }).addTo(map);
      polylineRef.current = poly;

      map.fitBounds(poly.getBounds(), { padding: [40, 40], animate: true, maxZoom: 14 });

      const distMarkers = getDistanceMarkers(
        route.geometry.coordinates as [number, number][],
      );
      distMarkers.forEach((dm) => {
        L.marker([dm.lat, dm.lng], { icon: makeDistIcon(dm.km) }).addTo(
          distLayer.current!,
        );
      });

      crossings.forEach((cross) => {
        if (cross.betweenIdx < 0 || cross.betweenIdx + 1 >= stops.length) return;
        const midLat = (stops[cross.betweenIdx].lat + stops[cross.betweenIdx + 1].lat) / 2;
        const midLon = (stops[cross.betweenIdx].lon + stops[cross.betweenIdx + 1].lon) / 2;
        const fromFlag = COUNTRY_FLAGS[cross.fromCountry] || "";
        const toFlag = COUNTRY_FLAGS[cross.toCountry] || "";
        L.marker([midLat, midLon], {
          icon: makeBorderIcon(fromFlag, toFlag),
        }).addTo(borderLayer.current!);
      });
    } else if (stops.length > 0) {
      const points: L.LatLngExpression[] = stops.map((s) => [s.lat, s.lon]);
      if (points.length === 1) {
        map.setView(points[0], 10, { animate: true });
      } else {
        map.fitBounds(L.latLngBounds(points), { padding: [40, 40], animate: true });
      }
    }

    stops.forEach((stop, i) => {
      const color = STOP_COLORS[stop.kind];
      const ring = STOP_RING[stop.kind];
      const num = i + 1;
      const totalStops = stops.length;
      const glyph = stop.kind === "destination" ? "🏁" : String(num);

      const marker = L.marker([stop.lat, stop.lon], {
        icon: makeStopIcon(color, glyph, ring),
      });

      const country = extractCountry(stop.label);
      const countryLine = country ? `<br>${COUNTRY_FLAGS[country] || ""} ${country}` : "";

      marker.bindPopup(
        `<strong>${STOP_LABELS[stop.kind]} ${num}/${totalStops}</strong><br>${stop.label}${countryLine}`,
        { offset: [0, -18] },
      );
      marker.addTo(markersLayer.current!);
    });

    return () => {
      if (polylineRef.current) {
        map.removeLayer(polylineRef.current);
        polylineRef.current = null;
      }
    };
  }, [route, stops, hasGeometry, crossings]);

  // Live tracking layer: vehicle marker + position trail
  useEffect(() => {
    const layer = trackingLayer.current;
    if (!layer) return;
    layer.clearLayers();

    if (!latestPos) return;

    const tl = layer;

    // Position history trail
    if (positions.length >= 2) {
      const sorted = [...positions].sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
      );
      const trailLatLngs: [number, number][] = sorted.map(p => [p.lat, p.lon]);
      const trail = L.polyline(trailLatLngs, {
        color: "#0e7c86",
        weight: 3,
        opacity: 0.4,
        dashArray: "6 4",
      });
      trail.bindPopup(`<strong>Position trail</strong><br>${sorted.length} points`);
      trail.addTo(tl);
    }

    // Vehicle marker
    const marker = L.marker([latestPos.lat, latestPos.lon], {
      icon: makeVehicleIcon(),
      zIndexOffset: 1000,
    });
    marker.bindPopup(
      `<strong>Vehicle</strong><br>` +
      `${latestPos.lat.toFixed(5)}, ${latestPos.lon.toFixed(5)}<br>` +
      (latestPos.accuracy ? `±${latestPos.accuracy.toFixed(0)}m` : "") +
      `<br>Source: ${latestPos.source}` +
      `<br><small>${new Date(latestPos.timestamp).toLocaleString()}</small>`,
      { offset: [0, -20] },
    );
    marker.addTo(tl);

    // If there's a route polyline, fit to include vehicle
    if (hasGeometry && polylineRef.current) {
      const bounds = polylineRef.current.getBounds().extend([latestPos.lat, latestPos.lon]);
      mapRef.current?.fitBounds(bounds, { padding: [40, 40], animate: true, maxZoom: 14 });
    }
  }, [positions, latestPos, hasGeometry]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    setTimeout(() => map.invalidateSize(), 100);
  }, [isFullscreen, ready]);

  const mapContent = (
    <div className={`relative ${isFullscreen ? "fixed inset-0 z-50 bg-white p-3" : ""}`}>
      <div
        ref={containerRef}
        className={`w-full rounded-xl shadow-md z-0 ${isFullscreen ? "h-full" : "h-[300px] sm:h-[420px]"}`}
      />

      {!ready && (
        <div className={`absolute inset-0 z-10 rounded-xl bg-spotter-50 animate-pulse flex items-center justify-center pointer-events-none ${isFullscreen ? "m-3" : ""}`}>
          <div className="text-sm text-spotter-300">Loading map...</div>
        </div>
      )}

      <button
        onClick={() => setFullscreen(!isFullscreen)}
        className="absolute top-3 right-3 z-[1000] bg-white/90 backdrop-blur-sm rounded-lg shadow p-1.5 hover:bg-white transition"
        title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
      >
        {isFullscreen ? <Minimize2 className="w-4 h-4 text-gray-600" /> : <Maximize2 className="w-4 h-4 text-gray-600" />}
      </button>

      {isFullscreen && (
        <button
          onClick={() => setFullscreen(false)}
          className="absolute top-3 left-3 z-[1000] bg-white/90 backdrop-blur-sm rounded-lg shadow px-3 py-1.5 text-sm text-gray-700 hover:bg-white"
        >
          ← Back
        </button>
      )}

      {ready && (
        <div className={`absolute top-3 ${isFullscreen ? "left-20" : "left-3"} z-[1000] bg-white/90 backdrop-blur-sm rounded-lg shadow px-3 py-2 text-xs space-y-0.5 pointer-events-none`}>
          {route.distance_km > 0 && (
            <div className="font-bold text-spotter-800 text-sm">
              {route.distance_km.toLocaleString()} km
            </div>
          )}
          {latestPos && (
            <div className="flex items-center gap-1 text-spotter-600">
              <Navigation className="w-3 h-3" />
              <span>{latestPos.lat.toFixed(4)}, {latestPos.lon.toFixed(4)}</span>
            </div>
          )}
          {eta && (
            <>
              <div className="text-gray-500">{eta.remainingKm} km remaining</div>
              <div className="text-gray-500">~{eta.etaHours < 1 ? `${Math.round(eta.etaHours * 60)} min` : `${eta.etaHours.toFixed(1)} hrs`} ETA</div>
              <div className="text-[10px] text-gray-400">{eta.speedKmh} km/h avg</div>
            </>
          )}
          {route.distance_km > 0 && !latestPos && (
            <div className="text-gray-500">
              ~{route.duration_h.toFixed(1)} hours
            </div>
          )}
          {stops.length > 0 && (
            <div className="text-gray-500">
              {stops.length} stop{stops.length !== 1 ? "s" : ""}
            </div>
          )}
          {positions.length > 1 && (
            <div className="text-[10px] text-gray-400">
              {positions.length} position{positions.length !== 1 ? "s" : ""}
            </div>
          )}
        </div>
      )}

      {!isFullscreen && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 px-1 mt-2">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full bg-[#0e7c86]" /> Start
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full bg-[#f59e0b]" /> Via
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-3 rounded-full bg-[#dc2626]" /> Destination
          </span>
          {hasGeometry && (
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-0.5 bg-[#0e7c86] rounded" /> Route
            </span>
          )}
          {latestPos && (
            <span className="flex items-center gap-1.5 text-spotter-600">
              <span className="inline-block w-3 h-3 rounded-full bg-[#0e7c86] animate-pulse" /> Vehicle
            </span>
          )}
          {crossings.length > 0 && (
            <span className="flex items-center gap-1.5 text-red-600 font-medium">
              <span className="inline-block w-3 h-3 border-2 border-red-500 rounded-sm" /> Border
            </span>
          )}
        </div>
      )}
    </div>
  );

  if (isFullscreen) return mapContent;

  return (
    <div>
      {mapContent}

      {legs.length > 0 && (
        <div className="mt-3 space-y-1">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Leg Distances</h4>
          {legs.map((leg, i) => (
            <div key={i} className="text-xs text-gray-600">
              <span className="font-medium text-gray-800">{leg.from}</span>
              <span className="mx-1.5 text-gray-400">→</span>
              <span className="font-medium text-gray-800">{leg.to}</span>
              <span className="ml-2 text-spotter-700 font-semibold">{leg.km} km</span>
            </div>
          ))}
        </div>
      )}

      {crossings.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {crossings.map((cross, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 text-[10px] font-medium bg-red-50 border border-red-200 rounded-full text-red-700">
              {(COUNTRY_FLAGS[cross.fromCountry] || "")} {cross.fromCountry} → {(COUNTRY_FLAGS[cross.toCountry] || "")} {cross.toCountry}
            </span>
          ))}
        </div>
      )}

      {stops.length > 0 && (
        <div className="mt-3 space-y-1">
          <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Stops</h4>
          {stops.map((stop, i) => {
            const country = extractCountry(stop.label);
            return (
              <button
                key={i}
                onClick={() => focusStop(stop.lat, stop.lon)}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-xs rounded-md hover:bg-spotter-50 transition text-left group"
              >
                <span
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0"
                  style={{ background: STOP_COLORS[stop.kind] }}
                >
                  {stop.kind === "destination" ? "🏁" : i + 1}
                </span>
                <span className="flex-1 text-gray-700 group-hover:text-gray-900">
                  {STOP_LABELS[stop.kind]}: <span className="font-medium">{stop.label}</span>
                </span>
                {country && <span className="text-sm">{COUNTRY_FLAGS[country] || ""}</span>}
                <MapPin className="w-3 h-3 text-gray-300 group-hover:text-spotter-500" />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
