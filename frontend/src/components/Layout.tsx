import { NavLink } from "react-router-dom";
import { Truck, BarChart3, MapPin, Users, FileText, Navigation, ClipboardList } from "lucide-react";

const links = [
  { to: "/app", icon: MapPin, label: "Trip Planner" },
  { to: "/app/trips", icon: FileText, label: "Trips" },
  { to: "/app/vehicles", icon: Truck, label: "Vehicles" },
  { to: "/app/drivers", icon: Users, label: "Drivers" },
  { to: "/app/dispatch", icon: ClipboardList, label: "Dispatch" },
  { to: "/app/live-map", icon: Navigation, label: "Live Map" },
  { to: "/app/dashboard", icon: BarChart3, label: "Dashboard" },
];

export function Sidebar() {
  return (
    <nav className="w-56 bg-spotter-800 text-white flex flex-col shrink-0 min-h-screen">
      <div className="px-5 py-5 border-b border-spotter-700">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-spotter-500 flex items-center justify-center">
            <Truck className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold">Trucki</h1>
            <p className="text-[10px] text-spotter-300">Fleet Management</p>
          </div>
        </div>
      </div>
      <div className="flex-1 px-3 py-3 space-y-1">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.to === "/app"}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition ${
                isActive
                  ? "bg-spotter-600 text-white font-medium"
                  : "text-spotter-200 hover:bg-spotter-700 hover:text-white"
              }`
            }
          >
            <link.icon className="w-4 h-4" />
            {link.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
