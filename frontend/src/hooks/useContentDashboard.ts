import { useState, useEffect, useCallback, useRef } from 'react'
import { contentApi } from '@/lib/content-api'
import { api } from '@/lib/api'
import { useAuth } from '@/lib/auth'
import type { ContentDashboardData } from '@/lib/content-demo-data'

// Poll the balance more often than the rest of the dashboard so a fresh
// Square invoice payment shows up within seconds of the customer returning
// from checkout.
const BALANCE_POLL_MS = 15_000

export function useContentDashboard() {
  const { org } = useAuth()
  const orgId = org?.org_id || 'demo'
  const [data, setData] = useState<ContentDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const balanceIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const mergeLiveBalance = useCallback(async (base: ContentDashboardData) => {
    // Demo orgs are served by content-api directly with mock credits;
    // skip the live fetch so we don't paper a "0 balance" over the demo.
    if (orgId === 'demo') return base
    try {
      const live = await api.creditBalance(orgId)
      return {
        ...base,
        credits: {
          balance: live.balance,
          lifetime_used: base.credits?.lifetime_used ?? 0,
          free_granted: base.credits?.free_granted ?? 0,
        },
      }
    } catch {
      // Surface the underlying dashboard data even if /api/credits/balance
      // is temporarily down. Better stale balance than blank screen.
      return base
    }
  }, [orgId])

  const load = useCallback(async () => {
    try {
      setLoading(prev => (!data ? true : prev))
      const result = await contentApi.dashboard(orgId)
      const withBalance = await mergeLiveBalance(result)
      setData(withBalance)
      setError(null)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to load content data'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [orgId, mergeLiveBalance]) // eslint-disable-line react-hooks/exhaustive-deps

  const refreshBalance = useCallback(async () => {
    if (orgId === 'demo') return
    try {
      const live = await api.creditBalance(orgId)
      setData(prev => prev ? {
        ...prev,
        credits: {
          balance: live.balance,
          lifetime_used: prev.credits?.lifetime_used ?? 0,
          free_granted: prev.credits?.free_granted ?? 0,
        },
      } : prev)
    } catch {
      // ignore; the next poll will retry
    }
  }, [orgId])

  useEffect(() => {
    load()
  }, [load])

  // Poll every 30s when active generation jobs exist
  useEffect(() => {
    if (data?.activeJobs && data.activeJobs.length > 0) {
      intervalRef.current = setInterval(load, 30000)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [data?.activeJobs?.length, load])

  // Balance-only polling so credit purchases land on the UI quickly
  // without re-fetching the whole content dashboard.
  useEffect(() => {
    if (orgId === 'demo') return
    balanceIntervalRef.current = setInterval(refreshBalance, BALANCE_POLL_MS)
    return () => {
      if (balanceIntervalRef.current) clearInterval(balanceIntervalRef.current)
    }
  }, [orgId, refreshBalance])

  return { data, loading, error, refetch: load, refreshBalance }
}
