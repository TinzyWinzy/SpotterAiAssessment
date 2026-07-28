import { ChevronRight, Crosshair, MapPin, Navigation, Truck, AlertTriangle, Loader2 } from "lucide-react";
import type { Trip } from "../../lib/types";

interface Props {
  trip: Trip;
  onStatusUpdate: (tripId: number, status: string) => Promise<void>;
  onSOS: () => void;
  onViewMap: () => void;
  updating: number | null;
  gpsTracking: boolean;
  onToggleGps: () => void;
  gpsCount: number;
  lastPosition: { lat: number; lon: number } | null;
}

const STATUS_FLOW: Record<string, string[]> = {
  dispatched: ["at_border"],
  at_border: ["in_transit"],
  in_transit: ["delivered"],
  delivered: [],
  paid: [],
  cancelled: [],
};

const STATUS_LABEL: Record<string, string> = {
  dispatched: "Dispatched",
  at_border: "At Border",
  in_transit: "In Transit",
  delivered: "Delivered",
  paid: "Paid",
  cancelled: "Cancelled",
};

export function ActiveTripCard({
  trip, onStatusUpdate, onSOS, onViewMap,
  updating, gpsTracking, onToggleGps, gpsCount, lastPosition,
}: Props) {
  const nextStatuses = STATUS_FLOW[trip.status] || [];

  return (
    <div className="bg-white rounded-xl shadow-md overflow-hidden">
      {/* Header */}
      <div className="bg-spotter-600 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2 text-white">
          <Truck className="w-4 h-4" />
          <span className="text-sm font-bold">Active Trip</span>
        </div>
        <button
          onClick={onSOS}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 active:bg-red-800"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          SOS
        </button>
      </div>

      {/* Route */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#0e7c86] shrink-0" />
          <span className="text-sm text-gray-800 font-medium">{trip.origin}</span>
        </div>
        <div className="flex items-center gap-2 ml-3">
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
        </div>
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#dc2626] shrink-0" />
          <span className="text-sm text-gray-800 font-medium">{trip.destination}</span>
        </div>
      </div>

      {/* Details grid */}
      <div className="px-4 pb-2 grid grid-cols-2 gap-y-1.5 text-xs text-gray-500">
        <span>Distance: <strong className="text-gray-700">{trip.distance_km} km</strong></span>
        {trip.load_weight_tonnes && (
          <span>Weight: <strong className="text-gray-700">{trip.load_weight_tonnes} t</strong></span>
        )}
        {trip.commodity_data && (
          <span className="col-span-2">
            Cargo: <strong className="text-gray-700">{trip.commodity_data.name}</strong>
          </span>
        )}
      </div>

      {/* Status update buttons */}
      {nextStatuses.length > 0 && (
        <div className="px-4 py-2 space-y-1.5">
          <p className="text-[10px] text-gray-400 uppercase tracking-wide font-semibold">Update Status</p>
          <div className="flex gap-2">
            {nextStatuses.map(s => (
              <button
                key={s}
                onClick={() => onStatusUpdate(trip.id, s)}
                disabled={updating === trip.id}
                className="flex-1 py-3 rounded-lg bg-spotter-600 text-white text-sm font-bold hover:bg-spotter-700 active:bg-spotter-800 disabled:opacity-50 transition-colors capitalize min-h-[44px]"
              >
                {updating === trip.id ? (
                  <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                ) : (
                  STATUS_LABEL[s]
                )}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* GPS tracking */}
      <div className="px-4 py-2 border-t border-gray-100">
        <button
          onClick={onToggleGps}
          className={`w-full flex items-center justify-center gap-2 py-3 rounded-lg text-sm font-medium transition-colors min-h-[44px] ${
            gpsTracking
              ? "bg-green-50 text-green-700 border border-green-200"
              : "bg-spotter-50 text-spotter-700 border border-spotter-200"
          }`}
        >
          <Crosshair className={`w-4 h-4 ${gpsTracking ? "animate-pulse" : ""}`} />
          {gpsTracking ? `GPS Active (${gpsCount} reports)` : "Start GPS Tracking"}
        </button>
      </div>

      {/* Position & Map */}
      <div className="px-4 pb-4 space-y-2">
        {lastPosition && (
          <div className="flex items-center gap-1.5 text-[10px] text-gray-400">
            <Navigation className="w-3 h-3 text-spotter-500" />
            {lastPosition.lat.toFixed(5)}, {lastPosition.lon.toFixed(5)}
          </div>
        )}
        <button
          onClick={onViewMap}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-gray-50 text-gray-600 text-sm font-medium hover:bg-gray-100 active:bg-gray-200 transition-colors border border-gray-200"
        >
          <MapPin className="w-4 h-4" />
          View on Live Map
        </button>
      </div>
    </div>
  );
}
