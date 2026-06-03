import { defineConfig, devices } from '@playwright/test'

/**
 * Minimal Playwright config for Canada portal realtime tests.
 *
 * Run with: `npm run test:e2e:realtime` (see package.json).
 * Requires env: see frontend/e2e/README.md.
 *
 * workers: 1 because tests mutate a shared Supabase row; parallel runs would
 * race the stage reset in afterEach.
 */
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
    baseURL: process.env.E2E_APP_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    headless: true,
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
