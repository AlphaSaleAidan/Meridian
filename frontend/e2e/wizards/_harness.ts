/**
 * Shared harness for the onboarding-wizard e2e proof suite (e2e/wizards/*).
 *
 * GOAL
 * ----
 * Prove every onboarding wizard works end-to-end WITHOUT real charges or real
 * provisioning, by driving the real UI through every step and intercepting the
 * network (Supabase auth/REST + backend /api/*) so the flow completes against
 * mocked success. For the steps that hit endpoints fixed in #193/#194 we also
 * assert the FIX holds (the request carries the Bearer the backend now demands,
 * checkout+provision share an org_id, etc.) — these double as regression guards.
 *
 * HOW AUTH IS FAKED
 * -----------------
 * The dev server is booted (see playwright.config.ts webServer.env) with FAKE
 * VITE_SUPABASE_URL=https://e2ewizard.supabase.co + a fake anon key, so the
 * real supabase-js client is instantiated (otherwise `supabase` is null and
 * getAuthHeaders() can never attach a Bearer). We then:
 *   1. addInitScript to seed a far-future Supabase session into localStorage
 *      under the supabase-js storage key (sb-e2ewizard-auth-token) BEFORE the
 *      app boots. getAuthHeaders() reads it via getSession() and attaches
 *      `Authorization: Bearer <jwt>`.
 *   2. seed `meridian_org` (customer) / `meridian_sales_rep` (rep) so the auth
 *      contexts hydrate an org/rep synchronously (they call loadOrg()/loadRep()
 *      from localStorage in their initial useState).
 *   3. page.route-mock every `**​/auth/v1/**` and `**​/rest/v1/**` call so no
 *      real Supabase network happens and signup()/getUser()/table reads resolve.
 *   4. page.route-mock `**​/api/**` to capture requests + return per-endpoint
 *      success, so we can assert endpoint + payload + headers.
 */
import { type Page, type Route, type Request, expect } from '@playwright/test'

// supabase-js derives its storage key from the URL subdomain:
//   `sb-${new URL(url).hostname.split('.')[0]}-auth-token`
// Our fake URL is https://e2ewizard.supabase.co → subdomain "e2ewizard".
export const SUPABASE_SUBDOMAIN = 'e2ewizard'
export const SUPABASE_STORAGE_KEY = `sb-${SUPABASE_SUBDOMAIN}-auth-token`

// Fixed test identities (valid-shaped UUIDs).
export const TEST_USER_ID = '11111111-1111-4111-8111-111111111111'
export const TEST_ORG_ID = '22222222-2222-4222-8222-222222222222'
export const TEST_REP_ID = '33333333-3333-4333-8333-333333333333'
export const TEST_EMAIL = 'owner@e2e-test.local'
export const TEST_REP_EMAIL = 'rep@e2e-test.local'

/** A syntactically-valid (unsigned) JWT. The backend is mocked, so it is never
 *  verified — we only assert it travels in the Authorization header. */
export function fakeJwt(claims: Record<string, unknown> = {}): string {
  const b64 = (o: unknown) =>
    Buffer.from(JSON.stringify(o))
      .toString('base64')
      .replace(/=/g, '')
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
  const now = Math.floor(Date.now() / 1000)
  const header = { alg: 'HS256', typ: 'JWT' }
  const payload = {
    sub: TEST_USER_ID,
    email: TEST_EMAIL,
    role: 'authenticated',
    aud: 'authenticated',
    iat: now,
    exp: now + 365 * 24 * 3600,
    ...claims,
  }
  return `${b64(header)}.${b64(payload)}.e2e_fake_signature`
}

export const TEST_ACCESS_TOKEN = fakeJwt()

/** A Supabase Session object shaped exactly as supabase-js persists it. */
export function fakeSession(userMeta: Record<string, unknown> = {}) {
  const now = Math.floor(Date.now() / 1000)
  return {
    access_token: TEST_ACCESS_TOKEN,
    token_type: 'bearer',
    expires_in: 3600,
    // Far future → getSession() returns it without triggering a refresh.
    expires_at: now + 365 * 24 * 3600,
    refresh_token: 'e2e-fake-refresh-token',
    user: fakeUser(userMeta),
  }
}

