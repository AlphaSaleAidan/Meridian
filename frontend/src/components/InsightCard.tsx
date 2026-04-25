import { clsx } from 'clsx'

function parseMarkdown(text: string) {
  // Parse *bold* text and \n newlines
  const parts = text.split(/(\*[^*]+\*|\n)/g)
  return parts.map((part, i) => {
    if (part === '\n') return <br key={i} />
    if (part.startsWith('*') && part.endsWith('*')) {
      return <strong key={i} className="text-[#F5F5F7] font-semibold">{part.slice(1, -1)}</strong>
    }
    return <span key={i}>{part}</span>
  })
}
import {
  Lightbulb, TrendingUp, Users, Tag, Package, AlertTriangle,
  BarChart3, Thermometer,
} from 'lucide-react'
import type { Insight } from '@/lib/api'
import { formatCents, formatRelative, formatConfidence } from '@/lib/format'

const typeConfig: Record<string, { icon: typeof Lightbulb; color: string; bg: string }> = {
  money_left: { icon: TrendingUp, color: 'text-[#4FE3C1]', bg: 'bg-[#4FE3C1]/10' },
  product_recommendation: { icon: Package, color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10' },
  staffing: { icon: Users, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  pricing: { icon: Tag, color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10' },
  inventory: { icon: Package, color: 'text-orange-400', bg: 'bg-orange-500/10' },
  anomaly: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
  seasonal: { icon: Thermometer, color: 'text-[#4FE3C1]', bg: 'bg-[#4FE3C1]/10' },
  benchmark: { icon: BarChart3, color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10' },
  general: { icon: Lightbulb, color: 'text-[#A1A1A8]', bg: 'bg-[#1F1F23]' },
}

interface Props {
  insight: Insight
  compact?: boolean
}

export default function InsightCard({ insight, compact = false }: Props) {
  const config = typeConfig[insight.type] || typeConfig.general
  const Icon = config.icon

  return (
    <div className="card-hover p-4 group">
      <div className="flex items-start gap-3">
        <div className={clsx(
          'p-2 rounded-lg flex-shrink-0 transition-all duration-300 group-hover:scale-110',
          config.bg
        )}>
          <Icon size={16} className={config.color} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <h4 className="text-sm font-semibold text-[#F5F5F7] leading-tight">
              {insight.title}
            </h4>
            {insight.impact_cents != null && insight.impact_cents !== 0 && (
              <span className={clsx(
                'text-xs font-bold font-mono flex-shrink-0',
                insight.impact_cents > 0 ? 'text-[#4FE3C1]' : 'text-red-400'
              )}>
                {insight.impact_cents > 0 ? '+' : ''}{formatCents(insight.impact_cents)}/mo
              </span>
            )}
          </div>
          {!compact && (
            <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
              {parseMarkdown(insight.summary)}
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
            <span className="text-[11px] text-[#A1A1A8]/50 font-mono">
              {formatConfidence(insight.confidence)}
            </span>
            <span className="text-[11px] text-[#A1A1A8]/40 hidden sm:inline">
              {formatRelative(insight.created_at)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
