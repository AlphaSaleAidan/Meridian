/**
 * UI smoke scraper: walks every portal route, clicks every non-destructive
 * interactive element, captures console errors + network 4xx/5xx + JS
 * exceptions, and exercises the add-lead sequence on both portals.
 *
 * Run:
 *   E2E_APP_URL=http://127.0.0.1:4173 \
 *   E2E_EMAIL=... E2E_PASSWORD=... \
 *   E2E_PORTAL=both \
 *   npx playwright test e2e/ui-smoke.spec.ts
 *
 * E2E_PORTAL: 'us' | 'canada' | 'both' (default: 'both')
 */
import { test, expect, Page, ConsoleMessage } from '@playwright/test'
import fs from 'node:fs'

type Issue = {
  portal: 'us' | 'canada'
  route: string
  kind: 'console-error' | 'page-error' | 'network-4xx' | 'network-5xx' | 'click-throw' | 'route-load-fail' | 'sequence-fail'
  detail: string
  selector?: string
  url?: string
  status?: number
}

const APP_URL = process.env.E2E_APP_URL ?? 'http://localhost:3000'
const EMAIL = process.env.E2E_EMAIL ?? ''
const PASSWORD = process.env.E2E_PASSWORD ?? ''
const PORTAL = (process.env.E2E_PORTAL ?? 'both') as 'us' | 'canada' | 'both'
const REPORT_PATH = '/tmp/ui-smoke-report.json'

const issues: Issue[] = []

const US_ROUTES = [
  '/us/portal/dashboard',
  '/us/portal/leads',
  '/us/portal/new-customer',
  '/us/portal/accounts',
  '/us/portal/commissions',
  '/us/portal/training',
  '/us/portal/team',
  '/us/portal/settings',
  '/us/portal/badge',
]

const CANADA_ROUTES = [
  '/canada/portal/dashboard',
  '/canada/portal/leads',
  '/canada/portal/new-customer',
  '/canada/portal/accounts',
  '/canada/portal/commissions',
  '/canada/portal/training',
  '/canada/portal/proposals',
  '/canada/portal/team',
  '/canada/portal/settings',
  '/canada/portal/badge',
]

const SKIP_PATTERNS = [
  /sign\s*out/i,
  /log\s*out/i,
  /^delete/i,
  /^remove/i,
  /destroy/i,
  /confirm.*delete/i,
]

function shouldSkip(text: string): boolean {
  if (!text) return false
  return SKIP_PATTERNS.some(p => p.test(text))
}

async function attachListeners(page: Page, portal: 'us' | 'canada', getRoute: () => string) {
  page.on('console', (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      const txt = msg.text()
      if (/Failed to load resource: the server responded with a status of 401/i.test(txt)) return
      issues.push({ portal, route: getRoute(), kind: 'console-error', detail: txt })
    }
  })
  page.on('pageerror', (err) => {
    issues.push({ portal, route: getRoute(), kind: 'page-error', detail: err.message })
  })
  page.on('response', (res) => {
    const status = res.status()
    if (status >= 400 && status < 500) {
      if (/\/auth\/v1\//.test(res.url()) && status === 400) return
      issues.push({ portal, route: getRoute(), kind: 'network-4xx', detail: `${status} ${res.url()}`, url: res.url(), status })
    } else if (status >= 500) {
      issues.push({ portal, route: getRoute(), kind: 'network-5xx', detail: `${status} ${res.url()}`, url: res.url(), status })
    }
  })
}

async function login(page: Page, portal: 'us' | 'canada') {
  const loginUrl = `${APP_URL}/${portal}/portal/login`
  await page.goto(loginUrl, { waitUntil: 'domcontentloaded' })
  await page.waitForSelector('input[type="email"]', { timeout: 15_000 })
  await page.fill('input[type="email"]', EMAIL)
  await page.fill('input[type="password"]', PASSWORD)
  await Promise.all([
    page.waitForURL(new RegExp(`/${portal}/portal/(dashboard|onboarding)`), { timeout: 20_000 }),
    page.click('button[type="submit"]'),
  ])
}

async function crawlRoute(page: Page, portal: 'us' | 'canada', route: string) {
  const url = `${APP_URL}${route}`
  let routeRef = route
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 20_000 })
    await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})
  } catch (e: any) {
    issues.push({ portal, route: routeRef, kind: 'route-load-fail', detail: e.message ?? String(e) })
    return
  }

  const candidates = await page.$$eval('button, [role="button"]', (els) =>
    els.map((el, idx) => ({
      idx,
      text: (el as HTMLElement).innerText?.trim().slice(0, 80) ?? '',
      disabled: (el as HTMLButtonElement).disabled === true || el.getAttribute('aria-disabled') === 'true',
      ariaLabel: el.getAttribute('aria-label') ?? '',
      visible: (el as HTMLElement).offsetParent !== null,
    })),
  )

  for (const c of candidates) {
    if (c.disabled || !c.visible) continue
    const label = c.text || c.ariaLabel
    if (shouldSkip(label)) continue

    try {
      const handles = await page.$$('button, [role="button"]')
      const handle = handles[c.idx]
      if (!handle) continue
      const stillVisible = await handle.isVisible().catch(() => false)
      if (!stillVisible) continue
      await handle.click({ timeout: 2000, trial: false })
      await page.waitForTimeout(100)
      await page.keyboard.press('Escape').catch(() => {})
      await page.waitForTimeout(50)
      if (!page.url().includes(`/${portal}/portal/`)) {
        await page.goto(url, { waitUntil: 'domcontentloaded' }).catch(() => {})
      }
    } catch (e: any) {
      const msg = e?.message ?? String(e)
      if (!/not visible|detached|hidden|intercepts pointer/i.test(msg)) {
        issues.push({ portal, route: routeRef, kind: 'click-throw', detail: msg, selector: `button[${c.idx}] "${label}"` })
      }
    }
  }
}

