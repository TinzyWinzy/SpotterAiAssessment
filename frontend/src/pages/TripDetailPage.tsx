import { useEffect, useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { fetchTrip, updateTripStatus, fetchTripPositions, reportTripPosition, fetchBookingImages } from "../lib/api";
import { useTripPositionPolling } from "../lib/useTripPositionPolling";
import type { Trip, TripPosition, TripImage } from "../lib/types";
import { RouteMap } from "../components/RouteMap";
import { ArrowLeft, DollarSign, Fuel, User, MapPin, Loader2, Download, Navigation, Crosshair, Package, Phone, Mail, Camera } from "lucide-react";
import { exportTripSheet } from "../lib/pdfExport";
import { StatusTimeline } from "../components/StatusTimeline";

const STATUS_FLOW: Record<string, string[]> = {
  dispatched: ["at_border", "cancelled"],
  at_border: ["in_transit", "cancelled"],
  in_transit: ["delivered", "cancelled"],
  delivered: ["paid"],
  paid: [],
  cancelled: [],
};

export function TripDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [positions, setPositions] = useState<TripPosition[]>([]);
  const [images, setImages] = useState<TripImage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [manualLat, setManualLat] = useState("");
  const [manualLon, setManualLon] = useState("");

  useEffect(() => {
    if (!id) return;
    Promise.all([
      fetchTrip(Number(id)),
      fetchTripPositions(Number(id)).catch(() => ({ ok: true, positions: [] })),
      fetchBookingImages(Number(id)).catch(() => ({ ok: true, images: [] })),
    ]).then(([tripRes, posRes, imgRes]) => {
      setTrip(tripRes.trip);
      setPositions(posRes.positions);
      setImages(imgRes.images);
    }).catch(e => {
      setError(e instanceof Error ? e.message : "Failed to load");
    }).finally(() => setLoading(false));
  }, [id]);

  async function handleStatusChange(newStatus: string) {
    setUpdating(true);
    try {
      const r = await updateTripStatus(Number(id), newStatus);
      setTrip(r.trip);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Status update failed");
    } finally {
      setUpdating(false);
    }
  }

  const reportGPS = useCallback(async () => {
    setGeoLoading(true);
    setGeoError(null);
    try {
      const pos = await new Promise<GeolocationPosition>((resolve, reject) => {
        if (!navigator.geolocation) reject(new Error("Geolocation not supported"));
        else navigator.geolocation.getCurrentPosition(resolve, reject, { enableHighAccuracy: true, timeout: 10000 });
      });
      await reportTripPosition(Number(id), {
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        accuracy: pos.coords.accuracy,
        source: "gps",
      });
      const posRes = await fetchTripPositions(Number(id));
      setPositions(posRes.positions);
    } catch (e) {
      setGeoError(e instanceof Error ? e.message : "GPS failed. Enter coordinates manually.");
    } finally {
      setGeoLoading(false);
    }
  }, [id]);

  async function reportManual() {
    const lat = parseFloat(manualLat);
    const lon = parseFloat(manualLon);
    if (isNaN(lat) || isNaN(lon)) { setError("Enter valid lat/lon"); return; }
    setGeoLoading(true);
    try {
      await reportTripPosition(Number(id), { lat, lon, source: "manual" });
      const posRes = await fetchTripPositions(Number(id));
      setPositions(posRes.positions);
      setManualLat(""); setManualLon("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed");
    } finally {
      setGeoLoading(false);
    }
  }

  const { positionHistory } = useTripPositionPolling(
    trip && ["dispatched", "at_border", "in_transit"].includes(trip.status) ? trip.id : undefined,
    15000,
  );

  const displayPositions = positionHistory.length > 0 ? positionHistory : positions;
  const lastPos = displayPositions[displayPositions.length - 1] || positions[0];

  const routeInfo = trip?.route_geometry ? {
    distance_km: trip.distance_km,
    duration_h: trip.distance_km / 60,
    geometry: trip.route_geometry as { type: "LineString"; coordinates: [number, number][] },
  } : null;

  const geoCoords = trip?.route_geometry
    ? (trip.route_geometry as { type: "LineString"; coordinates: [number, number][] }).coordinates
    : null;
  const stopMarkers: { lat: number; lon: number; label: string; kind: "origin" | "destination" }[] = [];
  if (trip) {
    if (geoCoords && geoCoords.length > 0) {
      stopMarkers.push({ lat: geoCoords[0][1], lon: geoCoords[0][0], label: trip.origin, kind: "origin" });
      stopMarkers.push({ lat: geoCoords[geoCoords.length - 1][1], lon: geoCoords[geoCoords.length - 1][0], label: trip.destination, kind: "destination" });
    } else {
      stopMarkers.push({ lat: 0, lon: 0, label: trip.origin, kind: "origin" });
      stopMarkers.push({ lat: 0, lon: 0, label: trip.destination, kind: "destination" });
    }
  }

  if (loading) return <div className="flex justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-spotter-500" /></div>;
  if (error) return <div className="p-4 bg-red-50 rounded-md text-red-800 text-sm">{error}</div>;
  if (!trip) return <div className="text-gray-500 text-sm">Trip not found</div>;

  const profit = parseFloat(String(trip.revenue_usd ?? 0)) - parseFloat(String(trip.actual_total_cost_usd ?? trip.estimated_total_cost_usd));

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/app/trips" className="text-spotter-600 hover:text-spotter-800"><ArrowLeft className="w-5 h-5" /></Link>
        <div>
          <h2 className="text-xl font-bold text-spotter-800">{trip.origin} → {trip.destination}</h2>
          <p className="text-sm text-gray-500">
            {trip.driver_name || "No driver"} · {trip.vehicle_plate || "No vehicle"} · {new Date(trip.created_at).toLocaleDateString()}
          </p>
        </div>
        <StatusBadge status={trip.status} />
        <button onClick={() => exportTripSheet(trip)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-spotter-600 text-white rounded-md hover:bg-spotter-700 ml-auto">
          <Download className="w-4 h-4" /> Export PDF
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 space-y-5">
          <div className="bg-white rounded-xl shadow-md p-5">
            <h3 className="text-sm font-semibold text-spotter-800 mb-3">Trip Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
              <Stat label="Distance" value={`${trip.distance_km} km`} icon={MapPin} />
              {trip.commodity_data ? (
                <div className="bg-spotter-50 rounded-lg p-3 col-span-2">
                  <div className="text-[10px] font-medium text-spotter-600 uppercase tracking-wide">Commodity</div>
                  <div className="mt-0.5 text-sm font-bold text-spotter-900">{trip.commodity_data.name}</div>
                  <div className="mt-0.5 flex gap-2 text-[10px] text-gray-500">
                    <span>{trip.commodity_data.category_name}</span>
                    {trip.load_weight_tonnes && <span>· {trip.load_weight_tonnes}t</span>}
                    <span>· {trip.commodity_data.unit}</span>
                  </div>
                  <div className="mt-1 flex gap-2 text-[10px] text-spotter-600">
                    {trip.commodity_data.rate_per_km && <span>${trip.commodity_data.rate_per_km}/km</span>}
                    {trip.commodity_data.rate_per_kg && <span>${trip.commodity_data.rate_per_kg}/kg</span>}
                    {trip.commodity_data.flat_fee && <span>+${trip.commodity_data.flat_fee} fee</span>}
                  </div>
                </div>
              ) : (
                <Stat label="Load Type" value={trip.load_type} icon={MapPin} />
              )}
              <Stat label="Priority" value={trip.priority} />
              <Stat label="Weight" value={trip.load_weight_tonnes ? `${trip.load_weight_tonnes}t` : "-"} />
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-5">
            <h3 className="text-sm font-semibold text-spotter-800 mb-3">Cost & Revenue</h3>
            <div className="space-y-2 text-sm">
              <CostRow label="Est. Fuel" value={`$${parseFloat(String(trip.estimated_fuel_cost_usd)).toFixed(2)}`} icon={Fuel} />
              <CostRow label="Est. Driver Pay" value={`$${parseFloat(String(trip.estimated_driver_pay_usd)).toFixed(2)}`} icon={User} />
              {parseFloat(String(trip.estimated_border_fees_usd)) > 0 && <CostRow label="Est. Border Fees" value={`$${parseFloat(String(trip.estimated_border_fees_usd)).toFixed(2)}`} />}
              <CostRow label="Est. Total Cost" value={`$${parseFloat(String(trip.estimated_total_cost_usd)).toFixed(2)}`} bold />
              {trip.actual_total_cost_usd != null && (
                <CostRow label="Actual Cost" value={`$${parseFloat(String(trip.actual_total_cost_usd)).toFixed(2)}`} bold />
              )}
              {trip.estimated_revenue != null && (
                <CostRow label="Est. Revenue" value={`$${parseFloat(String(trip.estimated_revenue)).toFixed(2)}`} icon={DollarSign} positive />
              )}
              {trip.revenue_usd != null && (
                <>
                  <CostRow label="Revenue" value={`$${parseFloat(String(trip.revenue_usd)).toFixed(2)}`} icon={DollarSign} positive />
                  <CostRow label={profit >= 0 ? "Profit" : "Loss"} value={`$${Math.abs(profit).toFixed(2)}`} bold positive={profit >= 0} />
                </>
              )}
            </div>
          </div>

          {/* Live Tracking Map */}
          <div className="bg-white rounded-xl shadow-md p-5">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-spotter-800 flex items-center gap-2">
                <Navigation className="w-4 h-4 text-spotter-500" /> Live Tracking
              </h3>
              {lastPos && (
                <span className="text-xs text-gray-500">
                  Last seen: {new Date(lastPos.timestamp).toLocaleString()}
                </span>
              )}
            </div>

            {routeInfo ? (
              <RouteMap
                route={routeInfo}
                stops={stopMarkers}
                restStops={[]}
                positions={displayPositions}
              />
            ) : (
              <div className="h-[200px] rounded-lg bg-spotter-50 flex items-center justify-center text-xs text-gray-400">
                {displayPositions.length > 0 ? (
                  <div className="text-center space-y-2">
                    <Navigation className="w-6 h-6 mx-auto text-spotter-300" />
                    <p className="font-mono text-spotter-700">
                      {lastPos!.lat.toFixed(5)}, {lastPos!.lon.toFixed(5)}
                    </p>
                    <div className="flex items-center justify-center gap-2">
                      {lastPos!.accuracy && <span className="text-gray-400">±{lastPos!.accuracy.toFixed(0)}m</span>}
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        lastPos!.source === "gps" ? "bg-green-100 text-green-700" :
                        lastPos!.source === "whatsapp" ? "bg-blue-100 text-blue-700" :
                        "bg-gray-100 text-gray-600"
                      }`}>{lastPos!.source}</span>
                    </div>
                  </div>
                ) : (
                  <p>No route data. Plan a trip or report a position.</p>
                )}
              </div>
            )}

            <div className="mt-4 pt-3 border-t border-gray-100 space-y-3">
              <div className="flex gap-2">
                <button onClick={reportGPS} disabled={geoLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-spotter-600 text-white rounded-md hover:bg-spotter-700 disabled:opacity-50">
                  {geoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Crosshair className="w-3.5 h-3.5" />}
                  Report My GPS
                </button>
              </div>
              {geoError && <p className="text-xs text-amber-600">{geoError}</p>}

              <div>
                <p className="text-xs text-gray-500 mb-1.5">Or enter coordinates manually:</p>
                <div className="flex gap-2">
                  <input value={manualLat} onChange={e => setManualLat(e.target.value)}
                    placeholder="Lat (e.g. -17.8292)" className="flex-1 px-2 py-1.5 border rounded text-xs" />
                  <input value={manualLon} onChange={e => setManualLon(e.target.value)}
                    placeholder="Lon (e.g. 31.0522)" className="flex-1 px-2 py-1.5 border rounded text-xs" />
                  <button onClick={reportManual} disabled={geoLoading}
                    className="px-3 py-1.5 text-xs bg-spotter-100 text-spotter-700 rounded-md hover:bg-spotter-200 disabled:opacity-50">
                    Add
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-5">
          {trip.customer_name && (
            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3 flex items-center gap-2"><User className="w-4 h-4" /> Customer</h3>
              <div className="space-y-2 text-xs">
                <p className="font-medium text-gray-900">{trip.customer_name}</p>
                {trip.customer_phone && <p className="text-gray-600 flex items-center gap-1"><Phone className="w-3 h-3" /> {trip.customer_phone}</p>}
                {trip.customer_email && <p className="text-gray-600 flex items-center gap-1"><Mail className="w-3 h-3" /> {trip.customer_email}</p>}
                {trip.booking_reference && <p className="text-gray-500 text-[10px]">Ref: {trip.booking_reference}</p>}
              </div>
            </div>
          )}

          {trip.cargo_items && trip.cargo_items.length > 0 && (
            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3 flex items-center gap-2"><Package className="w-4 h-4" /> Cargo ({trip.cargo_items.length} items)</h3>
              <div className="space-y-2">
                {trip.cargo_items.map((item, i) => (
                  <div key={i} className="text-xs bg-spotter-50 rounded p-2">
                    <div className="font-medium text-gray-900">{item.description || "Item"}</div>
                    <div className="text-gray-500 mt-0.5 flex flex-wrap gap-2">
                      <span>Qty: {item.quantity}</span>
                      <span>Weight: {item.estimated_weight_kg}kg</span>
                      {item.dimensions && <span>Dim: {item.dimensions}</span>}
                    </div>
                    {(item.is_fragile || item.needs_packing) && (
                      <div className="flex gap-1 mt-1">
                        {item.is_fragile && <span className="px-1 py-0.5 bg-red-100 text-red-700 rounded text-[10px]">Fragile</span>}
                        {item.needs_packing && <span className="px-1 py-0.5 bg-blue-100 text-blue-700 rounded text-[10px]">Needs Packing</span>}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {images.length > 0 && (
            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3 flex items-center gap-2"><Camera className="w-4 h-4" /> Images ({images.length})</h3>
              <div className="grid grid-cols-2 gap-2">
                {images.map(img => (
                  <a key={img.id} href={img.image} target="_blank" rel="noreferrer" className="block">
                    <img src={img.image} alt={img.caption || "Trip image"} className="w-full h-20 object-cover rounded-md border" />
                    {img.caption && <p className="text-[10px] text-gray-500 mt-0.5 truncate">{img.caption}</p>}
                  </a>
                ))}
              </div>
            </div>
          )}

          <div className="bg-white rounded-xl shadow-md p-5">
            <h3 className="text-sm font-semibold text-spotter-800 mb-3">Update Status</h3>
            <div className="space-y-1.5">
              {STATUS_FLOW[trip.status]?.map(s => (
                <button key={s} onClick={() => handleStatusChange(s)} disabled={updating}
                  className="w-full py-2 px-3 text-sm rounded-md bg-spotter-50 text-spotter-700 hover:bg-spotter-100 disabled:opacity-50 capitalize">
                  {updating ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : `Mark as ${s.replace(/_/g, " ")}`}
                </button>
              ))}
              {STATUS_FLOW[trip.status]?.length === 0 && (
                <p className="text-xs text-gray-500 text-center py-2">No further status updates available</p>
              )}
            </div>
          </div>

          <div className="bg-white rounded-xl shadow-md p-5">
            <h3 className="text-sm font-semibold text-spotter-800 mb-3">Status Timeline</h3>
            <StatusTimeline logs={trip.status_logs ?? []} />
          </div>

          {trip.notes && (
            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-2">Notes</h3>
              <p className="text-xs text-gray-600 whitespace-pre-wrap">{trip.notes}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    dispatched: "bg-blue-100 text-blue-800", at_border: "bg-amber-100 text-amber-800",
    in_transit: "bg-purple-100 text-purple-800", delivered: "bg-green-100 text-green-800",
    paid: "bg-emerald-100 text-emerald-800", cancelled: "bg-red-100 text-red-800",
  };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium capitalize ${colors[status] || ""}`}>{status.replace(/_/g, " ")}</span>;
}

function Stat({ icon: Icon, label, value }: { icon?: React.ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <div className="bg-spotter-50 rounded-lg p-3">
      <div className="flex items-center gap-1 text-spotter-600 text-[10px] font-medium">{Icon && <Icon className="w-3 h-3" />}{label}</div>
      <div className="mt-0.5 text-sm font-bold text-spotter-900 capitalize">{value}</div>
    </div>
  );
}

function CostRow({ label, value, icon: Icon, bold, positive }: {
  label: string; value: string; icon?: React.ComponentType<{ className?: string }>; bold?: boolean; positive?: boolean;
}) {
  return (
    <div className={`flex justify-between ${bold ? "font-semibold text-spotter-900" : "text-gray-700"}`}>
      <span className="flex items-center gap-1">{Icon && <Icon className="w-3 h-3 text-spotter-500" />}{label}</span>
      <span className={positive ? "text-green-700" : positive === false ? "text-red-600" : ""}>{value}</span>
    </div>
  );
}
