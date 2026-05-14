import { useState, useEffect } from 'react'
import { useOrgId } from './useOrg'

const API_BASE = import.meta.env.VITE_API_URL || ''

export function useInsightsCooldown() {
  const orgId = useOrgId()
  const [coolingDown, setCoolingDown] = useState(false)
  const [secondsRemaining, setSecondsRemaining] = useState(0)
  const [readyAt, setReadyAt] = useState<string | null>(null)

  useEffect(() => {
    if (orgId === 'demo') return

    async function check() {
      try {
        const res = await fetch(
          `${API_BASE}/api/dashboard/insights/cooldown?org_id=${orgId}`,
        )
        if (!res.ok) return
        const data = await res.json()
        setCoolingDown(data.cooling_down)
        setSecondsRemaining(data.seconds_remaining)
        setReadyAt(data.ready_at)
      } catch {
        /* swallow network errors silently */
      }
    }

    check()
    const interval = setInterval(check, 60_000) // re-check every minute
    return () => clearInterval(interval)
  }, [orgId])

  // Local countdown between server checks
  useEffect(() => {
    if (!coolingDown || secondsRemaining <= 0) return
    const timer = setInterval(() => {
      setSecondsRemaining(s => {
        if (s <= 1) {
          setCoolingDown(false)
          return 0
        }
        return s - 1
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [coolingDown, secondsRemaining])

  const formatTime = () => {
    if (!coolingDown) return null
    const h = Math.floor(secondsRemaining / 3600)
    const m = Math.floor((secondsRemaining % 3600) / 60)
    const s = secondsRemaining % 60
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
  }

  return { coolingDown, secondsRemaining, readyAt, timeDisplay: formatTime() }
}
