import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { planTrip, estimateTrip, fetchVehicles, fetchDrivers, fetchCommodities, fetchCommodityCategories, fetchServices } from "../lib/api";
import { RouteMap } from "../components/RouteMap";
import { CommoditySelector } from "../components/CommoditySelector";
import type { TripResponse, Vehicle, Driver, TripEstimateResponse, Commodity, CommodityCategory, ServiceType, CargoItem } from "../lib/types";
import { Truck, Loader2, Plus, X, DollarSign, Fuel, User, MapPin, ArrowLeftRight, Copy, Check, Package, Calendar } from "lucide-react";

type Region = "us" | "sadc";

const REGION_PRESETS: Record<Region, { label: string; origin: string; destination: string }[]> = {
  us: [
    { label: "NYC → Philly", origin: "New York, NY", destination: "Philadelphia, PA" },
    { label: "Philly → Baltimore", origin: "Philadelphia, PA", destination: "Baltimore, MD" },
    { label: "LA → Phoenix", origin: "Los Angeles, CA", destination: "Phoenix, AZ" },
    { label: "Chicago → Detroit", origin: "Chicago, IL", destination: "Detroit, MI" },
    { label: "Atlanta → Charlotte", origin: "Atlanta, GA", destination: "Charlotte, NC" },
    { label: "Denver → SLC", origin: "Denver, CO", destination: "Salt Lake City, UT" },
    { label: "Seattle → Portland", origin: "Seattle, WA", destination: "Portland, OR" },
    { label: "Miami → Orlando", origin: "Miami, FL", destination: "Orlando, FL" },
  ],
  sadc: [
    { label: "Harare → Beitbridge", origin: "Harare, Zimbabwe", destination: "Beitbridge, Zimbabwe" },
    { label: "Beitbridge → Joburg", origin: "Beitbridge, Zimbabwe", destination: "Johannesburg, South Africa" },
    { label: "Harare → Mutare", origin: "Harare, Zimbabwe", destination: "Mutare, Zimbabwe" },
    { label: "Lusaka → Harare", origin: "Lusaka, Zambia", destination: "Harare, Zimbabwe" },
    { label: "Joburg → Durban", origin: "Johannesburg, South Africa", destination: "Durban, South Africa" },
    { label: "Bulawayo → Francistown", origin: "Bulawayo, Zimbabwe", destination: "Francistown, Botswana" },
  ],
};

const REGION_DEFAULTS: Record<Region, { origin: string; destination: string }> = {
  us: { origin: "New York, NY", destination: "Philadelphia, PA" },
  sadc: { origin: "Harare, Zimbabwe", destination: "Beitbridge, Zimbabwe" },
};

