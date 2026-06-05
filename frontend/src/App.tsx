import { useState } from "react";
import { TripForm, type FormData } from "./components/TripForm";
import { RouteMap } from "./components/RouteMap";
import { DailyLog } from "./components/DailyLog";
import { planTrip } from "./lib/api";
import { exportTripPdf } from "./lib/pdfExport";
import type { TripResponse } from "./lib/types";
import { Download, AlertCircle, Truck, FileText, MapPin, Clock } from "lucide-react";

function App() {
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (data: FormData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await planTrip(data);
      if (!result.ok) {
        setError(result.warnings?.[0] || "Trip planning failed");
        return;
      }
      setTrip(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-spotter-50 to-gray-50">
      {/* Header */}
      <header className="bg-gradient-to-r from-spotter-700 to-spotter-600 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center">
              <Truck className="w-6 h-6 text-spotter-600" />
            </div>
            <div>
              <h1 className="text-xl font-bold">Spotter Trip Planner</h1>
              <p className="text-xs text-spotter-100">HOS-compliant route + daily log generator</p>
            </div>
          </div>
          <div className="text-xs text-spotter-100 hidden md:block">
            FMCSA Property-Carrying • 70hr/8day • 11/14/30/10/34
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Form panel */}
        <aside className="lg:col-span-4">
          <div className="bg-white rounded-xl shadow-md p-5 sticky top-6">
            <TripForm onSubmit={handleSubmit} loading={loading} />

            {error && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 shrink-0" />
                <p className="text-xs text-red-800">{error}</p>
              </div>
            )}
          </div>
        </aside>

        {/* Results panel */}
        <section className="lg:col-span-8 space-y-5">
          {!trip && !loading && (
            <div className="bg-white rounded-xl shadow-md p-10 text-center text-gray-500">
              <Truck className="w-12 h-12 mx-auto text-spotter-300 mb-3" />
              <h3 className="text-base font-semibold text-gray-700">No trip planned yet</h3>
              <p className="text-sm mt-1">Enter your stops on the left and click <strong>Plan Trip</strong>.</p>
              <p className="text-xs mt-4 text-gray-400">
                The planner geocodes your inputs, computes the OSRM route, then generates a fully
                HOS-compliant timeline with 24-hour daily log sheets.
              </p>
            </div>
          )}

          {loading && (
            <div className="bg-white rounded-xl shadow-md p-10 text-center text-gray-500">
              <div className="w-8 h-8 border-4 border-spotter-200 border-t-spotter-600 rounded-full animate-spin mx-auto mb-3" />
              <p className="text-sm">Geocoding + routing + HOS planning…</p>
            </div>
          )}

          {trip && (
            <>
              {/* Summary card */}
              <div className="bg-white rounded-xl shadow-md p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-lg font-semibold text-spotter-800">Trip Summary</h2>
                  <button
                    onClick={() => exportTripPdf(trip.days, trip.route, trip.stops)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-spotter-600 hover:bg-spotter-700 text-white rounded-md"
                  >
                    <Download className="w-4 h-4" /> Export PDF
                  </button>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                  <Stat
                    icon={<MapPin className="w-4 h-4" />}
                    label="Distance"
                    value={`${trip.total_distance_mi.toFixed(0)} mi`}
                  />
                  <Stat
                    icon={<Clock className="w-4 h-4" />}
                    label="Est. Drive"
                    value={`${trip.route.duration_h.toFixed(1)} hr`}
                  />
                  <Stat
                    icon={<FileText className="w-4 h-4" />}
                    label="Log Sheets"
                    value={`${trip.days.length} day${trip.days.length > 1 ? "s" : ""}`}
                  />
                  <Stat
                    icon={<Truck className="w-4 h-4" />}
                    label="Cycle Used"
                    value={`${trip.cycle_used_hrs.toFixed(1)} / 70 hr`}
                  />
                </div>

                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  {trip.stops.map((s, i) => (
                    <span
                      key={i}
                      className="px-2 py-1 rounded-full bg-spotter-50 text-spotter-700 border border-spotter-200"
                    >
                      <strong className="capitalize">{s.kind}:</strong> {s.label}
                    </span>
                  ))}
                </div>
              </div>

              {/* Map */}
              <div className="bg-white rounded-xl shadow-md p-5">
                <h2 className="text-lg font-semibold text-spotter-800 mb-3">Route Map</h2>
                <RouteMap route={trip.route} stops={trip.stops} restStops={trip.rest_stops} />
              </div>

              {/* Rest stops list */}
              {trip.rest_stops && trip.rest_stops.length > 0 && (
                <div className="bg-white rounded-xl shadow-md p-5">
                  <h2 className="text-lg font-semibold text-spotter-800 mb-3">
                    Stops &amp; Rests ({trip.rest_stops.length})
                  </h2>
                  <ol className="space-y-2 text-sm">
                    {trip.rest_stops.map((r, i) => (
                      <li
                        key={`${r.day}-${i}`}
                        className="flex items-center gap-3 px-3 py-2 bg-spotter-50/50 border border-spotter-100 rounded-md"
                      >
                        <span
                          className="w-7 h-7 flex items-center justify-center rounded-full text-white text-xs font-bold"
                          style={{
                            background:
                              r.kind === "fuel" ? "#7c3aed"
                              : r.kind === "break" ? "#f59e0b"
                              : r.kind === "rest" ? "#0e7c86"
                              : "#6b7280",
                          }}
                        >
                          {r.kind === "fuel" ? "⛽"
                            : r.kind === "break" ? "☕"
                            : r.kind === "rest" ? "🛏"
                            : "•"}
                        </span>
                        <div className="flex-1">
                          <div className="font-medium text-gray-900">{r.remark}</div>
                          <div className="text-xs text-gray-500">
                            {r.label} · {r.day} · {r.duration_h}h · {r.cumulative_miles} mi cumulative
                          </div>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              {/* Daily logs */}
              <div>
                <h2 className="text-lg font-semibold text-spotter-800 mb-2 px-1">
                  Daily Log Sheets
                </h2>
                {trip.days.map((d, i) => (
                  <DailyLog key={d.date + i} day={d} index={i} totalDays={trip.days.length} />
                ))}
              </div>
            </>
          )}
        </section>
      </main>

      <footer className="max-w-7xl mx-auto px-6 py-6 text-center text-xs text-gray-500">
        Built for the Spotter AI coding assessment • Django + React + OpenStreetMap
      </footer>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-spotter-50 border border-spotter-100 rounded-lg p-3">
      <div className="flex items-center gap-1.5 text-spotter-600 text-xs">
        {icon}
        <span className="font-medium">{label}</span>
      </div>
      <div className="mt-1 text-base font-bold text-spotter-900">{value}</div>
    </div>
  );
}

export default App;
