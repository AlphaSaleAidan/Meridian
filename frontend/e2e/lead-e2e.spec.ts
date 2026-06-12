/**
 * End-to-end: create a lead, walk it through stage progression, click into the
 * lead detail, and verify the "Save & Connect POS" button is operational
 * (POST to /api/onboarding/connect-pos fires).
 *
 * Captures every console error, page exception, and network 4xx/5xx for the
 * entire run — no filtering. Writes a structured report and screenshots at
 * each milestone so we can see what was on screen when a step failed.
 *
 * Run:
 *   E2E_APP_URL=http://127.0.0.1:4173 \
 *   E2E_EMAIL=... E2E_PASSWORD=... \
 *   npx playwright test e2e/lead-e2e.spec.ts --reporter=list
 */
import { test, expect, Page } from '@playwright/test'
import fs from 'node:fs'
import path from 'node:path'

const APP_URL = process.env.E2E_APP_URL ?? 'http://127.0.0.1:4173'
const EMAIL = process.env.E2E_EMAIL ?? ''
const PASSWORD = process.env.E2E_PASSWORD ?? ''
const SHOTS_DIR = '/tmp/lead-e2e-shots'
const REPORT_PATH = '/tmp/lead-e2e-report.json'

type Issue = {
  step: string
  kind: 'console-error' | 'page-error' | 'network-4xx' | 'network-5xx' | 'assertion-fail' | 'flow-fail'
  detail: string
  url?: string
  status?: number
}

const issues: Issue[] = []
let currentStep = 'setup'

if (!fs.existsSync(SHOTS_DIR)) fs.mkdirSync(SHOTS_DIR, { recursive: true })

function attachListeners(page: Page) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      issues.push({ step: currentStep, kind: 'console-error', detail: msg.text() })
    }
  })
  page.on('pageerror', (err) => {
    issues.push({ step: currentStep, kind: 'page-error', detail: err.message })
  })
  page.on('response', (res) => {
    const s = res.status()
    if (s >= 400 && s < 500) {
      issues.push({ step: currentStep, kind: 'network-4xx', detail: `${s} ${res.url()}`, url: res.url(), status: s })
    } else if (s >= 500) {
      issues.push({ step: currentStep, kind: 'network-5xx', detail: `${s} ${res.url()}`, url: res.url(), status: s })
    }
  })
}

async function shot(page: Page, name: string) {
  const p = path.join(SHOTS_DIR, `${name}.png`)
  await page.screenshot({ path: p, fullPage: true }).catch(() => {})
}

async function login(page: Page) {
  currentStep = 'login'
  await page.goto(`${APP_URL}/us/portal/login`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 15_000 })
  await page.fill('input[type="email"]', EMAIL)
  await page.fill('input[type="password"]', PASSWORD)
  await Promise.all([
    page.waitForURL(/\/us\/portal\/(dashboard|onboarding)/, { timeout: 20_000 }),
    page.click('button[type="submit"]'),
  ])
  await shot(page, '01-after-login')
}

