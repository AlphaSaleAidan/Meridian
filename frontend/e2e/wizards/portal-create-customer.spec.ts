/**
 * portal-create-customer.spec.ts
 *
 * Proves USPortalCreateCustomerPage (/us/portal/new-customer) and
 * CanadaPortalCreateCustomerPage (/canada/portal/new-customer), with focus on
 * the #194 fixes:
 *
 * A. org_id equality: POST /api/billing/create-checkout and
 *    POST /api/onboarding/provision-customer must carry the SAME org_id value.
 *    The buggy Canada code used `tempOrgId` for checkout and a separate
 *    `businessId` for provision — unreconcilable. The fix generates one
 *    `orgId` via `useState(() => uuid())` and passes it to both endpoints.
 *
 * B. commission_rate ?? 70: with rep seeded at commission_rate=0, the Supabase
 *    us_leads / canada_leads INSERT must send commission_rate=0, not 70.
 *    The old code was `rep?.commission_rate || 70`; `0 || 70 === 70` (falsy
 *    coercion). The fix is `rep?.commission_rate ?? 70`; `0 ?? 70 === 0`.
 *
 * Auth is faked via a seeded localStorage Supabase session + meridian_sales_rep
 * (see _harness.ts). commission_rate defaults to 0 in repSeedValue(), so the
 * spec proves the ?? fix directly.
 */
import { test, expect } from '@playwright/test'
import {
  captureApi,
  mockSupabase,
  seedRepAuth,
  expectBearer,
} from './_harness'

/**
 * Navigate through the 3 detail/plan/customize steps to reach step 4 (preview).
 * Both the Canada and US portals share identical form structure and button labels.
 */
async function fillAndAdvanceToPreview(page: import('@playwright/test').Page) {
  // Wait for the page content to render (SalesAuthProvider must become ready first).
  await expect(page.getByRole('heading', { name: 'Generate Proposal' })).toBeVisible()

  // ── Step 1: Details ──
  await page.getByPlaceholder('e.g. Lucky Dragon Kitchen').fill('E2E Bistro')
  await page.getByPlaceholder('e.g. James Chen').fill('Taylor Tester')
  await page.getByPlaceholder('james@luckydragon.com').fill('cust@e2e-test.local')
  await page.getByRole('button', { name: /next: select plan/i }).click()

  // ── Step 2: Plan (premium is pre-selected — just advance) ──
  await page.getByRole('button', { name: /next: customize/i }).click()

  // ── Step 3: Customize (leave defaults) ──
  await page.getByRole('button', { name: /next: generate/i }).click()

  // Confirm we reached step 4 before continuing.
  await expect(page.getByRole('heading', { name: 'Proposal Ready' })).toBeVisible()
}

