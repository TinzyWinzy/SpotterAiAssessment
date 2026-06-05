import { test, expect } from "@playwright/test";
import { ensureServers } from "./_setup";

test.beforeAll(async () => { await ensureServers(); });

test.describe("Trip planning flow", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("short trip: trip summary + map + log + PDF button", async ({ page }) => {
    await page.getByRole("button", { name: /short trip/i }).click();
    await page.getByRole("button", { name: /plan trip/i }).click();

    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 30_000 });

    // Map renders (Leaflet injects a .leaflet-container)
    await expect(page.locator(".leaflet-container").first()).toBeVisible();

    await expect(page.getByText(/driver.s daily log/i).first()).toBeVisible();

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

  test("long trip shows rest/fuel stops in the Stops & Rests list", async ({ page }) => {
    await page.getByRole("button", { name: /cross-country/i }).click();
    await page.getByRole("button", { name: /plan trip/i }).click();

    await expect(page.getByRole("heading", { name: /stops.*rests/i })).toBeVisible({ timeout: 60_000 });
    // At least one fuel + one break + one 10-hr reset for a 2126 mi cross-country trip
    await expect(page.getByText(/fueling/i).first()).toBeVisible();
    await expect(page.getByText(/30-min break/i).first()).toBeVisible();
    await expect(page.getByText(/10-hr reset/i).first()).toBeVisible();

    // The map should have rest-stop markers (counted via .custom-marker divs)
    const markers = page.locator(".custom-marker");
    expect(await markers.count()).toBeGreaterThan(3); // 3 main stops + rest stops
  });

  test("each daily log renders the FMCSA recap table", async ({ page }) => {
    await page.getByRole("button", { name: /cross-country/i }).click();
    await page.getByRole("button", { name: /plan trip/i }).click();

    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Driver's Daily Log/i).first()).toBeVisible({ timeout: 60_000 });
    // Recap table headers — both driver columns
    await expect(page.getByText(/70 Hour \/ 8 Day Drivers/i).first()).toBeVisible();
    await expect(page.getByText(/60 Hour \/ 7 Day Drivers/i).first()).toBeVisible();
    // All 6 cells (A, B, C, D, E, F) — visible in <text> elements
    for (const cell of ["A.", "B.", "C.", "D.", "E.", "F."]) {
      await expect(page.getByText(cell, { exact: true }).first()).toBeVisible();
    }
    await expect(page.getByText(/Original — File at home terminal/i).first()).toBeVisible();
    await expect(page.getByText(/Shipping Documents/i).first()).toBeVisible();
    await expect(page.getByText(/Use time standard of home terminal/i).first()).toBeVisible();
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
