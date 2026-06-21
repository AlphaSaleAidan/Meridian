import { useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import { Loader2, CheckCircle2, AlertCircle, UtensilsCrossed } from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { phoneService, type MenuBuildStatus as MenuStatus } from '@/lib/phone-service'
import { getMenuBuildDemo } from '@/lib/phone-orders-demo-data'

/**
 * Visible progress for the AUTO MENU-BUILDER.
 *
 * When a merchant connects their POS, the backend auto-builds the phone agent's
 * menu from the POS catalog (read-only). This polls GET /api/phone/menu/status
 * and shows: "Building your menu from your POS…" with a spinner, the item count
 * climbing, then "✓ N items ready" with a few sample items.
 *
 * Demo (org 'demo'): never touches the backend — runs a synthetic build that
 * animates up to a synthetic catalog so the experience is visible offline.
 */

const POLL_MS = 2500

export default function MenuBuildStatus() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()

  const [status, setStatus] = useState<MenuStatus>({ state: 'idle', item_count: 0, sample: [] })
  // Smooth, climbing count for the building animation (UI-only).
  const [displayCount, setDisplayCount] = useState(0)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)

  // ── Demo: synthetic build animation, no backend ──
  useEffect(() => {
    if (!isDemo) return
    const target = getMenuBuildDemo('midtown-kitchen')
    setStatus({ state: 'building', item_count: 0, sample: [] })
    setDisplayCount(0)
    let n = 0
    const id = setInterval(() => {
      n += Math.max(1, Math.round(target.item_count / 8))
      if (n >= target.item_count) {
        n = target.item_count
        clearInterval(id)
        setStatus({ state: 'ready', item_count: target.item_count, sample: target.sample })
      }
      setDisplayCount(Math.min(n, target.item_count))
    }, 320)
    return () => clearInterval(id)
  }, [isDemo])

  // ── Real: poll the backend until the build settles ──
  useEffect(() => {
    if (isDemo || !orgId) return
    let cancelled = false

    const poll = async () => {
      const s = await phoneService.getMenuStatus(orgId)
      if (cancelled) return
      setStatus(s)
      setDisplayCount(prev => (s.item_count > prev ? s.item_count : prev))
      // Stop polling once the build has settled (ready/error/idle-with-items).
      if (s.state !== 'building' && timer.current) {
        clearInterval(timer.current)
        timer.current = null
      }
    }

    void poll()
    timer.current = setInterval(poll, POLL_MS)
    return () => {
      cancelled = true
      if (timer.current) { clearInterval(timer.current); timer.current = null }
    }
  }, [isDemo, orgId])

  // Nothing to show before a POS is connected / a build has ever run.
  if (status.state === 'idle' && status.item_count === 0) return null

  const building = status.state === 'building'
  const ready = status.state === 'ready'
  const error = status.state === 'error'
  const count = building ? displayCount : status.item_count

  return (
    <div
      className={clsx(
        'card p-4 flex items-start gap-3 transition-colors',
        building && 'border-[#1A8FD6]/20',
        ready && 'border-[#17C5B0]/20',
        error && 'border-red-400/20',
      )}
      data-walkthrough="menu-build-status"
      aria-live="polite"
    >
      <div
        className={clsx(
          'w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0',
          building && 'bg-[#1A8FD6]/10',
          ready && 'bg-[#17C5B0]/10',
          error && 'bg-red-400/10',
        )}
      >
        {building && <Loader2 size={18} className="text-[#1A8FD6] animate-spin" />}
        {ready && <CheckCircle2 size={18} className="text-[#17C5B0]" />}
        {error && <AlertCircle size={18} className="text-red-400" />}
      </div>

      <div className="flex-1 min-w-0">
        {building && (
          <>
            <p className="text-sm font-semibold text-[#F5F5F7]">Building your menu from your POS…</p>
            <p className="text-xs text-[#A1A1A8] mt-0.5">
              Reading your catalog (read-only) —{' '}
              <span className="font-mono text-[#1A8FD6]">{count}</span> items so far
            </p>
            <div className="mt-2 h-1.5 rounded-full bg-[#1F1F23] overflow-hidden">
              <div className="h-full rounded-full bg-[#1A8FD6] animate-pulse" style={{ width: '60%' }} />
            </div>
          </>
        )}

        {ready && (
          <>
            <p className="text-sm font-semibold text-[#F5F5F7]">
              ✓ <span className="font-mono text-[#17C5B0]">{count}</span> menu items ready
            </p>
            <p className="text-xs text-[#A1A1A8] mt-0.5">
              Pulled from your POS — your phone agent can now talk about your real menu.
            </p>
            {status.sample.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {status.sample.map((name, i) => (
                  <span
                    key={`${name}-${i}`}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#111113] border border-[#1F1F23] text-[10px] text-[#A1A1A8]"
                  >
                    <UtensilsCrossed size={9} className="text-[#17C5B0]" /> {name}
                  </span>
                ))}
              </div>
            )}
          </>
        )}

        {error && (
          <>
            <p className="text-sm font-semibold text-[#F5F5F7]">Couldn’t build your menu automatically</p>
            <p className="text-xs text-[#A1A1A8] mt-0.5">
              We’ll keep trying on the next sync — or add items manually in Phone Orders settings.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
