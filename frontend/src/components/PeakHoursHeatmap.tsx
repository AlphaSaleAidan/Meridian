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

// Colours + thresholds match the Schedule "Expected traffic" key
// (PositionsBoard trafficTier) so the two legends read as one language.
const EMPTY = '#1F1F23'
const TIERS = [
  { color: '#E06B5E', label: 'Busy' },  // > 0.6
  { color: '#D4A843', label: 'Med' },   // > 0.33
  { color: '#17C5B0', label: 'Easy' },  // > 0
]

function tierColor(normalized: number): string {
  if (normalized <= 0) return EMPTY
  if (normalized > 0.6) return TIERS[0].color
  if (normalized > 0.33) return TIERS[1].color
  return TIERS[2].color
}

function tipFor(cell: HeatmapCell | undefined, dayLabel: string, hour: number, normalized: number): string {
  if (!cell || cell.intensity <= 0) return ''
  return cell.transactions != null
    ? `${dayLabel} ${hourLabels[hour]}: ${cell.transactions} txns, ${formatCents(cell.revenue ?? 0)}`
    : `${dayLabel} ${hourLabels[hour]}: ${Math.round(normalized * 100)}% of peak`
}

function Legend() {
  return (
    <div className="flex items-center justify-center gap-3 mt-3">
      {TIERS.map(t => (
        <span key={t.label} className="flex items-center gap-1">
          <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: t.color }} />
          <span className="text-[9px] text-[#A1A1A8]/50">{t.label}</span>
        </span>
      ))}
    </div>
  )
}

/** Shared demand heatmap, in the Busy/Med/Easy palette of the Schedule traffic
 *  key. Two modes:
 *   - week grid (default): 7 days × 24h — the Peak Hours analytics page.
 *   - single day (`day` set): one 24h strip for the selected day, so it fits
 *     beside the Schedule board and rotates as you change the day. */
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
  /** When set (0=Mon..6=Sun), render only that day's 24h strip. */
  day?: number
}) {
  const single = day != null

  if (single) {
    const dayCells = cells.filter(c => c.day === day)
    const max = Math.max(0, ...dayCells.map(c => c.intensity))
    const heading = `${title}${title.includes('—') ? '' : ' —'} ${dayFull[day] ?? ''}`.trim()
    return (
      <div className="card p-4 sm:p-5" data-walkthrough="peak-heatmap">
        <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">{heading}</h3>
        {caption && <p className="text-[11px] text-[#A1A1A8]/60 mb-3">{caption}</p>}
        <div className="flex items-end gap-px mb-1">
          {hourLabels.map((h, i) => (
            <div key={i} className="flex-1 text-center text-[8px] text-[#A1A1A8]/30">{i % 3 === 0 ? h : ''}</div>
          ))}
        </div>
        <div className="flex items-center gap-px">
          {Array.from({ length: 24 }, (_, hour) => {
            const cell = dayCells.find(c => c.hour === hour)
            const normalized = max > 0 ? (cell?.intensity || 0) / max : 0
            const tip = tipFor(cell, dayNames[day], hour, normalized)
            return (
              <div key={hour} className="flex-1 h-7 rounded-[2px] group relative cursor-default"
                style={{ backgroundColor: tierColor(normalized) }}>
                {tip && (
                  <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#F5F5F7] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                    {tip}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <Legend />
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
                      style={{ backgroundColor: tierColor(normalized) }}>
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
          <Legend />
        </div>
      </div>
    </div>
  )
}
