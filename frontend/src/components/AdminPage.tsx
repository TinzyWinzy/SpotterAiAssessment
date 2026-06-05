import { useEffect, useState } from "react";
import { fetchMetrics, fetchAdminTrips, login, logout, fetchMe, type AdminMetrics, type AdminTripRow, type User } from "../lib/api";
import { LogIn, LogOut, RefreshCw, Truck, MapPin, Clock, FileText, BarChart3, Users } from "lucide-react";

type State = "loading" | "anonymous" | "authenticated" | "forbidden";

export function AdminPage() {
  const [state, setState] = useState<State>("loading");
  const [user, setUser] = useState<User | null>(null);
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [trips, setTrips] = useState<AdminTripRow[] | null>(null);
  const [tripsTotal, setTripsTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = localStorage.getItem("spotter_token");
    if (!t) {
      setState("anonymous");
      return;
    }
    (async () => {
      const me = await fetchMe();
      if (!me) {
        localStorage.removeItem("spotter_token");
        setState("anonymous");
        return;
      }
      if (!me.is_admin) {
        setUser(me);
        setState("forbidden");
        return;
      }
      setUser(me);
      setState("authenticated");
      await loadAll();
    })();
  }, []);

  async function loadAll() {
    setBusy(true);
    setError(null);
    try {
      const [m, t] = await Promise.all([fetchMetrics(), fetchAdminTrips(1, 20)]);
      setMetrics(m);
      setTrips(t.trips);
      setTripsTotal(t.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setBusy(false);
    }
  }

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const r = await login(username, password);
      localStorage.setItem("spotter_token", r.token);
      setUser(r.user);
      if (!r.user.is_admin) {
        setState("forbidden");
        return;
      }
      setState("authenticated");
      setUsername("");
      setPassword("");
      await loadAll();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // ignore — local token is the source of truth client-side
    }
    localStorage.removeItem("spotter_token");
    setUser(null);
    setMetrics(null);
    setTrips(null);
    setState("anonymous");
  }

  if (state === "loading") {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        <div className="w-8 h-8 border-4 border-spotter-200 border-t-spotter-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (state === "anonymous" || state === "forbidden") {
    return (
      <div className="min-h-screen bg-gradient-to-br from-spotter-50 to-gray-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-xl shadow-md p-8 w-full max-w-sm">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-full bg-spotter-600 flex items-center justify-center">
              <Truck className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-spotter-800">Spotter Admin</h1>
              <p className="text-xs text-gray-500">Sign in to view fleet metrics</p>
            </div>
          </div>

          {state === "forbidden" ? (
            <div className="p-3 bg-amber-50 border border-amber-200 rounded-md text-sm text-amber-800">
              You're signed in as <strong>{user?.username}</strong>, but this account doesn't
              have admin access.
              <button
                onClick={handleLogout}
                className="block mt-2 text-xs underline text-amber-700"
              >
                Sign out
              </button>
            </div>
          ) : (
            <form onSubmit={handleLogin} className="space-y-3">
              <Field label="Username" id="admin-username">
                <input
                  id="admin-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-spotter-500"
                  required
                  autoComplete="username"
                />
              </Field>
              <Field label="Password" id="admin-password">
                <input
                  id="admin-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-spotter-500"
                  required
                  autoComplete="current-password"
                />
              </Field>
              {error && <p className="text-xs text-red-600">{error}</p>}
              <button
                type="submit"
                disabled={busy}
                className="w-full flex items-center justify-center gap-2 bg-spotter-600 hover:bg-spotter-700 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-md"
              >
                <LogIn className="w-4 h-4" /> {busy ? "Signing in…" : "Sign in"}
              </button>
              <p className="text-xs text-gray-400 text-center pt-2">
                Demo: <code className="text-gray-600">admin / admin</code>
              </p>
            </form>
          )}

          <div className="mt-5 text-center">
            <a href="#/" className="text-xs text-spotter-600 hover:underline">
              ← Back to trip planner
            </a>
          </div>
        </div>
      </div>
    );
  }

  // authenticated
  return (
    <div className="min-h-screen bg-gradient-to-br from-spotter-50 to-gray-50">
      <header className="bg-gradient-to-r from-spotter-700 to-spotter-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center">
              <BarChart3 className="w-5 h-5 text-spotter-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Spotter Admin</h1>
              <p className="text-xs text-spotter-100">
                Signed in as {user?.username}
                {user?.driver_id ? ` (driver #${user.driver_id})` : ""}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={loadAll}
              disabled={busy}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white/10 hover:bg-white/20 rounded-md"
            >
              <RefreshCw className={`w-4 h-4 ${busy ? "animate-spin" : ""}`} /> Refresh
            </button>
            <a
              href="#/"
              className="px-3 py-1.5 text-sm bg-white/10 hover:bg-white/20 rounded-md"
            >
              Trip Planner
            </a>
            <button
              onClick={handleLogout}
              className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-white/10 hover:bg-white/20 rounded-md"
            >
              <LogOut className="w-4 h-4" /> Sign out
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 space-y-5">
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">
            {error}
          </div>
        )}

        {metrics && (
          <>
            <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <KpiCard icon={<Truck className="w-4 h-4" />} label="Trips" value={metrics.totals.trips} />
              <KpiCard
                icon={<MapPin className="w-4 h-4" />}
                label="Total miles"
                value={metrics.totals.miles.toLocaleString()}
              />
              <KpiCard
                icon={<Clock className="w-4 h-4" />}
                label="On-duty hrs"
                value={metrics.totals.on_duty_hrs.toFixed(0)}
              />
              <KpiCard
                icon={<FileText className="w-4 h-4" />}
                label="Avg mi / trip"
                value={metrics.totals.avg_miles_per_trip.toFixed(0)}
              />
              <KpiCard
                icon={<Users className="w-4 h-4" />}
                label="Drivers"
                value={`${metrics.totals.drivers_with_trips} / ${metrics.totals.drivers}`}
              />
              <KpiCard
                icon={<Clock className="w-4 h-4" />}
                label="Trips (7d)"
                value={metrics.window.trips_7d}
              />
              <KpiCard
                icon={<Clock className="w-4 h-4" />}
                label="Trips (30d)"
                value={metrics.window.trips_30d}
              />
              <KpiCard
                icon={<BarChart3 className="w-4 h-4" />}
                label="With history"
                value={metrics.totals.drivers_with_history}
              />
            </section>

            <section className="bg-white rounded-xl shadow-md p-5">
              <h2 className="text-base font-semibold text-spotter-800 mb-3">
                Trips per day — last 30 days
              </h2>
              <Sparkline data={metrics.window.sparkline_30d} />
            </section>

            <section className="grid grid-cols-1 lg:grid-cols-2 gap-5">
              <div className="bg-white rounded-xl shadow-md p-5">
                <h2 className="text-base font-semibold text-spotter-800 mb-3">
                  Top routes
                </h2>
                {metrics.top_routes.length === 0 ? (
                  <p className="text-sm text-gray-500">No trips yet.</p>
                ) : (
                  <table className="w-full text-sm">
                    <thead className="text-xs text-gray-500 uppercase border-b">
                      <tr>
                        <th className="text-left py-1.5">Route</th>
                        <th className="text-right py-1.5">Trips</th>
                        <th className="text-right py-1.5">Miles</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.top_routes.map((r, i) => (
                        <tr key={i} className="border-b last:border-0">
                          <td className="py-1.5 text-gray-800">
                            {r.origin} → {r.destination}
                          </td>
                          <td className="py-1.5 text-right">{r.count}</td>
                          <td className="py-1.5 text-right">{r.miles}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>

              <div className="bg-white rounded-xl shadow-md p-5">
                <h2 className="text-base font-semibold text-spotter-800 mb-3">
                  Cycle-usage distribution
                </h2>
                <Histogram data={metrics.cycle_histogram} />
              </div>
            </section>

            <section className="bg-white rounded-xl shadow-md p-5">
              <h2 className="text-base font-semibold text-spotter-800 mb-3">
                Top drivers by miles
              </h2>
              {metrics.top_drivers.length === 0 ? (
                <p className="text-sm text-gray-500">No driver data.</p>
              ) : (
                <ol className="space-y-1.5 text-sm">
                  {metrics.top_drivers.map((d, i) => (
                    <li
                      key={d.id}
                      className="flex items-center justify-between px-3 py-2 bg-spotter-50/50 border border-spotter-100 rounded-md"
                    >
                      <span>
                        <strong className="text-spotter-700 mr-2">#{i + 1}</strong>
                        {d.name}
                      </span>
                      <span className="text-xs text-gray-600">
                        {d.trips} trip{d.trips !== 1 ? "s" : ""} · {d.miles.toFixed(0)} mi
                      </span>
                    </li>
                  ))}
                </ol>
              )}
            </section>
          </>
        )}

        <section className="bg-white rounded-xl shadow-md p-5">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-base font-semibold text-spotter-800">
              Recent trips ({tripsTotal})
            </h2>
          </div>
          {trips === null ? (
            <p className="text-sm text-gray-500">Loading…</p>
          ) : trips.length === 0 ? (
            <p className="text-sm text-gray-500">
              No trips yet. Plan one from the{" "}
              <a href="#/" className="text-spotter-600 underline">
                trip planner
              </a>{" "}
              to see it here.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs text-gray-500 uppercase border-b">
                  <tr>
                    <th className="text-left py-1.5">When</th>
                    <th className="text-left py-1.5">Driver</th>
                    <th className="text-left py-1.5">Route</th>
                    <th className="text-right py-1.5">Miles</th>
                    <th className="text-right py-1.5">Days</th>
                    <th className="text-right py-1.5">Cycle</th>
                  </tr>
                </thead>
                <tbody>
                  {trips.map((t) => (
                    <tr key={t.id} className="border-b last:border-0">
                      <td className="py-1.5 text-gray-600 text-xs">
                        {new Date(t.created_at).toLocaleString()}
                      </td>
                      <td className="py-1.5">{t.driver_name ?? "—"}</td>
                      <td className="py-1.5 text-gray-800">
                        {t.current_location} → {t.dropoff_location}
                      </td>
                      <td className="py-1.5 text-right">{t.total_miles.toFixed(0)}</td>
                      <td className="py-1.5 text-right">{t.total_days}</td>
                      <td className="py-1.5 text-right">
                        {t.final_cycle_used.toFixed(1)}h
                        {t.recap_approximate && (
                          <span
                            title="Recap is approximate (no driver history)"
                            className="ml-1 text-amber-600"
                          >
                            ~
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function Field({
  label,
  id,
  children,
}: {
  label: string;
  id: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-gray-700 mb-1">
        {label}
      </label>
      {children}
    </div>
  );
}

function KpiCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="bg-white rounded-xl shadow-md p-4">
      <div className="flex items-center gap-1.5 text-spotter-600 text-xs font-medium">
        {icon}
        <span>{label}</span>
      </div>
      <div className="mt-1.5 text-2xl font-bold text-spotter-900">{value}</div>
    </div>
  );
}

function Sparkline({ data }: { data: { date: string; count: number }[] }) {
  if (data.length === 0) return null;
  const max = Math.max(1, ...data.map((d) => d.count));
  const w = 800;
  const h = 80;
  const bw = w / data.length;
  return (
    <div className="w-full">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-20" preserveAspectRatio="none">
        {data.map((d, i) => {
          const bh = (d.count / max) * (h - 4);
          return (
            <rect
              key={d.date}
              x={i * bw + 0.5}
              y={h - bh}
              width={Math.max(1, bw - 1)}
              height={bh}
              fill="#0e7c86"
              opacity={d.count > 0 ? 0.85 : 0.15}
            >
              <title>
                {d.date}: {d.count} trip{d.count !== 1 ? "s" : ""}
              </title>
            </rect>
          );
        })}
      </svg>
      <div className="flex justify-between text-xs text-gray-400 mt-1">
        <span>{data[0]?.date}</span>
        <span>{data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
}

function Histogram({ data }: { data: { label: string; count: number }[] }) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div className="space-y-1.5">
      {data.map((b) => (
        <div key={b.label} className="flex items-center gap-2 text-xs">
          <span className="w-16 text-gray-600">{b.label}</span>
          <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
            <div
              className="h-full bg-spotter-500"
              style={{ width: `${(b.count / max) * 100}%` }}
            />
          </div>
          <span className="w-8 text-right text-gray-700 font-medium">{b.count}</span>
        </div>
      ))}
    </div>
  );
}
