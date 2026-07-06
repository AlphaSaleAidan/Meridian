/**
 * CameraSetupWizard — #193 auth-header regression guard.
 *
 * The #193 fix changed handleSubmit to spread getAuthHeaders() into the
 * fetch headers:
 *
 *   headers: { ...(await getAuthHeaders()) }
 *
 * getAuthHeaders() returns BOTH 'Content-Type' AND 'Authorization: Bearer <jwt>'.
 * Spreading it attaches the Supabase Bearer that require_org_access (CA-1) demands.
 * Before the fix, only Content-Type was sent → 401.
 *
 * REGRESSION GUARD: If someone removes the `{ ...(await getAuthHeaders()) }` spread
 * and replaces it with a bare `{ 'Content-Type': 'application/json' }`, the
 * 'Authorization' assertion in the primary test case below fails immediately.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, cleanup, fireEvent, act } from '@testing-library/react'
import CameraSetupWizard from '../CameraSetupWizard'

// Provide a deterministic Bearer token from getAuthHeaders().
// supabase is null so no real Supabase calls happen.
vi.mock('@/lib/supabase', () => ({
  supabase: null,
  getAuthHeaders: vi.fn().mockResolvedValue({
    'Content-Type': 'application/json',
    'Authorization': 'Bearer test-jwt',
  }),
}))

afterEach(cleanup)

describe('CameraSetupWizard', () => {
  let fetchSpy: ReturnType<typeof vi.fn>
  let onCompleteSpy: ReturnType<typeof vi.fn>
  let onCloseSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(global as any).fetch = fetchSpy
    onCompleteSpy = vi.fn()
    onCloseSpy = vi.fn()
  })

  it('POST /api/vision/cameras carries Authorization Bearer — regression guard for #193', async () => {
    render(
      <CameraSetupWizard
        orgId="org-123"
        onComplete={onCompleteSpy}
        onClose={onCloseSpy}
      />,
    )

    // ── Step 0: method picker ───────────────────────────────────────────────
    // #264 added a "How is your camera connected?" picker as the first screen.
    // The manual-RTSP card routes into the classic Camera → Zones → Privacy →
    // Confirm wizard this guard exercises. (Replaces the old 'Jetson Nano'
    // Device-step click — that step was removed when the wizard was rebuilt.)
    fireEvent.click(screen.getByText('Manual RTSP'))

    // ── Step 2: Camera ──────────────────────────────────────────────────────
    // Both Camera Name and RTSP URL must be filled for canAdvance() to be true.
    fireEvent.change(
      screen.getByPlaceholderText('e.g., Front Door, Checkout Area'),
      { target: { value: 'Test Camera' } },
    )
    fireEvent.change(
      screen.getByPlaceholderText('rtsp://192.168.1.100:554/stream1'),
      { target: { value: 'rtsp://192.168.1.50:554/stream' } },
    )
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    // ── Step 3: Zones ───────────────────────────────────────────────────────
    // No required fields; canAdvance() always returns true here.
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    // ── Step 4: Privacy ─────────────────────────────────────────────────────
    // compliance_mode defaults to 'anonymous'.
    // The consent checkbox is required for canAdvance() when mode !== 'disabled'.
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /Next/i }))

    // ── Step 5: Confirm — submit ────────────────────────────────────────────
    // handleSubmit() is async; wrap in act so React flushes the fetch chain.
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /Activate Camera/i }))
    })

    // ── Assertions ──────────────────────────────────────────────────────────

    // Exactly one fetch call (no retries on success)
    expect(fetchSpy).toHaveBeenCalledOnce()

    const [url, init] = fetchSpy.mock.calls[0] as [
      string,
      RequestInit & { body: string; headers: Record<string, string> },
    ]

    // URL ends with /api/vision/cameras
    expect(url).toMatch(/\/api\/vision\/cameras$/)

    // Method is POST
    expect(init.method).toBe('POST')

    // ── REGRESSION GUARD FOR #193 ───────────────────────────────────────────
    // Removing `{ ...(await getAuthHeaders()) }` from handleSubmit causes this
    // assertion to fail: the Authorization header would be absent → 401.
    expect(init.headers['Authorization']).toBe('Bearer test-jwt')
    expect(init.headers['Content-Type']).toBe('application/json')

    // Body contains the fields the backend expects
    const body = JSON.parse(init.body) as Record<string, unknown>
    expect(body['org_id']).toBe('org-123')
    expect(body['name']).toBe('Test Camera')
    expect(body['rtsp_url']).toBe('rtsp://192.168.1.50:554/stream')
    expect(body['compliance_mode']).toBe('anonymous')

    // onComplete was called — confirms the res.ok branch ran
    expect(onCompleteSpy).toHaveBeenCalledOnce()
  })

  it('calls onClose and makes no fetch when Cancel is clicked on step 1', () => {
    render(
      <CameraSetupWizard
        orgId="org-123"
        onComplete={onCompleteSpy}
        onClose={onCloseSpy}
      />,
    )
    // At step 0 (Device) the back/cancel footer button renders as "Cancel".
    fireEvent.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(onCloseSpy).toHaveBeenCalledOnce()
    expect(fetchSpy).not.toHaveBeenCalled()
  })
})
