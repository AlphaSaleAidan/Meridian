/**
 * Camera pillar e2e.
 *
 * Exercises the public Canada demo camera surface (no auth, synthetic data) at
 * /canada/demo/camera, which renders:
 *   - CameraDemo            — overlay layer toggles + presets over the replayed
 *                             YOLO+ByteTrack clip (LiveCamerasPage demo mode).
 *   - CameraAnalyticsShowcase — the "what your cameras unlock" metric gallery.
 *
 * No backend / Supabase env required: useIsDemo() keys off the URL, so the page
 * boots in demo mode and the toggles/presets/cards are pure client state.
 *
 * Run locally (Playwright boots the Vite dev server itself — see
 * playwright.config.ts webServer):
 *   npx playwright test e2e/camera.spec.ts
 */
import { test, expect } from '@playwright/test'

const CAMERA_URL = '/canada/demo/camera'

// Layer keys in CameraDemo (LAYERS) — order-independent membership checks.
const LAYER_KEYS = [
  'detections',
  'identity',
  'journey',
  'zones',
  'heatmap',
  'staff',
  'pos_xref',
  'exceptions',
] as const

// Metric keys in CameraAnalyticsShowcase (METRICS).
const METRIC_KEYS = [
  'traffic',
  'peak',
  'dwell',
  'conversion',
  'staff',
  'demographics',
  'loss',
] as const

test.describe('Camera pillar — public demo', () => {
  test.beforeEach(async ({ page }) => {
    // Skip the first-visit demo chrome that overlays the portal (the business-type
    // picker is a fixed full-screen modal that intercepts clicks; the tour adds a
    // spotlight). Both key off localStorage, so pre-seed before the app boots.
    await page.addInitScript(() => {
      window.localStorage.setItem('meridian.demo.businessType', 'restaurant')
      window.localStorage.setItem('meridian_tour_dismissed', 'true')
    })
    await page.goto(CAMERA_URL, { waitUntil: 'domcontentloaded' })
    // The pillar shell lazy-mounts the Live segment; wait for it to resolve.
    await expect(page.getByTestId('camera-demo')).toBeVisible()
  })

  test('renders the live demo + both pillar segments', async ({ page }) => {
    await expect(
      page.getByRole('heading', { name: /camera intelligence/i }),
    ).toBeVisible()

    // Segmented tab bar exposes Live (default) + Analytics.
    await expect(page.getByRole('button', { name: 'Live' })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Analytics' })).toBeVisible()

    // The replayed clip + occupancy overlay are present.
    await expect(page.locator('video')).toHaveCount(1)
    await expect(page.getByText('LIVE', { exact: true })).toBeVisible()
  })

  test('overlay layer toggles flip their pressed state', async ({ page }) => {
    const layers = page.getByTestId('camera-layers').locator('button')
    await expect(layers).toHaveCount(LAYER_KEYS.length)

    const detections = page.getByTestId('camera-layer-detections')
    const before = await detections.getAttribute('aria-pressed')
    const expected = before === 'true' ? 'false' : 'true'

    await detections.click()
    await expect(detections).toHaveAttribute('aria-pressed', expected)

    // Toggling back restores the original state.
    await detections.click()
    await expect(detections).toHaveAttribute('aria-pressed', before ?? 'false')
  })

  test('presets switch the active layer set on and off', async ({ page }) => {
    // "Raw" clears every layer.
    await page.getByTestId('camera-preset-Raw').click()
    for (const k of LAYER_KEYS) {
      await expect(page.getByTestId(`camera-layer-${k}`)).toHaveAttribute(
        'aria-pressed',
        'false',
      )
    }

    // "All" enables every layer.
    await page.getByTestId('camera-preset-All').click()
    for (const k of LAYER_KEYS) {
      await expect(page.getByTestId(`camera-layer-${k}`)).toHaveAttribute(
        'aria-pressed',
        'true',
      )
    }

    // "Operations" is a partial preset: detections/zones/heatmap on, staff off.
    await page.getByTestId('camera-preset-Operations').click()
    for (const k of ['detections', 'zones', 'heatmap'] as const) {
      await expect(page.getByTestId(`camera-layer-${k}`)).toHaveAttribute(
        'aria-pressed',
        'true',
      )
    }
    await expect(page.getByTestId('camera-layer-staff')).toHaveAttribute(
      'aria-pressed',
      'false',
    )
  })

  test('analytics showcase renders every metric card and selection works', async ({
    page,
  }) => {
    const showcase = page.getByTestId('camera-analytics-showcase')
    await expect(showcase).toBeVisible()

    const cards = showcase.locator('[data-testid^="camera-metric-"]')
    await expect(cards).toHaveCount(METRIC_KEYS.length)

    // Each metric card is individually present.
    for (const k of METRIC_KEYS) {
      await expect(page.getByTestId(`camera-metric-${k}`)).toBeVisible()
    }

    // Selecting a card marks it pressed; selecting again clears it.
    const traffic = page.getByTestId('camera-metric-traffic')
    await expect(traffic).toHaveAttribute('aria-pressed', 'false')
    await traffic.click()
    await expect(traffic).toHaveAttribute('aria-pressed', 'true')
    await traffic.click()
    await expect(traffic).toHaveAttribute('aria-pressed', 'false')
  })

  test('Analytics segment is reachable from the segment bar', async ({ page }) => {
    await page.getByRole('button', { name: 'Analytics' }).click()
    // CameraIntelligencePage is an SEO/marketing page; assert the URL switched
    // and the live demo surface is no longer mounted.
    await expect(page).toHaveURL(/view=intelligence/)
    await expect(page.getByTestId('camera-demo')).toHaveCount(0)
  })
})
