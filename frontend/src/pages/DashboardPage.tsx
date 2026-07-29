import { useEffect, useState } from "react";
import {
  Truck, MapPin, DollarSign, TrendingUp, Fuel, AlertTriangle,
  RefreshCw,
} from "lucide-react";
import { fetchDashboard } from "../lib/api";
import type { DashboardMetrics } from "../lib/types";

export function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const m = await fetchDashboard();
      setMetrics(m);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-spotter-800">Dashboard</h2>
          <p className="text-sm text-gray-500">Fleet performance overview</p>
        </div>
        <button onClick={load} disabled={busy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-spotter-100 text-spotter-700 rounded-md hover:bg-spotter-200">
          <RefreshCw className={`w-4 h-4 ${busy ? "animate-spin" : ""}`} /> Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">{error}</div>
      )}

      {metrics && (
        <>
          <section className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            <Kpi icon={MapPin} label="Total Trips" value={metrics.totals.trips} sub={`${metrics.window.trips_30d} in 30d`} />
            <Kpi icon={Truck} label="Active Vehicles" value={`${metrics.totals.active_vehicles}/${metrics.totals.vehicles}`} sub="fleet size" />
            <Kpi icon={MapPin} label="Total km" value={metrics.totals.km.toLocaleString()} sub={`${metrics.totals.avg_km_per_trip} avg/trip`} />
            <Kpi icon={DollarSign} label="Revenue" value={`$${Number(metrics.totals.revenue_usd || 0).toLocaleString()}`} />
            <Kpi icon={TrendingUp} label="Est. Profit" value={`$${Number(metrics.totals.estimated_profit_usd || 0).toLocaleString()}`}
              sub={metrics.totals.estimated_profit_usd > 0 ? "positive" : "negative"}
              positive={metrics.totals.estimated_profit_usd > 0} />
            <Kpi icon={Fuel} label="Fuel Efficiency" value={`${metrics.fuel.fleet_efficiency_l_100km} L/100km`}
              sub={`${metrics.fuel.total_litres.toFixed(0)}L total`} />
            <Kpi icon={AlertTriangle} label="Trips (7d)" value={metrics.window.trips_7d} />
            <Kpi icon={TrendingUp} label="This Month" value={metrics.comparison.trips_this_month}
              sub={`vs ${metrics.comparison.trips_last_month} last`} />
          </section>

          {metrics.window.sparkline_30d.length > 0 && (
            <section className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3">Trips — last 30 days</h3>
              <Sparkline data={metrics.window.sparkline_30d} />
            </section>
          )}

          <section className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3">Top Routes</h3>
              {metrics.top_routes.length === 0 ? (
                <p className="text-xs text-gray-500">No data</p>
              ) : (
                <table className="w-full text-xs">
                  <thead className="text-gray-500 uppercase border-b"><tr><th className="text-left py-1">Route</th><th className="text-right py-1">Trips</th><th className="text-right py-1">Km</th></tr></thead>
                  <tbody>
                    {metrics.top_routes.map((r, i) => (
                      <tr key={i} className="border-b last:border-0">
                        <td className="py-1">{r.origin} → {r.destination}</td>
                        <td className="py-1 text-right">{r.count}</td>
                        <td className="py-1 text-right">{r.km}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3">Top Drivers</h3>
              {metrics.top_drivers.length === 0 ? (
                <p className="text-xs text-gray-500">No data</p>
              ) : (
                <ol className="space-y-1 text-xs">
                  {metrics.top_drivers.map((d, i) => (
                    <li key={d.id} className="flex justify-between px-3 py-2 bg-spotter-50/50 rounded">
                      <span><strong className="text-spotter-700 mr-1">#{i + 1}</strong>{d.name}</span>
                      <span className="text-gray-600">{d.trips} trips · {d.km} km</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>

            <div className="bg-white rounded-xl shadow-md p-5">
              <h3 className="text-sm font-semibold text-spotter-800 mb-3">Top Vehicles</h3>
              {metrics.top_vehicles.length === 0 ? (
                <p className="text-xs text-gray-500">No data</p>
              ) : (
                <ol className="space-y-1 text-xs">
                  {metrics.top_vehicles.map((v, i) => (
                    <li key={v.id} className="flex justify-between px-3 py-2 bg-spotter-50/50 rounded">
                      <span><strong className="text-spotter-700 mr-1">#{i + 1}</strong>{v.plate}</span>
                      <span className="text-gray-600">{v.trips} trips · {v.km} km</span>
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </section>
        </>
      )}

      {!metrics && !error && !busy && (
        <div className="text-center text-gray-500 py-10">No data. Seed the database first.</div>
      )}
    </div>
  );
}

function Kpi({ icon: Icon, label, value, sub, positive }: {
  icon: React.ComponentType<{ className?: string }>;
  label: string; value: string | number; sub?: string; positive?: boolean;
}) {
  return (
    <div className="bg-white rounded-xl shadow-md p-4">
      <div className="flex items-center gap-1.5 text-spotter-600 text-xs font-medium">
        <Icon className="w-4 h-4" /><span>{label}</span>
      </div>
      <div className={`mt-1 text-xl font-bold ${positive === false ? "text-red-600" : "text-spotter-900"}`}>{value}</div>
      {sub && <div className="text-[10px] text-gray-400">{sub}</div>}
    </div>
  );
}

function Sparkline({ data }: { data: { date: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  const w = 600; const h = 60; const bw = w / data.length;
  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-16" preserveAspectRatio="none">
        {data.map((d, i) => {
          const bh = (d.count / max) * (h - 4);
          return <rect key={d.date} x={i * bw + 0.5} y={h - bh} width={Math.max(1, bw - 1)} height={bh} fill="#0e7c86" opacity={d.count > 0 ? 0.85 : 0.15}><title>{d.date}: {d.count}</title></rect>;
        })}
      </svg>
      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
        <span>{data[0]?.date}</span><span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
}
