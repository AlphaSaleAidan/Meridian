// Live feature sweep: US SR portal vs Canada SR portal (reference).
// Logs in as the dedicated e2e reps, visits every portal page with real
// navigations, exercises lead creation (US) and the training gate, and
// prints a pass/fail matrix. Read-mostly on Canada (live reps work there).
//
// Run: node tests/e2e/us-portal-feature-sweep.mjs   (from repo root)
import { chromium } from 'file:///root/meridian-us-ready/frontend/node_modules/playwright/index.mjs'

const BASE = 'https://meridian.tips'
const PAGES = ['dashboard', 'leads', 'new-customer', 'accounts', 'training', 'proposals', 'team', 'settings', 'badge']
const CRASH_RE = /No QueryClient|Something went wrong|unexpected error|Try refreshing/i

const US_CREDS = { email: 'e2e-usportal-test@meridian.tips', pass: 'E2eProbe!2026x' }
const CA_CREDS = { email: 'e2e-caportal-test@meridian.tips', pass: 'E2eProbe!2026x' }

function attachCollectors(page, sink) {
  page.on('pageerror', e => sink.push(`pageerror: ${e.message}`))
  page.on('console', m => {
    if (m.type() !== 'error') return
    const t = m.text()
    if (/telegram|favicon|net::ERR|Failed to load resource/i.test(t)) return // network noise, tracked separately
    sink.push(`console: ${t.slice(0, 160)}`)
  })
}

async function login(page, prefix, creds) {
  await page.goto(`${BASE}/${prefix}/portal/login`, { waitUntil: 'networkidle' })
  await page.locator('input').first().fill(creds.email)
  await page.locator('input[type="password"], input >> nth=1').first().fill(creds.pass)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL(/portal\/(dashboard|onboarding)/, { timeout: 20000 })
  await page.evaluate(() => localStorage.setItem('meridian_onboarding_complete', 'true'))
  return page.url()
}

async function signupIfNeeded(page, prefix, creds, name) {
  // try login first; fall back to signup
  try {
    return await login(page, prefix, creds)
  } catch {
    await page.goto(`${BASE}/${prefix}/portal/signup`, { waitUntil: 'networkidle' })
    const inputs = page.locator('input')
    await inputs.nth(0).fill(name)
    await inputs.nth(1).fill(creds.email)
    await inputs.nth(2).fill('(555) 010-0200')
    await inputs.nth(3).fill(creds.pass)
    await page.getByRole('button', { name: /create account/i }).click()
    await page.waitForURL(/portal\/(dashboard|onboarding)/, { timeout: 20000 })
    await page.evaluate(() => localStorage.setItem('meridian_onboarding_complete', 'true'))
    return page.url()
  }
}

