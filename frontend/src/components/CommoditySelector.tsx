import { useState } from "react";
import type { Commodity, CommodityCategory } from "../lib/types";
import { Package, Fuel, Container, Wheat, Pickaxe, HardHat, Snowflake, Truck, ChevronDown, ChevronUp } from "lucide-react";

const CATEGORY_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  "General Freight": Package,
  "Fuel & Chemicals": Fuel,
  Containers: Container,
  Agriculture: Wheat,
  "Mining & Minerals": Pickaxe,
  Construction: HardHat,
  Perishables: Snowflake,
  "Vehicles & Machinery": Truck,
};

interface Props {
  categories: CommodityCategory[];
  commodities: Commodity[];
  selectedId: number | null;
  weight: number | null;
  distanceKm: number;
  onSelect: (id: number | null, weight: number | null, rev: number | null) => void;
}

export function CommoditySelector({ categories, commodities, selectedId, weight, distanceKm, onSelect }: Props) {
  const [activeCategory, setActiveCategory] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  const filtered = activeCategory
    ? commodities.filter(c => c.category === activeCategory)
    : commodities;

  const visible = showAll ? filtered : filtered.slice(0, 6);
  const selected = commodities.find(c => c.id === selectedId);
  const hasMore = filtered.length > 6;

  function computeRevenue(com: Commodity, w: number | null): number {
    let rev = com.flat_fee ?? 0;
    if (com.rate_per_km && distanceKm) rev += com.rate_per_km * distanceKm;
    if (com.rate_per_kg && w) rev += com.rate_per_kg * w * 1000;
    return Math.round(rev * 100) / 100;
  }

  function handleSelect(com: Commodity) {
    const w = weight ?? 0;
    const rev = computeRevenue(com, w);
    onSelect(com.id, com.rate_per_kg ? Math.max(w || 1, 0.5) : null, rev);
  }

  function handleWeightChange(newWeight: number) {
    if (selected) {
      const rev = computeRevenue(selected, newWeight);
      onSelect(selected.id, newWeight, rev);
    } else {
      onSelect(null, newWeight, null);
    }
  }

  return (
    <div className="space-y-3">
      <label className="text-xs font-medium text-gray-600">Commodity / Cargo Type</label>

      <div className="flex flex-wrap gap-1.5">
        <button type="button" onClick={() => setActiveCategory(null)}
          className={`px-2.5 py-1 text-[11px] rounded-full font-medium transition ${
            activeCategory === null ? "bg-spotter-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
          }`}>
          All
        </button>
        {categories.map(cat => {
          const Icon = CATEGORY_ICONS[cat.name] || Package;
          return (
            <button key={cat.id} type="button" onClick={() => setActiveCategory(cat.id)}
              className={`px-2.5 py-1 text-[11px] rounded-full font-medium transition flex items-center gap-1 ${
                activeCategory === cat.id ? "bg-spotter-600 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}>
              <Icon className="w-3 h-3" />
              {cat.name}
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
        {visible.map(com => {
          const isSelected = com.id === selectedId;
          const rev = computeRevenue(com, weight ?? 0);
          return (
            <button key={com.id} type="button" onClick={() => handleSelect(com)}
              className={`relative text-left p-2.5 rounded-lg border text-xs transition ${
                isSelected
                  ? "border-spotter-500 bg-spotter-50 ring-1 ring-spotter-300"
                  : "border-gray-200 bg-white hover:border-spotter-300 hover:bg-spotter-50/50"
              }`}>
              <div className="font-semibold text-gray-800 text-[11px]">{com.name}</div>
              <div className="flex flex-wrap gap-x-1.5 mt-1 text-[10px] text-gray-500">
                {com.rate_per_km && <span>${com.rate_per_km}/km</span>}
                {com.rate_per_kg && <span>${com.rate_per_kg}/kg</span>}
                {com.flat_fee && <span>+${com.flat_fee}</span>}
              </div>
              {distanceKm > 0 && (
                <div className="mt-1 text-[10px] font-medium text-spotter-600">
                  ~${rev.toFixed(0)} rev.
                </div>
              )}
            </button>
          );
        })}
      </div>

      {hasMore && (
        <button type="button" onClick={() => setShowAll(!showAll)}
          className="flex items-center gap-1 text-xs text-spotter-600 hover:text-spotter-800">
          {showAll ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {showAll ? "Show less" : `Show all ${filtered.length} commodities`}
        </button>
      )}

      {selected?.rate_per_kg && (
        <div>
          <label className="text-xs font-medium text-gray-600">Load Weight (tonnes)</label>
          <input type="number" min={0.1} step={0.5} value={weight ?? ""}
            onChange={e => handleWeightChange(e.target.value ? parseFloat(e.target.value) : 0)}
            className="w-full mt-1 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-spotter-300 outline-none"
            placeholder="Enter weight in tonnes" />
        </div>
      )}
    </div>
  );
}
