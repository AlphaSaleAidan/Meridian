/**
 * Realtime two-context regression test (hardened).
 *
 * Proves the Supabase realtime write-through into `canadaKeys.leads(rep?.rep_id)`
 * actually lands in the cache bucket the mounted page reads from — i.e. that a
 * stage change in one browser context shows up in another live, *because of
 * realtime*, not via a TanStack Query refetch (e.g. refetchOnWindowFocus).
 *
 * The previous version only proved "tab B didn't reload" via a window flag.
 * That's not enough: a refetch would update the badge text and leave the flag
 * intact. This version adds the actual proof:
 *
 *   PRIMARY:   ≥1 postgres_changes WebSocket frame for canada_leads arrived on
 *              context B between A's click and B's badge flip.
 *   SANITY:    every canada_leads REST GET on B during that window came AFTER
 *              the first WS frame — i.e. was triggered by the realtime
 *              subscribe handler, not by focus-refetch.
 *
 * Note on the discriminator: our service's subscribe handler calls
 * `canadaLeadsService.list(repId)` after each WS frame to revalidate the cache.
 * That means the realtime path DOES fire a REST GET — but only AFTER a WS
 * frame. A focus-refetch fires a REST GET WITHOUT a preceding WS frame. The
 * `preWsRestGets` assertion below catches that.
 *
 * The window-reload flag is kept as a corroborating signal.
 */

import { test, expect, type Page } from '@playwright/test'
import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const APP_URL = process.env.E2E_APP_URL ?? 'http://localhost:5173'
const SUPABASE_URL = process.env.E2E_SUPABASE_URL ?? process.env.VITE_SUPABASE_URL ?? ''
const SUPABASE_ANON_KEY = process.env.E2E_SUPABASE_ANON_KEY ?? process.env.VITE_SUPABASE_ANON_KEY ?? ''
const REP_EMAIL = process.env.E2E_REP_EMAIL ?? ''
const REP_PASSWORD = process.env.E2E_REP_PASSWORD ?? ''
const SEED_LEAD_ID = process.env.E2E_SEED_LEAD_ID ?? ''

function requireEnv() {
  const missing: string[] = []
  if (!SUPABASE_URL) missing.push('E2E_SUPABASE_URL (or VITE_SUPABASE_URL)')
  if (!SUPABASE_ANON_KEY) missing.push('E2E_SUPABASE_ANON_KEY (or VITE_SUPABASE_ANON_KEY)')
  if (!REP_EMAIL) missing.push('E2E_REP_EMAIL')
  if (!REP_PASSWORD) missing.push('E2E_REP_PASSWORD')
  if (!SEED_LEAD_ID) missing.push('E2E_SEED_LEAD_ID')
  if (missing.length) {
    throw new Error(
      `[canada-realtime] missing env: ${missing.join(', ')}.\n` +
      `See frontend/e2e/README.md for setup.`
    )
  }
}

let supabase: SupabaseClient

test.beforeAll(async () => {
  requireEnv()
  supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  const { error } = await supabase.auth.signInWithPassword({
    email: REP_EMAIL,
    password: REP_PASSWORD,
  })
  if (error) throw new Error(`[canada-realtime] could not sign in test rep: ${error.message}`)
  await resetLeadToStartingStage()
})

test.afterAll(async () => {
  await resetLeadToStartingStage()
})

test.afterEach(async () => {
  await resetLeadToStartingStage()
})

async function resetLeadToStartingStage() {
  const { error } = await supabase
    .from('canada_leads')
    .update({ stage: 'proposal_shown', updated_at: new Date().toISOString().slice(0, 10) })
    .eq('id', SEED_LEAD_ID)
  if (error) {
    throw new Error(`[canada-realtime] reset failed for ${SEED_LEAD_ID}: ${error.message}`)
  }
}

async function loginRep(page: Page) {
  await page.goto(`${APP_URL}/canada/portal/login`)
  // Login form uses bare <input type="email"|"password"> — no <label>.
  await page.locator('input[type="email"]').fill(REP_EMAIL)
  await page.locator('input[type="password"]').fill(REP_PASSWORD)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL(/\/canada\/portal\/(dashboard|onboarding)/, { timeout: 20_000 })
}

/**
 * Wire HTTP + WebSocket observers on a page so we can later assert that the
 * only `canada_leads` reads on this page during a critical window were
 * triggered by realtime, not by focus-refetch or any other client schedule.
 *
 * Counting is gated by `state.counting` — flip it on AFTER the page's
 * baseline load has completed, then back off once the assertion has run.
 */
