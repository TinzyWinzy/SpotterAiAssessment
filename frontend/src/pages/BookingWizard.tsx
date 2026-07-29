import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Check, Truck, Package, MapPin, Calendar, DollarSign, Loader2 } from "lucide-react";
import { getPublicQuote, createPublicBooking } from "../lib/api";
import type { CargoItem, PublicQuoteResponse } from "../lib/types";

const SERVICE_NAMES: Record<string, string> = {
  household: "Household Removal", grocery: "Grocery Delivery", construction: "Construction Materials",
  furniture: "Furniture Delivery", office: "Office Relocation", long_distance: "Long Distance", custom: "Custom Transport",
};

const TIME_SLOTS = [
  { value: "morning", label: "Morning (8AM - 12PM)" },
  { value: "afternoon", label: "Afternoon (12PM - 5PM)" },
  { value: "evening", label: "Evening (5PM - 8PM)" },
];

export function BookingWizard() {
  const { service } = useParams<{ service: string }>();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [quote, setQuote] = useState<PublicQuoteResponse | null>(null);
  const [bookingRef, setBookingRef] = useState("");
  const [trackingUrl, setTrackingUrl] = useState("");

  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [date, setDate] = useState("");
  const [timeSlot, setTimeSlot] = useState("morning");
  const [items, setItems] = useState<CargoItem[]>([]);
  const [customerName, setCustomerName] = useState("");
  const [customerPhone, setCustomerPhone] = useState("");
  const [customerEmail, setCustomerEmail] = useState("");
  const [pickupNotes, setPickupNotes] = useState("");
  const [deliveryNotes, setDeliveryNotes] = useState("");
  const [needsPacking, setNeedsPacking] = useState(false);
  const [needsLabour, setNeedsLabour] = useState(false);
  const [floorCount, setFloorCount] = useState(0);

  function addItem() {
    setItems([...items, { description: "", quantity: 1, estimated_weight_kg: 0, is_fragile: false, needs_packing: false, needs_lifting: false }]);
  }

  function updateItem(i: number, field: string, value: string | number | boolean) {
    const updated = [...items];
    (updated[i] as any)[field] = value;
    setItems(updated);
  }

  function removeItem(i: number) {
    setItems(items.filter((_, idx) => idx !== i));
  }

  const hasFragile = items.some(i => i.is_fragile);

  async function handleGetQuote() {
    if (!origin.trim() || !destination.trim()) {
      setError("Please enter pickup and drop-off addresses");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const q = await getPublicQuote({
        service_type: service || "custom",
        origin, destination,
        cargo_items: items.filter(i => i.description.trim()),
        has_fragile: hasFragile,
        needs_packing: needsPacking,
        needs_labour: needsLabour,
        floor_count: floorCount,
      });
      setQuote(q);
      setStep(3);
    } catch (e: any) {
      setError(e.message || "Failed to get quote");
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    if (!customerPhone.trim()) {
      setError("Please enter your phone number");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const dateObj = date ? new Date(date) : undefined;
      const result = await createPublicBooking({
        service_type: service || "custom",
        origin, destination,
        cargo_items: items.filter(i => i.description.trim()),
        booking_time_preference: date ? { date: dateObj?.toISOString().split("T")[0], time_slot: timeSlot as any } : undefined,
        has_fragile: hasFragile, needs_packing: needsPacking, needs_labour: needsLabour, floor_count: floorCount,
        customer_name: customerName, customer_phone: customerPhone, customer_email: customerEmail,
        pickup_notes: pickupNotes, delivery_notes: deliveryNotes,
      });
      setBookingRef(result.booking_reference);
      setTrackingUrl(result.tracking_url);
      setStep(4);
    } catch (e: any) {
      setError(e.message || "Booking failed");
    } finally {
      setLoading(false);
    }
  }

  const svcName = SERVICE_NAMES[service || ""] || "Transport";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8">
        <button onClick={() => navigate(-1)} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-6">
          <ArrowLeft className="w-4 h-4" /> Back
        </button>

        <div className="flex items-center gap-2 mb-8">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${step >= 1 ? "bg-spotter-600" : "bg-gray-300"}`}>1</div>
          <div className={`h-0.5 w-12 ${step >= 2 ? "bg-spotter-600" : "bg-gray-300"}`} />
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${step >= 2 ? "bg-spotter-600" : "bg-gray-300"}`}>2</div>
          <div className={`h-0.5 w-12 ${step >= 3 ? "bg-spotter-600" : "bg-gray-300"}`} />
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${step >= 3 ? "bg-spotter-600" : "bg-gray-300"}`}>3</div>
          <div className={`h-0.5 w-12 ${step >= 4 ? "bg-spotter-600" : "bg-gray-300"}`} />
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-medium ${step >= 4 ? "bg-spotter-600" : "bg-gray-300"}`}>4</div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm mb-6">{error}</div>
        )}

        {/* Step 1: Pickup + Drop-off */}
        {step === 1 && (
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2"><MapPin className="w-5 h-5 text-spotter-600" /> Pickup & Delivery</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Pickup address</label>
                <input value={origin} onChange={e => setOrigin(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-spotter-500 focus:border-spotter-500 outline-none" placeholder="e.g. 123 Samora Machel Ave, Harare" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Drop-off address</label>
                <input value={destination} onChange={e => setDestination(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-spotter-500 focus:border-spotter-500 outline-none" placeholder="e.g. 456 Josiah Chinamano Ave, Bulawayo" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Preferred date</label>
                  <input type="date" value={date} onChange={e => setDate(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-spotter-500 focus:border-spotter-500 outline-none" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Time slot</label>
                  <select value={timeSlot} onChange={e => setTimeSlot(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-spotter-500 focus:border-spotter-500 outline-none">
                    {TIME_SLOTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
              </div>
            </div>
            <div className="mt-6 flex justify-end">
              <button onClick={() => setStep(2)} className="flex items-center gap-2 px-6 py-2.5 bg-spotter-600 text-white rounded-lg hover:bg-spotter-700 transition-colors">
                Next: Cargo <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step 2: Cargo */}
        {step === 2 && (
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2"><Package className="w-5 h-5 text-spotter-600" /> What are you moving?</h2>

            <div className="space-y-3 mb-4">
              {items.map((item, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-sm font-medium text-gray-700">Item {i + 1}</span>
                    <button onClick={() => removeItem(i)} className="text-xs text-red-500 hover:text-red-700">Remove</button>
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="col-span-2">
                      <input value={item.description} onChange={e => updateItem(i, "description", e.target.value)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:ring-2 focus:ring-spotter-500 outline-none" placeholder="e.g. Sofa, Fridge, Boxes" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Qty</label>
                      <input type="number" min={1} value={item.quantity} onChange={e => updateItem(i, "quantity", parseInt(e.target.value) || 1)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-0.5">Weight (kg)</label>
                      <input type="number" min={0} value={item.estimated_weight_kg || ""} onChange={e => updateItem(i, "estimated_weight_kg", parseFloat(e.target.value) || 0)} className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm" />
                    </div>
                    <div className="flex items-center gap-4 col-span-2">
                      <label className="flex items-center gap-1.5 text-sm text-gray-600">
                        <input type="checkbox" checked={item.is_fragile} onChange={e => updateItem(i, "is_fragile", e.target.checked)} className="rounded" /> Fragile
                      </label>
                      <label className="flex items-center gap-1.5 text-sm text-gray-600">
                        <input type="checkbox" checked={item.needs_packing} onChange={e => updateItem(i, "needs_packing", e.target.checked)} className="rounded" /> Needs packing
                      </label>
                      <label className="flex items-center gap-1.5 text-sm text-gray-600">
                        <input type="checkbox" checked={item.needs_lifting} onChange={e => updateItem(i, "needs_lifting", e.target.checked)} className="rounded" /> Needs lifting
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <button onClick={addItem} className="text-sm text-spotter-600 hover:text-spotter-800 font-medium mb-6">+ Add item</button>

            <div className="border-t pt-4 space-y-3">
              <h3 className="text-sm font-medium text-gray-700">Extra services</h3>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={needsPacking} onChange={e => setNeedsPacking(e.target.checked)} className="rounded" /> Packing service (+$25)
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <input type="checkbox" checked={needsLabour} onChange={e => setNeedsLabour(e.target.checked)} className="rounded" /> Extra labour (+$20)
              </label>
              <div className="flex items-center gap-3">
                <label className="text-sm text-gray-600">Floors with stairs:</label>
                <input type="number" min={0} value={floorCount} onChange={e => setFloorCount(parseInt(e.target.value) || 0)} className="w-20 border border-gray-300 rounded px-2 py-1.5 text-sm" />
              </div>
            </div>

            <div className="mt-6 flex justify-between">
              <button onClick={() => setStep(1)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Back</button>
              <button onClick={handleGetQuote} disabled={loading} className="flex items-center gap-2 px-6 py-2.5 bg-spotter-600 text-white rounded-lg hover:bg-spotter-700 transition-colors disabled:opacity-50">
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <DollarSign className="w-4 h-4" />}
                Get Quote
              </button>
            </div>
          </div>
        )}

        {/* Step 3: Quote + Confirm */}
        {step === 3 && quote && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2"><Truck className="w-5 h-5 text-spotter-600" /> Truck Recommendation</h2>
              <div className="bg-spotter-50 border border-spotter-200 rounded-lg p-4">
                <p className="text-2xl font-bold text-spotter-800">{quote.truck_recommendation.recommended_size}</p>
                <p className="text-sm text-gray-600 mt-1">{quote.truck_recommendation.explanation}</p>
              </div>
              {quote.truck_recommendation.alternatives.length > 0 && (
                <p className="text-sm text-gray-500 mt-2">Alternatives: {quote.truck_recommendation.alternatives.join(", ")}</p>
              )}
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2"><DollarSign className="w-5 h-5 text-spotter-600" /> Cost Estimate</h2>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-600">Base fee</span><span>${quote.cost_estimate.base_fee_usd.toFixed(2)}</span></div>
                <div className="flex justify-between"><span className="text-gray-600">Distance fee ({quote.cost_estimate.route_distance_km.toFixed(0)} km)</span><span>${quote.cost_estimate.distance_fee_usd.toFixed(2)}</span></div>
                {quote.cost_estimate.loading_fee_usd > 0 && <div className="flex justify-between"><span className="text-gray-600">Loading fee</span><span>${quote.cost_estimate.loading_fee_usd.toFixed(2)}</span></div>}
                {quote.cost_estimate.packing_fee_usd > 0 && <div className="flex justify-between"><span className="text-gray-600">Packing fee</span><span>${quote.cost_estimate.packing_fee_usd.toFixed(2)}</span></div>}
                {quote.cost_estimate.fragile_surcharge_usd > 0 && <div className="flex justify-between"><span className="text-gray-600">Fragile surcharge</span><span>${quote.cost_estimate.fragile_surcharge_usd.toFixed(2)}</span></div>}
                {quote.cost_estimate.floor_fee_usd > 0 && <div className="flex justify-between"><span className="text-gray-600">Floor charges</span><span>${quote.cost_estimate.floor_fee_usd.toFixed(2)}</span></div>}
                <div className="flex justify-between"><span className="text-gray-600">Fuel surcharge</span><span>${quote.cost_estimate.fuel_surcharge_usd.toFixed(2)}</span></div>
                <div className="border-t pt-2 flex justify-between font-bold text-lg"><span>Total</span><span className="text-spotter-700">${quote.cost_estimate.total_estimated_usd.toFixed(2)}</span></div>
              </div>
            </div>

            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2"><Calendar className="w-5 h-5 text-spotter-600" /> Your Details</h2>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Name (optional)</label>
                  <input value={customerName} onChange={e => setCustomerName(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-spotter-500 outline-none" placeholder="Your name" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone number <span className="text-red-500">*</span></label>
                  <input value={customerPhone} onChange={e => setCustomerPhone(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-spotter-500 outline-none" placeholder="+263 7XX XXX XXX" required />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email (optional)</label>
                  <input type="email" value={customerEmail} onChange={e => setCustomerEmail(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-spotter-500 outline-none" placeholder="you@example.com" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Pickup notes</label>
                  <input value={pickupNotes} onChange={e => setPickupNotes(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-spotter-500 outline-none" placeholder="Gate code, floor number, etc." />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Delivery notes</label>
                  <input value={deliveryNotes} onChange={e => setDeliveryNotes(e.target.value)} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-spotter-500 outline-none" placeholder="Delivery instructions" />
                </div>
              </div>
              <div className="mt-6 flex justify-between">
                <button onClick={() => setStep(2)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800">Back</button>
                <button onClick={handleConfirm} disabled={loading} className="flex items-center gap-2 px-6 py-2.5 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                  Confirm Booking
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Confirmation */}
        {step === 4 && (
          <div className="bg-white rounded-xl p-8 shadow-sm border border-gray-200 text-center">
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <Check className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Booking Confirmed!</h2>
            <p className="text-gray-500 mb-6">Your {svcName} booking has been submitted.</p>

            <div className="bg-gray-50 rounded-lg p-4 mb-6 inline-block">
              <p className="text-sm text-gray-500">Reference</p>
              <p className="text-2xl font-mono font-bold text-spotter-700">{bookingRef}</p>
            </div>

            <p className="text-sm text-gray-600 mb-6">
              We'll send a confirmation to <strong>{customerPhone}</strong> with your tracking link.
              You can also save this link to track your booking:
            </p>

            <div className="bg-gray-50 rounded-lg p-3 mb-6 text-left">
              <p className="text-xs text-gray-500 mb-1">Tracking link</p>
              <a href={trackingUrl} target="_blank" rel="noopener noreferrer" className="text-sm text-spotter-600 hover:underline break-all">{trackingUrl}</a>
            </div>

            <div className="flex justify-center gap-3">
              <button onClick={() => navigator.clipboard.writeText(trackingUrl)} className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-sm">
                Copy Link
              </button>
              <a href={trackingUrl} target="_blank" rel="noopener noreferrer" className="px-4 py-2 bg-spotter-600 text-white rounded-lg hover:bg-spotter-700 text-sm">
                Track Booking
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
