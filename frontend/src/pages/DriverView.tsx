import { useEffect, useState, useCallback, useRef } from "react";
import { logout } from "../lib/auth";
import { fetchTrips, updateTripStatus, triggerSos } from "../lib/api";
import type { Trip, User } from "../lib/types";
import { LogOut, Truck, Wifi, WifiOff, Loader2 } from "lucide-react";
import { ActiveTripCard } from "../components/driver/ActiveTripCard";
import { SOSAlert } from "../components/driver/SOSAlert";
import { useBackgroundGeolocation } from "../lib/useBackgroundGeolocation";
import { useOfflineSync } from "../lib/useOfflineSync";

interface Props {
  user: User;
  onLogout: () => void;
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    dispatched: "bg-blue-100 text-blue-800",
    at_border: "bg-amber-100 text-amber-800",
    in_transit: "bg-purple-100 text-purple-800",
    delivered: "bg-green-100 text-green-800",
    paid: "bg-emerald-100 text-emerald-800",
    cancelled: "bg-red-100 text-red-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${colors[status] || "bg-gray-100 text-gray-800"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function DriverView({ user, onLogout }: Props) {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<number | null>(null);
  const [showSOS, setShowSOS] = useState(false);
  const [gpsEnabled, setGpsEnabled] = useState(false);
  const driverId = user.driver_id;
  const mountedRef = useRef(true);

  const { isOnline, pendingCount } = useOfflineSync();

  const activeTrip = trips.find(t => ["dispatched", "at_border", "in_transit"].includes(t.status));

  const { isWatching, positionCount, currentPosition, error: geoError } = useBackgroundGeolocation({
    tripId: activeTrip?.id,
    enabled: gpsEnabled && !!activeTrip,
  });

  const load = useCallback(() => {
    if (!driverId) return;
    fetchTrips({ page_size: 50 }).then(res => {
      if (!mountedRef.current) return;
      const mine = res.trips.filter(t => t.driver === driverId);
      mine.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setTrips(mine);
      setError(null);
    }).catch(e => {
      if (!mountedRef.current) return;
      setError(e instanceof Error ? e.message : "Failed to load");
    }).finally(() => {
      if (mountedRef.current) setLoading(false);
    });
  }, [driverId]);

  useEffect(() => {
    load();
    return () => { mountedRef.current = false; };
  }, [load]);

  const handleStatusUpdate = useCallback(async (tripId: number, newStatus: string) => {
    setUpdating(tripId);
    try {
      await updateTripStatus(tripId, newStatus);
      await fetchTrips({ page_size: 50 }).then(res => {
        const mine = res.trips.filter(t => t.driver === driverId);
        mine.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setTrips(mine);
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setUpdating(null);
    }
  }, [driverId]);

  const handleSOS = useCallback(async (message: string) => {
    try {
      await triggerSos(activeTrip!.id, {
        message,
        lat: currentPosition?.lat,
        lon: currentPosition?.lon,
      });
      setShowSOS(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "SOS failed");
    }
  }, [activeTrip, currentPosition]);

  const handleViewMap = useCallback(() => {
    const lat = currentPosition?.lat || -19.0;
    const lon = currentPosition?.lon || 29.0;
    window.open(`https://www.google.com/maps?q=${lat},${lon}`, "_blank");
  }, [currentPosition]);

  const completedTrips = trips.filter(t => ["delivered", "paid", "cancelled"].includes(t.status));

  if (loading) {
    return (
      <div className="min-h-screen bg-spotter-50 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-spotter-500" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-spotter-50 flex flex-col">
      <header className="bg-spotter-700 text-white shrink-0">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-full bg-spotter-500 flex items-center justify-center">
              <Truck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold">TruckLedger</h1>
              <p className="text-[10px] text-spotter-200">{user.username}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isOnline ? (
              <Wifi className="w-3.5 h-3.5 text-green-300" />
            ) : (
              <WifiOff className="w-3.5 h-3.5 text-amber-300" />
            )}
            <button onClick={async () => { await logout(); onLogout(); }}
              className="p-2 rounded-md hover:bg-spotter-600">
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
        {pendingCount > 0 && (
          <div className="bg-amber-500/20 px-4 py-1.5 text-[10px] text-amber-200 text-center">
            {pendingCount} pending update{pendingCount !== 1 ? "s" : ""} — will sync when online
          </div>
        )}
      </header>

      <main className="flex-1 overflow-y-auto">
        <div className="max-w-md mx-auto px-4 py-4 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-800">{error}</div>
          )}

          {geoError && gpsEnabled && (
            <div className="p-2 bg-amber-50 border border-amber-200 rounded-lg text-[11px] text-amber-700">
              GPS: {geoError}
            </div>
          )}

          {activeTrip ? (
            <ActiveTripCard
              trip={activeTrip}
              onStatusUpdate={handleStatusUpdate}
              onSOS={() => setShowSOS(true)}
              onViewMap={handleViewMap}
              updating={updating}
              gpsTracking={isWatching}
              onToggleGps={() => setGpsEnabled(!gpsEnabled)}
              gpsCount={positionCount}
              lastPosition={currentPosition}
            />
          ) : (
            <div className="bg-white rounded-xl shadow-md p-8 text-center">
              <Truck className="w-12 h-12 mx-auto text-spotter-200 mb-3" />
              <p className="text-sm text-gray-500 font-medium">No active trips</p>
              <p className="text-xs text-gray-400 mt-1">No dispatched or in-progress trips assigned to you.</p>
            </div>
          )}

          {completedTrips.length > 0 && (
            <div className="bg-white rounded-xl shadow-md">
              <div className="px-4 py-3 border-b border-gray-100">
                <h2 className="text-sm font-bold text-spotter-800">
                  Recent Trips ({completedTrips.length})
                </h2>
              </div>
              <div className="divide-y divide-gray-50">
                {completedTrips.slice(0, 10).map(t => (
                  <div key={t.id} className="flex items-center justify-between px-4 py-3">
                    <div className="min-w-0 flex-1">
                      <div className="text-sm text-gray-800 font-medium truncate">
                        {t.origin} → {t.destination}
                      </div>
                      <div className="text-xs text-gray-400 mt-0.5">
                        {new Date(t.created_at).toLocaleDateString()} · {t.distance_km} km
                        {t.commodity_data && ` · ${t.commodity_data.name}`}
                      </div>
                    </div>
                    <div className="ml-3 shrink-0">
                      <StatusBadge status={t.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>

      {showSOS && (
        <SOSAlert
          onConfirm={handleSOS}
          onDismiss={() => setShowSOS(false)}
        />
      )}
    </div>
  );
}
