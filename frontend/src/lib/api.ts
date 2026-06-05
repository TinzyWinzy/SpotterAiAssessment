import type { TripRequest, TripResponse } from "./types";

const API_BASE = import.meta.env.VITE_API_URL || "";

export async function planTrip(req: TripRequest): Promise<TripResponse> {
  const resp = await fetch(`${API_BASE}/api/trip/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || err.detail || `HTTP ${resp.status}`);
  }
  return resp.json();
}
