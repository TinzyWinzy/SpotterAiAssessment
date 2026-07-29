import type { User } from "./types";

export interface AuthResult {
  ok: boolean;
  token: string;
  user: User;
}

const API_BASE = import.meta.env.VITE_API_URL || "";

export async function login(username: string, password: string): Promise<AuthResult> {
  const resp = await fetch(`${API_BASE}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  const body = await resp.json();
  if (!resp.ok) {
    throw new Error(body.error || body.detail || "Login failed");
  }
  localStorage.setItem("truckledger_token", body.token);
  return body;
}

export async function logout(): Promise<void> {
  const token = localStorage.getItem("truckledger_token");
  if (token) {
    await fetch(`${API_BASE}/api/auth/logout/`, {
      method: "POST",
      headers: { Authorization: `Token ${token}` },
    }).catch(() => {});
  }
  localStorage.removeItem("truckledger_token");
}

export async function fetchMe(): Promise<User | null> {
  const token = localStorage.getItem("truckledger_token");
  if (!token) return null;
  const resp = await fetch(`${API_BASE}/api/auth/me/`, {
    headers: { Authorization: `Token ${token}` },
  });
  if (resp.status === 401 || resp.status === 403) {
    localStorage.removeItem("truckledger_token");
    return null;
  }
  const body = await resp.json();
  return body.user;
}

export function getToken(): string | null {
  return localStorage.getItem("truckledger_token");
}

