import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/Layout";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { TripPlannerPage } from "./pages/TripPlannerPage";
import { TripsPage } from "./pages/TripsPage";
import { TripDetailPage } from "./pages/TripDetailPage";
import { VehiclesPage } from "./pages/VehiclesPage";
import { DriversPage } from "./pages/DriversPage";
import { DriverView } from "./pages/DriverView";
import { LiveMapPage } from "./pages/LiveMapPage";
import { fetchMe, logout } from "./lib/auth";
import type { User } from "./lib/types";
import { LogOut } from "lucide-react";

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function checkAuth() {
    const me = await fetchMe();
    setUser(me);
    setLoading(false);
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const me = await fetchMe();
      if (!cancelled) { setUser(me); setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, []);

  async function handleLogout() {
    await logout();
    setUser(null);
  }

  function handleLogin() {
    checkAuth();
  }

  return (
    <BrowserRouter>
      {loading ? (
        <div className="min-h-screen flex items-center justify-center text-gray-500">
          <div className="w-8 h-8 border-4 border-spotter-200 border-t-spotter-600 rounded-full animate-spin" />
        </div>
      ) : !user ? (
        <LoginPage onLogin={handleLogin} />
      ) : !user.is_admin ? (
        user.driver_id ? (
          <DriverView user={user} onLogout={handleLogout} />
        ) : (
          <LoginPage onLogin={handleLogin} />
        )
      ) : (
        <div className="flex min-h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
              <div className="text-xs text-gray-500">
                Signed in as <strong>{user.username}</strong>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-100 rounded-md"
              >
                <LogOut className="w-3.5 h-3.5" /> Sign out
              </button>
            </header>
            <main className="flex-1 p-6 overflow-auto">
              <Routes>
                <Route path="/" element={<TripPlannerPage />} />
                <Route path="/trips" element={<TripsPage />} />
                <Route path="/trips/:id" element={<TripDetailPage />} />
                <Route path="/vehicles" element={<VehiclesPage />} />
                <Route path="/drivers" element={<DriversPage />} />
                <Route path="/live-map" element={<LiveMapPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </main>
          </div>
        </div>
      )}
    </BrowserRouter>
  );
}

export default App;
