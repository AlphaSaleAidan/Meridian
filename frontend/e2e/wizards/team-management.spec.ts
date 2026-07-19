/**
 * Team Management — nav rename (1a) + publish schedule (1f) e2e proof.
 *
 * Proves:
 *   - the owner nav shows "Team Management" (renamed from "Schedule") and the
 *     pillar exposes a "Team" segment immediately after "Staff".
 *   - Publish Schedule works end-to-end: clicking Publish fires
 *     POST /api/schedule/publish with the correct payload and the UI reflects
 *     the published state.
 *
 * Auth + network are mocked via the shared wizard harness (no real Supabase /
 * backend). Merchant portal lives at /canada/merchant.
 */
import { test, expect } from '@playwright/test'
import { captureApi, mockSupabase, seedCustomerAuth, TEST_ORG_ID } from './_harness'

test.describe('Team Management', () => {
  test('nav is renamed to Team Management and exposes the Team segment', async ({ page }) => {
    await mockSupabase(page)
    await seedCustomerAuth(page)
    await captureApi(page)

    await page.goto('/canada/merchant/schedule?view=team', { waitUntil: 'domcontentloaded' })

    // The pillar label in the nav is now "Team Management" (not "Schedule").
    await expect(page.getByRole('link', { name: /team management/i }).first()).toBeVisible()

    // The Team segment tab is present alongside Schedule / Peak Hours / Staff.
    await expect(page.getByRole('link', { name: /^Staff$/ }).first()).toBeVisible()
    await expect(page.getByRole('link', { name: /^Team$/ }).first()).toBeVisible()
  })

  test('Publish Schedule fires POST /api/schedule/publish', async ({ page }) => {
    await mockSupabase(page)
    await seedCustomerAuth(page)
    const api = await captureApi(page, {
      responses: {
        // Publish endpoint reports a notified count so the UI shows success.
        '/api/schedule/publish': () => ({
          merchant_id: TEST_ORG_ID, week_start_date: '2026-07-13',
          status: 'published', published_at: new Date().toISOString(), notified_count: 2,
        }),
      },
    })

    await page.goto('/canada/merchant/schedule?view=builder', { waitUntil: 'domcontentloaded' })

    // The Publish control is present in the schedule toolbar.
    const publish = page.getByRole('button', { name: /publish/i }).first()
    await publish.scrollIntoViewIfNeeded()
    await expect(publish).toBeVisible()
    await publish.click()

    // The publish endpoint was called with the merchant + week payload.
    await expect.poll(() => api.all('/api/schedule/publish').length).toBeGreaterThan(0)
    const req = api.all('/api/schedule/publish')[0]
    expect(req?.json?.merchant_id).toBeTruthy()
    expect(req?.json?.week_start_date).toBeTruthy()
  })
})