export function fakeUser(userMeta: Record<string, unknown> = {}) {
  const nowIso = new Date().toISOString()
  return {
    id: TEST_USER_ID,
    aud: 'authenticated',
    role: 'authenticated',
    email: TEST_EMAIL,
    email_confirmed_at: nowIso,
    phone: '',
    confirmed_at: nowIso,
    last_sign_in_at: nowIso,
    app_metadata: { provider: 'email', providers: ['email'] },
    user_metadata: userMeta,
    identities: [],
    created_at: nowIso,
    updated_at: nowIso,
  }
}

export interface OrgSeed {
  org_id?: string
  business_name?: string
  owner_name?: string
  email?: string
  plan?: string
  pos_provider?: string | null
  pos_connected?: boolean
  onboarded?: boolean
}

/** localStorage value the customer AuthProvider hydrates via loadOrg(). */
export function orgSeedValue(seed: OrgSeed = {}) {
  return {
    org_id: seed.org_id ?? TEST_ORG_ID,
    business_name: seed.business_name ?? 'E2E Test Cafe',
    owner_name: seed.owner_name ?? 'Pat Owner',
    email: seed.email ?? TEST_EMAIL,
    plan: seed.plan ?? 'trial',
    pos_provider: seed.pos_provider ?? null,
    pos_connected: seed.pos_connected ?? false,
    created_at: new Date().toISOString(),
    onboarded: seed.onboarded ?? false,
  }
}

export interface RepSeed {
  rep_id?: string
  name?: string
  email?: string
  commission_rate?: number
  portal_context?: 'us' | 'canada' | 'all'
}

/** localStorage value the SalesAuthProvider hydrates via loadRep(). */
export function repSeedValue(seed: RepSeed = {}) {
  return {
    rep_id: seed.rep_id ?? TEST_REP_ID,
    name: seed.name ?? 'Riley Rep',
    email: seed.email ?? TEST_REP_EMAIL,
    phone: '(555) 100-2000',
    // commission_rate is the field exercised by the #194 `?? 70` fix; default 0
    // so specs can prove 0% survives instead of becoming 70%.
    commission_rate: seed.commission_rate ?? 0,
    recruiter: null,
    is_active: true,
    total_earned: 0,
    total_paid: 0,
    created_at: new Date().toISOString(),
    portal_context: seed.portal_context ?? 'all',
  }
}

// ── Demo-gate / tour keys (so the business-type modal + tour spotlight don't
//    intercept clicks on the portal surfaces). ──
const DEMO_GATE = {
  'meridian.demo.businessType': 'restaurant',
  meridian_tour_dismissed: 'true',
  // Dismiss the fixed cookie-consent banner so it never intercepts clicks.
  meridian_cookie_consent: 'essential',
}

/** Seed a customer (owner) session + org + demo gate before the app boots. */
export async function seedCustomerAuth(page: Page, opts: { org?: OrgSeed; userMeta?: Record<string, unknown> } = {}) {
  const storageKey = SUPABASE_STORAGE_KEY
  const session = fakeSession({ role: 'owner', org_id: opts.org?.org_id ?? TEST_ORG_ID, ...(opts.userMeta || {}) })
  const org = orgSeedValue(opts.org)
  await page.addInitScript(
    ([key, sess, orgVal, gate]) => {
      try {
        window.localStorage.setItem(key as string, JSON.stringify(sess))
        window.localStorage.setItem('meridian_org', JSON.stringify(orgVal))
        for (const [k, v] of Object.entries(gate as Record<string, string>)) {
          window.localStorage.setItem(k, v)
        }
      } catch {
        /* private mode */
      }
    },
    [storageKey, session, org, DEMO_GATE] as const,
  )
}

