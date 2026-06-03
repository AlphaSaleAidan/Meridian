/**
 * Admin routes coverage: logs in as an admin email and crawls
 * /customer/admin, /admin/it-health, /admin/pos-coverage, /admin/email.
 * Each is a protected surface not exercised by the rep-portal smoke tests.
 *
 * Captures console errors + network 4xx/5xx + page exceptions on every route.
 */
import { test, expect, Page } from '@playwright/test'
import fs from 'node:fs'

const APP_URL = process.env.E2E_APP_URL ?? 'http://127.0.0.1:4173'
const EMAIL = process.env.E2E_EMAIL ?? ''
const PASSWORD = process.env.E2E_PASSWORD ?? ''
const REPORT_PATH = '/tmp/admin-routes-report.json'

type Issue = {
  route: string
  kind: 'console-error' | 'page-error' | 'network-4xx' | 'network-5xx' | 'flow-fail' | 'click-throw' | 'route-blocked'
  detail: string
  url?: string
  status?: number
  selector?: string
}

const issues: Issue[] = []
const ROUTES = ['/customer/admin', '/admin/it-health', '/admin/pos-coverage', '/admin/email']

const SKIP_PATTERNS = [
  /sign\s*out/i, /log\s*out/i,
  /^delete/i, /^remove/i, /destroy/i,
  /reject/i, /approve/i,
  /disable/i, /deactivate/i,
  /reset.*password/i, /^email\b/i,
]
const shouldSkip = (t: string) => SKIP_PATTERNS.some((p) => p.test(t || ''))

function attach(page: Page, getRoute: () => string) {
  page.on('console', (m) => {
    if (m.type() === 'error') issues.push({ route: getRoute(), kind: 'console-error', detail: m.text() })
  })
  page.on('pageerror', (e) => issues.push({ route: getRoute(), kind: 'page-error', detail: e.message }))
  page.on('response', (r) => {
    const s = r.status()
    if (s >= 400 && s < 500) issues.push({ route: getRoute(), kind: 'network-4xx', detail: `${s} ${r.url()}`, url: r.url(), status: s })
    else if (s >= 500) issues.push({ route: getRoute(), kind: 'network-5xx', detail: `${s} ${r.url()}`, url: r.url(), status: s })
  })
}

async function loginAsAdmin(page: Page) {
  await page.goto(`${APP_URL}/customer/login`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 15_000 })
  await page.fill('input[type="email"]', EMAIL)
  await page.fill('input[type="password"]', PASSWORD)
  await page.click('button[type="submit"]')
  await page.waitForTimeout(2000)
}

async function crawl(page: Page, route: string) {
  await page.goto(`${APP_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 20_000 }).catch((e) => {
    issues.push({ route, kind: 'flow-fail', detail: `goto failed: ${e.message ?? e}` })
  })
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})

  if (/\/login/.test(page.url())) {
    issues.push({ route, kind: 'route-blocked', detail: `redirected to ${page.url()} — admin access denied or session expired` })
    return
  }

  const candidates = await page.$$eval('button, [role="button"]', (els) =>
    els.map((el, idx) => ({
      idx,
      text: (el as HTMLElement).innerText?.trim().slice(0, 80) ?? '',
      ariaLabel: el.getAttribute('aria-label') ?? '',
      disabled: (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true',
      visible: (el as HTMLElement).offsetParent !== null,
    })),
  )

  for (const c of candidates) {
    if (c.disabled || !c.visible) continue
    const label = c.text || c.ariaLabel
    if (shouldSkip(label)) continue
    try {
      const handles = await page.$$('button, [role="button"]')
      const h = handles[c.idx]
      if (!h || !(await h.isVisible().catch(() => false))) continue
      await h.click({ timeout: 2000 })
      await page.waitForTimeout(100)
      await page.keyboard.press('Escape').catch(() => {})
      await page.waitForTimeout(50)
      if (!page.url().includes(route)) {
        await page.goto(`${APP_URL}${route}`, { waitUntil: 'domcontentloaded' }).catch(() => {})
        await page.waitForLoadState('networkidle', { timeout: 3_000 }).catch(() => {})
      }
    } catch (e: any) {
      const msg = e?.message ?? String(e)
      if (!/not visible|detached|hidden|intercepts pointer/i.test(msg)) {
        issues.push({ route, kind: 'click-throw', detail: msg, selector: `button[${c.idx}] "${label}"` })
      }
    }
  }
}

test('admin routes: login as admin + crawl every protected admin surface', async ({ page }) => {
  test.skip(!EMAIL || !PASSWORD, 'E2E_EMAIL/E2E_PASSWORD required')
  test.setTimeout(240_000)
  let currentRoute = '/login'
  attach(page, () => currentRoute)
  await loginAsAdmin(page)
  for (const r of ROUTES) {
    currentRoute = r
    await crawl(page, r)
  }
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
        byKind: issues.reduce<Record<string, number>>((a, i) => ((a[i.kind] = (a[i.kind] ?? 0) + 1), a), {}),
        issues,
      },
      null,
      2,
    ),
  )
  // eslint-disable-next-line no-console
  console.log(`\n[admin-routes] ${issues.length} issue(s). Report: ${REPORT_PATH}`)
})
