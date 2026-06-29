/**
 * CanadaPortalAccountsPage — ZERO-POS rep-portal guard.
 *
 * The ZERO-POS doctrine (docs/CANADA_PORTAL_TRUTH.md) mandates that the rep
 * portal is READ-ONLY with respect to POS connections. Reps can SEE whether a
 * customer has synced but they cannot trigger, manage, or label a POS
 * connection themselves.
 *
 * This test locks in three properties:
 *
 *   A. No "Sync POS Data" button is rendered. Adding one would give reps
 *      a POS trigger they must not have (ZERO-POS doctrine, PR #96 / docs
 *      CANADA_PORTAL_TRUTH.md).
 *
 *   B. No "POS Connected" kanban label is rendered. That label conflates the
 *      internal stage name `pos_connected` with a UI action; the read-only
 *      badge is the only surface allowed.
 *
 *   C. A "Synced successfully" read-only badge DOES render for an active
 *      account (is_active=true). This is the approved read-only status indicator.
 *
 * REGRESSION GUARD: future edits that add a "Sync POS" button or "POS
 * Connected" label will immediately fail assertions A and B.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import CanadaPortalAccountsPage from '../canada/portal/CanadaPortalAccountsPage'
import type { Deal } from '@/lib/canada-sales-demo-data'

// ── Mock @/lib/supabase ────────────────────────────────────────────────────
// Suppresses the "Missing VITE_SUPABASE_URL" console warning; getAuthHeaders
// is only called on button clicks, not on initial render.
vi.mock('@/lib/supabase', () => ({
  supabase: null,
  getAuthHeaders: vi.fn().mockResolvedValue({ 'Content-Type': 'application/json' }),
}))

// ── Mock @/components/Toast ────────────────────────────────────────────────
vi.mock('@/components/Toast', () => ({
  useToast: () => ({ toast: vi.fn() }),
  ToastProvider: ({ children }: { children: ReactNode }) => children,
}))

// ── Mock @/lib/sales-auth ──────────────────────────────────────────────────
// Provide a fully authenticated rep so CanadaPortalAccountsPage renders the
// accounts list rather than an unauthenticated fallback.
const FAKE_REP = {
  rep_id: 'rep-zero-pos-guard',
  name: 'Zero POS Rep',
  email: 'rep@zero-pos-guard.local',
  phone: null,
  commission_rate: 70,
  recruiter: null,
  is_active: true,
  total_earned: 0,
  total_paid: 0,
  created_at: '2026-01-01T00:00:00Z',
  portal_context: 'canada' as const,
}

vi.mock('@/lib/sales-auth', () => ({
  useSalesAuth: () => ({
    ready: true,
    authenticated: true,
    rep: FAKE_REP,
    login: vi.fn(),
    signup: vi.fn(),
    resetPassword: vi.fn(),
    logout: vi.fn(),
  }),
}))

// ── Fake closed-won deal ──────────────────────────────────────────────────
// deriveClientsFromLeads maps 'closed_won' → is_active:true, which renders the
// "Synced successfully" badge. The pos_connected field is false (no notes
// mentioning a POS provider) — that is intentional: even without POS notes,
// the badge still appears for active accounts.
const ACTIVE_DEAL: Deal = {
  id: 'deal-zero-pos-guard-001',
  business_name: 'Accounts Test Kitchen',
  contact_name: 'Jordan Account',
  contact_email: 'acct@zero-pos-test.local',
  contact_phone: '5551230000',
  vertical: 'restaurant',
  stage: 'closed_won',
  monthly_value: 600,
  commission_rate: 70,
  expected_close_date: '2026-01-01',
  notes: '',
  source: '',
  city: '',
  province: '',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

// ── Mock @/lib/canada-queries ──────────────────────────────────────────────
// Return the pre-built deal directly. useCanadaLeadsRealtime is a no-op here;
// its real implementation subscribes to Supabase realtime which is not needed.
vi.mock('@/lib/canada-queries', () => ({
  useCanadaLeads: () => ({ data: [ACTIVE_DEAL], isLoading: false, error: null }),
  useCanadaLeadsRealtime: () => undefined,
}))

afterEach(() => {
  cleanup()
})

/** Render the page inside the minimal providers it needs. */
function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <CanadaPortalAccountsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CanadaPortalAccountsPage — ZERO-POS rep portal guard', () => {
  it(
    'A — renders NO "Sync POS Data" button (reps cannot trigger POS connections)',
    () => {
      renderPage()
      // The ZERO-POS doctrine: reps must never see a POS trigger on the accounts page.
      expect(screen.queryByText(/sync\s+pos\s+data/i)).toBeNull()
      expect(screen.queryByRole('button', { name: /sync\s+pos/i })).toBeNull()
    },
  )

  it(
    'B — renders NO "POS Connected" kanban label (internal stage name must not leak into UI)',
    () => {
      renderPage()
      // "pos_connected" is an internal stage enum value; it must not appear as a
      // visible label in the rep-facing UI — only the "Synced successfully" badge is allowed.
      expect(screen.queryByText(/pos\s+connected/i)).toBeNull()
    },
  )

  it(
    'C — renders "Synced successfully" read-only badge for an active account',
    () => {
      renderPage()
      // The approved read-only status indicator. Appears when is_active=true
      // (set by deriveClientsFromLeads for closed_won / pos_connected stages).
      expect(screen.getByText(/synced successfully/i)).toBeTruthy()
    },
  )
})
