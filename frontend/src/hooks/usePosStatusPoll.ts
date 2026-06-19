import { useEffect, useRef, useState } from 'react'

/**
 * Polls the POS connection status after a one-click OAuth round-trip.
 *
 * The OAuth callback redirects back with `?oauth=success&merchant_id=…` but NOT
 * the provider, so (like the Canada merchant wizard's detectConnected) we probe
 * every live provider's /status and return whichever reports connected. Stops as
 * soon as one connects or when `enabled` flips off.
 */
const API_BASE = import.meta.env.VITE_API_URL || ''
const PROVIDERS = ['square', 'clover'] as const

export interface PosStatus {
  connected: boolean
  merchant_id?: string
  status?: string
  last_sync_at?: string | null
  historical_import_complete?: boolean
}

export interface PosConnection {
  provider: string
  status: PosStatus
}

async function fetchStatus(provider: string, orgId: string): Promise<PosStatus | null> {
  try {
    const res = await fetch(`${API_BASE}/api/${provider}/status?org_id=${encodeURIComponent(orgId)}`)
    if (!res.ok) return null
    return (await res.json()) as PosStatus
  } catch {
    return null
  }
}

export function usePosStatusPoll(
  orgId: string | undefined,
  enabled: boolean,
  intervalMs = 4000,
): PosConnection | null {
  const [conn, setConn] = useState<PosConnection | null>(null)
  const ref = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!enabled || !orgId) {
      if (ref.current) { clearInterval(ref.current); ref.current = null }
      return
    }
    let active = true
    const tick = async () => {
      for (const p of PROVIDERS) {
        const st = await fetchStatus(p, orgId)
        if (active && st?.connected) {
          setConn({ provider: p, status: st })
          if (ref.current) { clearInterval(ref.current); ref.current = null }
          return
        }
      }
    }
    tick()
    ref.current = setInterval(tick, intervalMs)
    return () => { active = false; if (ref.current) { clearInterval(ref.current); ref.current = null } }
  }, [orgId, enabled, intervalMs])

  return conn
}
