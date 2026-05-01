import { clsx } from 'clsx'

interface FunnelStage {
  stage: string
  count: number
  pct: number
}

interface Props {
  funnel: FunnelStage[]
  dropOffs?: { from: string; to: string; lost: number; drop_pct: number }[]
}

const stageColors = [
  'bg-[#1A8FD6]',
  'bg-[#1A8FD6]/80',
  'bg-[#17C5B0]',
  'bg-[#17C5B0]/70',
  'bg-[#4FE3C1]',
]

export default function FootTrafficFunnel({ funnel, dropOffs }: Props) {
  if (!funnel.length) {
    return (
      <div className="card p-8 text-center text-sm text-[#A1A1A8]/50">
        No funnel data yet. Connect cameras to start tracking.
      </div>
    )
  }

  const maxCount = funnel[0]?.count || 1

  return (
    <div className="space-y-1">
      {funnel.map((stage, i) => {
        const widthPct = Math.max(10, (stage.count / maxCount) * 100)
        const dropOff = dropOffs?.[i]
        return (
          <div key={stage.stage}>
            <div className="flex items-center gap-3">
              <div className="w-32 sm:w-40 text-right">
                <span className="text-xs text-[#A1A1A8] font-medium">{stage.stage}</span>
              </div>
              <div className="flex-1 relative">
                <div
                  className={clsx(
                    'h-8 rounded-lg flex items-center px-3 transition-all duration-500',
                    stageColors[i] || 'bg-[#1F1F23]',
                  )}
                  style={{ width: `${widthPct}%` }}
                >
                  <span className="text-xs font-bold text-white font-mono">
                    {stage.count.toLocaleString()}
                  </span>
                </div>
              </div>
              <div className="w-14 text-right">
                <span className="text-xs text-[#A1A1A8]/60 font-mono">{stage.pct}%</span>
              </div>
            </div>
            {dropOff && dropOff.lost > 0 && (
              <div className="flex items-center gap-3 pl-[calc(8rem+0.75rem)] sm:pl-[calc(10rem+0.75rem)]">
                <div className="text-[10px] text-red-400/60 font-mono py-0.5">
                  ↓ {dropOff.lost.toLocaleString()} lost ({dropOff.drop_pct}%)
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
