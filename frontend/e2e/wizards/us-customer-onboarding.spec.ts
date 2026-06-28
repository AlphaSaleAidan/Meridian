/**
 * USCustomerOnboardingWizard — route /us/onboard
 *
 * Drives account → sla → pos → inventory → staff → schedule → checkout end-to-end
 * against mocked Supabase + /api, asserting:
 *   - every step advances,
 *   - the default monthly price is $250 USD when no ?price= param is present
 *     (monthlyPrice = prefill.price ? parseInt(prefill.price) : 250 in the source),
 *   - sign-sla / pos-select / billing / provision all carry a Bearer
 *     (require_org_access / require_service_auth family — fixed in #193/#194),
 *   - checkout invoices + provision share the SAME org_id,
 *   - a failed SLA write BLOCKS progression (the US wizard has the same strict
 *     compliance guard as Canada: `if (!resp.ok) { setError(...); return }`).
 *
 * Auth is faked via a seeded localStorage Supabase session + meridian_org — see
 * _harness.ts. The customer AuthProvider hydrates `org` synchronously from
 * meridian_org (loadOrg()), so org_id is the seeded TEST_ORG_ID throughout.
 * Because org?.org_id is truthy on mount, the account step's handleAccountNext
 * skips signup and goes straight to SLA — form values are still set via React
 * state for the downstream SLA + checkout calls.
 */
import { test, expect } from '@playwright/test'
import {
  captureApi,
  mockSupabase,
  seedCustomerAuth,
  expectBearer,
  TEST_ORG_ID,
} from './_harness'

// Source: `const monthlyPrice = prefill.price ? parseInt(prefill.price) : 250`
// No ?price= in URL → default 250 USD.
const EXPECTED_USD = 250
// SLA body: `monthly_price_usd_cents: Math.round(monthlyPriceUSD * 100)` → 25000
// Checkout: `amount_cents: monthlyPriceUSD * 100` → 25000
const EXPECTED_CENTS = 25000

async function fillAccountAndAdvance(page: import('@playwright/test').Page) {
  await page.getByPlaceholder('Your business name').fill('E2E Test Cafe')
  await page.getByPlaceholder('Full name').fill('Pat Owner')
  await page.getByPlaceholder('you@business.com').fill('owner@e2e-test.local')
  await page.getByPlaceholder('(555) 555-1234').fill('+15555551234')
  // US wizard has a State <select> (not Province). Playwright maps a single-select
  // to role=combobox. Only one select exists on the account step.
  await page.getByRole('combobox').selectOption('California')
  await page.getByPlaceholder('Min 8 characters').fill('supersecret123')
  await page.getByPlaceholder('Confirm password').fill('supersecret123')
  await page.getByRole('button', { name: /next: service agreement/i }).click()
}

async function signSla(page: import('@playwright/test').Page) {
  await expect(page.getByRole('heading', { name: 'Service Agreement', exact: true })).toBeVisible()
  // account.ownerName was set to 'Pat Owner' via the form above, so the
  // signature input placeholder resolves to 'Pat Owner' (not 'Your full legal name').
  await page.getByPlaceholder('Pat Owner').fill('Pat Owner')
  await page.getByRole('checkbox').check()
  await page.getByRole('button', { name: /sign.*continue/i }).click()
}

async function selectPos(page: import('@playwright/test').Page, name = 'Square') {
  // The POSSystemPicker trigger button text is "Search POS systems..." when nothing is selected.
  await page.getByRole('button', { name: /search pos systems/i }).click()
  await page.getByPlaceholder('Search POS systems...').fill(name)
  // The option button accessible name includes status badges (e.g. "Square Integrated ★ Rec"),
  // so match by substring and take first.
  await page.getByRole('button', { name: new RegExp(name, 'i') }).first().click()
  await page.getByRole('button', { name: /next: inventory/i }).click()
}