function installCanadaLeadsObservers(page: Page) {
  const state = {
    counting: false,
    leadsRestGets: 0,
    leadsWsFrames: 0,
    firstWsFrameAt: null as number | null,
    firstRestGetAt: null as number | null,
    /** REST GETs that fired BEFORE any WS frame — the focus-refetch tell. */
    preWsRestGets: 0,
  }

  page.on('request', (req) => {
    if (!state.counting) return
    if (req.method() !== 'GET') return
    // PostgREST list/getById both hit /rest/v1/canada_leads?...; PATCH/DELETE
    // use the same path but different method, already filtered above.
    if (!req.url().includes('/rest/v1/canada_leads')) return
    state.leadsRestGets++
    if (state.firstRestGetAt == null) state.firstRestGetAt = Date.now()
    if (state.firstWsFrameAt == null) state.preWsRestGets++
  })

  page.on('websocket', (ws) => {
    ws.on('framereceived', ({ payload }) => {
      if (!state.counting) return
      const text = typeof payload === 'string'
        ? payload
        : Buffer.isBuffer(payload) ? payload.toString('utf-8') : ''
      // Supabase realtime frames are Phoenix-channel JSON. A canada_leads
      // change frame contains both the event name and the table name.
      if (text.includes('postgres_changes') && text.includes('canada_leads')) {
        state.leadsWsFrames++
        if (state.firstWsFrameAt == null) state.firstWsFrameAt = Date.now()
      }
    })
  })

  return state
}

test('stage change in tab A appears in tab B via realtime (no refetch)', async ({ browser }) => {
  // Two independent contexts = two separate storage/cache partitions, mimicking
  // two real devices on the same rep account. Not two tabs in one context.
  const ctxA = await browser.newContext()
  const ctxB = await browser.newContext()
  const pageA = await ctxA.newPage()
  const pageB = await ctxB.newPage()

  // Install observers BEFORE any navigation so we never miss a request/frame.
  const bObs = installCanadaLeadsObservers(pageB)

  try {
    // Sequential login: keeps focus changes during login deterministic and
    // happens before counting is enabled, so login GETs aren't counted.
    await loginRep(pageA)
    await loginRep(pageB)

    // Park B on the Leads list.
    await pageB.goto(`${APP_URL}/canada/portal/leads`)
    const leadRowB = pageB.getByTestId(`lead-card-${SEED_LEAD_ID}`)
    await expect(leadRowB).toBeVisible({ timeout: 15_000 })
    await expect(leadRowB.getByTestId('lead-stage-badge')).toHaveText('Proposal Shown')

    // Reload sentinel — set AFTER baseline paint. Corroborating signal only;
    // the WS-frame assertion below is the primary proof.
    await pageB.evaluate(() => {
      ;(window as unknown as { __REALTIME_NO_RELOAD__: boolean }).__REALTIME_NO_RELOAD__ = true
    })

    // Start counting B's canada_leads reads. From here until the badge-flip
    // assertion completes we MUST NOT touch pageB — no clicks, no evaluate,
    // no bringToFront. Any focus event could trip TanStack Query's
    // refetchOnWindowFocus and confound the network counts. The badge
    // assertion below uses a DOM poll (toHaveText), which does not focus
    // the page.
    bObs.counting = true

    // Drive the mutation entirely from A.
    await pageA.goto(`${APP_URL}/canada/portal/leads/${SEED_LEAD_ID}`)
    const advanceBtn = pageA.getByTestId('advance-stage-button')
    await expect(advanceBtn).toBeVisible({ timeout: 15_000 })
    await advanceBtn.click()

    // Poll B's badge — Playwright web-first assertion, no focus event.
    await expect(leadRowB.getByTestId('lead-stage-badge'))
      .toHaveText('Customer Checkout', { timeout: 10_000 })

    bObs.counting = false

    // ── Assertions ────────────────────────────────────────────────────────

    // (a) Corroborating: tab B never reloaded.
    const flagStillSet = await pageB.evaluate(
      () => (window as unknown as { __REALTIME_NO_RELOAD__?: boolean }).__REALTIME_NO_RELOAD__ === true
    )
    expect(flagStillSet, 'tab B reloaded between baseline and badge flip').toBe(true)

    // (b) PRIMARY proof: at least one postgres_changes WS frame for
    // canada_leads arrived on B. Zero frames = realtime channel is dead and
    // any badge update must have come from a client refetch.
    expect(
      bObs.leadsWsFrames,
      'no postgres_changes WS frame arrived on B for canada_leads — the realtime channel did not deliver the update; ' +
      'B updated via some non-realtime path (likely a refetch).'
    ).toBeGreaterThan(0)

    // (c) Refetch guard: every canada_leads REST GET during the count window
    // must have been preceded by a WS frame. A pre-WS GET is the smoking gun
    // for refetchOnWindowFocus or a similar client-side schedule.
    expect(
      bObs.preWsRestGets,
      `a canada_leads REST GET fired on B before any realtime frame arrived — that's a refetch, not a realtime-triggered fetch. ` +
      `(preWsRestGets=${bObs.preWsRestGets}, leadsRestGets=${bObs.leadsRestGets}, leadsWsFrames=${bObs.leadsWsFrames}, ` +
      `firstWsFrameAt=${bObs.firstWsFrameAt}, firstRestGetAt=${bObs.firstRestGetAt})`
    ).toBe(0)
  } finally {
    await ctxA.close()
    await ctxB.close()
  }
})
