/**
 * OnboardingWizard — #2 / CA-2 auth-header regression guard.
 *
 * Strategy: mock @/lib/supabase with a fake supabase object (NOT null) so that
 * connectPos in auth.tsx takes the real fetch path (not the no-supabase early-
 * return). Set `meridian_org` in localStorage so the AuthProvider's initial org
 * state is seeded. Wrap the wizard in the real AuthProvider.
 *
 * This directly exercises the connectPos fix:
 *   headers: { ...(await getAuthHeaders()) }
 * on the POST /api/pos/connect call, which attaches the Supabase Bearer that
 * require_org_access (CA-1 / CA-2) demands.
 *
 * REGRESSION GUARD (#2): Removing the getAuthHeaders() spread from connectPos
 * causes the Authorization assertion at the bottom to fail immediately.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react'
import { AuthProvider } from '@/lib/auth'
import OnboardingWizard from '../OnboardingWizard'

// ── Fake supabase module ──────────────────────────────────────────────────────
// supabase must NOT be null so connectPos does not take the null-branch shortcut.
// getAuthHeaders() returns the Bearer token that the fix spreads into headers.
vi.mock('@/lib/supabase', () => ({
  supabase: {
    auth: {
      getSession: vi.fn().mockResolvedValue({ data: { session: null } }),
      onAuthStateChange: vi.fn().mockReturnValue({
        data: { subscription: { unsubscribe: vi.fn() } },
      }),
      refreshSession: vi.fn().mockResolvedValue({ data: { session: null } }),
    },
    from: vi.fn().mockReturnValue({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnThis(),
      limit: vi.fn().mockReturnThis(),
      maybeSingle: vi.fn().mockResolvedValue({ data: null }),
    }),
    rpc: vi.fn().mockResolvedValue({ data: false, error: null }),
  },
  getAuthHeaders: vi.fn().mockResolvedValue({
    'Content-Type': 'application/json',
    'Authorization': 'Bearer test-jwt',
  }),
}))

// react-router-dom: useNavigate is called on the 'done' step.
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

// Stub logo components — they have no bearing on the test.
vi.mock('@/components/MeridianLogo', () => ({
  MeridianEmblem: () => null,
  MeridianWordmark: () => null,
}))

// ── Test org seed ─────────────────────────────────────────────────────────────
const TEST_ORG = {
  org_id: 'org-123',
  business_name: 'Test Business',
  owner_name: 'Test Owner',
  email: 'test@example.com',
  plan: 'trial',
  pos_provider: null,
  pos_connected: false,
  created_at: '2024-01-01T00:00:00Z',
  onboarded: false,
}

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  localStorage.clear()
})

describe('OnboardingWizard', () => {
  let fetchSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    // Seed the org so AuthProvider's useState(loadOrg) initialiser has data.
    // connectPos checks `if (!org)` — if this is missing it returns early.
    localStorage.setItem('meridian_org', JSON.stringify(TEST_ORG))

    // Fake timers BEFORE render so AuthProvider's 5-second guard is a fake timer
    // (it never fires because getSession() resolves as a microtask first).
    vi.useFakeTimers()

    // Two-call fetch mock:
    //   call 0 → /api/pos/test-connection (no auth header — by design)
    //   call 1 → /api/pos/connect         (WITH Authorization — the #2 fix)
    fetchSpy = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(global as any).fetch = fetchSpy
  })

  it('POST /api/pos/connect carries Authorization Bearer — regression guard for #2/CA-2', async () => {
    render(
      <AuthProvider>
        <OnboardingWizard />
      </AuthProvider>,
    )

    // Flush AuthProvider's async initialisation (getSession resolves as microtask).
    // Prevents "state update outside act" warnings.
    await act(async () => {
      for (let i = 0; i < 5; i++) {
        await Promise.resolve()
      }
    })

    // ── Welcome step ─────────────────────────────────────────────────────────
    expect(screen.getByText(/Get Started/i)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /Get Started/i }))

    // ── Pricing step ─────────────────────────────────────────────────────────
    // Monthly billing is selected by default; no action needed before continuing.
    fireEvent.click(screen.getByRole('button', { name: /Continue to POS Setup/i }))

    // ── Provider step ────────────────────────────────────────────────────────
    // Click the Square provider to select it and advance to credentials.
    fireEvent.click(screen.getByRole('button', { name: /Square/i }))

    // ── Credentials step ─────────────────────────────────────────────────────
    // Square requires one field: Access Token (placeholder 'EAAAl...').
    const tokenInput = screen.getByPlaceholderText('EAAAl...')
    fireEvent.change(tokenInput, { target: { value: 'tok_test_123' } })

    // Click "Connect & Import Data" — triggers async handleConnect which:
    //   1. Sets step to 'connecting' (sync, before any await)
    //   2. Calls connectPos(provider, credentials) — two fetch calls
    //   3. Awaits a 2000ms delay (fake timer)
    //   4. Sets step to 'done'
    fireEvent.click(screen.getByRole('button', { name: /Connect & Import Data/i }))

    // 'connecting' step is set synchronously inside handleConnect before the
    // first await, so it should be visible right after the click + flush.
    await act(async () => {})
    // The connecting-step h2 heading is unique via role=heading
    expect(screen.getByRole('heading', { name: /Connecting to/i })).toBeTruthy()

    // ── Flush connectPos microtask chain ──────────────────────────────────────
    // connectPos makes two sequential fetches (test-connection + connect), each
    // with an await per call and json() resolution — ~5 microtask ticks total.
    // We loop 20 times to reliably drain the entire chain before touching timers.
    await act(async () => {
      for (let i = 0; i < 20; i++) {
        await Promise.resolve()
      }
    })

    // ── ASSERTIONS: auth header on /api/pos/connect ───────────────────────────
    // These can be made as soon as connectPos's microtask chain completes;
    // we do NOT need to wait for the 2s delay timer.

    // Two fetch calls were made: test-connection then connect.
    expect(fetchSpy).toHaveBeenCalledTimes(2)

    const [testConnUrl] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect(testConnUrl).toMatch(/\/api\/pos\/test-connection$/)

    const [connectUrl, connectInit] = fetchSpy.mock.calls[1] as [
      string,
      RequestInit & { headers: Record<string, string> },
    ]
    expect(connectUrl).toMatch(/\/api\/pos\/connect$/)

    // ── REGRESSION GUARD FOR #2 / CA-2 ──────────────────────────────────────
    // connectPos now spreads getAuthHeaders() into the /api/pos/connect request:
    //   headers: { ...(await getAuthHeaders()) }
    // This attaches the Supabase Bearer that require_org_access (CA-2) demands.
    // Removing the spread causes this assertion to fail → 401 on the real backend.
    expect(connectInit.headers['Authorization']).toBe('Bearer test-jwt')
    expect(connectInit.headers['Content-Type']).toBe('application/json')

    // Body fields
    const body = JSON.parse(connectInit.body as string) as Record<string, unknown>
    expect(body['org_id']).toBe('org-123')
    expect(body['pos_system']).toBe('square')

    // ── Advance 2s timer → 'done' step ───────────────────────────────────────
    // The fake 2000ms timer in handleConnect fires, setStep('done') runs.
    vi.advanceTimersByTime(2000)
    await act(async () => {
      for (let i = 0; i < 5; i++) {
        await Promise.resolve()
      }
    })

    expect(screen.getByText(/You're all set!/i)).toBeTruthy()
  })
})
