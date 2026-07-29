import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { fetchTrips } from "../lib/api";
import type { Trip } from "../lib/types";
import { FileText, Loader2, Filter, User } from "lucide-react";

const STATUS_OPTIONS = ["", "inquiry", "quoted", "confirmed", "assigned", "dispatched", "at_border", "in_transit", "delivered", "paid", "cancelled"];

export function TripsPage() {
  const [trips, setTrips] = useState<Trip[]>([]);
  const [total, setTotal] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const navigate = useNavigate();

  async function load(p: number = page, status: string = statusFilter) {
    setLoading(true);
    setError(null);
    try {
      const result = await fetchTrips({ status: status || undefined, page: p, page_size: 20 });
      setTrips(result.trips);
      setTotal(result.total);
      setPage(p);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(1, "");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-spotter-800">Trips</h2>
          <p className="text-sm text-gray-500">{total} total trips</p>
        </div>
        <Link to="/" className="px-3 py-1.5 text-sm bg-spotter-600 text-white rounded-md hover:bg-spotter-700">+ New Trip</Link>
      </div>

      <div className="flex items-center gap-2">
        <Filter className="w-4 h-4 text-gray-400" />
        <select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); load(1, e.target.value); }}
          className="px-3 py-1.5 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none">
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.filter(Boolean).map(s => (
            <option key={s} value={s} className="capitalize">{s.replace(/_/g, " ")}</option>
          ))}
        </select>
        {loading && <Loader2 className="w-4 h-4 animate-spin text-spotter-500" />}
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">{error}</div>}

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        {trips.length === 0 && !loading ? (
          <div className="p-10 text-center text-gray-400">
            <FileText className="w-10 h-10 mx-auto text-spotter-200 mb-3" />
            <p className="text-sm">No trips yet</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-500 uppercase border-b bg-spotter-50/50">
              <tr>
                <th className="text-left py-2 px-4">Route</th>
                <th className="text-left py-2 px-4">Customer</th>
                <th className="text-left py-2 px-4">Driver</th>
                <th className="text-left py-2 px-4">Service</th>
                <th className="text-right py-2 px-4">Km</th>
                <th className="text-right py-2 px-4">Status</th>
                <th className="text-right py-2 px-4">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {trips.map(t => (
                <tr key={t.id} className="border-b last:border-0 hover:bg-spotter-50/30 cursor-pointer"
                  onClick={() => navigate(`/app/trips/${t.id}`)}>
                  <td className="py-2 px-4">
                    <Link to={`/app/trips/${t.id}`} className="text-spotter-700 hover:underline font-medium">
                      {t.origin} → {t.destination}
                    </Link>
                    <div className="text-[10px] text-gray-400">{new Date(t.created_at).toLocaleDateString()}</div>
                  </td>
                  <td className="py-2 px-4">
                    {t.customer_name ? (
                      <div>
                        <span className="text-gray-700 text-xs font-medium flex items-center gap-1"><User className="w-3 h-3" /> {t.customer_name}</span>
                        {t.customer_phone && <div className="text-[10px] text-gray-400">{t.customer_phone}</div>}
                      </div>
                    ) : <span className="text-gray-400">-</span>}
                  </td>
                  <td className="py-2 px-4 text-gray-700">{t.driver_name || "-"}</td>
                  <td className="py-2 px-4">
                    {t.service_type ? <ServiceBadge type={t.service_type} /> : <span className="text-gray-400">-</span>}
                  </td>
                  <td className="py-2 px-4 text-right text-gray-700">{t.distance_km}</td>
                  <td className="py-2 px-4 text-right">
                    <StatusBadge status={t.status} />
                  </td>
                  <td className="py-2 px-4 text-right text-gray-700">
                    {t.revenue_usd != null ? `$${parseFloat(String(t.revenue_usd)).toFixed(0)}` : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {total > 20 && (
        <div className="flex justify-center gap-2">
          {page > 1 && <button onClick={() => load(page - 1)} className="px-3 py-1 text-sm bg-spotter-100 rounded-md">Prev</button>}
          <span className="px-3 py-1 text-sm text-gray-600">Page {page}</span>
          {page * 20 < total && <button onClick={() => load(page + 1)} className="px-3 py-1 text-sm bg-spotter-100 rounded-md">Next</button>}
        </div>
      )}
    </div>
  );
}

function ServiceBadge({ type }: { type: string }) {
  const colors: Record<string, string> = {
    household: "bg-orange-100 text-orange-800",
    grocery: "bg-green-100 text-green-800",
    construction: "bg-yellow-100 text-yellow-800",
    furniture: "bg-purple-100 text-purple-800",
    office: "bg-blue-100 text-blue-800",
    long_distance: "bg-indigo-100 text-indigo-800",
    custom: "bg-gray-100 text-gray-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${colors[type] || "bg-gray-100 text-gray-800"}`}>
      {type.replace(/_/g, " ")}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    inquiry: "bg-yellow-100 text-yellow-800",
    quoted: "bg-blue-100 text-blue-800",
    confirmed: "bg-green-100 text-green-800",
    assigned: "bg-purple-100 text-purple-800",
    dispatched: "bg-indigo-100 text-indigo-800",
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
