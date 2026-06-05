import { test, expect } from "@playwright/test";
import { ensureServers } from "./_setup";

test.beforeAll(async () => { await ensureServers(); });

test.describe("Admin page", () => {
  test("admin link is visible on the planner header", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("link", { name: /admin/i })).toBeVisible();
  });

  test("admin route renders login form when anonymous", async ({ page }) => {
    await page.goto("/#/admin");
    await expect(page.getByRole("heading", { name: /spotter admin/i })).toBeVisible();
    await expect(page.getByLabel(/username/i)).toBeVisible();
    await expect(page.getByLabel(/password/i)).toBeVisible();
  });

  test("admin login with valid credentials shows metrics dashboard", async ({ page, request }) => {
    // Use the API to ensure an admin user exists with known credentials.
    // The dev backend has the admin user from `python manage.py seed_demo`.
    await page.goto("/#/admin");
    await page.getByLabel(/username/i).fill("admin");
    await page.getByLabel(/password/i).fill("admin");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should land on the metrics dashboard
    await expect(page.getByRole("heading", { name: /spotter admin/i })).toBeVisible();
    await expect(page.getByText(/trips per day — last 30 days/i)).toBeVisible();
    await expect(page.getByText(/top routes/i)).toBeVisible();
    await expect(page.getByText(/cycle-usage distribution/i)).toBeVisible();
    await expect(page.getByText(/recent trips/i)).toBeVisible();
  });

  test("admin login with wrong password shows error", async ({ page }) => {
    await page.goto("/#/admin");
    await page.getByLabel(/username/i).fill("admin");
    await page.getByLabel(/password/i).fill("wrong-password");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/invalid credentials/i)).toBeVisible();
  });

  test("admin sign out clears session", async ({ page }) => {
    await page.goto("/#/admin");
    await page.getByLabel(/username/i).fill("admin");
    await page.getByLabel(/password/i).fill("admin");
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByText(/sign out/i)).toBeVisible();
    await page.getByRole("button", { name: /sign out/i }).click();
    await expect(page.getByLabel(/username/i)).toBeVisible();
  });

  test("metrics endpoint returns 403 for non-admin token", async ({ request }) => {
    // Register a fresh non-admin user, then probe the admin endpoint
    const username = `e2e_normie_${Date.now()}`;
    const reg = await request.post("/api/auth/register/", {
      data: { username, password: "abcdef", name: "E2E Normie" },
    });
    expect(reg.status()).toBe(201);
    const { token } = await reg.json();
    const r = await request.get("/api/admin/metrics/", {
      headers: { Authorization: `Token ${token}` },
    });
    expect(r.status()).toBe(403);
  });
});
