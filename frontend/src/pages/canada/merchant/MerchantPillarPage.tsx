import { Suspense } from 'react'
import { useLocation, useParams, useSearchParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { useMobile } from '@/hooks/useMobile'
import { PortalLoadingSkeleton } from '@/pages/canada/portal/PortalPage'
import ComingSoonBanner from '@/components/ComingSoonBanner'
import type { Pillar } from '@/config/merchantPillars'
import { useAuth } from '@/lib/auth'
import { useTradePack } from '@/config/moduleFlags'
import TradeHomePage from '@/pages/TradeHomePage'

/**
 * Generic pillar shell. Reads `?view=` to pick the active segment, renders a
 * segmented tab bar (hidden when the pillar has a single segment), and lazy-
 * mounts the segment's page component. Each page self-fetches its own data.
 */
export default function MerchantPillarPage({ pillar }: { pillar: Pillar }) {
  const [params, setParams] = useSearchParams()
  const { isMobile } = useMobile()
  const { org } = useAuth()

  // Deep links use a path segment (/camera/live); in-app tabs use ?view=.
  const splat = (useParams()['*'] || '').split('/')[0]

  /**
   * Drop the segments this merchant's TRADE does not use.
   *
   * Pillar-level on/off was too blunt: switching Inventory off for a barbershop
   * to "simplify" it also removed margin tracking, which they very much need —
   * they sell retail and burn through consumables. What they do not need is
   * Menu Matrix. Keeping the pillar and dropping the foreign segment is the
   * difference between a tailored product and a smaller one.
   *
   * A merchant with no trade set loses nothing: packFor() falls back to a pack
   * that hides nothing.
   */
  const pack = useTradePack()
  const hidden = pack.hiddenViews || []

  /**
   * On the demos, home IS the trade workspace.
   *
   * Not a segment beside Revenue — a two-tab bar above it is exactly what
   * made the overview read as "the first tab" rather than the focal screen.
   * The workspace already carries the money band, the trend and the
   * forecast, so Revenue is not lost, it is inlined.
   */
  const { pathname } = useLocation()
  const isDemo = pathname.startsWith('/demo') || pathname.startsWith('/canada/demo')

  /**
   * LIVE for the trades that DRIVE, demo for everyone else.
   *
   * The workspace was demo-only on purpose: a new home screen is not
   * something a paying merchant should discover. That caution still holds for
   * a barbershop, whose existing home page works.
   *
   * It does not hold for a pizza shop or a mobile detailer. Their day is a
   * ROUTE — where every driver is and which drop is about to be late — and
   * the old home page cannot show it at all, so leaving them on it is not the
   * safe option, it is the one that withholds the product they bought.
   * Aidan's call, scoped to `travels` so the blast radius is those two trades
   * rather than every merchant.
   */
  const workspaceHome = (isDemo || pack.travels) && pillar.path === ''

  const forTrade = pillar.segments.filter(
    s => !hidden.includes(`${pillar.path}/${s.view}`) && !(workspaceHome && s.view !== 'home'))
  const segments = isMobile ? forTrade.filter(s => !s.desktopOnly) : forTrade
  const requested = params.get('view') || splat
  const active = segments.find(s => s.view === requested) ?? segments[0]
  const Active = workspaceHome ? TradeHomePage : active.Component

  const selectView = (view: string) => {
    const next = new URLSearchParams(params)
    if (view === segments[0].view) next.delete('view')
    else next.set('view', view)
    setParams(next, { replace: true })
  }

  return (
    <div className="space-y-5">
      {pillar.comingSoon && <ComingSoonBanner label={pillar.label} sampleData={pillar.sampleData} />}
      {segments.length > 1 && (
        <div className="flex items-center gap-1 overflow-x-auto no-scrollbar -mx-1 px-1">
          {segments.map(seg => (
            <button
              key={seg.view}
              onClick={() => selectView(seg.view)}
              className={clsx(
                'px-3.5 py-1.5 rounded-lg text-[13px] font-medium whitespace-nowrap transition-colors',
                seg.view === active.view
                  ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]'
                  : 'text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#111113]',
              )}
            >
              {seg.label}
            </button>
          ))}
        </div>
      )}
      <Suspense fallback={<PortalLoadingSkeleton />}>
        <Active />
      </Suspense>
    </div>
  )
}