test.describe('PortalCreateCustomer — #194 regression guards', () => {

  test(
    'Canada: create-checkout and provision-customer carry the same org_id; commission_rate=0 survives ?? 70 fix',
    async ({ page }) => {
      // Seed rep with commission_rate=0 — the critical value for the ?? fix proof.
      await seedRepAuth(page, { rep: { commission_rate: 0, portal_context: 'all' } })

      // ── B: Capture Supabase canada_leads INSERT to verify commission_rate. ──
      // page.on('request') fires when the page initiates a request, before route
      // interception, so it captures bodies even for mocked endpoints.
      const canadaLeadInserts: Array<Record<string, unknown>> = []
      page.on('request', (req) => {
        if (
          req.url().includes('/rest/v1/canada_leads') &&
          req.method() === 'POST'
        ) {
          try {
            const raw = req.postData() ?? '[]'
            const parsed: unknown = JSON.parse(raw)
            // supabase-js v2 sends a single object or array; normalise to array.
            const rows = Array.isArray(parsed) ? parsed : [parsed]
            for (const row of rows) {
              if (row && typeof row === 'object') {
                canadaLeadInserts.push(row as Record<string, unknown>)
              }
            }
          } catch { /* ignore malformed */ }
        }
      })

      await mockSupabase(page)
      const api = await captureApi(page)

      await page.goto('/canada/portal/new-customer', { waitUntil: 'domcontentloaded' })
      await fillAndAdvanceToPreview(page)

      // ── Step 4: generate checkout first ──
      // This fires POST /api/billing/create-checkout with { org_id: orgId, ... }.
      await page.getByRole('button', { name: /generate checkout link & qr code/i }).click()
      await expect(page.getByText('Checkout session created!')).toBeVisible()

      // ── Then create the customer account ──
      // This fires POST /api/onboarding/provision-customer with { org_id: orgId, ... }
      // then awaits supabase.from('canada_leads').insert({ ..., commission_rate: rep?.commission_rate ?? 70, ... })
      // then calls setStep('confirm').
      await page.getByRole('button', { name: /create customer.*generate link/i }).click()

      // Wait for the confirm step — by which point the provision call and the
      // Supabase insert have both resolved (insert is awaited before setStep).
      await expect(page.getByText(/customer created successfully/i)).toBeVisible()

      // ── A. org_id equality (core #194 proof) ──
      const checkout = api.find('create-checkout')
      const provision = api.find('provision-customer')

      expect(checkout, 'POST /api/billing/create-checkout must have been captured').toBeTruthy()
      expect(provision, 'POST /api/onboarding/provision-customer must have been captured').toBeTruthy()

      const checkoutOrgId: string = checkout!.json.org_id
      const provisionOrgId: string = provision!.json.org_id

      expect(checkoutOrgId, 'create-checkout body must include a non-empty org_id').toBeTruthy()
      // This is the regression guard: both endpoints received the SAME org_id.
      // In the pre-fix Canada code they diverged (tempOrgId vs businessId).
      expect(checkoutOrgId).toBe(provisionOrgId)

      // Both requests must carry a Bearer JWT (require_org_access family fix).
      expectBearer(checkout, 'POST /api/billing/create-checkout')
      expectBearer(provision, 'POST /api/onboarding/provision-customer')

      // ── B. commission_rate ?? 70 fix ──
      // The INSERT to canada_leads carries `commission_rate: rep?.commission_rate ?? 70`.
      // With commission_rate=0 in the seeded rep and the ?? operator, it sends 0.
      expect(
        canadaLeadInserts.length,
        'supabase.from("canada_leads").insert() must have fired',
      ).toBeGreaterThan(0)
      const row = canadaLeadInserts[0]
      expect(
        row.commission_rate,
        'commission_rate=0 must survive (fix: ?? 70 not || 70)',
      ).toBe(0)
    },
  )

  test(
    'US: create-checkout and provision-customer carry the same org_id; commission_rate=0 survives ?? 70 fix',
    async ({ page }) => {
      await seedRepAuth(page, { rep: { commission_rate: 0, portal_context: 'all' } })

      // ── B: Capture Supabase us_leads INSERT ──
      const usLeadInserts: Array<Record<string, unknown>> = []
      page.on('request', (req) => {
        if (
          req.url().includes('/rest/v1/us_leads') &&
          req.method() === 'POST'
        ) {
          try {
            const raw = req.postData() ?? '[]'
            const parsed: unknown = JSON.parse(raw)
            const rows = Array.isArray(parsed) ? parsed : [parsed]
            for (const row of rows) {
              if (row && typeof row === 'object') {
                usLeadInserts.push(row as Record<string, unknown>)
              }
            }
          } catch { /* ignore malformed */ }
        }
      })

      await mockSupabase(page)
      const api = await captureApi(page)

      await page.goto('/us/portal/new-customer', { waitUntil: 'domcontentloaded' })
      await fillAndAdvanceToPreview(page)

      // Generate checkout link → POST /api/billing/create-checkout.
      await page.getByRole('button', { name: /generate checkout link & qr code/i }).click()
      await expect(page.getByText('Checkout session created!')).toBeVisible()

      // Create customer → POST /api/onboarding/provision-customer + us_leads insert.
      // US page additionally calls supabase.auth.resetPasswordForEmail (best-effort,
      // also mocked) before the leads insert.
      await page.getByRole('button', { name: /create customer.*generate link/i }).click()
      await expect(page.getByText(/customer created successfully/i)).toBeVisible()

      // ── A. org_id equality ──
      const checkout = api.find('create-checkout')
      const provision = api.find('provision-customer')

      expect(checkout, 'POST /api/billing/create-checkout must have been captured').toBeTruthy()
      expect(provision, 'POST /api/onboarding/provision-customer must have been captured').toBeTruthy()

      const checkoutOrgId: string = checkout!.json.org_id
      const provisionOrgId: string = provision!.json.org_id

      expect(checkoutOrgId, 'create-checkout body must include a non-empty org_id').toBeTruthy()
      // US already used a single uuid() for both in the original code; this guards
      // that the fix did not accidentally regress it.
      expect(checkoutOrgId).toBe(provisionOrgId)

      expectBearer(checkout, 'POST /api/billing/create-checkout')
      expectBearer(provision, 'POST /api/onboarding/provision-customer')

      // ── B. commission_rate ?? 70 fix ──
      expect(
        usLeadInserts.length,
        'supabase.from("us_leads").insert() must have fired',
      ).toBeGreaterThan(0)
      const row = usLeadInserts[0]
      expect(
        row.commission_rate,
        'commission_rate=0 must survive (fix: ?? 70 not || 70)',
      ).toBe(0)
    },
  )
})
