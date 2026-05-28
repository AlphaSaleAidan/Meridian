import { useState, useEffect, useCallback, useRef } from 'react'
import { contentApi } from '@/lib/content-api'
import { useAuth } from '@/lib/auth'
import type { ContentDashboardData } from '@/lib/content-demo-data'

export function useContentDashboard() {
  const { org } = useAuth()
  const orgId = org?.org_id || 'demo'
  const [data, setData] = useState<ContentDashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const load = useCallback(async () => {
    try {
      setLoading(prev => (!data ? true : prev))
      const result = await contentApi.dashboard(orgId)
      setData(result)
      setError(null)
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Failed to load content data'
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [orgId]) // eslint-disable-line react-hooks/exhaustive-deps

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

  return { data, loading, error, refetch: load }
}
