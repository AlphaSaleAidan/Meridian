import { useEffect, useState, useCallback } from 'react'
import { Sparkles, Plus, AlertTriangle, TrendingUp, Check, CalendarDays, CloudRain, Activity } from 'lucide-react'
import { api } from '@/lib/api'
import type { ScheduleShift, Holiday } from '@/lib/agent-data'
import { fmtTime } from './schedule-helpers'

const DAY_LABELS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

type FactorKind = 'peak' | 'holiday' | 'weather'
interface Factor { kind: FactorKind; label: string }
interface Signal { kind: 'holiday' | 'weather'; label: string }

interface Recommendation {
  id: string
  day_of_week: number
  start_time: string
  end_time: string
  role: string
  reason: string
  priority: 'critical' | 'recommended' | 'optional'
  peak_intensity?: number
  factors?: Factor[]
}

const FACTOR_STYLE: Record<FactorKind, { fg: string; Icon: typeof Activity }> = {
  peak: { fg: '#17C5B0', Icon: Activity },
  holiday: { fg: '#7C5CFF', Icon: CalendarDays },
  weather: { fg: '#1A8FD6', Icon: CloudRain },
}

interface Props {
  /** UUID merchant id for live mode; pass empty string in demo to use peakHours fallback */
  merchantId: string
  weekStart: string
  liveMode: boolean
  /** Demo-mode fallback: synthesize recs client-side from the same peak data the grid uses */
  peakHoursFallback: { day: number; hour: number; intensity: number }[]
  /** Current shifts so we can hide recs that are already covered */
  currentShifts: ScheduleShift[]
  /** Called when user accepts a recommendation. Parent creates the shift. */
  onAccept: (rec: { dayOfWeek: number; startTime: string; endTime: string; role: string }) => void
  /** 'CA' enables the weather + holiday agent on the backend; defaults to 'US' (peaks only) */
  country?: string
  /** Demo route — show the full synthesized data set (peaks included) */
  isDemo?: boolean
  /** Real POS connection. When false we can't predict peak demand, so we limit
   *  recommendations to holidays + weather only (never synthesized peaks). */
  posConnected?: boolean
  /** This week's holidays — used to build holiday recs client-side when there's
   *  no live backend connection (non-UUID merchant, POS not yet connected). */
  holidays?: Holiday[]
}

const HOLIDAY_DEFAULT_START = 11
const HOLIDAY_DEFAULT_END = 15

/** Date 'YYYY-MM-DD' → day-of-week with Monday = 0 (matches DAY_LABELS). */
function dowFromISO(iso: string): number {
  const d = new Date(`${iso}T00:00:00`)
  return (d.getDay() + 6) % 7
}

/** Build holiday-only recommendations client-side (no POS, no backend).
 *  Higher-traffic holidays (Boxing Day, Mother's Day) read as critical;
 *  low-traffic federal closures stay optional. */
function holidayRecsClient(holidays: Holiday[], currentShifts: ScheduleShift[]): Recommendation[] {
  if (holidays.length === 0) return []
  const coverage = new Map<string, number>()
  for (const s of currentShifts) {
    if (s.isRecommended) continue
    const sh = parseInt(s.startTime)
    const eh = parseInt(s.endTime)
    for (let h = sh; h < eh; h++) coverage.set(`${s.dayOfWeek}-${h}`, (coverage.get(`${s.dayOfWeek}-${h}`) || 0) + 1)
  }
  const recs: Recommendation[] = []
  for (const h of holidays) {
    const day = dowFromISO(h.date)
    const uncovered = Array.from({ length: HOLIDAY_DEFAULT_END - HOLIDAY_DEFAULT_START }, (_, i) => HOLIDAY_DEFAULT_START + i)
      .some(hr => (coverage.get(`${day}-${hr}`) || 0) < 1)
    if (!uncovered) continue
    const mult = h.trafficMultiplier
    const priority: Recommendation['priority'] = mult >= 1.5 ? 'critical' : mult >= 0.9 ? 'recommended' : 'optional'
    const label = mult >= 1.5 ? `${h.name} surge` : `${h.name} holiday`
    recs.push({
      id: `holiday-${h.date}`,
      day_of_week: day,
      start_time: `${String(HOLIDAY_DEFAULT_START).padStart(2, '0')}:00`,
      end_time: `${String(HOLIDAY_DEFAULT_END).padStart(2, '0')}:00`,
      role: 'any',
      reason: label,
      priority,
      factors: [{ kind: 'holiday', label }],
    })
  }
  const rank: Record<string, number> = { critical: 0, recommended: 1, optional: 2 }
  recs.sort((a, b) => rank[a.priority] - rank[b.priority] || a.day_of_week - b.day_of_week)
  return recs
}

