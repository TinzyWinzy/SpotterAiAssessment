import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { RestStopMarker, RouteInfo, StopMarker } from "../lib/types";

interface Props {
  route: RouteInfo;
  stops: StopMarker[];
  restStops: RestStopMarker[];
}

const MAIN_COLORS: Record<StopMarker["kind"], string> = {
  current: "#0e7c86",
  pickup: "#f59e0b",
  dropoff: "#dc2626",
};

const MAIN_LABELS: Record<StopMarker["kind"], string> = {
  current: "Start",
  pickup: "Pickup",
  dropoff: "Dropoff",
};

const REST_COLORS: Record<RestStopMarker["kind"], string> = {
  fuel: "#7c3aed",
  break: "#fde68a",
  rest: "#7dd3c0",
  pickup: "#f59e0b",
  dropoff: "#dc2626",
};

const REST_ICONS: Record<RestStopMarker["kind"], string> = {
  fuel: "⛽",
  break: "☕",
  rest: "🛏",
  pickup: "P",
  dropoff: "D",
};

function makeIcon(bg: string, glyph: string, ring: string): L.DivIcon {
  return L.divIcon({
    className: "custom-marker",
    html: `<div style="position:relative;width:26px;height:26px;">
      <div style="position:absolute;inset:0;border-radius:50%;background:${bg};border:3px solid ${ring};box-shadow:0 1px 3px rgba(0,0,0,0.4);"></div>
      <div style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#0b1f24;line-height:1;">${glyph}</div>
    </div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

export function RouteMap({ route, stops, restStops }: Props) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);

  useEffect(() => {
    if (!mapRef.current) return;
    if (mapInstance.current) {
      mapInstance.current.remove();
      mapInstance.current = null;
    }

    const map = L.map(mapRef.current, { zoomControl: true });
    mapInstance.current = map;

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "© OpenStreetMap",
      maxZoom: 19,
    }).addTo(map);

    // Route polyline
    const latlngs: [number, number][] = route.geometry.coordinates.map(
      ([lon, lat]) => [lat, lon],
    );
    if (latlngs.length > 0) {
      const polyline = L.polyline(latlngs, {
        color: "#0e7c86",
        weight: 4,
        opacity: 0.85,
      }).addTo(map);
      map.fitBounds(polyline.getBounds(), { padding: [50, 50] });
    }

    // Main stops (current / pickup / dropoff)
    stops.forEach((stop) => {
      const color = MAIN_COLORS[stop.kind];
      L.marker([stop.lat, stop.lon], { icon: makeIcon(color, "•", "white") })
        .addTo(map)
        .bindPopup(
          `<strong>${MAIN_LABELS[stop.kind]}</strong><br/>${stop.label}`,
        );
    });

    // Rest / fuel stops — smaller markers, different glyphs
    restStops.forEach((r) => {
      const color = REST_COLORS[r.kind];
      const glyph = REST_ICONS[r.kind];
      L.marker([r.lat, r.lon], { icon: makeIcon(color, glyph, "white") })
        .addTo(map)
        .bindPopup(
          `<strong>${r.remark}</strong><br/>${r.label}<br/>` +
            `<small>Day ${r.day} · ${r.duration_h}h · ${r.cumulative_miles} mi</small>`,
        );
    });

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, [route, stops, restStops]);

  return (
    <div className="space-y-3">
      <div ref={mapRef} className="h-[420px] w-full rounded-xl shadow-md" />
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600 px-1">
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-[#0e7c86]" /> Start
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-[#f59e0b]" /> Pickup
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-[#dc2626]" /> Dropoff
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-[#7c3aed]" /> ⛽ Fuel
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-[#fde68a]" /> ☕ Break
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-full bg-[#7dd3c0]" /> 🛏 Rest
        </span>
      </div>
    </div>
  );
}
