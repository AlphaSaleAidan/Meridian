/**
 * Sweep §1 + §4.1 regression tests.
 *
 * Locks in two cold-login fixes so future refactors of the React Query
 * layer don't silently re-introduce the "loads only after manual refresh"
 * bug:
 *
 *   §1 — useCanadaLeads must NOT call canadaLeadsService.list() while
 *        repId is undefined. Once a real repId arrives, list() fires
 *        exactly once with that repId.
 *   §4.1 — useCanadaLeadsRealtime must NOT call canadaLeadsService.subscribe
 *          while repId is undefined.
 */
import { describe, it, expect, vi, beforeEach, afterEach, type MockInstance } from 'vitest'
import { renderHook, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { type ReactNode } from 'react'

import { useCanadaLeads, useCanadaLeadsRealtime } from '@/lib/canada-queries'
import { canadaLeadsService } from '@/lib/canada-leads-service'

// Fresh client per test — no shared cache, no defaults that would hide
// the gate (refetchOnMount/staleTime are irrelevant here because the
// assertion is on whether queryFn fires at all).
function makeWrapper() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
    },
  })
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('useCanadaLeads — §1 cold-login gate', () => {
  let listSpy: MockInstance<typeof canadaLeadsService.list>

  beforeEach(() => {
    listSpy = vi.spyOn(canadaLeadsService, 'list').mockResolvedValue([])
  })
  afterEach(() => {
    listSpy.mockRestore()
    cleanup()
  })

  it('does NOT invoke list() while repId is undefined', async () => {
    const Wrapper = makeWrapper()
    const { result } = renderHook(() => useCanadaLeads(undefined), { wrapper: Wrapper })

    // Give React Query a tick to attempt any work — without the gate
    // the queryFn would fire synchronously after mount commit.
    await new Promise(r => setTimeout(r, 50))

    expect(listSpy).not.toHaveBeenCalled()
    // The query is gated, so React Query reports status='pending'
    // with fetchStatus='idle' (no in-flight request).
    expect(result.current.fetchStatus).toBe('idle')
  })

  it('invokes list(repId) exactly once when repId becomes defined', async () => {
    const Wrapper = makeWrapper()
    let repId: string | undefined = undefined
    const { rerender } = renderHook(() => useCanadaLeads(repId), { wrapper: Wrapper })

    // First render — gate held, no call.
    await new Promise(r => setTimeout(r, 25))
    expect(listSpy).not.toHaveBeenCalled()

    // Re-render with a real repId, simulating the navigate-driven
    // re-render committing rep_id from sales-auth context.
    repId = 'rep-uuid-1234'
    rerender()

    await waitFor(() => expect(listSpy).toHaveBeenCalledTimes(1))
    expect(listSpy).toHaveBeenCalledWith('rep-uuid-1234')
  })
})

describe('useCanadaLeadsRealtime — §4.1 cold-login guard', () => {
  let subscribeSpy: MockInstance<typeof canadaLeadsService.subscribe>
  let unsubscribeSpy: MockInstance<typeof canadaLeadsService.unsubscribe>

  beforeEach(() => {
    subscribeSpy = vi.spyOn(canadaLeadsService, 'subscribe').mockReturnValue(null)
    unsubscribeSpy = vi.spyOn(canadaLeadsService, 'unsubscribe').mockImplementation(() => {})
  })
  afterEach(() => {
    subscribeSpy.mockRestore()
    unsubscribeSpy.mockRestore()
    cleanup()
  })

  it('does NOT subscribe while repId is undefined', async () => {
    const Wrapper = makeWrapper()
    renderHook(() => useCanadaLeadsRealtime(undefined), { wrapper: Wrapper })

    await new Promise(r => setTimeout(r, 25))

    expect(subscribeSpy).not.toHaveBeenCalled()
    expect(unsubscribeSpy).not.toHaveBeenCalled()
  })

  it('subscribes exactly once when repId becomes defined', async () => {
    const Wrapper = makeWrapper()
    let repId: string | undefined = undefined
    const { rerender } = renderHook(() => useCanadaLeadsRealtime(repId), { wrapper: Wrapper })

    await new Promise(r => setTimeout(r, 25))
    expect(subscribeSpy).not.toHaveBeenCalled()

    repId = 'rep-uuid-1234'
    rerender()

    await waitFor(() => expect(subscribeSpy).toHaveBeenCalledTimes(1))
    expect(subscribeSpy).toHaveBeenCalledWith('rep-uuid-1234', expect.any(Function))
  })
})