function synthFromPeaks(
  rawPeaks: { day: number; hour: number; intensity: number }[],
  currentShifts: ScheduleShift[],
): Recommendation[] {
  if (rawPeaks.length === 0) return []
  // The demo heatmap emits raw transaction counts (~0–100); the backend emits
  // normalized 0–1. Normalize by the max so thresholds + % labels are sane.
  const maxI = rawPeaks.reduce((m, p) => Math.max(m, p.intensity), 0) || 1
  const scale = maxI > 1.5 ? 1 / maxI : 1
  const peaks = scale === 1 ? rawPeaks : rawPeaks.map(p => ({ ...p, intensity: p.intensity * scale }))
  // Coverage map from existing shifts
  const coverage = new Map<string, number>()
  for (const s of currentShifts) {
    if (s.isRecommended) continue
    const sh = parseInt(s.startTime)
    const eh = parseInt(s.endTime)
    for (let h = sh; h < eh; h++) {
      const k = `${s.dayOfWeek}-${h}`
      coverage.set(k, (coverage.get(k) || 0) + 1)
    }
  }
  // Required coverage by intensity (mirrors backend logic)
  const needed = (i: number) => i >= 0.75 ? 3 : i >= 0.5 ? 2 : i >= 0.25 ? 1 : 0
  // Group uncovered hours by day
  const byDay: Record<number, { hour: number; intensity: number }[]> = {}
  for (const p of peaks) {
    const need = needed(p.intensity)
    if (need <= 0) continue
    const cov = coverage.get(`${p.day}-${p.hour}`) || 0
    if (cov >= need) continue
    if (!byDay[p.day]) byDay[p.day] = []
    byDay[p.day].push({ hour: p.hour, intensity: p.intensity })
  }
  const recs: Recommendation[] = []
  for (const [dayStr, items] of Object.entries(byDay)) {
    const day = Number(dayStr)
    items.sort((a, b) => a.hour - b.hour)
    // Merge contiguous runs of 2+
    let start: number | null = null
    let prev: number | null = null
    let runMax = 0
    const flush = () => {
      if (start !== null && prev !== null && prev - start + 1 >= 2) {
        const intensity = runMax
        const priority = intensity >= 0.75 ? 'critical' : intensity >= 0.5 ? 'recommended' : 'optional'
        recs.push({
          id: `demo-rec-${day}-${start}-${prev}`,
          day_of_week: day,
          start_time: `${String(start).padStart(2, '0')}:00`,
          end_time: `${String(prev + 1).padStart(2, '0')}:00`,
          role: 'any',
          reason: `${intensity >= 0.75 ? 'Peak' : intensity >= 0.5 ? 'High' : 'Moderate'} demand window — ${Math.round(intensity * 100)}% intensity`,
          priority,
          peak_intensity: intensity,
        })
      }
    }
    for (const { hour, intensity } of items) {
      if (start === null) {
        start = prev = hour; runMax = intensity
      } else if (hour === (prev as number) + 1) {
        prev = hour; runMax = Math.max(runMax, intensity)
      } else {
        flush()
        start = prev = hour; runMax = intensity
      }
    }
    flush()
  }
  const rank: Record<string, number> = { critical: 0, recommended: 1, optional: 2 }
  recs.sort((a, b) => rank[a.priority] - rank[b.priority] || a.day_of_week - b.day_of_week || a.start_time.localeCompare(b.start_time))
  return recs
}

const PRIORITY_STYLE: Record<Recommendation['priority'], { fg: string; bg: string; label: string; Icon: typeof AlertTriangle }> = {
  critical: { fg: '#E06B5E', bg: '#E06B5E', label: 'Critical', Icon: AlertTriangle },
  recommended: { fg: '#D4A843', bg: '#D4A843', label: 'Recommended', Icon: TrendingUp },
  optional: { fg: '#A1A1A8', bg: '#A1A1A8', label: 'Optional', Icon: TrendingUp },
}

