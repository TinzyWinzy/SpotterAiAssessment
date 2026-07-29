import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, User, MapPin } from "lucide-react";
import { fetchBookings, assignBooking, fetchDrivers, fetchVehicles } from "../lib/api";
import type { Trip, Driver, Vehicle } from "../lib/types";

const STATUS_LABELS: Record<string, string> = {
  inquiry: "Inquiry", quoted: "Quoted", confirmed: "Confirmed", assigned: "Assigned",
};

const STATUS_ORDER = ["inquiry", "quoted", "confirmed", "assigned"];

export function DispatchPage() {
  const navigate = useNavigate();
  const [bookings, setBookings] = useState<Trip[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [assigning, setAssigning] = useState<number | null>(null);
  const [showAssign, setShowAssign] = useState<number | null>(null);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [selDriver, setSelDriver] = useState("");
  const [selVehicle, setSelVehicle] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [b, d, v] = await Promise.all([
        fetchBookings(),
        fetchDrivers(),
        fetchVehicles(),
      ]);
      setBookings(b.bookings);
      setDrivers(d.drivers);
      setVehicles(v.vehicles);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bookings");
    }
    setLoading(false);
  }

  useEffect(() => { load(); }, []);

  async function handleAssign(tripId: number) {
    if (!selDriver || !selVehicle) return;
    setAssigning(tripId);
    setError(null);
    try {
      await assignBooking(tripId, {
        driver_id: parseInt(selDriver),
        vehicle_id: parseInt(selVehicle),
      });
      setShowAssign(null);
      setSelDriver("");
      setSelVehicle("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to assign driver");
    }
    setAssigning(null);
  }

  const grouped = STATUS_ORDER.map(status => ({
    status,
    label: STATUS_LABELS[status] || status,
    items: bookings.filter(b => b.status === status),
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-900">Dispatch Queue</h1>
        <button onClick={load} className="text-sm text-spotter-600 hover:text-spotter-800">Refresh</button>
      </div>
      
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">{error}</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {grouped.map(group => (
          <div key={group.status}>
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${
                group.status === "inquiry" ? "bg-yellow-400" :
                group.status === "quoted" ? "bg-blue-400" :
                group.status === "confirmed" ? "bg-green-400" : "bg-purple-400"
              }`} />
              {group.label}
              <span className="text-xs text-gray-400">({group.items.length})</span>
            </h3>
            <div className="space-y-2">
              {group.items.map(trip => (
                <div key={trip.id} className="bg-white rounded-lg p-3 shadow-sm border border-gray-200 text-sm">
                  <div className="flex items-start justify-between mb-1">
                    <span className="font-medium text-gray-900 text-xs uppercase px-1.5 py-0.5 rounded bg-gray-100">{trip.service_type || "N/A"}</span>
                    <span className="text-xs text-gray-400">#{trip.booking_reference || trip.id}</span>
                  </div>
                  <p className="text-xs text-gray-600 flex items-center gap-1 mt-1"><MapPin className="w-3 h-3 shrink-0" /> {trip.origin} → {trip.destination}</p>
                  {trip.customer_name && <p className="text-xs text-gray-500 mt-1 flex items-center gap-1"><User className="w-3 h-3" /> {trip.customer_name} {trip.customer_phone && `· ${trip.customer_phone}`}</p>}
                  <div className="flex items-center gap-2 mt-2">
                    {group.status === "inquiry" && (
                      <button onClick={() => navigate(`/app/trips/${trip.id}`)} className="flex-1 text-xs py-1.5 px-2 bg-blue-100 text-blue-700 rounded hover:bg-blue-200">Review & Quote</button>
                    )}
                    {group.status === "confirmed" && (
                      <button onClick={() => { setShowAssign(trip.id); setSelDriver(""); setSelVehicle(""); }} className="flex-1 text-xs py-1.5 px-2 bg-green-100 text-green-700 rounded hover:bg-green-200">
                        Assign Driver
                      </button>
                    )}
                    {group.status === "assigned" && (
                      <button onClick={() => navigate(`/app/trips/${trip.id}`)} className="flex-1 text-xs py-1.5 px-2 bg-spotter-100 text-spotter-700 rounded hover:bg-spotter-200">
                        View Details
                      </button>
                    )}
                    {group.status === "quoted" && (
                      <span className="text-xs text-gray-400">Awaiting customer confirmation</span>
                    )}
                  </div>
                  {showAssign === trip.id && (
                    <div className="mt-2 border-t pt-2 space-y-2">
                      <select value={selDriver} onChange={e => setSelDriver(e.target.value)} className="w-full text-xs border rounded px-2 py-1">
                        <option value="">Select driver...</option>
                        {drivers.filter(d => d.status === "active").map(d => (
                          <option key={d.id} value={d.id}>{d.name} ({d.phone_number})</option>
                        ))}
                      </select>
                      <select value={selVehicle} onChange={e => setSelVehicle(e.target.value)} className="w-full text-xs border rounded px-2 py-1">
                        <option value="">Select vehicle...</option>
                        {vehicles.filter(v => v.status === "active").map(v => (
                          <option key={v.id} value={v.id}>{v.plate} ({v.make} {v.model})</option>
                        ))}
                      </select>
                      <div className="flex gap-2">
                        <button onClick={() => handleAssign(trip.id)} disabled={!selDriver || !selVehicle || assigning === trip.id} className="flex-1 text-xs py-1.5 bg-spotter-600 text-white rounded hover:bg-spotter-700 disabled:opacity-50">
                          {assigning === trip.id ? "Assigning..." : "Assign"}
                        </button>
                        <button onClick={() => setShowAssign(null)} className="text-xs py-1.5 px-2 text-gray-500 hover:text-gray-700">Cancel</button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
              {group.items.length === 0 && (
                <p className="text-xs text-gray-400 text-center py-4">No {group.label.toLowerCase()} bookings</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
