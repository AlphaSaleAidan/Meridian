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
const hourLabels = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12a'
  if (i < 12) return `${i}a`
  if (i === 12) return '12p'
  return `${i - 12}p`
})

const LEGEND = ['#1F1F23', 'rgba(26, 143, 214, 0.15)', 'rgba(26, 143, 214, 0.35)', 'rgba(23, 197, 176, 0.5)', 'rgba(23, 197, 176, 0.8)']

function cellColor(normalized: number): string {
  if (normalized === 0) return LEGEND[0]
  if (normalized < 0.25) return LEGEND[1]
  if (normalized < 0.5) return LEGEND[2]
  if (normalized < 0.75) return LEGEND[3]
  return LEGEND[4]
}

/** Shared weekly demand heatmap — used by the Peak Hours analytics page and,
 *  side-by-side, by the Schedule page so the auto-fill's demand signal is
 *  visible while you build the week. */
export default function PeakHoursHeatmap({
  cells,
  title = 'Weekly Transaction Heatmap',
  caption,
  compact = false,
}: {
  cells: HeatmapCell[]
  title?: string
  caption?: string
  /** Fit all 24h into a narrow column (no horizontal scroll) — for the
   *  side-by-side panel on the Schedule page. */
  compact?: boolean
}) {
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
            {dayNames.map((day, dayIdx) => (
              <div key={day} className="flex items-center gap-px">
                <div className="w-10 text-right pr-2 text-[10px] text-[#A1A1A8]/50 flex-shrink-0">{day}</div>
                {Array.from({ length: 24 }, (_, hour) => {
                  const cell = cells.find(c => c.day === dayIdx && c.hour === hour)
                  const intensity = cell?.intensity || 0
                  const normalized = maxIntensity > 0 ? intensity / maxIntensity : 0
                  const tip = cell && cell.intensity > 0
                    ? (cell.transactions != null
                        ? `${day} ${hourLabels[hour]}: ${cell.transactions} txns, ${formatCents(cell.revenue ?? 0)}`
                        : `${day} ${hourLabels[hour]}: ${Math.round(normalized * 100)}% of peak`)
                    : ''
                  return (
                    <div
                      key={hour}
                      className="flex-1 aspect-[2/1] rounded-[2px] group relative cursor-default"
                      style={{ backgroundColor: cellColor(normalized) }}
                    >
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
          <div className="flex items-center justify-center gap-2 mt-4">
            <span className="text-[9px] text-[#A1A1A8]/40">Low</span>
            <div className="flex gap-px">
              {LEGEND.map((c, i) => (
                <div key={i} className="w-6 h-3 rounded-sm" style={{ backgroundColor: c }} />
              ))}
            </div>
            <span className="text-[9px] text-[#A1A1A8]/40">High</span>
          </div>
        </div>
      </div>
    </div>
  )
}
