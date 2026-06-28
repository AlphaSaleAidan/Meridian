/**
 * SetupWizard (phone) — /app/phone-orders
 *
 * APPROACH: Playwright e2e driving the real route /app/phone-orders.
 * PhoneOrdersPage renders SetupWizard when setupDone===false (localStorage key
 * 'meridian_phone_setup' is not '1' and org is not in demo mode).
 *
 * Coverage:
 *  1. /api/phone/provision-number fires on wizard mount and carries Bearer.
 *  2. /api/credits/balance fires when the user reaches the Activate step and
 *     carries Bearer (via api.apiFetch which always calls getAuthHeaders()).
 *  3. Clicking "Activate Agent" POSTs /api/phone/config with Bearer AND the body
 *     includes `order_routing` (#187 fix: the field is persisted so the live
 *     agent uses the merchant's chosen routing, not a silent default).
 *
 * Auth: seedCustomerAuth — /app route is behind ProtectedRoute (loginPath=/customer/login).
 * The onboarded gate only fires for /canada/* paths, so onboarded:false is fine here.
 */

import { test, expect } from '@playwright/test'
import {
  captureApi,
  mockSupabase,
  seedCustomerAuth,
  expectBearer,
  TEST_ORG_ID,
} from './_harness'

// ── helpers ───────────────────────────────────────────────────────────────────

/** Drive through all 5 wizard steps and return when "Ready to Activate" heading is visible. */
async function driveToActivateStep(page: import('@playwright/test').Page): Promise<void> {
  // Wait for the wizard to appear (step 0: Business Details).
  await expect(
    page.getByRole('heading', { name: /business details/i }),
  ).toBeVisible({ timeout: 10000 })

  // Step 0: wait for provisioning to complete (phone field shows the provisioned number).
  // The number field switches from "Provisioning your number…" (readonly) to the real number.
  await expect(
    page.locator('input[readonly]').filter({ hasText: /Provisioning/ }),
  ).toHaveCount(0, { timeout: 15000 }).catch(async () => {
    // Fallback: just wait for the spinner inside step 0 to disappear.
    await page.waitForTimeout(2000)
  })

  // Once the phone number is assigned, the Next button is enabled. Click it.
  const nextBtn = page.getByRole('button', { name: /^next$/i })
  await expect(nextBtn).toBeEnabled({ timeout: 10000 })
  await nextBtn.click()

  // Step 1: Voice & Greeting.
  await expect(page.getByRole('heading', { name: /voice & greeting/i })).toBeVisible({ timeout: 5000 })
  await page.getByRole('button', { name: /^next$/i }).click()

  // Step 2: Menu Items.
  await expect(page.getByRole('heading', { name: /menu items/i })).toBeVisible({ timeout: 5000 })
  await page.getByRole('button', { name: /^next$/i }).click()

  // Step 3: Order Routing. (Transfer number is empty → valid → Next is enabled.)
  await expect(page.getByRole('heading', { name: /order routing/i })).toBeVisible({ timeout: 5000 })
  await page.getByRole('button', { name: /^next$/i }).click()

  // Step 4: Ready to Activate.
  await expect(page.getByRole('heading', { name: /ready to activate/i })).toBeVisible({ timeout: 5000 })
}

// ── test suite ────────────────────────────────────────────────────────────────

test.describe('SetupWizard (phone) — /app/phone-orders', () => {
  test.beforeEach(async ({ page }) => {
    await seedCustomerAuth(page, { org: { org_id: TEST_ORG_ID } })
    await mockSupabase(page)
  })

  // ── 1. provision-number fires with Bearer on wizard mount ────────────────
  test('wizard mount: /api/phone/provision-number carries Bearer', async ({ page }) => {
    const api = await captureApi(page)
    await page.goto('/app/phone-orders', { waitUntil: 'domcontentloaded' })

    // Wait for the wizard to appear.
    await expect(
      page.getByRole('heading', { name: /business details/i }),
    ).toBeVisible({ timeout: 10000 })

    // Provisioning fires automatically via useEffect on mount.
    // Allow time for the mock to resolve.
    await page.waitForTimeout(2000)

    const provisionReq = api.find('/api/phone/provision-number')
    expectBearer(provisionReq, 'POST /api/phone/provision-number')
    expect(provisionReq!.method).toBe('POST')
    // Body should include merchant_id and country.
    expect(provisionReq!.json?.merchant_id).toBe(TEST_ORG_ID)
    expect(provisionReq!.json?.country).toBeTruthy()
  })

  // ── 2. credits/balance fires with Bearer on Activate step ───────────────
  test('Activate step: /api/credits/balance carries Bearer', async ({ page }) => {
    const api = await captureApi(page)
    await page.goto('/app/phone-orders', { waitUntil: 'domcontentloaded' })

    await driveToActivateStep(page)

    // credits/balance fires via api.creditBalance() when step===4 for the
    // first time. Allow it to resolve.
    await page.waitForTimeout(1500)

    const balanceReq = api.find('/api/credits/balance')
    expectBearer(balanceReq, 'GET /api/credits/balance')
  })

  // ── 3. Activate Agent POST carries Bearer AND includes order_routing ─────
  test('Activate Agent: POST /api/phone/config carries Bearer and persists order_routing (#187)', async ({ page }) => {
    const api = await captureApi(page)
    await page.goto('/app/phone-orders', { waitUntil: 'domcontentloaded' })

    await driveToActivateStep(page)

    // Give the balance check time to resolve (so the button isn't blocked).
    await page.waitForTimeout(1500)

    // Click "Activate Agent".
    const activateBtn = page.getByRole('button', { name: /activate agent/i })
    await expect(activateBtn).toBeVisible({ timeout: 5000 })
    await activateBtn.click()

    // Allow the saveConfig POST to fire and resolve.
    await page.waitForTimeout(1500)

    const configPost = api.find('/api/phone/config')

    // Must carry Bearer (phoneService.saveConfig spreads getAuthHeaders()).
    expectBearer(configPost, 'POST /api/phone/config')
    expect(configPost!.method).toBe('POST')

    // #187 regression guard: order_routing MUST be present in the POST body.
    // Without the fix, this field was omitted and the live agent silently used
    // its own default routing instead of the merchant's chosen option.
    expect(
      configPost!.json?.order_routing,
      'POST /api/phone/config body must include order_routing (#187)',
    ).toBeTruthy()

    // Verify other key fields are persisted.
    expect(configPost!.json?.merchant_id).toBe(TEST_ORG_ID)
    expect(configPost!.json?.active).toBe(true)
    // order_routing defaults to 'sms' when no POS is connected.
    expect(['pos', 'webhook', 'sms', 'email']).toContain(configPost!.json?.order_routing)
  })

  // ── 4. Full Activate flow: verify order_routing value for no-POS merchant ─
  test('order_routing is "sms" when no POS is connected (default for no-POS merchants)', async ({ page }) => {
    const api = await captureApi(page)
    // Seed org with no pos_provider so the wizard defaults routing to 'sms'.
    await page.goto('/app/phone-orders', { waitUntil: 'domcontentloaded' })

    await driveToActivateStep(page)
    await page.waitForTimeout(1500)

    await page.getByRole('button', { name: /activate agent/i }).click()
    await page.waitForTimeout(1500)

    const configPost = api.find('/api/phone/config')
    expect(configPost!.json?.order_routing).toBe('sms')
  })
})
