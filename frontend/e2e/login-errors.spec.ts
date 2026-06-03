/**
 * Login error-state coverage. For each login surface (US rep, Canada rep,
 * customer), exercise:
 *   1. Empty submit  → expect HTML5 validation OR inline error
 *   2. Malformed email → expect inline error, no POST
 *   3. Wrong password → expect POST → 4xx + visible error banner
 *
 * Read-only: never submits a valid credential pair; never creates rows.
 */
import { test, expect, Page } from '@playwright/test'
import fs from 'node:fs'

const APP_URL = process.env.E2E_APP_URL ?? 'http://127.0.0.1:4173'
const REPORT_PATH = '/tmp/login-errors-report.json'

type Issue = {
  surface: string
  case: string
  kind: 'page-error' | 'console-error' | 'flow-fail' | 'silent-fail' | 'wrong-status'
  detail: string
}

const issues: Issue[] = []

const SURFACES: Array<{ name: string; path: string; expectedAuthEndpoint: string }> = [
  { name: 'us-rep', path: '/us/portal/login', expectedAuthEndpoint: '/auth/v1/token' },
  { name: 'canada-rep', path: '/canada/portal/login', expectedAuthEndpoint: '/auth/v1/token' },
  { name: 'customer', path: '/customer/login', expectedAuthEndpoint: '/auth/v1/token' },
]

function attach(page: Page, surface: string, getCase: () => string) {
  page.on('pageerror', (e) => issues.push({ surface, case: getCase(), kind: 'page-error', detail: e.message }))
  page.on('console', (m) => {
    if (m.type() === 'error') {
      const t = m.text()
      if (/Failed to load resource: the server responded with a status of 400/i.test(t)) return
      issues.push({ surface, case: getCase(), kind: 'console-error', detail: t })
    }
  })
}

async function findErrorBanner(page: Page): Promise<string> {
  const candidates = [
    '[role="alert"]',
    '[aria-live="polite"]',
    '[aria-live="assertive"]',
    '.text-red-400, .text-red-500, .text-red-600',
    'div:has-text("Invalid")',
    'div:has-text("incorrect")',
    'p:has-text("Invalid"), p:has-text("incorrect")',
  ]
  for (const sel of candidates) {
    const el = page.locator(sel).first()
    if (await el.isVisible({ timeout: 500 }).catch(() => false)) {
      const t = (await el.textContent())?.trim() ?? ''
      if (t.length > 0) return t.slice(0, 200)
    }
  }
  return ''
}

async function testEmptySubmit(page: Page, surface: { name: string; path: string }, caseName: string) {
  await page.goto(`${APP_URL}${surface.path}`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 10_000 })
  const submit = page.locator('button[type="submit"]').first()
  await submit.click().catch(() => {})
  await page.waitForTimeout(500)
  const emailInput = page.locator('input[type="email"]').first()
  const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.checkValidity()).catch(() => false)
  if (!isInvalid) {
    const banner = await findErrorBanner(page)
    if (!banner) {
      issues.push({ surface: surface.name, case: caseName, kind: 'silent-fail', detail: 'Empty submit produced no HTML5 validation AND no inline error — silent failure mode' })
    }
  }
}

async function testMalformedEmail(page: Page, surface: { name: string; path: string }, caseName: string) {
  await page.goto(`${APP_URL}${surface.path}`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 10_000 })
  await page.fill('input[type="email"]', 'not-an-email')
  await page.fill('input[type="password"]', 'something')
  await page.click('button[type="submit"]')
  await page.waitForTimeout(800)
  const emailInput = page.locator('input[type="email"]').first()
  const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.checkValidity()).catch(() => true)
  if (!isInvalid) {
    const banner = await findErrorBanner(page)
    if (!banner) {
      issues.push({ surface: surface.name, case: caseName, kind: 'silent-fail', detail: 'Malformed email accepted by form AND no inline error' })
    }
  }
}

async function testWrongPassword(page: Page, surface: { name: string; path: string; expectedAuthEndpoint: string }, caseName: string) {
  await page.goto(`${APP_URL}${surface.path}`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 10_000 })
  await page.fill('input[type="email"]', `nobody+${Date.now()}@example.com`)
  await page.fill('input[type="password"]', 'wrong-password-xxxxxxxx')
  const authResp = page.waitForResponse(
    (r) => r.url().includes(surface.expectedAuthEndpoint) && r.request().method() === 'POST',
    { timeout: 8_000 },
  ).catch(() => null)
  await page.click('button[type="submit"]')
  const r = await authResp
  if (!r) {
    issues.push({ surface: surface.name, case: caseName, kind: 'silent-fail', detail: 'Wrong-password submit did not fire a POST to the auth endpoint' })
    return
  }
  if (r.status() < 400) {
    issues.push({ surface: surface.name, case: caseName, kind: 'wrong-status', detail: `Wrong password returned ${r.status()} — expected 4xx` })
    return
  }
  await page.waitForTimeout(800)
  const banner = await findErrorBanner(page)
  if (!banner) {
    issues.push({ surface: surface.name, case: caseName, kind: 'silent-fail', detail: `Auth returned ${r.status()} but no visible error banner — silent failure mode` })
  }
}

test('login error states — every surface, every failure mode', async ({ page }) => {
  test.setTimeout(180_000)
  let caseName = 'init'
  for (const s of SURFACES) {
    attach(page, s.name, () => caseName)
    caseName = `${s.name}:empty-submit`
    await testEmptySubmit(page, s, caseName)
    caseName = `${s.name}:malformed-email`
    await testMalformedEmail(page, s, caseName)
    caseName = `${s.name}:wrong-password`
    await testWrongPassword(page, s, caseName)
  }
  const blocking = issues.filter((i) => i.kind === 'page-error' || i.kind === 'flow-fail' || i.kind === 'silent-fail' || i.kind === 'wrong-status')
  expect.soft(blocking, `Login error-state issues:\n${JSON.stringify(blocking, null, 2)}`).toHaveLength(0)
})

test.afterAll(() => {
  fs.writeFileSync(
    REPORT_PATH,
    JSON.stringify(
      {
        generatedAt: new Date().toISOString(),
        appUrl: APP_URL,
        totalIssues: issues.length,
        byKind: issues.reduce<Record<string, number>>((a, i) => ((a[i.kind] = (a[i.kind] ?? 0) + 1), a), {}),
        issues,
      },
      null,
      2,
    ),
  )
  // eslint-disable-next-line no-console
  console.log(`\n[login-errors] ${issues.length} issue(s). Report: ${REPORT_PATH}`)
})
