import type { TripRequest, TripResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

function authHeaders(): Record<string, string> {
  const t = localStorage.getItem("spotter_token");
  return t ? { Authorization: `Token ${t}` } : {};
}

async function jsonOrError<T>(resp: Response): Promise<T> {
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail = body.error || body.detail || JSON.stringify(body);
    throw new Error(detail);
  }
  return body as T;
}

export async function planTrip(req: TripRequest): Promise<TripResponse> {
  const resp = await fetch(`${API_BASE}/api/trip/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  return jsonOrError<TripResponse>(resp);
}

// --- Auth ---

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  driver_id: number | null;
}

export interface AuthResult {
  ok: boolean;
  token: string;
  user: User;
}

export async function login(username: string, password: string): Promise<AuthResult> {
  const resp = await fetch(`${API_BASE}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return jsonOrError<AuthResult>(resp);
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout/`, {
    method: "POST",
    headers: authHeaders(),
  });
}

export async function fetchMe(): Promise<User | null> {
  const resp = await fetch(`${API_BASE}/api/auth/me/`, { headers: authHeaders() });
  if (resp.status === 401 || resp.status === 403) return null;
  const body = await jsonOrError<{ ok: true; user: User }>(resp);
  return body.user;
}

// --- Admin ---

export interface AdminMetrics {
  ok: true;
  generated_at: string;
  totals: {
    trips: number;
    drivers: number;
    drivers_with_trips: number;
    drivers_with_history: number;
    miles: number;
    driving_hrs: number;
    on_duty_hrs: number;
    avg_miles_per_trip: number;
  };
  window: {
    trips_7d: number;
    trips_30d: number;
    sparkline_30d: { date: string; count: number }[];
  };
  top_routes: {
    origin: string;
    pickup: string;
    destination: string;
    count: number;
    miles: number;
  }[];
  cycle_histogram: { label: string; count: number }[];
  top_drivers: { id: number; name: string; trips: number; miles: number }[];
}

export interface AdminTripRow {
  id: number;
  driver: number | null;
  driver_name: string | null;
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  total_miles: number;
  total_days: number;
  total_driving_hrs: number;
  total_on_duty_hrs: number;
  final_cycle_used: number;
  recap_approximate: boolean;
  created_at: string;
}

export async function fetchMetrics(): Promise<AdminMetrics> {
  const resp = await fetch(`${API_BASE}/api/admin/metrics/`, { headers: authHeaders() });
  return jsonOrError<AdminMetrics>(resp);
}

export async function fetchAdminTrips(
  page = 1,
  pageSize = 20,
): Promise<{ ok: true; page: number; page_size: number; total: number; trips: AdminTripRow[] }> {
  const resp = await fetch(
    `${API_BASE}/api/admin/trips/?page=${page}&page_size=${pageSize}`,
    { headers: authHeaders() },
  );
  return jsonOrError(resp);
}
