import { useNavigate } from "react-router-dom";
import { Truck, ShoppingCart, HardHat, Armchair, Building2, Map, Package } from "lucide-react";

const SERVICES = [
  { key: "household", name: "Household Removal", desc: "Moving furniture and household belongings", icon: Truck, color: "bg-blue-500" },
  { key: "grocery", name: "Grocery Delivery", desc: "Transport of groceries and perishables", icon: ShoppingCart, color: "bg-green-500" },
  { key: "construction", name: "Construction Materials", desc: "Bricks, cement, timber and more", icon: HardHat, color: "bg-orange-500" },
  { key: "furniture", name: "Furniture Delivery", desc: "New or second-hand furniture items", icon: Armchair, color: "bg-purple-500" },
  { key: "office", name: "Office Relocation", desc: "Office equipment, desks and files", icon: Building2, color: "bg-indigo-500" },
  { key: "long_distance", name: "Long Distance", desc: "Intercity or cross-border transport", icon: Map, color: "bg-red-500" },
  { key: "custom", name: "Custom Transport", desc: "General goods transport", icon: Package, color: "bg-gray-500" },
];

export function BookingPage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 py-12">
        <div className="text-center mb-10">
          <h1 className="text-3xl font-bold text-gray-900">What are you moving?</h1>
          <p className="mt-2 text-gray-600">Select the type of move to get started</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {SERVICES.map((svc) => (
            <button
              key={svc.key}
              onClick={() => navigate(`/book/${svc.key}`)}
              className="bg-white rounded-xl p-6 text-left shadow-sm border border-gray-200 hover:shadow-md hover:border-spotter-300 transition-all group"
            >
              <div className={`w-12 h-12 ${svc.color} rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform`}>
                <svc.icon className="w-6 h-6 text-white" />
              </div>
              <h3 className="font-semibold text-gray-900">{svc.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{svc.desc}</p>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
