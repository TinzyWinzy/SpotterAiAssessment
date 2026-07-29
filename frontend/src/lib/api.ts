import type {
  TripRequest, TripResponse, TripEstimateRequest, TripEstimateResponse,
  Trip, Vehicle, Driver, FuelRecord, Commodity, CommodityCategory,
  PublicQuoteRequest, PublicQuoteResponse, PublicBookingRequest, PublicBookingResponse,
  TrackingData, TripImage, ServiceType,
} from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

function authHeaders(): Record<string, string> {
  const t = localStorage.getItem("truckledger_token");
  return t ? { Authorization: `Token ${t}`, "Content-Type": "application/json" } : { "Content-Type": "application/json" };
}

async function jsonOrError<T>(resp: Response): Promise<T> {
  if (resp.status === 401) {
    // Token expired or missing — clear stale credentials and force re-login
    localStorage.removeItem("truckledger_token");
    if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/book") && !window.location.pathname.startsWith("/track")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please log in again.");
  }
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = body.error || body.detail || JSON.stringify(body);
    throw new Error(detail);
  }
  return body as T;
}

// --- Trip Planning ---

export async function planTrip(req: TripRequest): Promise<TripResponse> {
  const resp = await fetch(`${API_BASE}/api/trip/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(req),
  });
  return jsonOrError<TripResponse>(resp);
}

export async function estimateTrip(req: TripEstimateRequest): Promise<TripEstimateResponse> {
  const resp = await fetch(`${API_BASE}/api/trip/estimate/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify(req),
  });
  return jsonOrError<TripEstimateResponse>(resp);
}

// --- Trips ---

