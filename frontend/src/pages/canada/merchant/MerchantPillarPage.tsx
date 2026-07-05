import { Suspense } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { useMobile } from '@/hooks/useMobile'
import { PortalLoadingSkeleton } from '@/pages/canada/portal/PortalPage'
import type { Pillar } from '@/config/merchantPillars'

/**
 * Generic pillar shell. Reads `?view=` to pick the active segment, renders a
 * segmented tab bar (hidden when the pillar has a single segment), and lazy-
 * mounts the segment's page component. Each page self-fetches its own data.
 */
export default function MerchantPillarPage({ pillar }: { pillar: Pillar }) {
  const [params, setParams] = useSearchParams()
  const { isMobile } = useMobile()

  // Deep links use a path segment (/camera/live); in-app tabs use ?view=.
  const splat = (useParams()['*'] || '').split('/')[0]
  const segments = isMobile ? pillar.segments.filter(s => !s.desktopOnly) : pillar.segments
  const requested = params.get('view') || splat
  const active = segments.find(s => s.view === requested) ?? segments[0]
  const Active = active.Component

  const selectView = (view: string) => {
    const next = new URLSearchParams(params)
    if (view === segments[0].view) next.delete('view')
    else next.set('view', view)
    setParams(next, { replace: true })
  }

  return (
    <div className="space-y-5">
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
