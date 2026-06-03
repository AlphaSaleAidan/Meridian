import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the Meridian frontend e2e suite.
 *
 * Specs in ./e2e cover three layers:
 *   - ui-smoke + customer-portal + admin-routes: broad surface crawls
 *   - lead-e2e + canada-lead-e2e: deep critical-path flows
 *   - login-errors + mobile-viewport: targeted edge-case coverage
 *
 * All specs accept E2E_APP_URL (default http://localhost:5173) and the
 * auth-requiring ones accept E2E_EMAIL / E2E_PASSWORD.
 *
 * workers: 1 because specs share a Supabase project and mutate state;
 * parallel runs would race lead-create + cleanup.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 300_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL: process.env.E2E_APP_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    headless: true,
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
