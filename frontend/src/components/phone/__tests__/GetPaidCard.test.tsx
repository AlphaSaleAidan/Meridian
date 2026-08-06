/**
 * GetPaidCard — embedded Stripe Connect onboarding.
 *
 * Contract:
 *  1. No connected account → the "get paid" pitch + a "Connect payments" CTA.
 *  2. Clicking it POSTs account-session and renders Stripe's onboarding
 *     INLINE (never a redirect — window.location must not change).
 *  3. onExit hands off to the "verifying" state, which polls /status.
 *  4. charges_enabled → the connected state, including the plain-language
 *     line about how the per-order fee is taken.
 *  5. Demo mode never calls the API and never enables the CTA.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, cleanup, fireEvent, waitFor, act } from '@testing-library/react'
import GetPaidCard from '../GetPaidCard'

vi.mock('@/lib/supabase', () => ({
  getAuthHeaders: vi.fn(async () => ({ Authorization: 'Bearer test-token' })),
}))

// Stripe's loader injects a real <script> on import; stub it out entirely.
const loadConnectAndInitialize = vi.fn((_params: unknown) => ({ __instance: true }))
vi.mock('@stripe/connect-js', () => ({
  loadConnectAndInitialize: (params: unknown) => loadConnectAndInitialize(params),
}))

// Capture onExit so the test can drive the post-onboarding handoff.
let capturedOnExit: (() => void) | null = null
vi.mock('@stripe/react-connect-js', () => ({
  ConnectComponentsProvider: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  ConnectAccountOnboarding: ({ onExit }: { onExit: () => void }) => {
    capturedOnExit = onExit
    return <div data-testid="stripe-onboarding">stripe embedded onboarding</div>
  },
}))

const STATUS_URL = /\/api\/stripe\/connect\/status\//
const SESSION_URL = /\/api\/stripe\/connect\/account-session\//

function jsonRes(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as Response
}

/** Route fetch by URL; `status` is re-read on every call so a test can flip it. */
function mockApi(status: () => Record<string, unknown>) {
  return vi.fn(async (url: string | URL) => {
    const u = String(url)
    if (SESSION_URL.test(u)) {
      return jsonRes({ account_id: 'acct_123', client_secret: 'cs_test_123', publishable_key: 'pk_test_123' })
    }
    if (STATUS_URL.test(u)) return jsonRes(status())
    throw new Error(`unexpected fetch: ${u}`)
  })
}

describe('GetPaidCard', () => {
  beforeEach(() => {
    cleanup()
    capturedOnExit = null
    loadConnectAndInitialize.mockClear()
  })
  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
  })

  it('offers the connect CTA when no account exists', async () => {
    vi.stubGlobal('fetch', mockApi(() => ({ connected: false, charges_enabled: false })))
    render(<GetPaidCard orgId="merchant-1" />)

    expect(await screen.findByRole('button', { name: /connect payments/i })).toBeTruthy()
    expect(screen.getByText(/no Stripe account needed/i)).toBeTruthy()
  })

  it('renders Stripe onboarding inline — no redirect', async () => {
    const fetchMock = mockApi(() => ({ connected: false, charges_enabled: false }))
    vi.stubGlobal('fetch', fetchMock)
    const hrefBefore = window.location.href

    render(<GetPaidCard orgId="merchant-1" />)
    fireEvent.click(await screen.findByRole('button', { name: /connect payments/i }))

    expect(await screen.findByTestId('stripe-onboarding')).toBeTruthy()
    expect(window.location.href).toBe(hrefBefore)

    // Connect.js got the platform pk and a secret-fetcher that returns the
    // secret already minted by the account-session call.
    const params = loadConnectAndInitialize.mock.calls[0][0] as {
      publishableKey: string
      fetchClientSecret: () => Promise<string>
    }
    expect(params.publishableKey).toBe('pk_test_123')
    await expect(params.fetchClientSecret()).resolves.toBe('cs_test_123')
    expect(fetchMock.mock.calls.some(([u]) => SESSION_URL.test(String(u)))).toBe(true)
  })

  it('onExit shows the verifying state, then the connected state once charges are enabled', async () => {
    let charges = false
    vi.stubGlobal('fetch', mockApi(() => ({ connected: true, charges_enabled: charges, details_submitted: false })))

    render(<GetPaidCard orgId="merchant-1" />)
    fireEvent.click(await screen.findByRole('button', { name: /finish connecting/i }))
    await screen.findByTestId('stripe-onboarding')

    charges = true
    await act(async () => { capturedOnExit?.() })

    await waitFor(() => expect(screen.getByText(/You're all set/i)).toBeTruthy())
    expect(screen.getByText(/nothing to invoice, nothing to pay us/i)).toBeTruthy()
  })

  it('an account mid-verification reloads into the verifying state, not a fresh CTA', async () => {
    vi.stubGlobal('fetch', mockApi(() => ({ connected: true, charges_enabled: false, details_submitted: true })))
    render(<GetPaidCard orgId="merchant-1" />)

    expect(await screen.findByText(/verifying your details/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /connect payments/i })).toBeNull()
  })

  it('demo mode never calls the API and never enables the CTA', async () => {
    const fetchMock = mockApi(() => ({ connected: false, charges_enabled: false }))
    vi.stubGlobal('fetch', fetchMock)

    render(<GetPaidCard orgId="merchant-1" isDemo />)

    const cta = await screen.findByRole('button', { name: /connect payments/i })
    expect((cta as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(cta)
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
