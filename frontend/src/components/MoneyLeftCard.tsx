import { DollarSign, TrendingDown, AlertTriangle } from 'lucide-react'
import type { MoneyLeftScore } from '@/lib/api'
import { formatCents, formatRelative } from '@/lib/format'
import DashboardTiltCard from './DashboardTiltCard'

interface Props {
  score: MoneyLeftScore | null
}

const componentLabels: Record<string, { label: string; icon: typeof DollarSign }> = {
  underpriced_products: { label: 'Underpriced Products', icon: TrendingDown },
  dead_stock: { label: 'Dead Stock', icon: AlertTriangle },
  staffing_waste: { label: 'Staffing Waste', icon: AlertTriangle },
  peak_hour_missed: { label: 'Peak Hour Gaps', icon: TrendingDown },
}

export default function MoneyLeftCard({ score }: Props) {
  if (!score) {
    return (
      <DashboardTiltCard className="card p-6 glow-violet" glowColor="rgba(124, 92, 255, 0.08)">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-[#7C5CFF]/10 flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-[#7C5CFF]" />
          </div>
          <div>
            <h3 className="font-semibold text-[#F5F5F7]">Money Left on the Table</h3>
            <p className="text-xs text-[#A1A1A8]">No data yet — connect your POS to get started</p>
          </div>
        </div>
        <div className="text-3xl font-bold font-mono text-[#A1A1A8]/30">—</div>
      </DashboardTiltCard>
    )
  }

  const total = score.total_score_cents
  const components = score.components || {}
  const sorted = Object.entries(components).sort(
    ([, a], [, b]) => (b.amount_cents || 0) - (a.amount_cents || 0)
  )

  return (
    <DashboardTiltCard
      className="card p-6 glow-violet border-[#7C5CFF]/10"
      glowColor="rgba(124, 92, 255, 0.08)"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#7C5CFF]/10 flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-[#7C5CFF]" />
          </div>
          <div>
            <h3 className="font-semibold text-[#F5F5F7]">Money Left on the Table</h3>
            <p className="text-xs text-[#A1A1A8]">
              Estimated monthly opportunity • Updated {formatRelative(score.scored_at)}
            </p>
          </div>
        </div>
      </div>

      <div className="text-4xl font-extrabold font-mono text-[#7C5CFF] mb-5">
        {formatCents(total)}
        <span className="text-base font-medium text-[#A1A1A8] ml-2">/month</span>
      </div>

      {sorted.length > 0 && (
        <div className="space-y-3">
          {sorted.map(([key, comp]) => {
            const config = componentLabels[key] || { label: key.replace(/_/g, ' '), icon: DollarSign }
            const Icon = config.icon
            const pct = total > 0 ? ((comp.amount_cents || 0) / total * 100) : 0

            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <Icon size={12} className="text-[#A1A1A8]" />
                    <span className="text-xs text-[#A1A1A8] capitalize">{config.label}</span>
                  </div>
                  <span className="text-xs font-semibold font-mono text-[#F5F5F7]">
                    {formatCents(comp.amount_cents || 0)}
                  </span>
                </div>
                <div className="h-1.5 bg-[#1F1F23] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[#7C5CFF] to-[#4FE3C1] transition-all duration-700"
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      )}
    </DashboardTiltCard>
  )
}
