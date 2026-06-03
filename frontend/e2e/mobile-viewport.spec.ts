/**
 * Mobile-viewport pass of the rep portal. Uses iPhone SE dimensions
 * (375x667) to surface CSS bugs that only manifest below the sm: breakpoint
 * (640px in Tailwind).
 *
 * Walks the same routes as ui-smoke but in a mobile context — so we exercise
 * the mobile nav, the hamburger menu, the dialog overlays, etc. Read-only:
 * deliberately skips the add-lead sequence and any mutation.
 *
 * Run:
 *   E2E_APP_URL=http://127.0.0.1:4173 \
 *   E2E_EMAIL=... E2E_PASSWORD=... \
 *   npx playwright test e2e/mobile-viewport.spec.ts --reporter=list
 */
import { test, expect, Page, devices } from '@playwright/test'
import fs from 'node:fs'

const APP_URL = process.env.E2E_APP_URL ?? 'http://127.0.0.1:4173'
const EMAIL = process.env.E2E_EMAIL ?? ''
const PASSWORD = process.env.E2E_PASSWORD ?? ''
const REPORT_PATH = '/tmp/mobile-viewport-report.json'

type Issue = {
  portal: 'us' | 'canada'
  route: string
  kind: 'console-error' | 'page-error' | 'network-4xx' | 'network-5xx' | 'flow-fail' | 'click-throw' | 'overflow'
  detail: string
  url?: string
  status?: number
}

const issues: Issue[] = []
const US_ROUTES = [
  '/us/portal/dashboard', '/us/portal/leads', '/us/portal/accounts',
  '/us/portal/commissions', '/us/portal/training', '/us/portal/team',
  '/us/portal/settings', '/us/portal/badge',
]
const CA_ROUTES = [
  '/canada/portal/dashboard', '/canada/portal/leads', '/canada/portal/accounts',
  '/canada/portal/commissions', '/canada/portal/training', '/canada/portal/proposals',
  '/canada/portal/team', '/canada/portal/settings', '/canada/portal/badge',
]

const SKIP = [
  /sign\s*out/i, /log\s*out/i, /^delete/i, /^remove/i, /destroy/i,
  /advance/i, /next stage/i, /mark.*lost/i,
  /save.*connect/i, /create.*customer/i, /create.*account/i,
]
const shouldSkip = (t: string) => SKIP.some((p) => p.test(t || ''))

function attach(page: Page, portal: 'us' | 'canada', getRoute: () => string) {
  page.on('console', (m) => {
    if (m.type() === 'error') issues.push({ portal, route: getRoute(), kind: 'console-error', detail: m.text() })
  })
  page.on('pageerror', (e) => issues.push({ portal, route: getRoute(), kind: 'page-error', detail: e.message }))
  page.on('response', (r) => {
    const s = r.status()
    if (s >= 400 && s < 500) issues.push({ portal, route: getRoute(), kind: 'network-4xx', detail: `${s} ${r.url()}`, url: r.url(), status: s })
    else if (s >= 500) issues.push({ portal, route: getRoute(), kind: 'network-5xx', detail: `${s} ${r.url()}`, url: r.url(), status: s })
  })
}

async function login(page: Page, portal: 'us' | 'canada') {
  await page.goto(`${APP_URL}/${portal}/portal/login`, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 15_000 })
  await page.fill('input[type="email"]', EMAIL)
  await page.fill('input[type="password"]', PASSWORD)
  await Promise.all([
    page.waitForURL(new RegExp(`/${portal}/portal/(dashboard|onboarding)`), { timeout: 20_000 }),
    page.click('button[type="submit"]'),
  ])
}

async function checkHorizontalOverflow(page: Page, portal: 'us' | 'canada', route: string) {
  // CSS that overflows the viewport horizontally is a classic mobile bug.
  // Compare document scrollWidth to clientWidth.
  const overflow = await page.evaluate(() => ({
    sw: document.documentElement.scrollWidth,
    cw: document.documentElement.clientWidth,
  }))
  if (overflow.sw > overflow.cw + 2) {
    issues.push({
      portal, route, kind: 'overflow',
      detail: `Page scrollWidth ${overflow.sw}px > viewport ${overflow.cw}px — horizontal overflow at mobile breakpoint`,
    })
  }
}

async function crawl(page: Page, portal: 'us' | 'canada', route: string) {
  await page.goto(`${APP_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 20_000 }).catch((e) => {
    issues.push({ portal, route, kind: 'flow-fail', detail: `goto: ${e.message ?? e}` })
  })
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})
  await checkHorizontalOverflow(page, portal, route)

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
        issues.push({ portal, route, kind: 'click-throw', detail: msg })
      }
    }
  }
}

test.use({ ...devices['iPhone SE'] })

test.describe.serial('mobile viewport', () => {
  test.skip(!EMAIL || !PASSWORD, 'E2E_EMAIL/E2E_PASSWORD required')
  for (const portal of ['us', 'canada'] as const) {
    test(`${portal} portal — iPhone SE`, async ({ page }) => {
      test.setTimeout(240_000)
      let currentRoute = '/login'
      attach(page, portal, () => currentRoute)
      await login(page, portal)
      const routes = portal === 'us' ? US_ROUTES : CA_ROUTES
      for (const r of routes) {
        currentRoute = r
        await crawl(page, portal, r)
      }
      const blocking = issues.filter((i) => i.portal === portal && (i.kind === 'page-error' || i.kind === 'network-5xx' || i.kind === 'flow-fail'))
      expect.soft(blocking, `Blocking mobile issues for ${portal}: ${JSON.stringify(blocking, null, 2)}`).toHaveLength(0)
    })
  }
  test.afterAll(() => {
    fs.writeFileSync(
      REPORT_PATH,
      JSON.stringify(
        {
          generatedAt: new Date().toISOString(),
          appUrl: APP_URL,
          viewport: '375x667 (iPhone SE)',
          totalIssues: issues.length,
          byKind: issues.reduce<Record<string, number>>((a, i) => ((a[i.kind] = (a[i.kind] ?? 0) + 1), a), {}),
          issues,
        },
        null,
        2,
      ),
    )
    // eslint-disable-next-line no-console
    console.log(`\n[mobile] ${issues.length} issue(s). Report: ${REPORT_PATH}`)
  })
})
