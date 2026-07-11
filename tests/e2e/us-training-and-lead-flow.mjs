// E2E of the US rep happy path through the real UI: complete the Training
// Course (5 videos + quizzes), sign the Code of Conduct, then verify lead
// creation unlocks and works. Uses the dedicated e2e rep.
import { chromium } from 'file:///root/meridian-us-ready/frontend/node_modules/playwright/index.mjs'
import { build } from 'file:///root/meridian-us-ready/frontend/node_modules/esbuild/lib/main.js'
import { writeFileSync } from 'node:fs'

// transpile course-data.ts so we know the correct quiz answers
await build({
  entryPoints: ['/root/meridian-us-ready/frontend/src/components/training/course-data.ts'],
  outfile: '/tmp/course-data.mjs', format: 'esm', bundle: false,
})
const { COURSE_MODULES } = await import('/tmp/course-data.mjs')

const BASE = 'https://meridian.tips'
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a)

const browser = await chromium.launch()
const page = await browser.newPage()
const jsErrors = []
page.on('pageerror', e => jsErrors.push(e.message))

// login
await page.goto(`${BASE}/us/portal/login`, { waitUntil: 'networkidle' })
await page.locator('input').first().fill('e2e-usportal-test@meridian.tips')
await page.locator('input[type="password"]').first().fill('E2eProbe!2026x')
await page.getByRole('button', { name: /sign in/i }).click()
await page.waitForURL(/portal\/(dashboard|onboarding)/, { timeout: 20000 })
await page.evaluate(() => localStorage.setItem('meridian_onboarding_complete', 'true'))
log('logged in')

await page.goto(`${BASE}/us/portal/training`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)

for (const mod of COURSE_MODULES) {
  // select the module (skip if already passed — button shows Passed state)
  await page.getByText(mod.title, { exact: false }).first().click()
  await page.waitForTimeout(1200)
  const panelText = await page.evaluate(() => document.body.innerText)
  if (/Passed(\s*·|\b)/.test(panelText) && !/quiz is open|unlock the quiz/i.test(panelText)) {
    log(`module ${mod.id}: already passed`)
    continue
  }
  // watch the video to the end (seek near the end so `ended` fires for real)
  const watched = await page.evaluate(async () => {
    const v = document.querySelector('video')
    if (!v) return 'no-video'
    v.muted = true
    await v.play().catch(() => {})
    if (!isFinite(v.duration)) await new Promise(r => v.addEventListener('loadedmetadata', r, { once: true }))
    v.currentTime = Math.max(0, v.duration - 0.4)
    await new Promise(r => v.addEventListener('ended', r, { once: true }))
    return 'ended'
  })
  log(`module ${mod.id}: video ${watched}`)
  await page.waitForTimeout(1500)
  // open quiz
  await page.getByRole('button', { name: /take the quiz|retake/i }).first().click()
  await page.waitForTimeout(800)
  // answer every question by checking the correct radio (name=q-<mod>-<idx>)
  for (let qi = 0; qi < mod.quiz.length; qi++) {
    await page.locator(`input[name="q-${mod.id}-${qi}"]`).nth(mod.quiz[qi].answer).check()
    await page.waitForTimeout(150)
  }
  await page.getByRole('button', { name: /submit/i }).click()
  await page.waitForTimeout(2500)
  const passed = await page.getByText(/passed|nice work|4\/4|correct/i).first().textContent().catch(() => 'unknown')
  log(`module ${mod.id}: quiz result -> ${String(passed).trim().slice(0, 50)}`)
  const cont = page.getByRole('button', { name: /continue/i })
  if (await cont.count()) await cont.first().click()
  await page.waitForTimeout(800)
}

// sign the Code of Conduct (step 6 in the course stepper)
await page.goto(`${BASE}/us/portal/training`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2000)
await page.getByRole('button', { name: /code of conduct/i }).first().click()
await page.waitForTimeout(1200)
if (await page.getByText(/signed/i).first().isVisible().catch(() => false) &&
    (await page.locator('input[type="checkbox"]').count()) === 0) {
  log('conduct: already signed')
} else {
  await page.locator('input[type="checkbox"]').first().check()
  await page.locator('input[type="text"]').last().fill('E2E Test Rep')
  await page.getByRole('button', { name: /sign the code of conduct/i }).click()
  await page.waitForTimeout(3000)
  log('conduct: signed')
}

// verify lead creation now unlocks
await page.goto(`${BASE}/us/portal/leads`, { waitUntil: 'networkidle' })
await page.waitForTimeout(2500)
await page.getByRole('button', { name: /new lead/i }).first().click()
await page.waitForTimeout(1200)
if (page.url().includes('/training')) {
  log('LEAD CREATE: still locked (redirected to training)')
} else {
  const biz = `E2E Flow Diner ${Date.now() % 100000}`
  await page.getByPlaceholder(/business name/i).fill(biz)
  await page.getByPlaceholder(/contact name/i).fill('Flow Tester')
  await page.getByRole('button', { name: /add lead/i }).click()
  await page.waitForTimeout(3000)
  const listed = (await page.evaluate(() => document.body.innerText)).includes(biz)
  log(`LEAD CREATE: ${listed ? 'OK — lead appears in pipeline' : 'FAILED — not listed'}`)
  if (listed) {
    await page.getByText(biz).first().click()
    await page.waitForTimeout(2500)
    const detailOk = /\/us\/portal\/leads\/.+/.test(page.url()) &&
      !/No QueryClient|Something went wrong/i.test(await page.evaluate(() => document.body.innerText))
    log(`LEAD DETAIL: ${detailOk ? 'OK' : 'FAILED'} (${page.url()})`)
  }
}
log('js errors during whole flow:', jsErrors.length ? jsErrors.slice(0, 5) : 'none')
writeFileSync('/tmp/us-training-flow-errors.json', JSON.stringify(jsErrors, null, 2))
await browser.close()
