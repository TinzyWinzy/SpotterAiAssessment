import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../lib/auth";
import { Truck, LogIn } from "lucide-react";

import type { User } from "../lib/types";

interface Props {
  onLogin: () => Promise<User | null>;
}

export function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await login(username, password);
      const me = await onLogin();
      if (me?.is_admin) {
        navigate("/app/dashboard");
      } else if (me?.driver_id) {
        navigate("/driver");
      } else {
        navigate("/app/dashboard");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-spotter-50 to-gray-50 flex items-center justify-center p-6">
      <div className="bg-white rounded-xl shadow-md p-8 w-full max-w-sm">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-full bg-spotter-600 flex items-center justify-center">
            <Truck className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-spotter-800">Trucki</h1>
            <p className="text-xs text-gray-500">Sign in to your fleet</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label htmlFor="username" className="block text-xs font-medium text-gray-700 mb-1">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-spotter-500"
              required
              autoComplete="username"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-medium text-gray-700 mb-1">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-spotter-500"
              required
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-xs text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="w-full flex items-center justify-center gap-2 bg-spotter-600 hover:bg-spotter-700 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-md"
          >
            <LogIn className="w-4 h-4" /> {busy ? "Signing in…" : "Sign in"}
          </button>
          <p className="text-xs text-gray-400 text-center pt-2">
            Demo: <code className="text-gray-600">admin / admin</code>
          </p>
        </form>
      </div>
    </div>
  );
}
