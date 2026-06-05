import { useState } from "react";
import { Loader2, Truck } from "lucide-react";

interface Props {
  onSubmit: (data: FormData) => void;
  loading: boolean;
}

export interface FormData {
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used_hrs: number;
  use_sleeper_berth: boolean;
}

const PRESETS = [
  { label: "Short trip", current: "New York, NY", pickup: "Philadelphia, PA", dropoff: "Baltimore, MD", cycle: 0 },
  { label: "Long trip (multi-day)", current: "New York, NY", pickup: "Philadelphia, PA", dropoff: "Atlanta, GA", cycle: 0 },
  { label: "Cross-country", current: "Los Angeles, CA", pickup: "Albuquerque, NM", dropoff: "Chicago, IL", cycle: 0 },
  { label: "70hr at limit", current: "Miami, FL", pickup: "Jacksonville, FL", dropoff: "New York, NY", cycle: 65 },
];

export function TripForm({ onSubmit, loading }: Props) {
  const [current, setCurrent] = useState("New York, NY");
  const [pickup, setPickup] = useState("Philadelphia, PA");
  const [dropoff, setDropoff] = useState("Baltimore, MD");
  const [cycle, setCycle] = useState(0);
  const [sleeper, setSleeper] = useState(true);

  const apply = (p: typeof PRESETS[0]) => {
    setCurrent(p.current);
    setPickup(p.pickup);
    setDropoff(p.dropoff);
    setCycle(p.cycle);
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      current_location: current,
      pickup_location: pickup,
      dropoff_location: dropoff,
      current_cycle_used_hrs: cycle,
      use_sleeper_berth: sleeper,
    });
  };

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="flex items-center gap-2 mb-2">
        <Truck className="w-5 h-5 text-spotter-600" />
        <h2 className="text-lg font-semibold text-spotter-800">Plan a Trip</h2>
      </div>

      <div>
        <label htmlFor="current-location" className="text-xs font-medium text-gray-600">Current location</label>
        <input
          id="current-location"
          required
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 focus:border-spotter-500 outline-none"
          placeholder="e.g. New York, NY"
        />
      </div>

      <div>
        <label htmlFor="pickup-location" className="text-xs font-medium text-gray-600">Pickup location</label>
        <input
          id="pickup-location"
          required
          value={pickup}
          onChange={(e) => setPickup(e.target.value)}
          className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 focus:border-spotter-500 outline-none"
          placeholder="e.g. Philadelphia, PA"
        />
      </div>

      <div>
        <label htmlFor="dropoff-location" className="text-xs font-medium text-gray-600">Dropoff location</label>
        <input
          id="dropoff-location"
          required
          value={dropoff}
          onChange={(e) => setDropoff(e.target.value)}
          className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 focus:border-spotter-500 outline-none"
          placeholder="e.g. Baltimore, MD"
        />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label htmlFor="cycle-used" className="text-xs font-medium text-gray-600">Cycle used (hrs)</label>
          <input
            id="cycle-used"
            type="number"
            min={0}
            max={70}
            step={0.5}
            value={cycle}
            onChange={(e) => setCycle(parseFloat(e.target.value) || 0)}
            className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 focus:border-spotter-500 outline-none"
          />
        </div>
        <div className="flex items-end">
          <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
            <input
              type="checkbox"
              checked={sleeper}
              onChange={(e) => setSleeper(e.target.checked)}
              aria-label="Use sleeper berth"
              className="w-4 h-4 rounded border-gray-300 text-spotter-600 focus:ring-spotter-500"
            />
            Use sleeper berth
          </label>
        </div>
      </div>

      <div>
        <p className="text-xs font-medium text-gray-600 mb-1">Quick presets</p>
        <div className="flex flex-wrap gap-1.5">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              onClick={() => apply(p)}
              className="px-2.5 py-1 text-xs rounded-full bg-spotter-50 text-spotter-700 hover:bg-spotter-100 border border-spotter-200"
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-spotter-600 hover:bg-spotter-700 text-white font-semibold py-2.5 rounded-md transition disabled:opacity-60 flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Planning trip…
          </>
        ) : (
          "Plan Trip"
        )}
      </button>
    </form>
  );
}
