import { defineConfig, devices } from "@playwright/test";

/**
 * Root Playwright configuration for end-to-end acceptance.
 *
 * The React workbench is delivered from P24-01 onwards and is served by
 * `npm --workspace @logistics/frontend run dev` (Vite default port 5173, overridable
 * with PLAYWRIGHT_BASE_URL). No e2e spec exists yet, so `npm run test:e2e:list`
 * legitimately reports zero tests until P24-01 lands; a Gate must therefore not
 * treat an empty Playwright run as acceptance evidence.
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173";

export default defineConfig({
  testDir: "./apps/frontend/e2e",
  outputDir: "./artifacts/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["json", { outputFile: "artifacts/e2e/results.json" }]],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
});