export default function RecommendationsPanel({
  merchantId, weekStart, liveMode, peakHoursFallback, currentShifts, onAccept, country,
  isDemo = false, posConnected = false, holidays = [],
}: Props) {
  const [recs, setRecs] = useState<Recommendation[] | null>(null)
  const [signals, setSignals] = useState<Signal[]>([])
  const [loading, setLoading] = useState(false)
  const [acceptedIds, setAcceptedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    // Live merchant: the backend decides what to include. It only emits peak
    // windows when there's real POS history, otherwise holidays + weather only.
    if (liveMode) {
      let cancelled = false
      setLoading(true)
      api.scheduleRecommend(merchantId, weekStart, 8, country ? { country } : {})
        .then(res => {
          if (cancelled) return
          setRecs(res.recommendations)
          setSignals(res.signals ?? [])
        })
        .catch(e => {
          console.warn('scheduleRecommend failed:', e)
          if (!cancelled) { setRecs([]); setSignals([]) }
        })
        .finally(() => { if (!cancelled) setLoading(false) })
      return () => { cancelled = true }
    }
    // Demo route: show the full synthesized data set (peaks included).
    if (isDemo) {
      setRecs(synthFromPeaks(peakHoursFallback, currentShifts))
      setSignals([])
      return
    }
    // Real merchant, no live connection. Without POS history we can't predict
    // peak demand — limit recommendations to holidays (client-side) only.
    const hRecs = holidayRecsClient(holidays, currentShifts)
    setRecs(hRecs)
    setSignals(holidays.map(h => ({ kind: 'holiday' as const, label: `${h.name} (${DAY_LABELS[dowFromISO(h.date)]})` })))
  }, [liveMode, isDemo, posConnected, merchantId, weekStart, peakHoursFallback, currentShifts, country, holidays])

  const handleAccept = useCallback((rec: Recommendation) => {
    setAcceptedIds(prev => new Set(prev).add(rec.id))
    onAccept({
      dayOfWeek: rec.day_of_week,
      startTime: rec.start_time.length >= 5 ? rec.start_time.slice(0, 5) : rec.start_time,
      endTime: rec.end_time.length >= 5 ? rec.end_time.slice(0, 5) : rec.end_time,
      role: rec.role || 'any',
    })
  }, [onAccept])

  if (loading) {
    return (
      <div className="rounded-xl border border-[#1F1F23] bg-[#0A0A0B] p-4 flex items-center gap-2 text-xs text-[#A1A1A8]">
        <Sparkles size={14} className="text-[#17C5B0] animate-pulse" />
        Analyzing peak hours…
      </div>
    )
  }
  if (recs === null) return null
  const visible = recs.filter(r => !acceptedIds.has(r.id))

  return (
    <div className="rounded-xl border border-[#1F1F23] bg-[#0A0A0B] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-[#17C5B0]" />
          <h3 className="text-[13px] font-semibold text-[#F5F5F7]">AI Recommendations</h3>
        </div>
        {visible.length === 0 && recs.length > 0 && (
          <span className="text-[11px] text-[#17C5B0] flex items-center gap-1">
            <Check size={11} /> All accepted
          </span>
        )}
      </div>
      {signals.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {signals.map((s, i) => {
            const fs = FACTOR_STYLE[s.kind]
            const Icon = fs.Icon
            return (
              <span
                key={i}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
                style={{ backgroundColor: `${fs.fg}12`, color: fs.fg, border: `1px solid ${fs.fg}30` }}
              >
                <Icon size={10} />
                {s.label}
              </span>
            )
          })}
        </div>
      )}
      {recs.length === 0 ? (
        !liveMode && !isDemo && !posConnected ? (
          <p className="text-[12px] text-[#A1A1A8] leading-relaxed">
            Connect your POS to unlock peak-demand staffing recommendations.
            Until then, holiday &amp; weather tips will appear here automatically.
          </p>
        ) : (
          <p className="text-[12px] text-[#A1A1A8]">
            <Check size={11} className="inline text-[#17C5B0] mr-1" />
            Your schedule covers every detected peak window.
          </p>
        )
      ) : visible.length === 0 ? (
        <p className="text-[12px] text-[#A1A1A8]">Nice — every recommendation is on the schedule.</p>
      ) : (
        <ul className="space-y-2">
          {visible.slice(0, 6).map(rec => {
            const style = PRIORITY_STYLE[rec.priority]
            const Icon = style.Icon
            return (
              <li
                key={rec.id}
                className="flex items-center justify-between gap-3 rounded-lg border border-[#1F1F23] bg-[#111113] px-3 py-2"
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <div
                    className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold"
                    style={{ backgroundColor: `${style.bg}15`, color: style.fg, border: `1px solid ${style.fg}40` }}
                  >
                    <Icon size={10} />
                    {style.label}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] font-medium text-[#F5F5F7]">
                      {DAY_LABELS[rec.day_of_week] || '?'} · {fmtTime(rec.start_time)}–{fmtTime(rec.end_time)}
                    </div>
                    {rec.factors && rec.factors.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-1 mt-0.5">
                        {rec.factors.map((f, i) => {
                          const fs = FACTOR_STYLE[f.kind]
                          const Icon = fs.Icon
                          return (
                            <span key={i} className="flex items-center gap-0.5 text-[10px]" style={{ color: fs.fg }}>
                              <Icon size={9} />
                              {f.label}
                            </span>
                          )
                        })}
                      </div>
                    ) : (
                      <div className="text-[10px] text-[#A1A1A8]/70 truncate">{rec.reason}</div>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleAccept(rec)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-[#17C5B0]/15 border border-[#17C5B0]/30 text-[11px] font-semibold text-[#17C5B0] hover:bg-[#17C5B0]/25 transition-colors shrink-0"
                  aria-label="Add this recommendation as a draft shift"
                >
                  <Plus size={11} />
                  Add
                </button>
              </li>
            )
          })}
          {visible.length > 6 && (
            <li className="text-[11px] text-[#A1A1A8]/50 text-center pt-1">
              +{visible.length - 6} more
            </li>
          )}
        </ul>
      )}
    </div>
  )
}
