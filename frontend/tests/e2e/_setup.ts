/**
 * One-time setup for Playwright: starts Django + Vite dev servers in the background
 * if they're not already running. Idempotent — safe to import from multiple specs.
 *
 * Server detection: GETs /api/health/ and the Vite root, waits up to 30s each.
 * If the frontend is already up, this becomes a no-op.
 */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const BACKEND_DIR = path.resolve(__dirname, "../../../backend");
const FRONTEND_DIR = path.resolve(__dirname, "../../");
const BACKEND_PORT = 8001;
const FRONTEND_PORT = 5173;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health/`;
const FRONTEND_URL = `http://127.0.0.1:${FRONTEND_PORT}/`;

let setupDone = false;

function probe(url: string, timeoutMs = 1500): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(url, (res) => {
      res.resume();
      resolve(!!res.statusCode && res.statusCode < 500);
    });
    req.on("error", () => resolve(false));
    req.setTimeout(timeoutMs, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitFor(url: string, timeoutMs: number): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await probe(url)) return;
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`Timeout waiting for ${url}`);
}

function start(name: string, cmd: string, args: string[], cwd: string) {
  if (process.platform === "win32") {
    // Spawn a detached process and return immediately.
    const child = spawn("cmd.exe", ["/c", "start", "/B", "cmd.exe", "/c", [cmd, ...args].join(" ")], {
      cwd,
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    });
    child.unref();
    return child;
  }
  const child = spawn(cmd, args, { cwd, detached: true, stdio: "ignore" });
  child.unref();
  return child;
}

export async function ensureServers(): Promise<void> {
  if (setupDone) return;
  setupDone = true;

  if (!existsSync(path.join(BACKEND_DIR, "manage.py"))) {
    throw new Error(`Django backend not found at ${BACKEND_DIR}`);
  }

  if (!(await probe(BACKEND_URL))) {
    start("django", "python", ["manage.py", "runserver", `127.0.0.1:${BACKEND_PORT}`], BACKEND_DIR);
    await waitFor(BACKEND_URL, 30_000);
  }

  if (!(await probe(FRONTEND_URL))) {
    start("vite", "npx", ["vite", "--port", String(FRONTEND_PORT), "--host", "127.0.0.1"], FRONTEND_DIR);
    await waitFor(FRONTEND_URL, 30_000);
  }
}

export const config = {
  FRONTEND_URL,
  BACKEND_URL,
};
