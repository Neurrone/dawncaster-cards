import { test, expect } from "@playwright/test";

const WAIT_TIMEOUT = 10_000;

test("cards page filters populate and filter results", async ({ page }) => {
  await page.goto("/cards.html");

  await page.waitForSelector("#loading", { state: "hidden" });

  await page.waitForSelector("#category option[value]", {
    state: "attached",
    timeout: WAIT_TIMEOUT,
  }); // ensure filters populated

  const categoryOptions = page.locator("#category option");
  const categoryCount = await categoryOptions.count();
  expect(categoryCount).toBeGreaterThan(1);

  await page.waitForSelector('#banner option[value="2"]', {
    state: "attached",
    timeout: WAIT_TIMEOUT,
  });

  await page.selectOption("#banner", "2");

  await expect(page.locator("#cardTableContainer")).toBeVisible();

  await page.waitForFunction(
    () => document.querySelectorAll("#cardTable tbody tr").length > 0,
    { timeout: WAIT_TIMEOUT }
  );

  const rowCount = await page.locator("#cardTable tbody tr").count();
  expect(rowCount).toBeGreaterThan(0);
});
