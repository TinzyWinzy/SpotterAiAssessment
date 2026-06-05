import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for Spotter trip planner e2e tests.
 *
 * The Django + Vite servers are started by tests/e2e/_setup.ts via `beforeAll`
 * (idempotent — skips if a server is already running).
 *
 * Set FRONTEND_URL to point at the deployed app instead of running locally.
 */
const FRONTEND_URL = process.env.FRONTEND_URL;

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL: FRONTEND_URL ?? "http://127.0.0.1:5173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
