import { useEffect, useRef, useState, useCallback, startTransition } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { fetchActiveTrips } from "../lib/api";
import type { Trip, TripPosition } from "../lib/types";
import { Loader2, AlertTriangle, Navigation } from "lucide-react";

interface ActiveTrip extends Trip {
  last_position: TripPosition | null;
}

function makeVehicleIcon(sos: boolean): L.DivIcon {
  return L.divIcon({
    className: "tl-live-marker",
    html: `<div style="
      width:32px;height:32px;
      display:flex;align-items:center;justify-content:center;
      background:${sos ? "#dc2626" : "#0e7c86"};border-radius:50%;
      border:3px solid #fff;
      box-shadow:0 2px 8px rgba(0,0,0,0.4);
      animation:${sos ? "none" : "pulse-dot 2s ease-in-out infinite"};
    ">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="1" y="3" width="15" height="13"/><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>
      </svg>
    </div>
    <style>
      @keyframes pulse-dot {
        0%, 100% { box-shadow: 0 2px 8px rgba(14,124,134,0.4), 0 0 0 0 rgba(14,124,134,0.3); }
        50% { box-shadow: 0 2px 8px rgba(14,124,134,0.4), 0 0 0 8px rgba(14,124,134,0); }
      }
    </style>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

export function LiveMapPage() {
  const [activeTrips, setActiveTrips] = useState<ActiveTrip[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTrip, setSelectedTrip] = useState<ActiveTrip | null>(null);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayer = useRef<L.LayerGroup | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetchActiveTrips();
      setActiveTrips(res.active_trips);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    startTransition(() => { load(); });
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load]);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = L.map(containerRef.current, {
      zoomControl: true,
      attributionControl: false,
    }).setView([-19.0, 29.0], 5);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
    }).addTo(map);

    markersLayer.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => { map.remove(); mapRef.current = null; };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const layer = markersLayer.current;
    if (!map || !layer) return;

    layer.clearLayers();

    if (activeTrips.length === 0) {
      map.setView([-19.0, 29.0], 5);
      return;
    }

    const bounds = L.latLngBounds([]);

    activeTrips.forEach(trip => {
      const pos = trip.last_position;
      if (!pos) return;

      const latlng: L.LatLngExpression = [pos.lat, pos.lon];
      bounds.extend(latlng);

      const hasSos = !!trip.sos_triggered_at && !trip.sos_acknowledged_at;
      const marker = L.marker(latlng, { icon: makeVehicleIcon(hasSos) });

      const statusLabel = trip.status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      const sosWarning = hasSos ? "<br><span style='color:#dc2626;font-weight:bold;'>🚨 SOS ACTIVE</span>" : "";

      marker.bindPopup(`
        <div style="font-family:system-ui,sans-serif;min-width:200px;">
          <strong style="color:#0e7c86;font-size:14px;">Trip #${trip.id}</strong>${sosWarning}
          <br><small style="color:#6b7280;">${trip.origin} → ${trip.destination}</small>
          <hr style="margin:6px 0;border:none;border-top:1px solid #e5e7eb;">
          <div style="font-size:12px;color:#374151;">
            <div><strong>Driver:</strong> ${trip.driver_name || "—"}</div>
            <div><strong>Status:</strong> ${statusLabel}</div>
            <div><strong>Pos:</strong> ${pos.lat.toFixed(4)}, ${pos.lon.toFixed(4)}</div>
            ${trip.distance_km ? `<div><strong>Dist:</strong> ${trip.distance_km} km</div>` : ""}
          </div>
        </div>
      `, { offset: [0, -18] });

      marker.on("click", () => setSelectedTrip(trip));
      marker.addTo(layer);
    });

    const hasBounds = activeTrips.some(t => t.last_position);
    if (hasBounds) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
    }
  }, [activeTrips]);

  const sosTrips = activeTrips.filter(t => t.sos_triggered_at && !t.sos_acknowledged_at);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col">
      {/* Status bar */}
      <div className="flex items-center justify-between mb-2 shrink-0">
        <div className="flex items-center gap-3 text-xs text-gray-500">
          <span className="font-medium">{activeTrips.length} active trip{activeTrips.length !== 1 ? "s" : ""}</span>
          {sosTrips.length > 0 && (
            <span className="flex items-center gap-1 text-red-600 font-bold">
              <AlertTriangle className="w-3 h-3" />
              {sosTrips.length} SOS
            </span>
          )}
        </div>
        <button onClick={load} disabled={loading} className="text-xs text-spotter-600 hover:text-spotter-800">
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded px-3 py-1.5 text-xs text-red-700 mb-2">{error}</div>
      )}

      {/* SOS Banner */}
      {sosTrips.length > 0 && (
        <div className="bg-red-600 text-white px-3 py-1.5 rounded text-xs font-medium flex items-center gap-2 mb-2 animate-pulse">
          <AlertTriangle className="w-3.5 h-3.5" />
          SOS: {sosTrips.map(t => `#${t.id} (${t.driver_name || "—"})`).join(", ")}
        </div>
      )}

      {/* Map */}
      <div className="flex-1 relative rounded-xl overflow-hidden shadow-md">
        <div ref={containerRef} className="absolute inset-0" />
        {loading && (
          <div className="absolute top-3 right-3 z-[1000] bg-white/90 rounded-lg shadow px-2 py-1">
            <Loader2 className="w-4 h-4 animate-spin text-spotter-500" />
          </div>
        )}

        {/* Active trips list (floating) */}
        <div className="absolute top-3 left-3 z-[1000] bg-white/95 rounded-xl shadow-lg w-60 max-h-[70%] overflow-y-auto">
          <div className="px-3 py-2 border-b border-gray-100 text-[11px] font-bold text-gray-500 uppercase tracking-wide">
            Active Trips
          </div>
          {activeTrips.length === 0 ? (
            <div className="px-3 py-4 text-center text-[11px] text-gray-400">No active trips</div>
          ) : (
            <div className="divide-y divide-gray-50">
              {activeTrips.map(trip => {
                const hasSos = !!trip.sos_triggered_at && !trip.sos_acknowledged_at;
                const statusLabel = trip.status.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
                return (
                  <button
                    key={trip.id}
                    onClick={() => {
                      setSelectedTrip(trip);
                      if (trip.last_position) {
                        mapRef.current?.setView([trip.last_position.lat, trip.last_position.lon], 10);
                      }
                    }}
                    className={`w-full text-left px-3 py-2 hover:bg-spotter-50 transition text-[11px] ${
                      selectedTrip?.id === trip.id ? "bg-spotter-50" : ""
                    } ${hasSos ? "bg-red-50" : ""}`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-gray-800">
                        {hasSos && <AlertTriangle className="w-2.5 h-2.5 inline text-red-600 mr-1" />}
                        #{trip.id}
                      </span>
                      <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${
                        hasSos ? "bg-red-100 text-red-800" : "bg-gray-100 text-gray-600"
                      }`}>{statusLabel}</span>
                    </div>
                    <div className="text-gray-500 mt-0.5 truncate">{trip.origin} → {trip.destination}</div>
                    <div className="text-gray-400 mt-0.5">{trip.driver_name || "—"}</div>
                    {trip.last_position && (
                      <div className="text-gray-400 mt-0.5 flex items-center gap-1">
                        <Navigation className="w-2.5 h-2.5" />
                        {trip.last_position.lat.toFixed(3)}, {trip.last_position.lon.toFixed(3)}
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
