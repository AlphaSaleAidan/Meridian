import { formatCents } from '@/lib/format'

/** A day×hour demand cell. `revenue`/`transactions` are optional so live
 *  schedule data (intensity-only) can render the same heatmap as the analytics
 *  page (which has the full POS figures for the hover tooltip). */
export interface HeatmapCell {
  day: number
  hour: number
  intensity: number
  revenue?: number
  transactions?: number
}

const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const dayFull = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
const hourLabels = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12a'
  if (i < 12) return `${i}a`
  if (i === 12) return '12p'
  return `${i - 12}p`
})

// Peak-hours intensity ramp: quiet = blue, busy = teal (low → high).
const LEGEND = ['#1F1F23', 'rgba(26, 143, 214, 0.15)', 'rgba(26, 143, 214, 0.35)', 'rgba(23, 197, 176, 0.5)', 'rgba(23, 197, 176, 0.8)']

function cellColor(normalized: number): string {
  if (normalized <= 0) return LEGEND[0]
  if (normalized < 0.25) return LEGEND[1]
  if (normalized < 0.5) return LEGEND[2]
  if (normalized < 0.75) return LEGEND[3]
  return LEGEND[4]
}

function tipFor(cell: HeatmapCell | undefined, dayLabel: string, hour: number, normalized: number): string {
  if (!cell || cell.intensity <= 0) return ''
  return cell.transactions != null
    ? `${dayLabel} ${hourLabels[hour]}: ${cell.transactions} txns, ${formatCents(cell.revenue ?? 0)}`
    : `${dayLabel} ${hourLabels[hour]}: ${Math.round(normalized * 100)}% of peak`
}

function GradientLegend() {
  return (
    <div className="flex items-center justify-center gap-2 mt-4">
      <span className="text-[9px] text-[#A1A1A8]/40">Low</span>
      <div className="flex gap-px">
        {LEGEND.map((c, i) => <div key={i} className="w-6 h-3 rounded-sm" style={{ backgroundColor: c }} />)}
      </div>
      <span className="text-[9px] text-[#A1A1A8]/40">High</span>
    </div>
  )
}

/** Shared demand heatmap. Two modes:
 *   - week grid (default): 7 days × 24h — the Peak Hours analytics page.
 *   - single day (`day` set): a VERTICAL list of the selected day's 24 hours
 *     (hour label + bar), so it fits a narrow column beside the Schedule board
 *     and rotates as you change the day. */
export default function PeakHoursHeatmap({
  cells,
  title = 'Weekly Transaction Heatmap',
  caption,
  compact = false,
  day,
}: {
  cells: HeatmapCell[]
  title?: string
  caption?: string
  compact?: boolean
  /** When set (0=Mon..6=Sun), render only that day's 24h as a vertical list. */
  day?: number
}) {
  const single = day != null

  if (single) {
    const dayCells = cells.filter(c => c.day === day)
    const max = Math.max(0, ...dayCells.map(c => c.intensity))
    // Only show the hours the business is actually open (non-zero demand) so the
    // list stays short — fall back to all 24 if a day has no data at all.
    const active = Array.from({ length: 24 }, (_, h) => h).filter(h => (dayCells.find(c => c.hour === h)?.intensity || 0) > 0)
    const hours = active.length ? active : Array.from({ length: 24 }, (_, h) => h)
    const heading = `${title}${title.includes('—') ? '' : ' —'} ${dayFull[day] ?? ''}`.trim()
    return (
      <div className="card p-4 sm:p-5" data-walkthrough="peak-heatmap">
        <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">{heading}</h3>
        {caption && <p className="text-[11px] text-[#A1A1A8]/60 mb-3">{caption}</p>}
        <div className="space-y-0.5">
          {hours.map(hour => {
            const cell = dayCells.find(c => c.hour === hour)
            const normalized = max > 0 ? (cell?.intensity || 0) / max : 0
            const tip = tipFor(cell, dayNames[day], hour, normalized)
            return (
              <div key={hour} className="flex items-center gap-2" title={tip}>
                <span className="w-7 flex-shrink-0 text-right text-[9px] text-[#A1A1A8]/50">{hourLabels[hour]}</span>
                <div className="flex-1 h-3 rounded-[3px]" style={{ backgroundColor: cellColor(normalized) }} />
              </div>
            )
          })}
        </div>
        <GradientLegend />
      </div>
    )
  }

  // ── Week grid ──
  const maxIntensity = Math.max(0, ...cells.map(c => c.intensity))
  const labelEvery = compact ? 6 : 2
  return (
    <div className="card p-4 sm:p-5" data-walkthrough="peak-heatmap">
      <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">{title}</h3>
      {caption && <p className="text-[11px] text-[#A1A1A8]/60 mb-3">{caption}</p>}
      <div className={compact ? '' : 'overflow-x-auto'}>
        <div className={compact ? '' : 'min-w-[700px]'}>
          <div className="flex items-end gap-px mb-1 pl-10">
            {hourLabels.map((h, i) => (
              <div key={i} className="flex-1 text-center text-[8px] text-[#A1A1A8]/30">{i % labelEvery === 0 ? h : ''}</div>
            ))}
          </div>
          <div className="space-y-px">
            {dayNames.map((dn, dayIdx) => (
              <div key={dn} className="flex items-center gap-px">
                <div className="w-10 text-right pr-2 text-[10px] text-[#A1A1A8]/50 flex-shrink-0">{dn}</div>
                {Array.from({ length: 24 }, (_, hour) => {
                  const cell = cells.find(c => c.day === dayIdx && c.hour === hour)
                  const normalized = maxIntensity > 0 ? (cell?.intensity || 0) / maxIntensity : 0
                  const tip = tipFor(cell, dn, hour, normalized)
                  return (
                    <div key={hour} className="flex-1 aspect-[2/1] rounded-[2px] group relative cursor-default"
                      style={{ backgroundColor: cellColor(normalized) }}>
                      {tip && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#F5F5F7] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          {tip}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
          <GradientLegend />
        </div>
      </div>
    </div>
  )
}
