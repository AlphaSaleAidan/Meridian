/**
 * Customer-side portal smoke: walks the public /customer/login and
 * /customer/signup pages, clicks every non-destructive button, and verifies
 * forms render fillable inputs. No auth required — these are the surfaces
 * real merchants hit after the sales rep creates their account.
 *
 * Skips a real signup submit by default (would create a real Supabase user
 * in prod). Set E2E_CUSTOMER_SUBMIT=1 to also fire the signup POST.
 *
 * Run:
 *   E2E_APP_URL=http://127.0.0.1:4173 npx playwright test e2e/customer-portal.spec.ts
 */
import { test, expect, Page } from '@playwright/test'
import fs from 'node:fs'

const APP_URL = process.env.E2E_APP_URL ?? 'http://localhost:3000'
const SHOULD_SUBMIT = process.env.E2E_CUSTOMER_SUBMIT === '1'
const REPORT_PATH = '/tmp/customer-portal-report.json'

type Issue = {
  route: string
  kind: 'console-error' | 'page-error' | 'network-4xx' | 'network-5xx' | 'flow-fail' | 'click-throw'
  detail: string
  url?: string
  status?: number
  selector?: string
}

const issues: Issue[] = []

const ROUTES = [
  '/customer/login',
  '/customer/signup',
]

const SKIP_PATTERNS = [/sign\s*out/i, /log\s*out/i, /^delete/i, /^remove/i]
const shouldSkip = (t: string) => SKIP_PATTERNS.some((p) => p.test(t || ''))

async function attachListeners(page: Page, getRoute: () => string) {
  page.on('console', (msg) => {
    if (msg.type() === 'error') issues.push({ route: getRoute(), kind: 'console-error', detail: msg.text() })
  })
  page.on('pageerror', (err) => issues.push({ route: getRoute(), kind: 'page-error', detail: err.message }))
  page.on('response', (r) => {
    const s = r.status()
    if (s >= 400 && s < 500) issues.push({ route: getRoute(), kind: 'network-4xx', detail: `${s} ${r.url()}`, url: r.url(), status: s })
    else if (s >= 500) issues.push({ route: getRoute(), kind: 'network-5xx', detail: `${s} ${r.url()}`, url: r.url(), status: s })
  })
}

async function crawl(page: Page, route: string) {
  await page.goto(`${APP_URL}${route}`, { waitUntil: 'domcontentloaded', timeout: 20_000 }).catch((e) => {
    issues.push({ route, kind: 'flow-fail', detail: `goto failed: ${e.message ?? e}` })
  })
  await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})

  // Verify there's at least one fillable input — these are forms, so an empty
  // page would be a real bug.
  const inputCount = await page.locator('input:not([type="hidden"])').count()
  if (inputCount === 0) {
    issues.push({ route, kind: 'flow-fail', detail: 'No fillable inputs found on a customer auth page — likely a render bug' })
  }

  const candidates = await page.$$eval('button, [role="button"]', (els) =>
    els.map((el, idx) => ({
      idx,
      text: (el as HTMLElement).innerText?.trim().slice(0, 80) ?? '',
      ariaLabel: el.getAttribute('aria-label') ?? '',
      disabled: (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true',
      visible: (el as HTMLElement).offsetParent !== null,
      isSubmit: (el as HTMLButtonElement).type === 'submit',
    })),
  )

  for (const c of candidates) {
    if (c.disabled || !c.visible) continue
    const label = c.text || c.ariaLabel
    if (shouldSkip(label)) continue
    // Don't click a submit button by default — it would attempt signup/login
    // with empty fields and noisy-fail validation. Caller can opt in via env.
    if (c.isSubmit && !SHOULD_SUBMIT) continue
    try {
      const handles = await page.$$('button, [role="button"]')
      const h = handles[c.idx]
      if (!h) continue
      if (!(await h.isVisible().catch(() => false))) continue
      await h.click({ timeout: 2000 })
      await page.waitForTimeout(100)
      await page.keyboard.press('Escape').catch(() => {})
      await page.waitForTimeout(50)
      // Bounce back if we navigated off the route
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

test('customer portal: walk login + signup', async ({ page }) => {
  test.setTimeout(180_000)
  let currentRoute = ROUTES[0]
  await attachListeners(page, () => currentRoute)
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
        submittedForms: SHOULD_SUBMIT,
        totalIssues: issues.length,
        byKind: issues.reduce<Record<string, number>>((a, i) => ((a[i.kind] = (a[i.kind] ?? 0) + 1), a), {}),
        issues,
      },
      null,
      2,
    ),
  )
  // eslint-disable-next-line no-console
  console.log(`\n[customer-portal] ${issues.length} issue(s). Report: ${REPORT_PATH}`)
})
