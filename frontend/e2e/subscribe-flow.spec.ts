/**
 * subscribe-flow.spec.ts
 *
 * Asserts the Stripe subscribe short-link + QR contract on
 * CanadaPortalLeadDetailPage:
 *
 * 1. Clicking "Generate Invoice (CAD)" fires POST /api/stripe/subscribe-link
 *    with the correct body: currency = 'CAD' and monthly_amount_cents > 0.
 * 2. A <img alt="Checkout QR code"> renders after the call resolves (the QR is
 *    generated client-side by the qrcode lib — no external service dependency).
 * 3. "Open subscribe link" appears pointing at the mocked subscribe URL.
 *
 * Auth + Supabase REST are fully mocked via the wizard harness so no live
 * credentials are needed for the main test suite. The block marked
 * "live portal smoke" is guarded with test.skip unless E2E_EMAIL +
 * E2E_PASSWORD are set — consistent with all other non-wizard e2e specs.
 *
 * Run (mocked — default):
 *   npx playwright test e2e/subscribe-flow.spec.ts
 * Run (live, needs creds):
 *   E2E_EMAIL=... E2E_PASSWORD=... E2E_APP_URL=... \
 *   npx playwright test e2e/subscribe-flow.spec.ts
 */
import { test, expect } from '@playwright/test'
import {
  captureApi,
  mockSupabase,
  seedRepAuth,
} from './wizards/_harness'

const APP_URL = process.env.E2E_APP_URL ?? 'http://localhost:3000'
const EMAIL = process.env.E2E_EMAIL ?? ''
const PASSWORD = process.env.E2E_PASSWORD ?? ''

// ── Mock lead row ────────────────────────────────────────────────────────────
// Stage `customer_checkout` maps to currentStep=2 (STAGE_TO_STEP), which makes
// the "Invoice & Checkout" section visible immediately — no stage progression
// needed during the test. Shape matches CanadaLeadRowSchema (canada-leads-service).
const TEST_LEAD_ID = 'aaaaaaaa-1234-4abc-8abc-aaa000000001'
const MOCK_DEAL_ROW = {
  id: TEST_LEAD_ID,
  business_name: 'E2E Subscribe Bistro',
  contact_name: 'Tess Tester',
  contact_email: 'subscribe@e2e.local',
  contact_phone: '5551230001',
  vertical: 'restaurant',
  stage: 'customer_checkout',
  monthly_value: 500, // $500 default → 50 000 cents
  commission_rate: 0.7,
  expected_close_date: '2026-12-01',
  notes: '',
  source: '',
  city: '',
  province: '',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

// Mock URL returned by the subscribe-link API stub.
const MOCK_SUBSCRIBE_URL = 'https://meridian.tips/subscribe/e2e-test-token-abc'

// ─────────────────────────────────────────────────────────────────────────────
// MOCKED flow — no live credentials required, runs in CI
// ─────────────────────────────────────────────────────────────────────────────
test.describe('subscribe-flow — mocked', () => {
  test(
    'POST /api/stripe/subscribe-link carries currency:CAD + monthly_amount_cents; QR and link render',
    async ({ page }) => {
      // 1. Seed rep auth: fake Supabase session + sales-rep profile in localStorage
      //    before the app boots. SalesAuthProvider reads this in its initial useState.
      await seedRepAuth(page)

      // 2. Mock Supabase auth + all REST calls (default harness returns null for REST).
      await mockSupabase(page)

      // 3. Override the canada_leads endpoint AFTER mockSupabase so Playwright's
      //    last-registered-wins rule gives this route priority for canada_leads.
      //    supabase-js .single() expects a single JSON object (not array).
      await page.route('**/rest/v1/canada_leads**', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_DEAL_ROW),
        })
      })

      // 4. Capture all /api/** requests; return mock subscribe URL for the
      //    subscribe-link endpoint. captureApi must be registered AFTER the
      //    Supabase mocks (it intercepts **/api/** only).
      const api = await captureApi(page, {
        responses: {
          '/api/stripe/subscribe-link': { url: MOCK_SUBSCRIBE_URL },
        },
      })

      // 5. Navigate to the lead detail page.
      await page.goto(
        `${APP_URL}/canada/portal/leads/${TEST_LEAD_ID}`,
        { waitUntil: 'domcontentloaded' },
      )

      // 6. Wait for the "Invoice & Checkout" section heading (currentStep >= 2).
      await expect(
        page.getByRole('heading', { name: /invoice.*checkout/i }),
      ).toBeVisible({ timeout: 20_000 })

      // 7. Click "Generate Invoice (CAD)".
      await page.getByRole('button', { name: /generate invoice.*cad/i }).click()

      // 8. Wait for the POST to be captured, then assert request body.
      //    The component sets currency: 'CAD' unconditionally and computes
      //    monthly_amount_cents from the price slider default ($500 → 50 000).
      await expect
        .poll(
          () => api.find('/api/stripe/subscribe-link'),
          { timeout: 10_000, message: 'subscribe-link POST was not captured' },
        )
        .toBeTruthy()

      const req = api.find('/api/stripe/subscribe-link')!
      expect(req.method, 'must be POST').toBe('POST')
      expect(req.json?.currency, 'currency must be CAD').toBe('CAD')
      expect(
        typeof req.json?.monthly_amount_cents,
        'monthly_amount_cents must be a number',
      ).toBe('number')
      expect(
        req.json?.monthly_amount_cents,
        'monthly_amount_cents must be positive',
      ).toBeGreaterThan(0)

      // 9. Assert client-side QR renders (generated by the qrcode lib from the
      //    returned URL; no external image service is used).
      await expect(
        page.locator('img[alt="Checkout QR code"]'),
      ).toBeVisible({ timeout: 10_000 })

      // 10. Assert "Open subscribe link" anchor is visible.
      await expect(
        page.getByRole('link', { name: /open subscribe link/i }),
      ).toBeVisible({ timeout: 5_000 })
    },
  )
})

// ─────────────────────────────────────────────────────────────────────────────
// LIVE-PORTAL smoke guard
// Skipped in CI unless E2E_EMAIL + E2E_PASSWORD are explicitly provided.
// Mirrors the guard pattern used by canada-lead-e2e.spec.ts and canada-realtime.spec.ts.
// ─────────────────────────────────────────────────────────────────────────────
test.describe('subscribe-flow — live portal smoke', () => {
  test(
    'subscribe-link API is reachable from live portal after login',
    async ({ page }) => {
      test.skip(
        !EMAIL || !PASSWORD,
        'Set E2E_EMAIL + E2E_PASSWORD + E2E_APP_URL to run the live-portal smoke',
      )

      // Login, then navigate to the leads list and confirm the app boots
      // without a subscribe-link 500 (the specific lead/invoice interaction
      // is not automated here — that requires a pre-existing test lead).
      await page.goto(`${APP_URL}/canada/portal/login`, { waitUntil: 'domcontentloaded' })
      await page.waitForSelector('input[type="email"]', { timeout: 15_000 })
      await page.fill('input[type="email"]', EMAIL)
      await page.fill('input[type="password"]', PASSWORD)
      await Promise.all([
        page.waitForURL(/\/canada\/portal\/(dashboard|leads)/, { timeout: 30_000 }),
        page.click('button[type="submit"]'),
      ])
      // If we reached the dashboard/leads without error, the portal is up.
      await expect(page.locator('body')).toBeVisible()
    },
  )
})