export function TripPlannerPage() {
  const [region, setRegion] = useState<Region>("us");
  const [origin, setOrigin] = useState(REGION_DEFAULTS.us.origin);
  const [destination, setDestination] = useState(REGION_DEFAULTS.us.destination);
  const [waypointInput, setWaypointInput] = useState("");
  const [waypoints, setWaypoints] = useState<string[]>([]);
  const [vehicleId, setVehicleId] = useState<number | undefined>();
  const [driverId, setDriverId] = useState<number | undefined>();
  const [commodityId, setCommodityId] = useState<number | null>(null);
  const [loadWeight, setLoadWeight] = useState<number | null>(null);
  const [estimatedRevenue, setEstimatedRevenue] = useState<number | null>(null);
  const [serviceType, setServiceType] = useState("");
  const [cargoItems, setCargoItems] = useState<CargoItem[]>([]);
  const [bookingDate, setBookingDate] = useState("");
  const [bookingTimeSlot, setBookingTimeSlot] = useState("");

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [commodities, setCommodities] = useState<Commodity[]>([]);
  const [commodityCategories, setCommodityCategories] = useState<CommodityCategory[]>([]);
  const [services, setServices] = useState<ServiceType[]>([]);
  const [trip, setTrip] = useState<TripResponse | null>(null);
  const [estimateResult, setEstimateResult] = useState<TripEstimateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchVehicles().then(r => setVehicles(r.vehicles)).catch(() => {});
    fetchDrivers().then(r => setDrivers(r.drivers)).catch(() => {});
    fetchCommodities().then(r => setCommodities(r.commodities)).catch(() => {});
    fetchCommodityCategories().then(r => setCommodityCategories(r.categories)).catch(() => {});
    fetchServices().then(r => setServices(r.services)).catch(() => {});
  }, []);

  function addCargoItem() {
    setCargoItems([...cargoItems, { description: "", quantity: 1, estimated_weight_kg: 0, is_fragile: false, needs_packing: false, needs_lifting: false }]);
  }

  function updateCargoItem(i: number, field: keyof CargoItem, value: unknown) {
    setCargoItems(cargoItems.map((item, idx) => idx === i ? { ...item, [field]: value } : item));
  }

  function removeCargoItem(i: number) {
    setCargoItems(cargoItems.filter((_, idx) => idx !== i));
  }

  async function handleEstimate(e: FormEvent) {
    e.preventDefault();
    if (!origin || !destination) return;
    setLoading(true);
    setError(null);
    try {
      const result = await estimateTrip({
        origin, destination, waypoints,
        vehicle_id: vehicleId, driver_id: driverId,
        border_crossings: 0,
      });
      setEstimateResult(result);
      setTrip(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Estimate failed");
    } finally {
      setLoading(false);
    }
  }

  async function handlePlan(e: FormEvent) {
    e.preventDefault();
    if (!origin || !destination) return;
    setLoading(true);
    setError(null);
    try {
      const payload: Record<string, unknown> = {
        origin, destination, waypoints,
        vehicle_id: vehicleId, driver_id: driverId,
        commodity_id: commodityId ?? undefined,
        load_weight_tonnes: loadWeight ?? undefined,
        estimated_revenue: estimatedRevenue ?? undefined,
      };
      if (serviceType) payload.service_type = serviceType;
      if (cargoItems.length > 0) payload.cargo_items = cargoItems;
      if (bookingDate || bookingTimeSlot) {
        payload.booking_time_preference = {};
        if (bookingDate) (payload.booking_time_preference as Record<string, string>).date = bookingDate;
        if (bookingTimeSlot) (payload.booking_time_preference as Record<string, string>).time_slot = bookingTimeSlot;
      }
      const result = await planTrip(payload as unknown as Parameters<typeof planTrip>[0]);
      setTrip(result);
      setEstimateResult(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Trip planning failed");
    } finally {
      setLoading(false);
    }
  }

  function addWaypoint() {
    if (waypointInput.trim()) {
      setWaypoints([...waypoints, waypointInput.trim()]);
      setWaypointInput("");
    }
  }

  function handleReverse() {
    setOrigin(destination);
    setDestination(origin);
    setWaypoints([...waypoints].reverse());
  }

  async function handleCopyWhatsApp() {
    const lines = [
      `*Trip Route*`,
      `From: ${origin}`,
      `To: ${destination}`,
      waypoints.length > 0 ? `Via: ${waypoints.join(", ")}` : "",
      route ? `Distance: ${route.distance_km} km` : "",
      route ? `Est. Time: ~${route.duration_h.toFixed(1)} hours` : "",
      cost ? `` : "",
      cost ? `*Cost Estimate*` : "",
      cost ? `Fuel: $${cost.fuel_cost_usd.toFixed(2)}` : "",
      cost ? `Driver Pay: $${cost.driver_pay_usd.toFixed(2)}` : "",
      cost ? `Total Cost: $${cost.total_cost_usd.toFixed(2)}` : "",
      cost ? `Recommended Revenue: $${cost.recommended_revenue_usd.toFixed(2)}` : "",
    ].filter(Boolean);

    await navigator.clipboard.writeText(lines.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const cost = trip?.cost_estimate || estimateResult?.cost_estimate;
  const route = trip?.route || estimateResult?.route;
  const stops = trip?.stops;

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-xl font-bold text-spotter-800">Trip Planner</h2>
        <p className="text-sm text-gray-500">Plan routes and estimate costs</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-5 space-y-4">
          <form onSubmit={handleEstimate} className="bg-white rounded-xl shadow-md p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Truck className="w-5 h-5 text-spotter-600" />
              <h3 className="text-sm font-semibold text-spotter-800">Route</h3>
              <div className="ml-auto flex gap-1">
                <button type="button" onClick={handleReverse}
                  className="px-2 py-1 text-xs text-spotter-600 hover:bg-spotter-50 rounded-md flex items-center gap-1"
                  title="Reverse route">
                  <ArrowLeftRight className="w-3.5 h-3.5" /> Swap
                </button>
                {route && (
                  <button type="button" onClick={handleCopyWhatsApp}
                    className={`px-2 py-1 text-xs rounded-md flex items-center gap-1 ${
                      copied ? "bg-green-100 text-green-700" : "text-spotter-600 hover:bg-spotter-50"
                    }`}
                    title="Copy route as WhatsApp text">
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? "Copied" : "Share"}
                  </button>
                )}
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600">Origin</label>
              <input required value={origin} onChange={e => setOrigin(e.target.value)}
                className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 focus:border-spotter-500 outline-none"
                placeholder="Harare, Zimbabwe" />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600">Destination</label>
              <input required value={destination} onChange={e => setDestination(e.target.value)}
                className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 focus:border-spotter-500 outline-none"
                placeholder="Beitbridge, Zimbabwe" />
            </div>

            <div>
              <label className="text-xs font-medium text-gray-600">Waypoints</label>
              <div className="flex gap-1.5 mt-1">
                <input value={waypointInput} onChange={e => setWaypointInput(e.target.value)}
                  onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); addWaypoint(); } }}
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none"
                  placeholder="Masvingo, Zimbabwe" />
                <button type="button" onClick={addWaypoint}
                  className="px-3 py-2 text-sm bg-spotter-100 text-spotter-700 rounded-md hover:bg-spotter-200"><Plus className="w-4 h-4" /></button>
              </div>
              {waypoints.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {waypoints.map((wp, i) => (
                    <li key={i} className="flex items-center justify-between text-xs bg-spotter-50 px-2 py-1 rounded">
                      <span>{wp}</span>
                      <button type="button" onClick={() => setWaypoints(waypoints.filter((_, j) => j !== i))}
                        className="text-red-500 hover:text-red-700"><X className="w-3 h-3" /></button>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600">Vehicle</label>
                <select value={vehicleId || ""} onChange={e => setVehicleId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none">
                  <option value="">Any</option>
                  {vehicles.filter(v => v.status === "active").map(v => (
                    <option key={v.id} value={v.id}>{v.plate} ({v.fuel_consumption_rate_l_100km}L/100km)</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Driver</label>
                <select value={driverId || ""} onChange={e => setDriverId(e.target.value ? Number(e.target.value) : undefined)}
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none">
                  <option value="">Any</option>
                  {drivers.filter(d => d.status === "active").map(d => (
                    <option key={d.id} value={d.id}>{d.name} (${d.rate_per_day_usd}/day)</option>
                  ))}
                </select>
              </div>
            </div>

            <hr className="border-spotter-100" />
            <CommoditySelector
              categories={commodityCategories}
              commodities={commodities}
              selectedId={commodityId}
              weight={loadWeight}
              distanceKm={route?.distance_km ?? 0}
              onSelect={(id, w, rev) => { setCommodityId(id); setLoadWeight(w); setEstimatedRevenue(rev); }}
            />
            {estimatedRevenue != null && estimatedRevenue > 0 && (
              <div className="flex items-center justify-between px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-xs">
                <span className="font-medium text-green-800">Est. Revenue</span>
                <span className="font-bold text-green-700 text-sm">${estimatedRevenue.toFixed(2)}</span>
              </div>
            )}

            <hr className="border-spotter-100" />
            <div>
              <label className="text-xs font-medium text-gray-600 flex items-center gap-1"><Package className="w-3 h-3" /> Service Type</label>
              <select value={serviceType} onChange={e => setServiceType(e.target.value)}
                className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none">
                <option value="">Standard Trip</option>
                {services.map(s => (
                  <option key={s.key} value={s.key}>{s.name}</option>
                ))}
              </select>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-gray-600 flex items-center gap-1"><Package className="w-3 h-3" /> Cargo Items ({cargoItems.length})</label>
                <button type="button" onClick={addCargoItem} className="text-xs text-spotter-600 hover:text-spotter-800">+ Add Item</button>
              </div>
              {cargoItems.length > 0 && (
                <div className="mt-2 space-y-2">
                  {cargoItems.map((item, i) => (
                    <div key={i} className="flex flex-wrap gap-1.5 p-2 bg-spotter-50 rounded-md">
                      <input value={item.description} onChange={e => updateCargoItem(i, "description", e.target.value)}
                        placeholder="Description" className="flex-1 min-w-[120px] px-2 py-1 text-xs border rounded" />
                      <input type="number" value={item.quantity || ""} onChange={e => updateCargoItem(i, "quantity", parseInt(e.target.value) || 0)}
                        placeholder="Qty" className="w-14 px-2 py-1 text-xs border rounded" />
                      <input type="number" value={item.estimated_weight_kg || ""} onChange={e => updateCargoItem(i, "estimated_weight_kg", parseFloat(e.target.value) || 0)}
                        placeholder="Kg" className="w-16 px-2 py-1 text-xs border rounded" />
                      <label className="flex items-center gap-1 text-[10px] text-gray-600">
                        <input type="checkbox" checked={item.is_fragile} onChange={e => updateCargoItem(i, "is_fragile", e.target.checked)} /> Fragile
                      </label>
                      <label className="flex items-center gap-1 text-[10px] text-gray-600">
                        <input type="checkbox" checked={item.needs_packing} onChange={e => updateCargoItem(i, "needs_packing", e.target.checked)} /> Pack
                      </label>
                      <button type="button" onClick={() => removeCargoItem(i)} className="text-red-500 hover:text-red-700"><X className="w-3 h-3" /></button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs font-medium text-gray-600 flex items-center gap-1"><Calendar className="w-3 h-3" /> Scheduled Date</label>
                <input type="date" value={bookingDate} onChange={e => setBookingDate(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none" />
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600">Time Slot</label>
                <select value={bookingTimeSlot} onChange={e => setBookingTimeSlot(e.target.value)}
                  className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none">
                  <option value="">Any</option>
                  <option value="morning">Morning</option>
                  <option value="afternoon">Afternoon</option>
                  <option value="evening">Evening</option>
                </select>
              </div>
            </div>

            <div className="flex gap-1.5 mb-2">
              <button type="button" onClick={() => { setRegion("us"); setOrigin(REGION_DEFAULTS.us.origin); setDestination(REGION_DEFAULTS.us.destination); setWaypoints([]); setTrip(null); setEstimateResult(null); }}
                className={`px-3 py-1 text-xs rounded-full border font-medium ${region === "us" ? "bg-spotter-600 text-white border-spotter-600" : "bg-white text-gray-600 border-gray-300 hover:bg-spotter-50"}`}>
                US Interstate
              </button>
              <button type="button" onClick={() => { setRegion("sadc"); setOrigin(REGION_DEFAULTS.sadc.origin); setDestination(REGION_DEFAULTS.sadc.destination); setWaypoints([]); setTrip(null); setEstimateResult(null); }}
                className={`px-3 py-1 text-xs rounded-full border font-medium ${region === "sadc" ? "bg-spotter-600 text-white border-spotter-600" : "bg-white text-gray-600 border-gray-300 hover:bg-spotter-50"}`}>
                Southern Africa
              </button>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {REGION_PRESETS[region].map(p => (
                <button key={p.label} type="button" onClick={() => { setOrigin(p.origin); setDestination(p.destination); setWaypoints([]); }}
                  className="px-2 py-0.5 text-xs rounded-full bg-spotter-50 text-spotter-700 hover:bg-spotter-100 border border-spotter-200">
                  {p.label}
                </button>
              ))}
            </div>

            <div className="flex gap-2">
              <button type="button" onClick={handleEstimate} disabled={loading}
                className="flex-1 bg-spotter-100 text-spotter-700 font-semibold py-2 rounded-md hover:bg-spotter-200 disabled:opacity-60 text-sm">
                {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Estimate Cost"}
              </button>
              <button type="button" onClick={handlePlan} disabled={loading}
                className="flex-1 bg-spotter-600 hover:bg-spotter-700 text-white font-semibold py-2 rounded-md disabled:opacity-60 text-sm">
                {loading ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : "Plan & Save"}
              </button>
            </div>

            {error && <div className="p-2 bg-red-50 border border-red-200 rounded text-xs text-red-800">{error}</div>}
          </form>

          {cost && (
            <div className="bg-white rounded-xl shadow-md p-5 space-y-2">
              <h3 className="text-sm font-semibold text-spotter-800 flex items-center gap-2"><DollarSign className="w-4 h-4" /> Cost Breakdown</h3>
              <CostRow label="Distance" value={`${cost.route_distance_km} km`} />
              <CostRow label="Est. Days" value={String(cost.estimated_days)} />
              <CostRow label="Fuel" value={`$${cost.fuel_cost_usd.toFixed(2)}`} icon={Fuel} />
              <CostRow label="Driver Pay" value={`$${cost.driver_pay_usd.toFixed(2)}`} icon={User} />
              {cost.border_fees_usd > 0 && <CostRow label="Border Fees" value={`$${cost.border_fees_usd.toFixed(2)}`} />}
              {cost.tolls_usd > 0 && <CostRow label="Tolls" value={`$${cost.tolls_usd.toFixed(2)}`} />}
              <CostRow label="Maintenance" value={`$${cost.maintenance_provision_usd.toFixed(2)}`} />
              <hr className="border-spotter-100" />
              <CostRow label="Total Cost" value={`$${cost.total_cost_usd.toFixed(2)}`} bold />
              <CostRow label="Break-even Revenue" value={`$${cost.break_even_revenue_usd.toFixed(2)}`} />
              <CostRow label="Recommended (+20%)" value={`$${cost.recommended_revenue_usd.toFixed(2)}`} bold positive />
            </div>
          )}
        </div>

        <div className="lg:col-span-7">
          {route ? (
            <div className="bg-white rounded-xl shadow-md p-5">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-spotter-800">Route Map</h3>
                <span className="text-xs text-gray-500">{route.distance_km} km · {route.duration_h.toFixed(1)} hours</span>
              </div>
              <RouteMap route={route} stops={stops || []} restStops={[]} />
              {trip?.trip_id && (
                <button onClick={() => navigate(`/app/trips/${trip.trip_id}`)}
                  className="mt-3 w-full py-2 bg-spotter-600 text-white text-sm rounded-md hover:bg-spotter-700">
                  View Trip Details
                </button>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-xl shadow-md p-10 text-center text-gray-400">
              <MapPin className="w-10 h-10 mx-auto text-spotter-200 mb-3" />
              <p className="text-sm">Enter a route and click <strong>Estimate Cost</strong> or <strong>Plan & Save</strong></p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function CostRow({ label, value, icon: Icon, bold, positive }: {
  label: string; value: string; icon?: React.ComponentType<{ className?: string }>; bold?: boolean; positive?: boolean;
}) {
  return (
    <div className={`flex justify-between text-xs ${bold ? "font-bold text-spotter-900 text-sm" : "text-gray-700"}`}>
      <span className="flex items-center gap-1">{Icon && <Icon className="w-3 h-3 text-spotter-500" />}{label}</span>
      <span className={positive ? "text-green-700" : ""}>{value}</span>
    </div>
  );
}
