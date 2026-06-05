import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { RouteInfo, StopMarker } from "../lib/types";

interface Props {
  route: RouteInfo;
  stops: StopMarker[];
}

const KIND_COLORS: Record<StopMarker["kind"], string> = {
  current: "#0e7c86",
  pickup: "#f59e0b",
  dropoff: "#dc2626",
};

const KIND_LABELS: Record<StopMarker["kind"], string> = {
  current: "Start",
  pickup: "Pickup",
  dropoff: "Dropoff",
};

export function RouteMap({ route, stops }: Props) {
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

    // Route line
    const latlngs: [number, number][] = route.geometry.coordinates.map(
      ([lon, lat]) => [lat, lon]
    );
    if (latlngs.length > 0) {
      const polyline = L.polyline(latlngs, {
        color: "#0e7c86",
        weight: 4,
        opacity: 0.85,
      }).addTo(map);
      map.fitBounds(polyline.getBounds(), { padding: [40, 40] });
    }

    // Stop markers
    stops.forEach((stop) => {
      const color = KIND_COLORS[stop.kind];
      const icon = L.divIcon({
        className: "custom-marker",
        html: `<div style="width:24px;height:24px;border-radius:50%;background:${color};border:3px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);"></div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });
      L.marker([stop.lat, stop.lon], { icon })
        .addTo(map)
        .bindPopup(`<strong>${KIND_LABELS[stop.kind]}</strong><br/>${stop.label}`);
    });

    return () => {
      if (mapInstance.current) {
        mapInstance.current.remove();
        mapInstance.current = null;
      }
    };
  }, [route, stops]);

  return <div ref={mapRef} className="h-[420px] w-full rounded-xl shadow-md" />;
}