export async function fetchTrips(params?: { status?: string; from_date?: string; to_date?: string; page?: number; page_size?: number }): Promise<{ ok: true; trips: Trip[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.from_date) qs.set("from_date", params.from_date);
  if (params?.to_date) qs.set("to_date", params.to_date);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const resp = await fetch(`${API_BASE}/api/trips/?${qs}`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function fetchTrip(id: number): Promise<{ ok: true; trip: Trip }> {
  const resp = await fetch(`${API_BASE}/api/trips/${id}/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function updateTrip(id: number, data: Partial<Trip>): Promise<{ ok: true; trip: Trip }> {
  const resp = await fetch(`${API_BASE}/api/trips/${id}/`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

export async function updateTripStatus(id: number, status: string, location_text?: string, notes?: string): Promise<{ ok: true; trip: Trip }> {
  const resp = await fetch(`${API_BASE}/api/trips/${id}/status/`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ status, location_text, notes }),
  });
  return jsonOrError(resp);
}

// --- Vehicles ---

export async function fetchVehicles(): Promise<{ ok: true; vehicles: Vehicle[] }> {
  const resp = await fetch(`${API_BASE}/api/vehicles/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function createVehicle(data: Partial<Vehicle>): Promise<{ ok: true; vehicle: Vehicle }> {
  const resp = await fetch(`${API_BASE}/api/vehicles/`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

export async function updateVehicle(id: number, data: Partial<Vehicle>): Promise<{ ok: true; vehicle: Vehicle }> {
  const resp = await fetch(`${API_BASE}/api/vehicles/${id}/`, {
    method: "PATCH", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

// --- Drivers ---

export async function fetchDrivers(): Promise<{ ok: true; drivers: Driver[] }> {
  const resp = await fetch(`${API_BASE}/api/drivers/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function createDriver(data: Partial<Driver>): Promise<{ ok: true; driver: Driver }> {
  const resp = await fetch(`${API_BASE}/api/drivers/`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

export async function updateDriver(id: number, data: Partial<Driver>): Promise<{ ok: true; driver: Driver }> {
  const resp = await fetch(`${API_BASE}/api/drivers/${id}/`, {
    method: "PATCH", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

// --- Fuel ---

export async function createFuelRecord(data: { trip: number; vehicle: number; litres: number; price_per_litre_usd: number; total_cost_usd: number; location_text?: string }): Promise<{ ok: true; fuel_record: FuelRecord }> {
  const resp = await fetch(`${API_BASE}/api/fuel/`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

// --- Commodities ---

export async function fetchCommodities(): Promise<{ ok: true; commodities: Commodity[] }> {
  const resp = await fetch(`${API_BASE}/api/commodities/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function fetchCommodityCategories(): Promise<{ ok: true; categories: CommodityCategory[] }> {
  const resp = await fetch(`${API_BASE}/api/commodity-categories/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

// --- Auth ---

// --- Position tracking ---

export async function fetchTripPositions(tripId: number): Promise<{ ok: true; positions: import("./types").TripPosition[] }> {
  const resp = await fetch(`${API_BASE}/api/trips/${tripId}/positions/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function reportTripPosition(
  tripId: number,
  data: { lat: number; lon: number; accuracy?: number; source?: string; remark?: string },
): Promise<{ ok: true; position: import("./types").TripPosition }> {
  const resp = await fetch(`${API_BASE}/api/trips/${tripId}/positions/`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

// --- Admin / Live Map ---

export async function fetchActiveTrips(): Promise<{ ok: true; active_trips: (import("./types").Trip & { last_position: import("./types").TripPosition | null })[]; count: number }> {
  const resp = await fetch(`${API_BASE}/api/admin/active-trips/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

// --- SOS ---

export async function triggerSos(
  tripId: number,
  data?: { message?: string; lat?: number; lon?: number },
): Promise<{ ok: true }> {
  const resp = await fetch(`${API_BASE}/api/trips/${tripId}/sos/`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(data || {}),
  });
  return jsonOrError(resp);
}

export async function acknowledgeSos(tripId: number): Promise<{ ok: true }> {
  const resp = await fetch(`${API_BASE}/api/trips/${tripId}/sos/acknowledge/`, {
    method: "POST", headers: authHeaders(),
  });
  return jsonOrError(resp);
}

// --- Public Booking ---

export async function getPublicQuote(req: PublicQuoteRequest): Promise<PublicQuoteResponse> {
  const resp = await fetch(`${API_BASE}/api/public/quote/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return jsonOrError(resp);
}

export async function createPublicBooking(req: PublicBookingRequest): Promise<PublicBookingResponse> {
  const resp = await fetch(`${API_BASE}/api/public/book/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return jsonOrError(resp);
}

export async function getPublicBooking(ref: string, token: string): Promise<{ ok: boolean; booking: Trip }> {
  const resp = await fetch(`${API_BASE}/api/public/book/${ref}/?token=${encodeURIComponent(token)}`);
  return jsonOrError(resp);
}

export async function confirmPublicBooking(ref: string, token: string): Promise<{ ok: boolean; status: string }> {
  const resp = await fetch(`${API_BASE}/api/public/book/${ref}/confirm/?token=${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  return jsonOrError(resp);
}

export async function trackPublicBooking(ref: string, token: string): Promise<TrackingData> {
  const resp = await fetch(`${API_BASE}/api/public/track/${ref}/?token=${encodeURIComponent(token)}`);
  return jsonOrError(resp);
}

export async function fetchServices(): Promise<{ ok: boolean; services: ServiceType[] }> {
  const resp = await fetch(`${API_BASE}/api/services/`);
  return jsonOrError(resp);
}

// --- Admin Booking ---

export async function fetchBookings(params?: { status?: string; service_type?: string }): Promise<{ ok: boolean; bookings: Trip[] }> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.service_type) qs.set("service_type", params.service_type);
  const resp = await fetch(`${API_BASE}/api/bookings/?${qs}`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function assignBooking(id: number, data: { driver_id: number; vehicle_id: number }): Promise<{ ok: boolean; trip: Trip }> {
  const resp = await fetch(`${API_BASE}/api/bookings/${id}/assign/`, {
    method: "POST", headers: authHeaders(), body: JSON.stringify(data),
  });
  return jsonOrError(resp);
}

export async function fetchBookingImages(id: number): Promise<{ ok: boolean; images: TripImage[] }> {
  const resp = await fetch(`${API_BASE}/api/bookings/${id}/images/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function uploadBookingImage(id: number, file: File, caption?: string): Promise<{ ok: boolean; image: TripImage }> {
  const form = new FormData();
  form.append("image", file);
  if (caption) form.append("caption", caption);
  const t = localStorage.getItem("truckledger_token");
  const headers: Record<string, string> = {};
  if (t) headers["Authorization"] = `Token ${t}`;
  const resp = await fetch(`${API_BASE}/api/bookings/${id}/images/`, {
    method: "POST", headers, body: form,
  });
  return jsonOrError(resp);
}

// --- Dashboard ---

export async function fetchDashboard(): Promise<import("./types").DashboardMetrics> {
  const resp = await fetch(`${API_BASE}/api/admin/metrics/`, { headers: authHeaders() });
  return jsonOrError(resp);
}

export async function fetchFleetSummary(): Promise<string> {
  const resp = await fetch(`${API_BASE}/api/admin/summary/`, { headers: authHeaders() });
  const body = await jsonOrError<{ text: string }>(resp);
  return body.text;
}
