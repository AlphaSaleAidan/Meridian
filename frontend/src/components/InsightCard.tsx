import { clsx } from 'clsx'
import {
  Lightbulb, TrendingUp, Users, Tag, Package, AlertTriangle,
  BarChart3, Thermometer, Award, HelpCircle,
} from 'lucide-react'
import type { Insight } from '@/lib/api'
import { formatCents, formatRelative, formatConfidence } from '@/lib/format'

const typeConfig: Record<string, { icon: typeof Lightbulb; color: string; bg: string }> = {
  money_left: { icon: TrendingUp, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
  product_recommendation: { icon: Package, color: 'text-blue-400', bg: 'bg-blue-500/10' },
  staffing: { icon: Users, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  pricing: { icon: Tag, color: 'text-purple-400', bg: 'bg-purple-500/10' },
  inventory: { icon: Package, color: 'text-orange-400', bg: 'bg-orange-500/10' },
  anomaly: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
  seasonal: { icon: Thermometer, color: 'text-cyan-400', bg: 'bg-cyan-500/10' },
  benchmark: { icon: BarChart3, color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  general: { icon: Lightbulb, color: 'text-slate-400', bg: 'bg-slate-500/10' },
}

interface Props {
  insight: Insight
  compact?: boolean
}

export default function InsightCard({ insight, compact = false }: Props) {
  const config = typeConfig[insight.type] || typeConfig.general
  const Icon = config.icon

  return (
    <div className="card-hover p-4">
      <div className="flex items-start gap-3">
        <div className={clsx('p-2 rounded-lg flex-shrink-0', config.bg)}>
          <Icon size={16} className={config.color} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-sm font-semibold text-white leading-tight">
              {insight.title}
            </h4>
            {insight.impact_cents != null && insight.impact_cents !== 0 && (
              <span className={clsx(
                'text-xs font-bold flex-shrink-0',
                insight.impact_cents > 0 ? 'text-emerald-400' : 'text-red-400'
              )}>
                {insight.impact_cents > 0 ? '+' : ''}{formatCents(insight.impact_cents)}/mo
              </span>
            )}
          </div>
          {!compact && (
            <p className="text-xs text-slate-400 mt-1 leading-relaxed">
              {insight.summary}
            </p>
          )}
          <div className="flex items-center gap-3 mt-2">
            <span className={clsx('badge', {
              'badge-blue': insight.action_status === 'pending',
              'badge-amber': insight.action_status === 'viewed',
              'badge-green': insight.action_status === 'accepted' || insight.action_status === 'completed',
              'badge-red': insight.action_status === 'dismissed',
            })}>
              {insight.action_status}
            </span>
            {insight.confidence != null && (
              <span className="text-xs text-slate-500">
                {formatConfidence(insight.confidence)} confidence
              </span>
            )}
            <span className="text-xs text-slate-600">
              {formatRelative(insight.created_at)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