test.describe('USCustomerOnboardingWizard — /us/onboard', () => {
  test.beforeEach(async ({ page }) => {
    await seedCustomerAuth(page, { org: { org_id: TEST_ORG_ID } })
    await mockSupabase(page)
  })

  test('full happy path: account→…→checkout fires authed $250 USD invoices', async ({ page }) => {
    const api = await captureApi(page)
    await page.goto('/us/onboard', { waitUntil: 'domcontentloaded' })

    // ── account ──
    await expect(page.getByRole('heading', { name: /welcome to meridian/i })).toBeVisible()
    await fillAccountAndAdvance(page)

    // ── sla ── (assert advance + signed agreement POSTed with auth + correct price)
    await signSla(page)
    await expect(page.getByRole('heading', { name: /connect your pos/i })).toBeVisible()
    const sla = api.find('/api/us/sign-sla')
    expectBearer(sla, 'POST /api/us/sign-sla')
    expect(sla!.json.org_id).toBe(TEST_ORG_ID)
    // $250 USD default: monthly_price_usd_cents === 25000 (no ?price= in URL).
    expect(sla!.json.monthly_price_usd_cents).toBe(EXPECTED_CENTS)

    // ── pos ──
    await selectPos(page)
    await expect(page.getByRole('heading', { name: /inventory & cost of goods/i })).toBeVisible()
    const posSel = api.find('/api/pos/select')
    expectBearer(posSel, 'POST /api/pos/select')
    expect(posSel!.json.org_id).toBe(TEST_ORG_ID)
    expect(posSel!.json.pos_system).toBe('square')

    // ── inventory → staff → schedule (skip each optional step) ──
    await page.getByRole('button', { name: /skip for now/i }).click()
    await expect(page.getByRole('heading', { name: /add your team/i })).toBeVisible()
    await page.getByRole('button', { name: /skip for now/i }).click()
    await expect(page.getByRole('heading', { name: /upload your schedule/i })).toBeVisible()
    await page.getByRole('button', { name: /skip for now/i }).click()

    // ── checkout ──
    await expect(page.getByRole('heading', { name: /activate your subscription/i })).toBeVisible()
    // UI shows USD price: "$250.00" (setup fee line). Two occurrences ($250.00 and $250.00/mo).
    await expect(page.getByText('$250.00').first()).toBeVisible()
    await page.getByRole('button', { name: /send invoice to my email/i }).click()

    // Success state.
    await expect(page.getByText(/invoices sent/i).first()).toBeVisible()

    // Two invoices (upfront + recurring), both authed, both for the right org + amount.
    const invoices = api.all('/api/billing/create-invoice')
    expect(invoices).toHaveLength(2)
    for (const inv of invoices) {
      expectBearer(inv, 'create-invoice')
      expect(inv.json.org_id).toBe(TEST_ORG_ID)
      // amount_cents = monthlyPriceUSD * 100 = 250 * 100 = 25000
      expect(inv.json.amount_cents).toBe(EXPECTED_CENTS)
    }

    // Provision call is authed and shares the same org_id as the invoices.
    const prov = api.find('/api/onboarding/provision-customer')
    expectBearer(prov, 'provision-customer')
    expect(prov!.json.org_id).toBe(TEST_ORG_ID)
    // monthly_price (dollars, not cents) sent to provision: 250
    expect(prov!.json.monthly_price).toBe(EXPECTED_USD)
  })

  test('a failed SLA write blocks progression (no silent signature loss)', async ({ page }) => {
    // US wizard has the same strict compliance guard as Canada:
    //   if (!resp.ok) { setError(...); return }  — does NOT advance to POS on failure.
    const api = await captureApi(page, { status: { '/api/us/sign-sla': 500 } })
    await page.goto('/us/onboard', { waitUntil: 'domcontentloaded' })

    await fillAccountAndAdvance(page)
    await signSla(page)

    // The attempt was made …
    expect(api.find('/api/us/sign-sla')).toBeTruthy()
    // … but we did NOT advance to the POS step.
    await expect(page.getByRole('heading', { name: /connect your pos/i })).toHaveCount(0)
    // An error is surfaced (two error elements on SLA step — use first()).
    await expect(page.getByText(/could not save your signed agreement/i).first()).toBeVisible()
    // We remain on the SLA step.
    await expect(page.getByRole('heading', { name: 'Service Agreement', exact: true })).toBeVisible()
  })
})
