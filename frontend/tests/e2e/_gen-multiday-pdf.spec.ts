// Generate a multi-day trip PDF by clicking through the UI and capturing the download.
import { test, expect } from "@playwright/test";
import { ensureServers } from "./_setup";
void ensureServers;

test("generate multi-day PDF (LA -> Chicago)", async ({ page }, testInfo) => {
  test.setTimeout(120_000);
  await page.goto("/");
  // Cross-country preset is LA -> Albuquerque -> Chicago (multi-day)
  await page.getByRole("button", { name: /cross-country/i }).click();
  await page.getByRole("button", { name: /plan trip/i }).click();
  await expect(page.getByRole("heading", { name: /trip summary/i })).toBeVisible({ timeout: 60_000 });

  const dl = page.waitForEvent("download", { timeout: 30_000 });
  await page.getByRole("button", { name: /export pdf/i }).click();
  const download = await dl;
  const out = testInfo.outputPath("spotter-trip-plan-multiday.pdf");
  await download.saveAs(out);
  console.log(`Saved: ${out}`);
});
