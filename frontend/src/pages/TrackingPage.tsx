import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { Loader2, Truck, MapPin, Phone, User, Package, RefreshCw, AlertCircle } from "lucide-react";
import { trackPublicBooking } from "../lib/api";
import type { TrackingData } from "../lib/types";

const STATUS_FLOW: Record<string, { label: string; step: number }> = {
  inquiry: { label: "Inquiry Received", step: 0 },
  quoted: { label: "Quote Sent", step: 1 },
  confirmed: { label: "Booking Confirmed", step: 2 },
  assigned: { label: "Driver Assigned", step: 3 },
  dispatched: { label: "Driver En Route", step: 4 },
  at_border: { label: "At Border", step: 5 },
  in_transit: { label: "In Transit", step: 6 },
  delivered: { label: "Delivered", step: 7 },
  paid: { label: "Paid", step: 8 },
  cancelled: { label: "Cancelled", step: -1 },
};

export function TrackingPage() {
  const { ref } = useParams<{ ref: string }>();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";

  const [data, setData] = useState<TrackingData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    if (!ref || !token) {
      setError("Invalid tracking link");
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await trackPublicBooking(ref, token);
      setData(result);
    } catch (e: any) {
      setError(e.message || "Failed to load tracking data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [ref, token]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex items-center gap-2 text-gray-500"><Loader2 className="w-5 h-5 animate-spin" /> Loading tracking...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white rounded-xl p-8 shadow-sm max-w-md text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-gray-900">Tracking not found</h2>
          <p className="text-sm text-gray-500 mt-2">{error || "This tracking link is invalid or expired."}</p>
        </div>
      </div>
    );
  }

  const statusInfo = STATUS_FLOW[data.status] || { label: data.status, step: 0 };
  const currentStep = statusInfo.step;
  const isCancelled = data.status === "cancelled";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 mb-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs text-gray-500">Booking Reference</p>
            <button onClick={load} className="flex items-center gap-1 text-xs text-spotter-600 hover:text-spotter-800"><RefreshCw className="w-3 h-3" /> Refresh</button>
          </div>
          <p className="text-2xl font-mono font-bold text-spotter-700">{data.booking_reference}</p>
          <div className={`mt-3 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium ${isCancelled ? "bg-red-100 text-red-700" : "bg-spotter-100 text-spotter-700"}`}>
            <Truck className="w-4 h-4" /> {statusInfo.label}
          </div>
        </div>

        {/* Progress timeline */}
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Progress</h3>
          <div className="relative">
            {!isCancelled ? (
              <div className="space-y-0">
                {Object.entries(STATUS_FLOW).filter(([_, v]) => v.step >= 0).map(([key, info]) => (
                  <div key={key} className="flex items-start gap-3 py-1.5">
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center mt-0.5 shrink-0 ${currentStep >= info.step ? "border-spotter-600 bg-spotter-600" : "border-gray-300 bg-white"}`}>
                      {currentStep >= info.step && <div className="w-2 h-2 rounded-full bg-white" />}
                    </div>
                    <span className={`text-sm ${currentStep >= info.step ? "text-gray-900 font-medium" : "text-gray-400"}`}>{info.label}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center gap-3 py-2">
                <div className="w-5 h-5 rounded-full border-2 border-red-500 bg-red-500 flex items-center justify-center shrink-0">
                  <div className="w-2 h-2 rounded-full bg-white" />
                </div>
                <span className="text-sm text-red-600 font-medium">Booking Cancelled</span>
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5"><MapPin className="w-4 h-4 text-spotter-600" /> Route</h3>
            <p className="text-sm font-medium text-gray-900">{data.origin_address || data.origin}</p>
            <p className="text-xs text-gray-400 my-1 text-center">↓</p>
            <p className="text-sm font-medium text-gray-900">{data.destination_address || data.destination}</p>
            <p className="text-xs text-gray-500 mt-2">{data.distance_km.toFixed(0)} km</p>
          </div>

          {data.driver_name && (
            <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5"><User className="w-4 h-4 text-spotter-600" /> Driver</h3>
              <p className="text-sm font-medium text-gray-900">{data.driver_name}</p>
              {data.driver_phone && (
                <a href={`tel:${data.driver_phone}`} className="text-sm text-spotter-600 hover:underline flex items-center gap-1 mt-1">
                  <Phone className="w-3.5 h-3.5" /> {data.driver_phone}
                </a>
              )}
              {data.vehicle_plate && <p className="text-xs text-gray-500 mt-1">{data.vehicle_plate}</p>}
            </div>
          )}
        </div>

        {/* Cargo */}
        {data.cargo_items && data.cargo_items.length > 0 && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200 mb-4">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1.5"><Package className="w-4 h-4 text-spotter-600" /> Cargo</h3>
            <div className="space-y-2">
              {data.cargo_items.map((item, i) => (
                <div key={i} className="flex items-start gap-2 text-sm">
                  <div className="w-1.5 h-1.5 rounded-full bg-gray-400 mt-2 shrink-0" />
                  <div>
                    <span className="text-gray-900">{item.description}</span>
                    <span className="text-gray-500 ml-1">x{item.quantity}</span>
                    {item.is_fragile && <span className="ml-2 text-xs text-amber-600">Fragile</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Status timeline */}
        {data.status_logs && data.status_logs.length > 0 && (
          <div className="bg-white rounded-xl p-5 shadow-sm border border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Updates</h3>
            <div className="space-y-2">
              {data.status_logs.slice(0, 10).map((log) => (
                <div key={log.id} className="flex items-start gap-2 text-sm">
                  <div className="w-2 h-2 rounded-full bg-spotter-400 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-gray-700">{STATUS_FLOW[log.to_status]?.label || log.to_status}</p>
                    <p className="text-xs text-gray-400">{new Date(log.timestamp).toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.pickup_notes && (
          <div className="mt-4 text-xs text-gray-400 text-center">
            <p>Notes: {data.pickup_notes}</p>
          </div>
        )}
      </div>
    </div>
  );
}
