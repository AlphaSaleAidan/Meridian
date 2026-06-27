/**
 * CameraAnalyticsShowcase component tests.
 *
 * Covers the two states the e2e camera spec can't reach without auth/a backend:
 *   - connected={false} → "Sample data" badge + the dashed connect-a-camera CTA
 *     (this is the empty/value-gallery state shown on LiveCamerasPage when a real
 *     merchant has no cameras yet).
 *   - connected={true}  → no badge, no CTA (live-feed copy).
 * Plus the metric-card select/deselect interaction (aria-pressed).
 */
import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, cleanup, fireEvent, within } from '@testing-library/react'
import CameraAnalyticsShowcase from '../CameraAnalyticsShowcase'

const METRIC_KEYS = [
  'traffic', 'peak', 'dwell', 'conversion', 'staff', 'demographics', 'loss',
] as const

afterEach(cleanup)

describe('CameraAnalyticsShowcase', () => {
  it('renders one button per metric', () => {
    render(<CameraAnalyticsShowcase />)
    const showcase = screen.getByTestId('camera-analytics-showcase')
    for (const k of METRIC_KEYS) {
      expect(within(showcase).getByTestId(`camera-metric-${k}`)).toBeTruthy()
    }
  })

  it('disconnected state shows the "Sample data" badge and connect CTA', () => {
    render(<CameraAnalyticsShowcase connected={false} />)
    expect(screen.getByText(/sample data/i)).toBeTruthy()
    expect(screen.getByText(/connect a camera/i)).toBeTruthy()
    expect(screen.getByText(/add a camera in settings/i)).toBeTruthy()
  })

  it('connected state hides the badge and CTA, shows live copy', () => {
    render(<CameraAnalyticsShowcase connected />)
    expect(screen.queryByText(/sample data/i)).toBeNull()
    expect(screen.queryByText(/add a camera in settings/i)).toBeNull()
    expect(screen.getByText(/generated from your live camera feeds/i)).toBeTruthy()
  })

  it('selecting a metric card toggles its pressed state', () => {
    render(<CameraAnalyticsShowcase />)
    const card = screen.getByTestId('camera-metric-traffic')
    expect(card.getAttribute('aria-pressed')).toBe('false')
    fireEvent.click(card)
    expect(card.getAttribute('aria-pressed')).toBe('true')
    fireEvent.click(card)
    expect(card.getAttribute('aria-pressed')).toBe('false')
  })
})
