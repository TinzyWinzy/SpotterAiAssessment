import { chromium } from "@playwright/test";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const OUT = resolve(__dirname, "..", "..", "docs", "screenshots");

async function main() {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();

  await page.goto("https://frontend-three-sage-11.vercel.app/", { waitUntil: "networkidle", timeout: 60_000 });
  await page.waitForTimeout(1500);
  await page.screenshot({ path: `${OUT}/00-form.png`, fullPage: false });
  console.log("form shot saved");

  await page.getByRole("button", { name: /cross-country/i }).click();
  await page.getByRole("button", { name: /plan trip/i }).click();
  await page.getByRole("heading", { name: /trip summary/i }).waitFor({ timeout: 60_000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: `${OUT}/01-cross-country-hero.png`, fullPage: true });
  console.log("hero shot saved");

  const firstLogSvg = page.locator("svg").filter({ hasText: /Recap/ }).first();
  await firstLogSvg.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1500);
  const logContainer = firstLogSvg.locator("xpath=..").locator("xpath=..");
  await logContainer.screenshot({ path: `${OUT}/02-daily-log-recap.png` });
  console.log("recap shot saved");

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
