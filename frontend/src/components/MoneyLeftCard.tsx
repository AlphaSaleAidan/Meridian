import { DollarSign, TrendingDown, AlertTriangle } from 'lucide-react'
import type { MoneyLeftScore } from '@/lib/api'
import { formatCents, formatRelative } from '@/lib/format'

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
      <div className="card p-6 glow-blue">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-xl bg-meridian-700/20 flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-meridian-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Money Left on the Table</h3>
            <p className="text-xs text-slate-400">No data yet — connect your POS to get started</p>
          </div>
        </div>
        <div className="text-3xl font-bold text-slate-600">—</div>
      </div>
    )
  }

  const total = score.total_score_cents
  const components = score.components || {}
  const sorted = Object.entries(components).sort(
    ([, a], [, b]) => (b.amount_cents || 0) - (a.amount_cents || 0)
  )

  return (
    <div className="card p-6 glow-blue border-meridian-800/40">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-meridian-700/20 flex items-center justify-center">
            <DollarSign className="w-5 h-5 text-meridian-400" />
          </div>
          <div>
            <h3 className="font-semibold text-white">Money Left on the Table</h3>
            <p className="text-xs text-slate-400">
              Estimated monthly opportunity • Updated {formatRelative(score.scored_at)}
            </p>
          </div>
        </div>
      </div>

      <div className="text-4xl font-extrabold text-meridian-400 mb-5">
        {formatCents(total)}
        <span className="text-base font-medium text-slate-400 ml-2">/month</span>
      </div>

      {sorted.length > 0 && (
        <div className="space-y-2.5">
          {sorted.map(([key, comp]) => {
            const meta = componentLabels[key] || { label: key.replace(/_/g, ' '), icon: DollarSign }
            const Icon = meta.icon
            const pct = total > 0 ? ((comp.amount_cents || 0) / total * 100) : 0

            return (
              <div key={key} className="flex items-center gap-3">
                <Icon size={14} className="text-slate-500 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-medium text-slate-300 capitalize">{meta.label}</span>
                    <span className="text-xs font-semibold text-slate-200">{formatCents(comp.amount_cents)}</span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-meridian-600 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(pct, 100)}%` }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
