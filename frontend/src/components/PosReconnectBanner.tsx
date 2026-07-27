import { useEffect, useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { useOrgId } from '@/hooks/useOrg'

// OAuth providers that can be re-linked in one click. Toast (manual token) is
// intentionally excluded — it has no authorize flow.
const STATUS_URL: Record<string, string> = {
  square: '/api/square/status',
  clover: '/api/clover/status',
}
const AUTHORIZE_URL: Record<string, string> = {
  square: '/api/square/authorize',
  clover: '/api/clover/authorize',
}
const LABEL: Record<string, string> = { square: 'Square', clover: 'Clover' }

/**
 * Shows a "Your POS key was rotated — reconnect" prompt when a connected POS
 * token has been rotated/revoked (backend flips pos_connections.status →
 * 'needs_reconnect' when a refresh fails). Reconnecting re-runs OAuth, which
 * mints a fresh token and flips the status back to 'connected'. Renders nothing
 * when every connection is healthy.
 */
export default function PosReconnectBanner() {
  const orgId = useOrgId()
  const apiBase = import.meta.env.VITE_API_URL || ''
  const [stale, setStale] = useState<string | null>(null)

  useEffect(() => {
    if (!orgId || orgId === 'demo') return
    let active = true
    ;(async () => {
      for (const provider of ['square', 'clover']) {
        try {
          const r = await fetch(
            `${apiBase}${STATUS_URL[provider]}?org_id=${encodeURIComponent(orgId)}`,
          )
          const d = await r.json()
          if (d?.status === 'needs_reconnect') {
            if (active) setStale(provider)
            return
          }
        } catch {
          /* status check is best-effort — never block the page */
        }
      }
    })()
    return () => {
      active = false
    }
  }, [orgId, apiBase])

  if (!stale) return null

  const ret = encodeURIComponent(window.location.pathname + window.location.search)
  const reconnectUrl =
    `${apiBase}${AUTHORIZE_URL[stale]}?org_id=${encodeURIComponent(orgId)}&return_to=${ret}`
  const name = LABEL[stale] || 'POS'

  return (
    <div className="mb-4 flex flex-col gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-400" />
        <div>
          <p className="text-sm font-semibold text-[#F5F5F7]">
            Your {name} POS key was rotated
          </p>
          <p className="text-xs text-[#A1A1A8]">
            Orders can’t reach your kitchen until you reconnect. It takes a few seconds.
          </p>
        </div>
      </div>
      <a
        href={reconnectUrl}
        target="_blank"
        rel="noopener"
        className="shrink-0 rounded-lg bg-amber-400 px-4 py-2 text-center text-sm font-semibold text-black transition-colors hover:bg-amber-300"
      >
        Reconnect {name}
      </a>
    </div>
  )
}