/** Seed a sales-rep session + rep profile + demo gate before the app boots. */
export async function seedRepAuth(page: Page, opts: { rep?: RepSeed; userMeta?: Record<string, unknown> } = {}) {
  const storageKey = SUPABASE_STORAGE_KEY
  // role intentionally NOT "sales_rep": resolveRepProfile() returns null for a
  // non-sales_rep user, so the seeded localStorage rep is kept verbatim
  // (including commission_rate:0) instead of being overwritten via repFromRow
  // (whose `|| 0.7` would itself coerce 0 → 70).
  const session = fakeSession({ ...(opts.userMeta || {}) })
  const rep = repSeedValue(opts.rep)
  await page.addInitScript(
    ([key, sess, repVal, gate]) => {
      try {
        window.localStorage.setItem(key as string, JSON.stringify(sess))
        window.localStorage.setItem('meridian_sales_rep', JSON.stringify(repVal))
        for (const [k, v] of Object.entries(gate as Record<string, string>)) {
          window.localStorage.setItem(k, v)
        }
      } catch {
        /* private mode */
      }
    },
    [storageKey, session, rep, DEMO_GATE] as const,
  )
}

/** Seed only the demo-gate keys (for public, no-auth surfaces). */
export async function seedDemoGate(page: Page) {
  await page.addInitScript((gate) => {
    try {
      for (const [k, v] of Object.entries(gate as Record<string, string>)) {
        window.localStorage.setItem(k, v)
      }
    } catch {
      /* ignore */
    }
  }, DEMO_GATE)
}

/**
 * Mock every Supabase auth + REST call so the page makes no real network calls
 * to the fake host. signUp/getUser/getSession/token + table reads/writes/RPC
 * all resolve to benign success. Auth-context org/rep therefore fall back to the
 * seeded localStorage values.
 */
export async function mockSupabase(page: Page) {
  await page.route('**/auth/v1/**', async (route: Route) => {
    const url = route.request().url()
    const method = route.request().method()
    const json = (body: unknown) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(body) })

    if (url.includes('/signup')) {
      // Return a confirmed user + active session so signup() takes the
      // data.session happy path (no email-confirm gate).
      return json({ ...fakeSession(), user: fakeUser({ role: 'owner' }) })
    }
    if (url.includes('/token')) {
      return json(fakeSession())
    }
    if (url.includes('/user')) {
      return json(fakeUser())
    }
    if (url.includes('/logout')) {
      return route.fulfill({ status: 204, body: '' })
    }
    if (url.includes('/recover') || url.includes('/otp') || url.includes('/magiclink')) {
      return json({})
    }
    if (method === 'OPTIONS') return route.fulfill({ status: 200, body: '' })
    return json({})
  })

  await page.route('**/rest/v1/**', async (route: Route) => {
    const method = route.request().method()
    if (method === 'OPTIONS') return route.fulfill({ status: 200, body: '' })
    // RPCs (create_business_for_user, is_admin, etc.) and table selects/inserts
    // all resolve empty — auth contexts then fall back to seeded localStorage.
    return route.fulfill({ status: 200, contentType: 'application/json', body: 'null' })
  })

  // Supabase Storage uploads (inventory docs, schedules) — accept silently.
  await page.route('**/storage/v1/**', async (route: Route) => {
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ Key: 'e2e/mock' }) })
  })
}

export interface CapturedRequest {
  url: string
  pathname: string
  method: string
  headers: Record<string, string>
  authorization: string | undefined
  postData: string | null
  json: any
}

export interface ApiMock {
  /** Path substring → JSON body (or function returning body). 200 by default. */
  responses?: Record<string, unknown | ((req: Request) => unknown)>
  /** Path substring → explicit status code (default 200). */
  status?: Record<string, number>
}

/**
 * Mock the backend `/api/*` and capture every matched request.
 * Returns a live array of CapturedRequest plus a `find(substr)` helper.
 */
