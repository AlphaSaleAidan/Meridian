import { clsx } from 'clsx'

interface Props {
  zoneVisits: Record<string, number>
  zoneAvgDwell: Record<string, number>
  zonePolygons?: Record<string, any>
  totalVisits: number
}

const zoneColors: Record<string, { bg: string; text: string; border: string }> = {
  entrance: { bg: 'bg-[#1A8FD6]/20', text: 'text-[#1A8FD6]', border: 'border-[#1A8FD6]/40' },
  checkout: { bg: 'bg-[#4FE3C1]/20', text: 'text-[#4FE3C1]', border: 'border-[#4FE3C1]/40' },
  bar: { bg: 'bg-[#7C5CFF]/20', text: 'text-[#7C5CFF]', border: 'border-[#7C5CFF]/40' },
  tables: { bg: 'bg-amber-500/20', text: 'text-amber-400', border: 'border-amber-500/40' },
  menu_board: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/40' },
  browse: { bg: 'bg-pink-500/20', text: 'text-pink-400', border: 'border-pink-500/40' },
  sidewalk: { bg: 'bg-[#A1A1A8]/10', text: 'text-[#A1A1A8]', border: 'border-[#A1A1A8]/30' },
}

function getZoneColor(zone: string) {
  const key = Object.keys(zoneColors).find(k => zone.toLowerCase().includes(k))
  return zoneColors[key || ''] || { bg: 'bg-[#1F1F23]', text: 'text-[#A1A1A8]', border: 'border-[#1F1F23]' }
}

function heatLevel(visits: number, max: number): string {
  const ratio = visits / Math.max(max, 1)
  if (ratio > 0.7) return 'ring-2 ring-red-500/40'
  if (ratio > 0.4) return 'ring-2 ring-amber-500/30'
  if (ratio > 0.2) return 'ring-1 ring-[#1A8FD6]/20'
  return ''
}

export default function ZoneHeatmap({ zoneVisits, zoneAvgDwell, totalVisits }: Props) {
  const zones = Object.keys(zoneVisits)
  if (!zones.length) {
    return (
      <div className="card p-8 text-center text-sm text-[#A1A1A8]/50">
        No zone data yet. Configure zones in camera settings.
      </div>
    )
  }

  const maxVisits = Math.max(...Object.values(zoneVisits))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {zones.map(zone => {
          const visits = zoneVisits[zone] || 0
          const dwell = zoneAvgDwell[zone] || 0
          const pct = Math.round((visits / Math.max(totalVisits, 1)) * 100)
          const colors = getZoneColor(zone)
          const heat = heatLevel(visits, maxVisits)

          return (
            <div
              key={zone}
              className={clsx(
                'card p-4 rounded-xl border transition-all duration-200',
                colors.bg, colors.border, heat,
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <span className={clsx('text-xs font-semibold uppercase tracking-wider', colors.text)}>
                  {zone.replace(/_/g, ' ')}
                </span>
                <span className="text-[10px] text-[#A1A1A8]/50 font-mono">{pct}%</span>
              </div>
              <p className="text-lg font-bold text-[#F5F5F7] font-mono">{visits.toLocaleString()}</p>
              <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">visits</p>
              {dwell > 0 && (
                <div className="mt-2 pt-2 border-t border-[#1F1F23]">
                  <p className="text-[10px] text-[#A1A1A8]/50">
                    avg dwell: <span className="text-[#F5F5F7] font-mono">{Math.round(dwell)}s</span>
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>

      <div className="flex items-center gap-4 text-[10px] text-[#A1A1A8]/40">
        <span>Heat: </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-[#1F1F23]" /> Low
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-[#1F1F23] ring-1 ring-[#1A8FD6]/20" /> Medium
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-[#1F1F23] ring-2 ring-amber-500/30" /> High
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded bg-[#1F1F23] ring-2 ring-red-500/40" /> Hot
        </span>
      </div>
    </div>
  )
}
