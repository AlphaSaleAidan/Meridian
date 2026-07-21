/**
 * SettingsPage — POS OAuth return banner.
 *
 * The Square/Clover OAuth callbacks redirect to /app/settings with
 * ?oauth=success|partial|denied|install_complete. These tests cover the two
 * cases that must never regress silently:
 *   1. oauth=success shows the green "POS connected" banner and clears the
 *      clover_install_relaunch one-shot key.
 *   2. oauth=install_complete with the one-shot key ALREADY set must NOT
 *      relaunch authorize again (no redirect loop) — it shows the
 *      "connect manually" banner and clears the key.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import SettingsPage from '../SettingsPage'

vi.mock('@/hooks/useApi', () => ({
  // One shape serves both call sites: conn.data.connections and cameras.data.cameras
  useApi: () => ({
    loading: false,
    error: null,
    data: { connections: [], cameras: [], total: 0 },
    refetch: vi.fn(),
  }),
}))
vi.mock('@/lib/api', () => ({ api: { connection: vi.fn(), cameras: vi.fn() } }))
vi.mock('@/hooks/useOrg', () => ({ useOrgId: () => 'org-1' }))
vi.mock('@/lib/supabase', () => ({ getAuthHeaders: vi.fn().mockResolvedValue({}) }))
vi.mock('@/components/ScrollReveal', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
vi.mock('@/components/DashboardTiltCard', () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
vi.mock('@/components/POSSelectorPanel', () => ({ default: () => null }))
vi.mock('@/components/POSLogo', () => ({ default: () => null }))
vi.mock('@/components/vision/CameraSetupWizard', () => ({ default: () => null }))
vi.mock('@/lib/agent-data', () => ({
  generateBusinessProfiles: () => [{
    type: 'coffee_shop',
    label: 'Coffee Shop',
    benchmarks: { avgTicketCents: 850, marginPct: 70, peakHours: '7-9am', topCategory: 'Espresso', wastePct: 4, staffingRatio: '1:20' },
    agentThresholds: { voidAlertPct: 1, refundAlertPct: 2, revenueDropAlertPct: 20, lowMarginPct: 40, highMarginPct: 75, peakStaffingMin: 2 },
  }],
}))

const RELAUNCH_KEY = 'clover_install_relaunch'

function renderSettings(query: string) {
  return render(
    <MemoryRouter initialEntries={[`/app/settings${query}`]}>
      <SettingsPage />
    </MemoryRouter>
  )
}

beforeEach(() => {
  sessionStorage.clear()
  localStorage.clear()
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }))
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('SettingsPage OAuth return banner', () => {
  it('shows the success banner with merchant id and clears the relaunch key', () => {
    sessionStorage.setItem(RELAUNCH_KEY, '1')
    renderSettings('?oauth=success&merchant_id=MID123')
    expect(screen.getByText('POS connected (merchant MID123)')).toBeTruthy()
    expect(sessionStorage.getItem(RELAUNCH_KEY)).toBeNull()
  })

  it('shows the partial (amber) banner with the warning text', () => {
    renderSettings('?oauth=partial&warning=Token%20saved%20but%20sync%20failed')
    expect(screen.getByText('Token saved but sync failed')).toBeTruthy()
  })

  it('shows the denied (red) banner with the error text', () => {
    renderSettings('?oauth=denied&error=Access%20denied%20by%20merchant')
    expect(screen.getByText('Access denied by merchant')).toBeTruthy()
  })

  it('does NOT relaunch a second time on install_complete — shows the manual-connect banner and clears the key', () => {
    sessionStorage.setItem(RELAUNCH_KEY, '1')
    renderSettings('?oauth=install_complete&provider=clover&merchant_id=MID123')
    // No navigation happened (jsdom would log a navigation error) — instead the
    // merchant is told to connect manually, and the one-shot key is cleared so
    // a future genuine install can auto-relaunch again.
    expect(screen.getByText(/connection did not finish/i)).toBeTruthy()
    expect(sessionStorage.getItem(RELAUNCH_KEY)).toBeNull()
  })
})
