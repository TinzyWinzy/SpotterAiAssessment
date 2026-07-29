import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Sidebar } from "./components/Layout";
import { LandingPage } from "./pages/LandingPage";
import { LoginPage } from "./pages/LoginPage";
import { DashboardPage } from "./pages/DashboardPage";
import { TripPlannerPage } from "./pages/TripPlannerPage";
import { TripsPage } from "./pages/TripsPage";
import { TripDetailPage } from "./pages/TripDetailPage";
import { VehiclesPage } from "./pages/VehiclesPage";
import { DriversPage } from "./pages/DriversPage";
import { DriverView } from "./pages/DriverView";
import { LiveMapPage } from "./pages/LiveMapPage";
import { BookingPage } from "./pages/BookingPage";
import { BookingWizard } from "./pages/BookingWizard";
import { TrackingPage } from "./pages/TrackingPage";
import { DispatchPage } from "./pages/DispatchPage";
import { fetchMe, logout } from "./lib/auth";
import type { User } from "./lib/types";
import { LogOut } from "lucide-react";

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

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

  async function handleLogin(): Promise<User | null> {
    const me = await fetchMe();
    setUser(me);
    return me;
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        <div className="w-8 h-8 border-4 border-spotter-200 border-t-spotter-600 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={
          !user ? <LoginPage onLogin={handleLogin} /> : <Navigate to={user.is_admin ? "/app" : "/driver"} />
        } />
        <Route path="/book" element={<BookingPage />} />
        <Route path="/book/:service" element={<BookingWizard />} />
        <Route path="/track/:ref" element={<TrackingPage />} />
        <Route path="/driver" element={
          user?.driver_id ? <DriverView user={user} onLogout={handleLogout} /> : <Navigate to="/login" />
        } />
        <Route path="/app/*" element={
          user?.is_admin ? <AdminShell><AdminRoutes /></AdminShell> : <Navigate to="/login" />
        } />
      </Routes>
    </BrowserRouter>
  );
}

function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        {children}
      </div>
    </div>
  );
}

function AdminRoutes() {
  const [user, setUser_] = useState<User | null>(null);
  useEffect(() => { fetchMe().then(setUser_); }, []);

  async function handleLogout() {
    await logout();
    window.location.href = "/";
  }

  return (
    <>
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="text-xs text-gray-500">
          Signed in as <strong>{user?.username || "..."}</strong>
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
          <Route path="/dispatch" element={<DispatchPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </main>
    </>
  );
}

export default App;
