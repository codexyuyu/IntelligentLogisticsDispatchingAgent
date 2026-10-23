import { defineConfig } from "vitest/config";

/**
 * Frontend test configuration (jsdom + Testing Library).
 *
 * The React workbench itself is delivered from P24-01 onward; this configuration exists so
 * that component and hook tests written from that phase have a fixed runner, coverage
 * target and setup file, and so `npm run test` behaves identically locally and in CI.
 */
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.{test,spec}.{ts,tsx}", "test/**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules/**", "dist/**", "e2e/**"],
    clearMocks: true,
    restoreMocks: true,
    reporters: process.env.CI ? ["default", "junit"] : ["default"],
    outputFile: { junit: "../../artifacts/vitest/junit.xml" },
  },
});