async function tryAddLeadSequence(page: Page, portal: 'us' | 'canada') {
  const seqName = `${portal}-add-lead`
  const route = `/${portal}/portal/leads?new=true&t=${Date.now()}`
  try {
    await page.goto(`${APP_URL}${route}`, { waitUntil: 'domcontentloaded' })
    await page.waitForLoadState('networkidle', { timeout: 4_000 }).catch(() => {})

    let modal = page.locator('form:has(input[placeholder*="Business Name" i])').first()
    if (!(await modal.isVisible({ timeout: 4000 }).catch(() => false))) {
      const addBtn = page.locator('button:has-text("New Lead"), button:has-text("Add Lead")').first()
      if (await addBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
        await addBtn.click()
        await page.waitForTimeout(400)
        modal = page.locator('form:has(input[placeholder*="Business Name" i])').first()
      }
    }
    if (!(await modal.isVisible({ timeout: 3000 }).catch(() => false))) {
      issues.push({ portal, route: seqName, kind: 'sequence-fail', detail: 'New Lead modal never opened' })
      return
    }

    const ts = Date.now().toString().slice(-6)
    const textFields: Array<[string, string]> = [
      ['Business Name', `Smoke Test Biz ${ts}`],
      ['Contact Name', `Smoke Tester ${ts}`],
      ['Contact Email', `smoke+${ts}@example.com`],
      ['Phone', '5551234567'],
      ['City', 'Testville'],
    ]
    for (const [placeholder, val] of textFields) {
      const input = modal.locator(`input[placeholder*="${placeholder}" i]`).first()
      if (await input.isVisible({ timeout: 1000 }).catch(() => false)) {
        await input.fill(val).catch(() => {})
      }
    }

    const selectCount = await modal.locator('select').count()
    for (let i = 0; i < selectCount; i++) {
      const sel = modal.locator('select').nth(i)
      const optionValues = await sel.locator('option').evaluateAll((opts) =>
        opts.map((o) => (o as HTMLOptionElement).value).filter((v) => v !== ''),
      )
      if (optionValues.length > 0) {
        await sel.selectOption(optionValues[0]).catch(() => {})
      }
    }

    const submit = modal.locator('button[type="submit"]').first()
    if (!(await submit.isVisible({ timeout: 2000 }).catch(() => false))) {
      issues.push({ portal, route: seqName, kind: 'sequence-fail', detail: 'Submit button not found inside modal' })
      return
    }

    const tableName = portal === 'us' ? 'us_leads' : 'canada_leads'
    const respPromise = page.waitForResponse(
      (r) => r.url().includes(`/rest/v1/${tableName}`) && r.request().method() === 'POST',
      { timeout: 10_000 },
    ).catch(() => null)
    await submit.click().catch(() => {})
    const resp = await respPromise
    if (resp && resp.status() >= 400) {
      let body = ''
      try { body = await resp.text() } catch {}
      issues.push({
        portal,
        route: seqName,
        kind: 'sequence-fail',
        detail: `INSERT ${tableName} → HTTP ${resp.status()}: ${body.slice(0, 400)}`,
        url: resp.url(),
        status: resp.status(),
      })
    } else if (!resp) {
      const invalidFields = await modal.locator(':invalid').evaluateAll((els) =>
        els.map((el) => {
          const e = el as HTMLInputElement | HTMLSelectElement
          return `${e.tagName.toLowerCase()}[${(e as HTMLInputElement).placeholder ?? e.name ?? ''}]`
        }),
      )
      issues.push({
        portal,
        route: seqName,
        kind: 'sequence-fail',
        detail: `No POST to ${tableName} within 10s after submit; invalid fields: ${invalidFields.join(', ') || 'none'}`,
      })
    }
  } catch (e: any) {
    issues.push({ portal, route: seqName, kind: 'sequence-fail', detail: e?.message ?? String(e) })
  }
}

function shouldRun(portal: 'us' | 'canada'): boolean {
  return PORTAL === 'both' || PORTAL === portal
}

test.describe.serial('UI smoke scrape', () => {
  test.skip(!EMAIL || !PASSWORD, 'E2E_EMAIL and E2E_PASSWORD must be set')

  for (const portal of ['us', 'canada'] as const) {
    test(`${portal} portal — login + crawl every route + add-lead sequence`, async ({ page }) => {
      test.skip(!shouldRun(portal), `E2E_PORTAL=${PORTAL} excludes ${portal}`)
      test.setTimeout(300_000)
      let currentRoute = '/login'
      await attachListeners(page, portal, () => currentRoute)
      await login(page, portal)
      const routes = portal === 'us' ? US_ROUTES : CANADA_ROUTES
      for (const r of routes) {
        currentRoute = r
        await crawlRoute(page, portal, r)
      }
      currentRoute = `/${portal}/portal/leads (add-lead seq)`
      await tryAddLeadSequence(page, portal)
      const blocking = issues.filter(
        (i) => i.portal === portal && (i.kind === 'sequence-fail' || i.kind === 'page-error' || i.kind === 'network-5xx'),
      )
      expect.soft(blocking, `Blocking issues for ${portal}: ${JSON.stringify(blocking, null, 2)}`).toHaveLength(0)
    })
  }

  test.afterAll(() => {
    fs.writeFileSync(
      REPORT_PATH,
      JSON.stringify(
        {
          generatedAt: new Date().toISOString(),
          appUrl: APP_URL,
          portalScope: PORTAL,
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
    console.log(`\n[ui-smoke] ${issues.length} issue(s). Report: ${REPORT_PATH}`)
  })
})
