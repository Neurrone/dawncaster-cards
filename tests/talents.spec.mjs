import { test, expect } from "@playwright/test";

const WAIT_TIMEOUT = 10_000;

test("talents page populates filters and renders results", async ({ page }) => {
  await page.goto("/talents.html");

  await page.waitForSelector("#loading", { state: "hidden" });

  await page.waitForSelector("#expansion option[value]", {
    state: "attached",
    timeout: WAIT_TIMEOUT,
  });

  await page.waitForSelector('#expansion option[value="1"]', {
    state: "attached",
    timeout: WAIT_TIMEOUT,
  });

  await page.selectOption("#expansion", "1");

  await expect(page.locator("#talentTableContainer")).toBeVisible();

  await page.waitForFunction(
    () => document.querySelectorAll("#talentTable tbody tr").length > 0,
    { timeout: WAIT_TIMEOUT }
  );

  const rowCount = await page.locator("#talentTable tbody tr").count();
  expect(rowCount).toBeGreaterThan(0);
});
