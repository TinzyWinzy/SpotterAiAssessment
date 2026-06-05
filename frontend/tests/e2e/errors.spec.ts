import { test, expect } from "@playwright/test";
import { ensureServers } from "./_setup";

test.beforeAll(async () => { await ensureServers(); });

test.describe("Error handling", () => {
  test("unknown location shows error message", async ({ page }) => {
    await page.goto("/");
    await page.getByLabel(/current location/i).fill("ZZZQXQXQXQXQX");
    await page.getByLabel(/pickup/i).fill("Philadelphia, PA");
    await page.getByLabel(/drop.?off/i).fill("Baltimore, MD");
    await page.getByRole("button", { name: /plan trip/i }).click();

    // Error message should appear
    await expect(page.getByText(/geocoding failed|error|failed/i).first()).toBeVisible({ timeout: 15_000 });
  });

  test("blank current location shows validation error", async ({ page }) => {
    await page.goto("/");
    const currentInput = page.getByLabel(/current location/i);
    await currentInput.fill("");
    await page.getByLabel(/pickup/i).fill("Philadelphia, PA");
    await page.getByLabel(/drop.?off/i).fill("Baltimore, MD");
    await page.getByRole("button", { name: /plan trip/i }).click();

    // The form should NOT show a successful trip summary
    await expect(page.getByRole("heading", { name: /trip summary/i })).not.toBeVisible({ timeout: 5_000 });
  });

  test("cycle hours above 70 is rejected by validation", async ({ page }) => {
    await page.goto("/");
    // The cycle input is type=number with max=70 — filling a value and submitting
    // with a large value triggers a backend validation error (or browser blocks).
    const cycleInput = page.getByLabel(/cycle.*used/i);
    await cycleInput.fill("100");
    await page.getByLabel(/pickup/i).fill("Philadelphia, PA");
    await page.getByLabel(/drop.?off/i).fill("Baltimore, MD");
    await page.getByRole("button", { name: /plan trip/i }).click();

    // Backend rejects >70 — should NOT produce a trip summary
    await expect(page.getByRole("heading", { name: /trip summary/i })).not.toBeVisible({ timeout: 8_000 });
  });
});

test.describe("Sleeper berth toggle", () => {
  test("toggling sleeper off still produces a result", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /long trip/i }).click();

    // Disable sleeper
    const toggle = page.getByLabel(/sleeper/i);
    await toggle.click();
    await expect(toggle).not.toBeChecked();

    await page.getByRole("button", { name: /plan trip/i }).click();
    await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 60_000 });
  });
});