export async function captureApi(page: Page, mock: ApiMock = {}) {
  const captured: CapturedRequest[] = []
  await page.route('**/api/**', async (route: Route) => {
    const req = route.request()
    const url = new URL(req.url())
    const headers = req.headers()
    let body: any = null
    const postData = req.postData()
    try {
      body = postData ? JSON.parse(postData) : null
    } catch {
      body = postData
    }
    captured.push({
      url: req.url(),
      pathname: url.pathname,
      method: req.method(),
      headers,
      authorization: headers['authorization'],
      postData: postData ?? null,
      json: body,
    })

    if (req.method() === 'OPTIONS') {
      return route.fulfill({ status: 200, body: '' })
    }

    // Per-endpoint response selection.
    const path = url.pathname
    let status = 200
    if (mock.status) {
      for (const [k, v] of Object.entries(mock.status)) if (path.includes(k)) status = v
    }
    let payload: unknown = defaultApiResponse(path, url)
    if (mock.responses) {
      for (const [k, v] of Object.entries(mock.responses)) {
        if (path.includes(k)) payload = typeof v === 'function' ? (v as (r: Request) => unknown)(req) : v
      }
    }
    return route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(payload ?? {}),
    })
  })

  return {
    requests: captured,
    /** All requests whose pathname includes `substr`. */
    all(substr: string) {
      return captured.filter((r) => r.pathname.includes(substr))
    },
    /** Last request whose pathname includes `substr` (or undefined). */
    find(substr: string) {
      return [...captured].reverse().find((r) => r.pathname.includes(substr))
    },
  }
}

/** Sensible default success bodies keyed by endpoint so wizards advance. */
function defaultApiResponse(path: string, url: URL): unknown {
  if (path.includes('/api/square/status') || path.includes('/api/clover/status')) {
    return { connected: false, org_id: url.searchParams.get('org_id') }
  }
  if (path.includes('/api/pos/test-connection')) return { success: true, valid: true }
  if (path.includes('/api/pos/connect')) return { success: true, connection_id: 'e2e-conn' }
  if (path.includes('/api/pos/select')) return { success: true }
  if (path.includes('/api/billing/create-invoice')) {
    return { invoice_id: 'inv_e2e', invoice_url: 'https://squareup.com/pay/e2e', status: 'sent' }
  }
  if (path.includes('/api/billing/create-checkout')) {
    return { checkout_url: 'https://checkout.stripe.com/e2e', session_id: 'cs_e2e' }
  }
  if (path.includes('/api/onboarding/provision-customer')) {
    return { success: true, org_id: TEST_ORG_ID, business_id: TEST_ORG_ID }
  }
  if (path.includes('/api/onboarding/mark-onboarded')) return { success: true }
  if (path.includes('/api/us/sign-sla') || path.includes('/api/canada/sign-sla')) {
    return { success: true, signed_at: new Date().toISOString() }
  }
  if (path.includes('/api/vision/cameras')) return { success: true, camera_id: 'cam_e2e' }
  if (path.includes('/api/quote-request')) return { success: true, id: 'quote_e2e' }
  if (path.includes('/api/phone/provision-number')) return { success: true, phone_number: '+15875550123' }
  if (path.includes('/api/phone/config')) return { success: true }
  if (path.includes('/api/credits/balance')) return { balance_cents: 5000, balance: 50 }
  if (path.includes('/api/stripe/connect/status')) return { connected: false, charges_enabled: false }
  if (path.includes('/api/stripe/connect/onboard')) return { url: 'https://connect.stripe.com/e2e' }
  return { success: true }
}

/** Convenience: assert a captured request carried a Bearer JWT. */
export function expectBearer(req: CapturedRequest | undefined, label = 'request') {
  expect(req, `${label} should have been sent`).toBeTruthy()
  expect(req!.authorization, `${label} must carry an Authorization header`).toBeTruthy()
  expect(req!.authorization, `${label} Authorization must be a Bearer token`).toMatch(/^Bearer .+/)
}