async function sweepPages(page, prefix, errors) {
  const rows = []
  for (const p of PAGES) {
    errors.length = 0
    await page.goto(`${BASE}/${prefix}/portal/${p}`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(2500)
    const body = await page.evaluate(() => document.body.innerText)
    const crashed = CRASH_RE.test(body)
    const h1 = await page.locator('h1, h2').first().textContent().catch(() => '')
    rows.push({ portal: prefix, page: p, crashed, jsErrors: [...errors], heading: (h1 || '').trim().slice(0, 40), bodyLen: body.length })
  }
  return rows
}

async function testUsLeadFeature(page, errors) {
  const out = {}
  errors.length = 0
  // create a lead through the real form
  await page.goto(`${BASE}/us/portal/leads?new=true`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(1500)
  const biz = `E2E Sweep Diner ${Date.now() % 100000}`
  await page.getByPlaceholder(/business name/i).fill(biz)
  await page.getByPlaceholder(/contact name/i).fill('Sweep Tester')
  await page.getByPlaceholder(/contact email/i).fill('sweep@example.com')
  await page.getByRole('button', { name: /add lead/i }).click()
  await page.waitForTimeout(3000)
  const listed = (await page.evaluate(() => document.body.innerText)).includes(biz)
  out.createLead = { ok: listed, biz, jsErrors: [...errors] }
  if (!listed) return out
  // open detail
  errors.length = 0
  await page.getByText(biz).first().click()
  await page.waitForTimeout(2500)
  const detailUrl = page.url()
  const detailBody = await page.evaluate(() => document.body.innerText)
  out.leadDetail = { ok: /us\/portal\/leads\/.+/.test(detailUrl) && !CRASH_RE.test(detailBody), url: detailUrl, jsErrors: [...errors] }
  // try to delete (cleanup) if a delete control exists
  const del = page.getByRole('button', { name: /delete/i }).first()
  if (await del.count()) {
    page.once('dialog', d => d.accept())
    await del.click().catch(() => {})
    await page.waitForTimeout(500)
    const confirm = page.getByRole('button', { name: /confirm|yes|delete/i }).last()
    if (await confirm.count()) await confirm.click().catch(() => {})
    await page.waitForTimeout(2000)
    await page.goto(`${BASE}/us/portal/leads`, { waitUntil: 'networkidle' })
    await page.waitForTimeout(2000)
    out.cleanup = { deleted: !(await page.evaluate(() => document.body.innerText)).includes(biz) }
  } else {
    out.cleanup = { deleted: false, note: 'no delete control; test lead remains in e2e rep pipeline (RLS-isolated)' }
  }
  return out
}

async function testTrainingGate(page, prefix) {
  // untrained rep on new-customer should see the training gate, not a crash
  await page.goto(`${BASE}/${prefix}/portal/new-customer`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(2500)
  const body = await page.evaluate(() => document.body.innerText)
  return {
    gateShown: /finish training/i.test(body),
    crashed: CRASH_RE.test(body),
    wizardShown: /business|customer/i.test(body) && !/finish training/i.test(body),
  }
}

const browser = await chromium.launch()
const report = { us: {}, canada: {} }

for (const [key, prefix, creds, name] of [
  ['us', 'us', US_CREDS, 'E2E Test Rep'],
  ['canada', 'canada', CA_CREDS, 'E2E CA Test Rep'],
]) {
  const ctx = await browser.newContext()
  const page = await ctx.newPage()
  const errors = []
  attachCollectors(page, errors)
  try {
    report[key].login = await signupIfNeeded(page, prefix, creds, name)
    report[key].pages = await sweepPages(page, prefix, errors)
    report[key].trainingGate = await testTrainingGate(page, prefix)
    if (key === 'us') report[key].leadFeature = await testUsLeadFeature(page, errors)
  } catch (e) {
    report[key].fatal = String(e).slice(0, 300)
  }
  await ctx.close()
}
await browser.close()

// ---- print matrix ----
const pad = (s, n) => String(s).padEnd(n)
console.log('\n=== PAGE MATRIX (live meridian.tips) ===')
console.log(pad('page', 14) + pad('US', 26) + 'CANADA')
for (const p of PAGES) {
  const u = report.us.pages?.find(r => r.page === p)
  const c = report.canada.pages?.find(r => r.page === p)
  const cell = r => !r ? 'SKIPPED' : r.crashed ? 'CRASHED' : r.jsErrors.length ? `ok, ${r.jsErrors.length} js-err` : 'OK'
  console.log(pad(p, 14) + pad(cell(u), 26) + cell(c))
}
console.log('\nUS training gate:', JSON.stringify(report.us.trainingGate))
console.log('CA training gate:', JSON.stringify(report.canada.trainingGate))
console.log('US lead feature:', JSON.stringify(report.us.leadFeature))
for (const k of ['us', 'canada']) {
  if (report[k].fatal) console.log(`${k} FATAL:`, report[k].fatal)
  for (const r of report[k].pages || []) if (r.jsErrors.length) console.log(`${k}/${r.page} js errors:`, r.jsErrors.slice(0, 3))
}
console.log('\nFull report JSON written to /tmp/us-portal-sweep.json')
await import('node:fs').then(fs => fs.promises.writeFile('/tmp/us-portal-sweep.json', JSON.stringify(report, null, 2)))
