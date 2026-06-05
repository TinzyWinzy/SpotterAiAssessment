import { test, expect } from "@playwright/test";
import { ensureServers } from "./_setup";

test.beforeAll(async () => { await ensureServers(); });

/**
 * Full trip-planning flow: select preset -> submit -> verify map + log + PDF button.
 */
test.describe("Trip planning flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("short trip: trip summary + map + log + PDF button", async ({ page }) => {
    await page.getByRole("button", { name: /short trip/i }).click();
    await page.getByRole("button", { name: /plan trip/i }).click();

    // Wait for the Trip Summary heading to appear
    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 30_000 });

    // Map renders (Leaflet injects a .leaflet-container)
    await expect(page.locator(".leaflet-container").first()).toBeVisible();

    // At least one daily log appears
    await expect(page.getByText(/driver.s daily log/i).first()).toBeVisible();

    // PDF export button is present
    await expect(page.getByRole("button", { name: /export pdf/i })).toBeVisible();
  });

  test("long trip: multiple day logs", async ({ page }) => {
    await page.getByRole("button", { name: /long trip/i }).click();
    await page.getByRole("button", { name: /plan trip/i }).click();

    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 60_000 });
    const dayLogs = page.getByText(/driver.s daily log/i);
    expect(await dayLogs.count()).toBeGreaterThanOrEqual(2);
  });

  test("custom input: typed locations work", async ({ page }) => {
    await page.getByLabel(/current location/i).fill("Boston, MA");
    await page.getByLabel(/pickup/i).fill("Hartford, CT");
    await page.getByLabel(/drop.?off/i).fill("New York, NY");
    await page.getByRole("button", { name: /plan trip/i }).click();

    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 30_000 });
  });
});

test.describe("PDF export", () => {
  test("export PDF button triggers download", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /short trip/i }).click();
    await page.getByRole("button", { name: /plan trip/i }).click();
    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 30_000 });

    const downloadPromise = page.waitForEvent("download", { timeout: 15_000 });
    await page.getByRole("button", { name: /export pdf/i }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toMatch(/\.pdf$/i);
    const path = await download.path();
    expect(path).toBeTruthy();
  });
});
