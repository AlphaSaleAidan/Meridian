import { test, expect } from '@playwright/test'
import { seedCustomerAuth, mockSupabase, TEST_ORG_ID } from './wizards/_harness'

test('diagnose: catch ALL fetch/xhr to find what fires', async ({ page }) => {
  const ALL: string[] = []
  // Intercept EVERYTHING to see what URLs are actually fetched
  await page.route('**/*', async (route) => {
    const url = route.request().url()
    const m = route.request().method()
    ALL.push(`${m} ${url}`)
    await route.continue()
  })

  await seedCustomerAuth(page, { org: { org_id: TEST_ORG_ID, onboarded: true } })
  await mockSupabase(page)

  // Add a spy for fetch calls via page injection — runs inside the browser
  await page.addInitScript(() => {
    const origFetch = window.fetch
    window.__fetchCalls = []
    window.fetch = function(...args) {
      const url = typeof args[0] === 'string' ? args[0] : (args[0] as Request).url
      ;(window as any).__fetchCalls.push(url)
      return origFetch.apply(this, args)
    }
  })

  await page.goto('/canada/merchant/onboard', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(6000)

  // Collect all network intercepted URLs
  console.log('=== ALL INTERCEPTED URLS ===')
  ALL.filter(u => !u.includes('fonts') && !u.includes('@vite') && !u.includes('@react') && !u.includes('telegram')).forEach(u => console.log(u))

  // Collect fetch calls inside browser
  const browserFetches = await page.evaluate(() => (window as any).__fetchCalls || [])
  console.log('=== BROWSER fetch() CALLS ===')
  browserFetches.forEach((u: string) => console.log(u))

  const h = await page.$$eval('h1, h2, h3', els => els.map(e => e.textContent?.trim()).join(' | ')).catch(() => '')
  const orgRaw = await page.evaluate(() => localStorage.getItem('meridian_org'))
  console.log('=== HEADING ===', h)
  console.log('=== ORG ===', orgRaw?.substring(0, 80))

  expect(true).toBe(true)
})
