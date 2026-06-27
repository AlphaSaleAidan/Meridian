import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config.
 *
 * Two modes:
 *  - Against a deployed instance (Canada portal realtime / ui-smoke specs):
 *    set E2E_APP_URL (+ E2E_EMAIL / E2E_PASSWORD). Run `npm run test:e2e:realtime`.
 *    See frontend/e2e/README.md for required env.
 *  - Local public surfaces (e.g. camera.spec.ts hits the public /canada/demo
 *    pages with no auth): leave E2E_APP_URL unset and Playwright boots the Vite
 *    dev server itself via the `webServer` block below.
 *
 * workers: 1 because the realtime specs mutate a shared Supabase row; parallel
 * runs would race the stage reset in afterEach.
 */
const LOCAL_URL = 'http://localhost:3000' // matches vite.config.ts server.port
const baseURL = process.env.E2E_APP_URL ?? LOCAL_URL

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    headless: true,
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  // Only manage the dev server when targeting localhost. When E2E_APP_URL points
  // at a deployed instance we never start anything.
  webServer: process.env.E2E_APP_URL
    ? undefined
    : {
        command: 'npm run dev',
        url: LOCAL_URL,
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
})
