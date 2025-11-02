import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  use: {
    baseURL: "http://127.0.0.1:4173",
    headless: true,
  },
  webServer: {
    url: "http://127.0.0.1:4173/cards.html",
    reuseExistingServer: true,
  },
});