async function createLead(page: Page): Promise<{ businessName: string }> {
  currentStep = 'create-lead'
  await page.goto(`${APP_URL}/us/portal/leads?new=true&t=${Date.now()}`, { waitUntil: 'domcontentloaded' })
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})

  let modal = page.locator('form:has(input[placeholder*="Business Name" i])').first()
  if (!(await modal.isVisible({ timeout: 4000 }).catch(() => false))) {
    await page.locator('button:has-text("New Lead")').first().click()
    await page.waitForTimeout(400)
    modal = page.locator('form:has(input[placeholder*="Business Name" i])').first()
  }
  if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) {
    issues.push({ step: currentStep, kind: 'flow-fail', detail: 'New Lead modal never opened' })
    throw new Error('modal-not-open')
  }
  await shot(page, '02-new-lead-modal')

  const ts = Date.now().toString().slice(-6)
  const businessName = `E2E Smoke ${ts}`
  const textFields: Array<[string, string]> = [
    ['Business Name', businessName],
    ['Contact Name', `Tester ${ts}`],
    ['Contact Email', `e2e+${ts}@example.com`],
    ['Phone', '5551234567'],
    ['City', 'Testville'],
  ]
  for (const [placeholder, val] of textFields) {
    const input = modal.locator(`input[placeholder*="${placeholder}" i]`).first()
    if (await input.isVisible({ timeout: 1000 }).catch(() => false)) await input.fill(val)
  }
  const selectCount = await modal.locator('select').count()
  for (let i = 0; i < selectCount; i++) {
    const sel = modal.locator('select').nth(i)
    const vals = await sel.locator('option').evaluateAll((opts) => opts.map((o) => (o as HTMLOptionElement).value).filter((v) => v !== ''))
    if (vals.length > 0) await sel.selectOption(vals[0]).catch(() => {})
  }

  const insertResp = page.waitForResponse(
    (r) => r.url().includes('/rest/v1/us_leads') && r.request().method() === 'POST',
    { timeout: 10_000 },
  )
  await modal.locator('button[type="submit"]').first().click()
  const resp = await insertResp.catch(() => null)
  if (!resp || resp.status() >= 400) {
    const detail = resp ? `INSERT us_leads → HTTP ${resp.status()}` : 'No POST to us_leads observed after submit'
    issues.push({ step: currentStep, kind: 'flow-fail', detail })
    throw new Error(detail)
  }
  await page.waitForTimeout(500)
  await shot(page, '03-after-create')
  return { businessName }
}

async function openLeadDetail(page: Page, businessName: string) {
  currentStep = 'open-detail'
  // Navigate to leads list, find the card for our business, click it.
  await page.goto(`${APP_URL}/us/portal/leads`, { waitUntil: 'domcontentloaded' })
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})

  // The lead card is a Link with the business name inside. Wait then click.
  const card = page.locator(`a[href*="/us/portal/leads/"]:has-text("${businessName}")`).first()
  await card.waitFor({ state: 'visible', timeout: 8_000 })
  await Promise.all([
    page.waitForURL(/\/us\/portal\/leads\/[0-9a-f-]{36}/, { timeout: 10_000 }),
    card.click(),
  ])
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})
  await shot(page, '04-detail-step1')
}

