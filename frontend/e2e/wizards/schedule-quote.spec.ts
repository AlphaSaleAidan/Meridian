/**
 * landing/ScheduleQuote — public quote-request flow (no auth).
 *
 * Proves: the CTA opens the form, client validation blocks a bad submit, and a
 * valid submit fires POST /api/quote-request with the correct payload shape,
 * then renders the success state. Mirrors the audit's "✅ confirmed working".
 *
 * Mounted on the Canada landing page (/canada) — see CanadaLandingPage.tsx.
 */
import { test, expect } from '@playwright/test'
import { captureApi, mockSupabase, seedDemoGate } from './_harness'

test.describe('ScheduleQuote — public quote request', () => {
  test('opens form, validates, submits correct payload, shows success', async ({ page }) => {
    await seedDemoGate(page)
    await mockSupabase(page)
    const api = await captureApi(page)

    await page.goto('/canada', { waitUntil: 'domcontentloaded' })

    // Reach the quote section (lazy / below the fold on a long landing page).
    const quote = page.locator('#quote')
    await quote.scrollIntoViewIfNeeded()
    await expect(quote).toBeVisible()

    // CTA → form.
    await page.getByRole('button', { name: /schedule a quote/i }).click()
    await expect(page.locator('#sq-name')).toBeVisible()

    // Invalid submit (empty) must NOT fire the network call.
    await page.getByRole('button', { name: /request my call/i }).click()
    await expect(page.getByText(/please enter your full name/i)).toBeVisible()
    expect(api.all('/api/quote-request')).toHaveLength(0)

    // Fill valid data.
    await page.locator('#sq-name').fill('Jane Doe')
    await page.locator('#sq-biz').fill('Sunrise Coffee Co.')
    await page.locator('#sq-email').fill('jane@sunrise.test')
    await page.locator('#sq-phone').fill('+15551234567')
    // date/window selects already default to first option.

    await page.getByRole('button', { name: /request my call/i }).click()

    // Success state.
    await expect(page.getByText(/we'll call you within your window/i)).toBeVisible()

    // Correct request fired with the right payload shape.
    const req = api.find('/api/quote-request')
    expect(req, 'POST /api/quote-request should have fired').toBeTruthy()
    expect(req!.method).toBe('POST')
    expect(req!.json).toMatchObject({
      full_name: 'Jane Doe',
      business_name: 'Sunrise Coffee Co.',
      email: 'jane@sunrise.test',
      phone: '+15551234567',
    })
    // source + scheduling fields present.
    expect(req!.json.source).toBeTruthy()
    expect(req!.json.preferred_date).toBeTruthy()
    expect(req!.json.preferred_window).toBeTruthy()
    // Honeypot stays empty.
    expect(req!.json.company_website).toBe('')
  })
})
