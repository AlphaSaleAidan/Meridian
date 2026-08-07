import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { Lightbulb, ArrowUpCircle, AlertTriangle, TrendingUp, Info } from 'lucide-react'
import { phoneService } from '@/lib/phone-service'
import type { PhoneRecommendation } from '@/lib/phone-service'

/**
 * Advisory call-telemetry recommendations (READ-ONLY).
 *
 * Consumes GET /api/phone/recommendations/{merchantId} — the feedback loop over
 * voice_call_endings telemetry — and renders each derived signal as a card with
 * the evidence behind it and a *suggested* change. Nothing here mutates a
 * merchant's cap or fee; every card is clearly advisory. A human decides.
 *
 * Hidden entirely in demo mode and when there are no recommendations, so it only
 * appears when live telemetry actually surfaces something worth acting on.
 */

interface Props {
  merchantId: string
  isDemo: boolean
  /** Lookback window in days (matches the dashboard period). */
  days?: number
}

const SIGNAL_STYLE: Record<string, { icon: typeof Lightbulb; color: string; bg: string; border: string; label: string }> = {
  RAISE_CAP: {
    icon: ArrowUpCircle,
    color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', border: 'border-[#1A8FD6]/20',
    label: 'Call cap',
  },
  AGENT_QUALITY: {
    icon: AlertTriangle,
    color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/20',
    label: 'Agent quality',
  },
  PRICING_HEADROOM: {
    icon: TrendingUp,
    color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', border: 'border-[#17C5B0]/20',
    label: 'Pricing',
  },
}

const FALLBACK_STYLE = {
  icon: Info, color: 'text-[#A1A1A8]', bg: 'bg-[#1F1F23]', border: 'border-[#1F1F23]', label: 'Signal',
}

/** Humanize an evidence key + value for the read-only evidence chips. */
function fmtEvidence(key: string, value: number): string | null {
  switch (key) {
    case 'cutoff_without_order':
      return `${value} calls cut off before an order`
    case 'cutoff_without_order_rate':
      return `${Math.round(value * 100)}% of calls`
    case 'projected_orders_recoverable_per_week':
      return `~${value} orders/wk recoverable`
    case 'current_cap_minutes':
      return `cap ${value} min`
    case 'silence':
      return `${value} silent`
    case 'error':
      return `${value} errors`
    case 'quality_loss_rate':
      return `${Math.round(value * 100)}% lost`
    case 'avg_duration_seconds':
      return `avg ${Math.floor(value / 60)}:${String(value % 60).padStart(2, '0')}`
    case 'included_minutes':
      return `${value} min included`
    case 'overage_cents_per_min':
      // 0 = call time isn't billed; rendering "0¢/min overage" would imply a
      // charge exists. Drop the chip entirely in that case.
      return value > 0 ? `${value}¢/min overage` : null
    case 'total_calls':
      return `${value} calls`
    default:
      return null
  }
}

function RecCard({ rec }: { rec: PhoneRecommendation }) {
  const s = SIGNAL_STYLE[rec.signal] ?? FALLBACK_STYLE
  const Icon = s.icon
  const chips = Object.entries(rec.evidence)
    .map(([k, v]) => fmtEvidence(k, v))
    .filter((x): x is string => Boolean(x))
  return (
    <div className={clsx('rounded-lg border p-3', s.bg, s.border)}>
      <div className="flex items-start gap-2.5">
        <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0', s.bg)}>
          <Icon size={15} className={s.color} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={clsx('text-[9px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded', s.bg, s.color)}>{s.label}</span>
            <span className="text-[9px] text-[#6B6B72] uppercase tracking-wide">advisory</span>
          </div>
          <p className="text-xs font-semibold text-[#F5F5F7] mt-1.5">{rec.title}</p>
          <p className="text-[11px] text-[#A1A1A8] mt-1 leading-relaxed">{rec.suggested_change}</p>
          {chips.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {chips.map((c, i) => (
                <span key={i} className="text-[9px] font-mono text-[#C7C7CC] bg-[#111113] border border-[#1F1F23] rounded px-1.5 py-0.5">{c}</span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function CallRecommendationsCard({ merchantId, isDemo, days = 7 }: Props) {
  const [recs, setRecs] = useState<PhoneRecommendation[] | null>(null)

  useEffect(() => {
    if (isDemo || !merchantId) { setRecs(null); return }
    let cancelled = false
    phoneService.getRecommendations(merchantId, days).then(res => {
      if (!cancelled) setRecs(res?.recommendations ?? [])
    })
    return () => { cancelled = true }
  }, [merchantId, isDemo, days])

  // Only render when live telemetry produced at least one recommendation.
  if (isDemo || !recs || recs.length === 0) return null

  return (
    <div className="card p-4 border-[#7C5CFF]/15" data-walkthrough="phone-recommendations">
      <div className="flex items-center gap-2 mb-1">
        <Lightbulb size={14} className="text-[#7C5CFF]" />
        <h3 className="text-sm font-semibold text-[#F5F5F7]">Telemetry Suggestions</h3>
      </div>
      <p className="text-[10px] text-[#A1A1A8] mb-3 leading-relaxed">
        Read-only signals from your call outcomes. Nothing changes automatically — review and decide.
      </p>
      <div className="space-y-2.5">
        {recs.map((r, i) => <RecCard key={`${r.signal}-${i}`} rec={r} />)}
      </div>
    </div>
  )
}