async function crawlDetailButtons(page: Page) {
  currentStep = 'detail-button-crawl'
  // Click every visible, non-destructive, non-stage-mutating button on the
  // lead detail page to surface JS errors / 4xx hidden under deep clicks
  // (file upload triggers, modal opens, link previews, copy actions, etc.).
  // We deliberately SKIP buttons that mutate the lead state because the
  // dedicated stage-advance + POS + create-customer steps below exercise
  // those individually.
  const SKIP_TEXT = [
    /advance/i, /next stage/i,           // stage mutation — tested separately
    /mark.*lost/i, /closed lost/i,        // destructive stage change
    /save.*connect/i, /connect.*pos/i,    // POS connect — tested separately
    /create.*account/i, /create.*customer/i, // create-customer — tested separately
    /sign\s*out/i, /log\s*out/i,          // would log us out
    /delete/i, /remove/i,                  // destructive
    /upload/i,                              // opens OS file picker, hangs Playwright
  ]
  const shouldClick = (t: string) => t && !SKIP_TEXT.some((p) => p.test(t))

  const candidates = await page.$$eval('button, [role="button"]', (els) =>
    els.map((el, idx) => ({
      idx,
      text: (el as HTMLElement).innerText?.trim().slice(0, 80) ?? '',
      ariaLabel: el.getAttribute('aria-label') ?? '',
      disabled: (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true',
      visible: (el as HTMLElement).offsetParent !== null,
    })),
  )

  let clicked = 0
  for (const c of candidates) {
    if (c.disabled || !c.visible) continue
    const label = c.text || c.ariaLabel
    if (!shouldClick(label)) continue
    try {
      const handles = await page.$$('button, [role="button"]')
      const h = handles[c.idx]
      if (!h || !(await h.isVisible().catch(() => false))) continue
      await h.click({ timeout: 2000 })
      clicked++
      await page.waitForTimeout(120)
      // Close any modal/dialog so the next click isn't blocked
      await page.keyboard.press('Escape').catch(() => {})
      await page.waitForTimeout(60)
      // If we navigated off the detail page, snap back
      if (!/\/us\/portal\/leads\/[0-9a-f-]{36}/.test(page.url())) {
        await page.goBack({ waitUntil: 'domcontentloaded' }).catch(() => {})
        await page.waitForLoadState('networkidle', { timeout: 3_000 }).catch(() => {})
      }
    } catch (e: any) {
      const msg = e?.message ?? String(e)
      if (!/not visible|detached|hidden|intercepts pointer/i.test(msg)) {
        issues.push({ step: currentStep, kind: 'flow-fail', detail: `click "${label}": ${msg}` })
      }
    }
  }
  fs.writeFileSync(`${SHOTS_DIR}/detail-crawl-stats.txt`, `Clicked ${clicked} button(s) on lead detail page.\n`)
  await shot(page, '04b-after-detail-crawl')
}

async function advanceStageTwice(page: Page) {
  currentStep = 'advance-stage-1'
  // The "Advance to Next Stage" button appears in the "Advance Deal" card
  // when currentStep < 3. We need to click it twice (1 → 2 → 3).
  for (let i = 1; i <= 2; i++) {
    currentStep = `advance-stage-${i}`
    const btn = page.locator('button:has-text("Advance to Next Stage")').first()
    if (!(await btn.isVisible({ timeout: 5000 }).catch(() => false))) {
      issues.push({ step: currentStep, kind: 'flow-fail', detail: `"Advance to Next Stage" button not visible on iteration ${i}` })
      throw new Error('advance-button-missing')
    }
    const stageUpdateResp = page.waitForResponse(
      (r) => r.url().includes('/rest/v1/us_leads') && (r.request().method() === 'PATCH' || r.request().method() === 'POST'),
      { timeout: 8_000 },
    )
    await btn.click()
    const r = await stageUpdateResp.catch(() => null)
    if (!r) {
      issues.push({ step: currentStep, kind: 'flow-fail', detail: 'No PATCH to us_leads observed after stage-advance click' })
    } else if (r.status() >= 400) {
      issues.push({ step: currentStep, kind: 'flow-fail', detail: `Stage advance returned HTTP ${r.status()}`, url: r.url(), status: r.status() })
    }
    await page.waitForTimeout(600)
    await shot(page, `05-after-advance-${i}`)
  }
}

async function testConnectPos(page: Page) {
  currentStep = 'connect-pos'
  // POS Connect section becomes visible at currentStep >= 3 (customer_walkthrough).
  const posSection = page.locator('h2:has-text("Connect POS System")').first()
  if (!(await posSection.isVisible({ timeout: 6000 }).catch(() => false))) {
    issues.push({ step: currentStep, kind: 'flow-fail', detail: '"Connect POS System" section did not appear after advancing to walkthrough' })
    throw new Error('pos-section-missing')
  }
  await shot(page, '06-pos-section-visible')

  // Scope to the POS section card (h2's parent div). The POSSystemPicker is
  // a sibling of the h2, inside the same card div.
  const posCard = posSection.locator('xpath=..').first()

  // Step 1: open the POSSystemPicker dropdown by clicking the trigger that
  // shows "Search POS systems..." (placeholder when nothing is selected).
  const trigger = posCard.locator('button:has-text("Search POS systems")').first()
  if (!(await trigger.isVisible({ timeout: 3000 }).catch(() => false))) {
    issues.push({ step: currentStep, kind: 'flow-fail', detail: 'POS picker trigger button not visible' })
    throw new Error('picker-trigger-missing')
  }
  await trigger.click()
  await page.waitForTimeout(300)
  await shot(page, '06b-picker-open')

  // Step 2: pick Square — first integrated POS in the supported list, has
  // merchantRequirements wired so the credential form renders cleanly.
  const squareOption = page.locator('button:has-text("Square")').filter({ hasText: 'Supported' }).first()
  if (!(await squareOption.isVisible({ timeout: 3000 }).catch(() => false))) {
    issues.push({ step: currentStep, kind: 'flow-fail', detail: 'Square option not visible in POS picker dropdown' })
    throw new Error('no-pos-option')
  }
  const chosenName = 'Square'
  await squareOption.click()
  await page.waitForTimeout(400)
  await shot(page, '06c-pos-selected')

  // Step 3: credential inputs now render below the picker trigger. Fill by
  // placeholder match (more specific than positional), with an explicit blur
  // after each fill so React's controlled-input onChange commits before the
  // next interaction. The placeholders are still Square's canonical prefixes
  // (sq0atp- for Access Token, sq0idp- for App ID) — the locator matches on
  // placeholder substring, not on the value. The filled VALUES are obviously
  // fake fixtures (no real-credential prefix), since validateCredentials in
  // src/lib/pos-credentials.ts only checks non-empty — not the format.
  // Avoid the sq0atp- prefix in fixtures so secret-scanners (GitGuardian)
  // don't false-positive on the test fill.
  const accessToken = posCard.locator('input[placeholder*="sq0atp" i]').first()
  const appId = posCard.locator('input[placeholder*="sq0idp" i]').first()
  if (await accessToken.isVisible({ timeout: 2000 }).catch(() => false)) {
    await accessToken.fill('dummy-square-token-for-e2e-XXXXXXXXXX')
    await accessToken.blur()
    await page.waitForTimeout(150)
  }
  if (await appId.isVisible({ timeout: 2000 }).catch(() => false)) {
    await appId.fill('dummy-square-app-id-for-e2e-XXXXXXXXXX')
    await appId.blur()
    await page.waitForTimeout(150)
  }
  await shot(page, '07-pos-credentials-filled')

  // Step 4: click "Save & Connect <name>". Button text starts with "Save &
  // Connect" when onCredentialSubmit is wired (which it is in this flow).
  const connectBtn = posCard.locator('button:has-text("Save & Connect")').first()
  if (!(await connectBtn.isVisible({ timeout: 5000 }).catch(() => false))) {
    issues.push({
      step: currentStep,
      kind: 'flow-fail',
      detail: `POS "Save & Connect" button not found after selecting "${chosenName}"`,
    })
    throw new Error('pos-button-missing')
  }
  const btnText = (await connectBtn.textContent())?.trim() ?? '(no text)'

  // Watch for POST to the backend connect-pos endpoint
  const posPost = page.waitForResponse(
    (r) => r.url().includes('/api/onboarding/connect-pos') && r.request().method() === 'POST',
    { timeout: 10_000 },
  ).catch(() => null)
  await connectBtn.click()
  const resp = await posPost
  await shot(page, '08-after-pos-click')

  if (!resp) {
    issues.push({
      step: currentStep,
      kind: 'flow-fail',
      detail: `POS Connect button "${btnText}" clicked but no POST to /api/onboarding/connect-pos observed within 10s — button may be non-operational`,
    })
    return
  }
  // 4xx from the backend is OK for the button-operational test — it means the
  // button fires the request, even if the dummy creds were rejected. Only a
  // missing request or a 5xx is a real failure here.
  if (resp.status() >= 500) {
    let body = ''
    try { body = await resp.text() } catch {}
    issues.push({
      step: currentStep,
      kind: 'flow-fail',
      detail: `/api/onboarding/connect-pos returned ${resp.status()}: ${body.slice(0, 300)}`,
      status: resp.status(),
      url: resp.url(),
    })
  } else {
    // Button is operational. Record the response status for the report.
    fs.writeFileSync(
      path.join(SHOTS_DIR, 'pos-button-result.txt'),
      `Button text: ${btnText}\nHTTP status: ${resp.status()}\nURL: ${resp.url()}\n`,
    )
  }
}

async function testCreateCustomerAccount(page: Page) {
  currentStep = 'create-customer-account'
  // "Create Customer Account Login" card is visible at currentStep >= 3 with
  // a primary CTA button that calls POST /api/us/create-customer and then
  // triggers Supabase resetPasswordForEmail (so customer sets own password).
  const createBtn = page
    .locator('button:has-text("Create Customer Account Login"), button:has-text("Create Account")')
    .first()
  if (!(await createBtn.isVisible({ timeout: 6000 }).catch(() => false))) {
    issues.push({ step: currentStep, kind: 'flow-fail', detail: '"Create Customer Account Login" button not visible at step 3' })
    return
  }
  // Scroll button into view in case the page is long
  await createBtn.scrollIntoViewIfNeeded().catch(() => {})
  await shot(page, '09-before-create-customer')

  const createPost = page.waitForResponse(
    (r) => r.url().includes('/api/us/create-customer') && r.request().method() === 'POST',
    { timeout: 15_000 },
  ).catch(() => null)
  // Supabase recovery email call is a side-effect after success
  const recoverPost = page.waitForResponse(
    (r) => /\/auth\/v1\/recover/.test(r.url()) && r.request().method() === 'POST',
    { timeout: 15_000 },
  ).catch(() => null)

  await createBtn.click()
  const create = await createPost
  await shot(page, '10-after-create-customer-click')

  if (!create) {
    issues.push({
      step: currentStep,
      kind: 'flow-fail',
      detail: 'No POST to /api/us/create-customer observed within 15s after button click — button may be non-operational',
    })
    return
  }
  const status = create.status()
  let body = ''
  try { body = await create.text() } catch {}

  fs.writeFileSync(
    path.join(SHOTS_DIR, 'create-customer-result.txt'),
    `Button: Create Customer Account Login\n/api/us/create-customer status: ${status}\nBody: ${body.slice(0, 500)}\n`,
  )

  if (status >= 500) {
    issues.push({
      step: currentStep,
      kind: 'flow-fail',
      detail: `/api/us/create-customer returned ${status}: ${body.slice(0, 300)}`,
      status,
      url: create.url(),
    })
    return
  }
  if (status >= 400) {
    // 4xx may be a legitimate validation rejection (e.g., duplicate email
    // when re-running with the same throwaway). Surface it but don't mark
    // blocking — button is operational either way.
    issues.push({
      step: currentStep,
      kind: 'network-4xx',
      detail: `/api/us/create-customer returned ${status}: ${body.slice(0, 300)}`,
      status,
      url: create.url(),
    })
    return
  }

  // Success path: also expect Supabase recovery email POST
  const recover = await recoverPost
  fs.appendFileSync(
    path.join(SHOTS_DIR, 'create-customer-result.txt'),
    `Supabase /auth/v1/recover: ${recover ? recover.status() : '(no request)'}\n`,
  )
  if (!recover) {
    issues.push({
      step: currentStep,
      kind: 'flow-fail',
      detail: 'create-customer succeeded but no follow-up POST to /auth/v1/recover (password-setup email)',
    })
  }
  await page.waitForTimeout(800)
  await shot(page, '11-after-create-customer-success')
}

test('US portal: create lead → walkthrough → POS connect + create customer account', async ({ page }) => {
  test.skip(!EMAIL || !PASSWORD, 'E2E_EMAIL/E2E_PASSWORD required')
  test.setTimeout(300_000)
  attachListeners(page)

  await login(page)
  const { businessName } = await createLead(page)
  await openLeadDetail(page, businessName)
  await crawlDetailButtons(page)
  await advanceStageTwice(page)
  await testConnectPos(page)
  await testCreateCustomerAccount(page)

  // Soft-assert no blocking issues. Page errors and 5xx are blocking.
  const blocking = issues.filter((i) => i.kind === 'page-error' || i.kind === 'network-5xx' || i.kind === 'flow-fail')
  expect.soft(blocking, `Blocking issues:\n${JSON.stringify(blocking, null, 2)}`).toHaveLength(0)
})

test.afterAll(() => {
  fs.writeFileSync(
    REPORT_PATH,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        appUrl: APP_URL,
        totalIssues: issues.length,
        byKind: issues.reduce<Record<string, number>>((acc, i) => {
          acc[i.kind] = (acc[i.kind] ?? 0) + 1
          return acc
        }, {}),
        issues,
      },
      null,
      2,
    ),
  )
  // eslint-disable-next-line no-console
  console.log(`\n[lead-e2e] ${issues.length} issue(s). Report: ${REPORT_PATH}. Shots: ${SHOTS_DIR}`)
})
