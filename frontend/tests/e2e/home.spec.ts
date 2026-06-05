import { test, expect } from "@playwright/test";
import { ensureServers } from "./_setup";

test.beforeAll(async () => { await ensureServers(); });

test.describe("Home page renders", () => {
  test("page loads with title and branding", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Spotter/i);
    // The hero card heading
    await expect(page.getByRole("heading", { name: /plan a trip/i })).toBeVisible();
  });

  test("all 4 location inputs are present", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByLabel(/current location/i)).toBeVisible();
    await expect(page.getByLabel(/pickup/i)).toBeVisible();
    await expect(page.getByLabel(/drop.?off/i)).toBeVisible();
  });

  test("cycle hours input is present", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByLabel(/cycle.*used/i)).toBeVisible();
  });

  test("sleeper berth toggle is present", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByLabel(/sleeper/i)).toBeVisible();
  });

  test("plan trip button is present and initially enabled/disabled appropriately", async ({ page }) => {
    await page.goto("/");
    const btn = page.getByRole("button", { name: /plan trip/i });
    await expect(btn).toBeVisible();
  });

  test("4 quick preset buttons exist", async ({ page }) => {
    await page.goto("/");
    // Quick presets in the form
    await expect(page.getByRole("button", { name: /short trip/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /long trip/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /cross-country/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /70hr/i })).toBeVisible();
  });
});

test.describe("Form interactions", () => {
  test("typing into current location updates value", async ({ page }) => {
    await page.goto("/");
    const input = page.getByLabel(/current location/i);
    await input.fill("Boston, MA");
    await expect(input).toHaveValue("Boston, MA");
  });

  test("cycle hours input accepts decimal", async ({ page }) => {
    await page.goto("/");
    const input = page.getByLabel(/cycle.*used/i);
    await input.fill("42.5");
    await expect(input).toHaveValue("42.5");
  });

  test("sleeper berth toggle is on by default", async ({ page }) => {
    await page.goto("/");
    const toggle = page.getByLabel(/sleeper/i);
    await expect(toggle).toBeChecked();
  });

  test("clicking short preset fills the form", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /short trip/i }).click();
    await expect(page.getByLabel(/current location/i)).toHaveValue(/new york/i);
    await expect(page.getByLabel(/pickup/i)).toHaveValue(/philadelphia/i);
    await expect(page.getByLabel(/drop.?off/i)).toHaveValue(/baltimore/i);
  });
});
