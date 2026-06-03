# Canada portal — E2E tests

## `canada-realtime.spec.ts`

Two-context regression that proves the Supabase realtime write-through key
matches the read key, and that the live update path actually delivers via the
realtime channel — not via a TanStack Query refetch.

### What it does

1. Spins up two **independent** Playwright contexts (separate storage, like
   two devices) and signs both in as the same rep — both
   `useCanadaLeads(rep?.rep_id)` calls resolve to the same query key.
2. Tab B parks on `/canada/portal/leads` and confirms the seed lead reads
   "Proposal Shown".
3. Tab B sets `window.__REALTIME_NO_RELOAD__ = true` *after* its initial
   paint. A reload would clear this — corroborating signal only.
4. Tab A opens the lead's detail page and clicks **Advance to Next Stage**.
5. Tab B's stage badge must flip to "Customer Checkout" within 10s.

### What it asserts (three layers)

| Layer | Check | What a failure means |
|---|---|---|
| Crude | `window.__REALTIME_NO_RELOAD__` survived | Tab B reloaded between baseline and badge flip |
| **Primary** | ≥1 `postgres_changes` WebSocket frame for `canada_leads` arrived on B | Realtime channel is dead; update came through some other path |
| Refetch guard | `preWsRestGets === 0` (no `canada_leads` REST GET before the first WS frame) | A client refetch (likely `refetchOnWindowFocus`) updated the badge — the realtime path was never proven |

### Why this is more than just a reload check

A `TanStack Query` refetch (e.g. `refetchOnWindowFocus: true` firing when
Playwright shifts focus to a context) would:

- update the badge text via cache,
- leave `__REALTIME_NO_RELOAD__` intact, and
- **pass a "no reload" test even with realtime dead.**

The WS-frame assertion and the `preWsRestGets === 0` guard close that hole.

### Discriminator nuance — read this

Our service's `canadaLeadsService.subscribe` handler calls
`canadaLeadsService.list(repId)` after each realtime frame to revalidate the
cache. That means the realtime path **does** fire a REST GET — but only
*after* a WS frame. A focus-refetch fires a REST GET with **no** preceding WS
frame. So the right discriminator is:

- WS frame count ≥ 1
- Every REST GET on B during the window came after the first WS frame
  (i.e. `preWsRestGets === 0`)

The simpler assertion the original spec brief described ("zero REST GETs on
B during the window") would always fail in our codebase because the
subscribe handler re-lists. The spec implements the equivalent-strength
assertion that's correct for our architecture.

### Focus-refetch caveat (deliberately not changed in the app)

The app sets `refetchOnWindowFocus: true` in `createCanadaQueryClient` (free
freshness on tab switch back). The test asserts **around** this — it
contains the count window between baseline and badge flip, and never
interacts with `pageB` during that window, so no focus event fires on B.
DOM-polling assertions like `toHaveText` do not focus the page.

If you change the app to disable `refetchOnWindowFocus`, this test still
passes — it's strictly stronger than the app setting requires.

### Verifying the test can actually fail (negative-case check)

Trust a green run only after you've seen the test go red against a known-
bad state. Pick one of these, run the test, observe failure, then revert:

- **Comment out the realtime hook call.** In
  `frontend/src/pages/canada/portal/CanadaPortalLeadsPage.tsx`, comment out
  `useCanadaLeadsRealtime(rep?.rep_id)`. The WS frame assertion (`leadsWsFrames > 0`)
  should fail with the "realtime channel did not deliver the update" message.
- **Break the write-through key.** In `useCanadaLeadsRealtime`
  (`frontend/src/lib/canada-queries.ts`), change the `setQueryData` target
  to `canadaKeys.leads('__never__')`. The badge text assertion should time
  out (the cache entry the page reads from never updates).
- **Force a refetch path instead of realtime.** Temporarily set
  `refetchOnWindowFocus: true` *and* in the test, after the window flag is
  set, add `await pageB.bringToFront()` immediately after `pageA.click()`.
  The `preWsRestGets === 0` assertion should fail.

Revert before committing. None of these need to be automated — they're
manual sanity steps to validate the test instrument.

It does **not** mock the Supabase realtime channel — that would defeat the
test. The whole point is proving the live path works end-to-end.

## Setup

### 1. Install Playwright

```bash
cd frontend
npm install --save-dev @playwright/test
npx playwright install chromium
```

(`@supabase/supabase-js` is already a runtime dep — the test imports it for
the reset helper.)

### 2. Required env vars

Set these before running. Put them in `frontend/.env.test.local`,
`frontend/.env.local`, or export in your shell — the test reads
`process.env`, so any standard mechanism that surfaces them to the node
process running Playwright works.

| Var | What | Example / source |
|---|---|---|
| `E2E_APP_URL` | Where the running dev server lives | `http://localhost:5173` (default if unset) |
| `E2E_SUPABASE_URL` | Supabase project URL (or reuse `VITE_SUPABASE_URL`) | `https://kbuzufjxwflrutowwnfl.supabase.co` |
| `E2E_SUPABASE_ANON_KEY` | Supabase anon key (or reuse `VITE_SUPABASE_ANON_KEY`) | from Supabase project settings |
| `E2E_REP_EMAIL` | Email of an **approved** Canada sales rep test account | something like `e2e-test-rep@example.com` |
| `E2E_REP_PASSWORD` | Password for that test rep | – |
| `E2E_SEED_LEAD_ID` | UUID of a lead owned by `E2E_REP_EMAIL`'s rep that starts in `proposal_shown` | from `canada_leads` table |

### 3. Required Supabase setup (one-time)

A real backend is needed; the test does not mock realtime. You need:

- A Canada sales rep row in `canada_reps` whose `email = E2E_REP_EMAIL`,
  with `is_active = true` (the protected route blocks pending reps).
- An auth user (`auth.users`) for that email, password set to
  `E2E_REP_PASSWORD`.
- A lead row in `canada_leads`:
  - `rep_id` = the test rep's `rep_id`
  - `stage` = `'proposal_shown'`
  - Note its `id`; that goes in `E2E_SEED_LEAD_ID`.
- RLS policies on `canada_leads` must allow the rep's session to `UPDATE`
  their own leads (already the case in production — just confirming).
- **Realtime must be enabled on `canada_leads`** (Supabase dashboard →
  Database → Replication → `canada_leads` toggle ON). Without this, the WS
  frame assertion will fail with no `postgres_changes` ever arriving.

### 4. Run

```bash
# In one terminal — start the app
cd frontend
npm run dev

# In another terminal — run the test
cd frontend
npm run test:e2e:realtime
```

Or, set `E2E_APP_URL` to a deployed preview URL to run against staging:

```bash
E2E_APP_URL=https://meridian-preview.vercel.app npm run test:e2e:realtime
```

## What I deliberately did **not** do

- **No mock of Supabase realtime.** Mocking the channel would make the test
  pass even if the write-through key were wrong or realtime were
  unsubscribed — the exact bugs we're guarding against.
- **No change to `refetchOnWindowFocus`.** The test asserts around the app
  setting rather than mutating it.
- **No headless seed of the test rep / lead.** Creating the auth user
  requires the Supabase service-role key, which we don't want to read from
  CI. One-time manual setup keeps the secret out of the repo.
- **No parallelism.** The test mutates a shared row. `workers: 1` and
  `fullyParallel: false` in `playwright.config.ts` enforce this.
