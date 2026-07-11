// Live test of the US Proposals page: signs up a throwaway rep, opens the
// proposals page, scrapes the real deck links, opens a sample of decks in the
// browser, and asserts data propagation (rep/email/price params -> rendered
// deck shows rep contact + USD pricing, no C$).
import { chromium } from 'file:///root/meridian-us-ready/frontend/node_modules/playwright/index.mjs'

const BASE = 'https://meridian.tips'
const EMAIL = `e2e-proposals-${Date.now() % 1000000}@meridian.tips`
const PASS = 'E2eProbe!2026x'
const REP_NAME = 'Props Tester'
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a)

const browser = await chromium.launch()
const page = await browser.newPage()
const errs = []
page.on('pageerror', e => errs.push(e.message))

// signup fresh throwaway rep
await page.goto(`${BASE}/us/portal/signup`, { waitUntil: 'networkidle' })
const inputs = page.locator('input')
await inputs.nth(0).fill(REP_NAME)
await inputs.nth(1).fill(EMAIL)
await inputs.nth(2).fill('(555) 010-0300')
await inputs.nth(3).fill(PASS)
await page.getByRole('button', { name: /create account/i }).click()
await page.waitForURL(/portal\/(dashboard|onboarding)/, { timeout: 20000 })
await page.evaluate(() => localStorage.setItem('meridian_onboarding_complete', 'true'))
log('signed up as', EMAIL)

// open proposals page, scrape all deck links
await page.goto(`${BASE}/us/portal/proposals`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2500)
const pageText = await page.evaluate(() => document.body.innerText)
if (/No QueryClient|Something went wrong/i.test(pageText)) { console.log('PROPOSALS PAGE CRASHED'); process.exit(1) }
const links = await page.evaluate(() =>
  Array.from(document.querySelectorAll('a[href*="meridian-decks"]')).map(a => a.href))
const bySlug = {}
for (const l of links) { const m = l.match(/meridian-decks\.vercel\.app\/([a-z-]+)/); if (m) bySlug[m[1]] = l }
const slugs = Object.keys(bySlug)
log(`proposals page renders ${slugs.length} deck links`)
const caLinks = slugs.filter(s => s.startsWith('ca-'))
log('ca- links (should be none):', caLinks.length ? caLinks : 'none')
const missingParams = slugs.filter(s => { const u = new URL(bySlug[s]); return !(u.searchParams.get('rep') === REP_NAME && u.searchParams.get('currency') === 'USD' && +u.searchParams.get('price') > 0) })
log('links missing rep/currency/price params:', missingParams.length ? missingParams.slice(0, 5) : 'none — all propagate')

// open a sample of decks (new ones + one veteran) and assert rendering
const sample = ['us-bakery', 'us-grocery', 'us-pharmacy', 'us-hotel', 'us-vetclinic', 'us-liquor', 'us-gym', 'us-bar'].filter(s => bySlug[s])
let fails = 0
for (const s of sample) {
  const dp = await browser.newPage()
  const derr = []
  dp.on('pageerror', e => derr.push(e.message))
  await dp.goto(bySlug[s], { waitUntil: 'networkidle' })
  await dp.waitForTimeout(2000)
  const r = await dp.evaluate((repName) => {
    const t = document.body.innerText
    return {
      title: document.title.slice(0, 50),
      hasRep: t.includes(repName),
      hasCadSymbol: /C\$\d/.test(t),
      usdPrice: (t.match(/\$\d{3}/) || [null])[0],
      slideCount: document.querySelectorAll('section, .slide').length,
      textLen: t.length,
    }
  }, REP_NAME)
  const ok = r.hasRep && !r.hasCadSymbol && r.usdPrice && r.textLen > 2000 && derr.length === 0
  if (!ok) fails++
  log(`${s}: ${ok ? 'OK' : 'FAIL'} — title="${r.title}" rep=${r.hasRep} C$=${r.hasCadSymbol} price=${r.usdPrice} textLen=${r.textLen} jsErr=${derr.length}`)
  await dp.close()
}
log(`deck sample: ${sample.length - fails}/${sample.length} pass; portal js errors: ${errs.length || 'none'}`)
console.log(JSON.stringify({ email: EMAIL, slugs: slugs.length, caLinks: caLinks.length, missingParams: missingParams.length, sampleFails: fails }))
await browser.close()
