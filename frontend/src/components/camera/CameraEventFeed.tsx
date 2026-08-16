/**
 * The event recorder, in the camera pillar.
 *
 * Everything else on this page is a count — walk-ins, occupancy, queue wait.
 * Counts are read at the end of a week. This is the part that is read now: a
 * spill by the machine, a case opened with no sale behind it, four minutes on
 * a handset at the till.
 *
 * It is a WORKLIST, not a chart. Every row carries the one sentence that says
 * why it is worth interrupting somebody for, and two buttons that close it.
 * An alert with no way to close it and no reason attached is an alert people
 * learn to scroll past, which is worse than not having it.
 *
 * ANONYMOUS. A row says someone at the counter was on a phone. It never says
 * who, and there is no column in the table that could.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle, Check, Clock, Droplets, EyeOff, PackageOpen,
  Smartphone, DoorOpen, Moon, X,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useOrgId } from '@/hooks/useOrg'
import {
  EVENT_KINDS, fetchVisionEvents, resolveVisionEvent,
  type EventKind, type EventSummary, type VisionEvent,
} from '@/lib/vision-events'

const ICONS: Record<EventKind, typeof Droplets> = {
  spill: Droplets,
  product_loss: PackageOpen,
  phone_use: Smartphone,
  unattended: EyeOff,
  blocked_exit: DoorOpen,
  after_hours: Moon,
}

const TONE = {
  critical: { text: 'text-[#E5484D]', chip: 'border-[#E5484D]/40 bg-[#E5484D]/10 text-[#E5484D]' },
  warning: { text: 'text-[#F5A524]', chip: 'border-[#F5A524]/40 bg-[#F5A524]/10 text-[#F5A524]' },
  info: { text: 'text-[#A1A1A8]', chip: 'border-[#1F1F23] bg-[#111113] text-[#A1A1A8]' },
} as const

function ago(iso: string): string {
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function duration(sec: number | null): string | null {
  if (!sec) return null
  if (sec < 60) return `${sec}s`
  return `${Math.round(sec / 60)} min`
}

export default function CameraEventFeed() {
  const orgId = useOrgId()
  const [events, setEvents] = useState<VisionEvent[]>([])
  const [summary, setSummary] = useState<EventSummary | null>(null)
  const [kind, setKind] = useState<EventKind | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [showClosed, setShowClosed] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetchVisionEvents(orgId, { kind })
      setEvents(res.events)
      setSummary(res.summary)
      setFailed(false)
    } catch {
      // An empty feed and a feed we could not load mean opposite things —
      // "nothing happened" versus "we do not know". Never show the first
      // when the second is true.
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }, [orgId, kind])

  useEffect(() => { void load() }, [load])

  const act = async (id: string, status: 'resolved' | 'dismissed') => {
    // Optimistic: the operator is standing up, and a spinner on a two-button
    // decision is a worse trade than a rare re-render.
    setEvents((prev) => prev.map((e) => (e.id === id ? { ...e, status } : e)))
    try {
      await resolveVisionEvent(orgId, id, status)
    } catch {
      void load()
    }
  }

  const visible = showClosed ? events : events.filter((e) => e.status === 'new')

  return (
    <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-[#F5F5F7]">What the cameras saw</h2>
          <p className="mt-0.5 text-xs text-[#6B6B73]">
            Spills, stock leaving without a sale, phones at the counter. Nobody
            is identified — the cameras record what happened, never who.
          </p>
        </div>
        {summary && summary.open > 0 && (
          <span className={clsx(
            'rounded-full border px-2.5 py-1 text-xs font-semibold',
            summary.criticalOpen > 0 ? TONE.critical.chip : TONE.warning.chip,
          )}>
            {summary.open} open
            {summary.criticalOpen > 0 && ` · ${summary.criticalOpen} urgent`}
          </span>
        )}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        <FilterChip active={kind === null} onClick={() => setKind(null)} label="Everything" />
        {EVENT_KINDS.map((k) => (
          <FilterChip
            key={k.key}
            active={kind === k.key}
            onClick={() => setKind(k.key)}
            label={k.label}
            count={summary?.byKind?.[k.key]}
          />
        ))}
        <button
          onClick={() => setShowClosed((v) => !v)}
          className="ml-auto text-xs text-[#6B6B73] transition-colors hover:text-[#A1A1A8]"
        >
          {showClosed ? 'Hide closed' : 'Show closed'}
        </button>
      </div>

      <div className="mt-4 space-y-2">
        {loading ? (
          <p className="py-8 text-center text-sm text-[#6B6B73]">Loading…</p>
        ) : failed ? (
          <p className="py-8 text-center text-sm text-[#E5484D]">
            Could not load events. This is not the same as nothing happening.
          </p>
        ) : visible.length === 0 ? (
          <p className="py-8 text-center text-sm text-[#6B6B73]">
            {showClosed
              ? 'Nothing recorded in the last two days.'
              : 'Nothing open. Everything the cameras flagged has been dealt with.'}
          </p>
        ) : (
          visible.map((e) => {
            const Icon = ICONS[e.kind] || AlertTriangle
            const tone = TONE[e.severity]
            const closed = e.status !== 'new'
            const dur = duration(e.durationSec)
            return (
              <article
                key={e.id}
                className={clsx(
                  'rounded-lg border p-4 transition-opacity',
                  closed ? 'border-[#1F1F23] bg-[#0E0E11] opacity-60' : 'border-[#1F1F23] bg-[#0A0A0B]',
                )}
              >
                <div className="flex items-start gap-3">
                  <span className={clsx(
                    'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border',
                    tone.chip,
                  )}>
                    <Icon className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <h3 className={clsx('text-sm font-semibold', closed ? 'text-[#A1A1A8]' : 'text-[#F5F5F7]')}>
                        {e.title}
                      </h3>
                      {e.zone && (
                        <span className="text-xs text-[#A1A1A8]">{e.zone}</span>
                      )}
                      <span className="flex items-center gap-1 text-xs text-[#6B6B73]">
                        <Clock className="h-3 w-3" />
                        {ago(e.detectedAt)}
                        {dur && ` · ${dur}`}
                      </span>
                    </div>

                    {e.detail && (
                      <p className="mt-1 text-sm leading-relaxed text-[#A1A1A8]">{e.detail}</p>
                    )}
                    {/* The sentence that justifies the interruption. */}
                    <p className={clsx('mt-1 text-xs', tone.text)}>{e.why}</p>

                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      {closed ? (
                        <span className="text-xs text-[#6B6B73]">
                          {e.status === 'dismissed' ? 'Dismissed — the camera was wrong' : 'Dealt with'}
                        </span>
                      ) : (
                        <>
                          <button
                            onClick={() => act(e.id, 'resolved')}
                            className="flex items-center gap-1.5 rounded-lg bg-[#17C5B0] px-3 py-1.5 text-xs font-semibold text-[#0A0A0B] transition-colors hover:bg-[#17C5B0]/90"
                          >
                            <Check className="h-3.5 w-3.5" /> Dealt with
                          </button>
                          {/* Kept apart from "dealt with" on purpose: one means
                              the mop came out, the other means the camera was
                              wrong, and only the second says a detector is not
                              worth leaving on. */}
                          <button
                            onClick={() => act(e.id, 'dismissed')}
                            className="flex items-center gap-1.5 rounded-lg bg-[#1F1F23] px-3 py-1.5 text-xs font-medium text-[#A1A1A8] transition-colors hover:bg-[#2A2A2F] hover:text-[#F5F5F7]"
                          >
                            <X className="h-3.5 w-3.5" /> Not a real one
                          </button>
                        </>
                      )}
                      {e.confidence != null && (
                        <span className="ml-auto text-[11px] text-[#6B6B73]">
                          {Math.round(e.confidence * 100)}% confidence
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </article>
            )
          })
        )}
      </div>
    </section>
  )
}

function FilterChip({ active, onClick, label, count }: {
  active: boolean
  onClick: () => void
  label: string
  count?: number
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors',
        active
          ? 'border-[#1A8FD6]/50 bg-[#1A8FD6]/10 text-[#1A8FD6]'
          : 'border-[#1F1F23] text-[#6B6B73] hover:text-[#A1A1A8]',
      )}
    >
      {label}
      {count != null && count > 0 && (
        <span className="ml-1.5 text-[10px] opacity-70">{count}</span>
      )}
    </button>
  )
}
