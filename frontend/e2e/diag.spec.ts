import { test, expect } from '@playwright/test'
import { seedCustomerAuth, mockSupabase, TEST_ORG_ID, SUPABASE_STORAGE_KEY } from './wizards/_harness'
import type { Route, Request } from '@playwright/test'

test('diagnose: what fetch calls fire for /canada/merchant/onboard', async ({ page }) => {
  const allFetches: string[] = []
  // Intercept ALL requests to see what's happening
  await page.route('**/*', async (route: Route, req: Request) => {
    const url = req.url()
    if (!url.includes('supabase') && !url.includes('localhost:3000/src') && !url.includes('node_modules')) {
      allFetches.push(req.method() + ' ' + url)
    }
    await route.continue()
  })
  
  await seedCustomerAuth(page, { org: { org_id: TEST_ORG_ID, onboarded: true } })
  
  await page.goto('/canada/merchant/onboard', { waitUntil: 'domcontentloaded' })
  await page.waitForTimeout(5000)
  
  console.log('URL:', page.url())
  console.log('All fetches:', JSON.stringify(allFetches.slice(0, 20), null, 2))
  
  // Check localStorage
  const orgRaw = await page.evaluate(() => localStorage.getItem('meridian_org'))
  const authRaw = await page.evaluate((key) => localStorage.getItem(key), SUPABASE_STORAGE_KEY)
  console.log('meridian_org:', orgRaw?.substring(0, 100))
  console.log('auth token present:', !!authRaw)
  
  const h = await page.$$eval('h1, h2, h3', els => els.map(e => e.textContent?.trim()).join(' | '))
  console.log('HEADINGS:', h)
  
  expect(true).toBe(true)
})
