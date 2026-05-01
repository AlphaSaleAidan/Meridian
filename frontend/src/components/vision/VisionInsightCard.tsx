import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Eye, TrendingUp, Users, AlertTriangle, Heart,
  MapPin, Smile, Sun, UserCheck, ShoppingBag,
  ChevronDown, ChevronUp,
} from 'lucide-react'

interface VisionInsight {
  type: string
  title: string
  body: string
  data?: Record<string, any>
  confidence: number
  period: string
  generated_at?: string
}

interface Props {
  insight: VisionInsight
}

const typeConfig: Record<string, { icon: typeof Eye; color: string; bg: string }> = {
  passerby_missed: { icon: Eye, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  conversion_trend: { icon: TrendingUp, color: 'text-[#4FE3C1]', bg: 'bg-[#4FE3C1]/10' },
  gender_skew: { icon: Users, color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10' },
  daypart_demographic: { icon: Sun, color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10' },
  churn_risk: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
  sentiment_decline: { icon: Smile, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  zone_imbalance: { icon: MapPin, color: 'text-orange-400', bg: 'bg-orange-500/10' },
  menu_confusion: { icon: MapPin, color: 'text-orange-400', bg: 'bg-orange-500/10' },
  daypart_gap: { icon: Sun, color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10' },
  loyalty_opportunity: { icon: Heart, color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10' },
  window_shopper_conversion: { icon: ShoppingBag, color: 'text-[#4FE3C1]', bg: 'bg-[#4FE3C1]/10' },
  new_vs_returning: { icon: UserCheck, color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10' },
  non_customer_traffic: { icon: Eye, color: 'text-amber-400', bg: 'bg-amber-500/10' },
  low_repeat_rate: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/10' },
}

function confidenceColor(c: number): string {
  if (c >= 0.8) return 'bg-[#4FE3C1]/10 text-[#4FE3C1] border-[#4FE3C1]/20'
  if (c >= 0.6) return 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20'
  return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
}

export default function VisionInsightCard({ insight }: Props) {
  const [showData, setShowData] = useState(false)
  const config = typeConfig[insight.type] || { icon: Eye, color: 'text-[#A1A1A8]', bg: 'bg-[#1F1F23]' }
  const Icon = config.icon

  return (
    <div className="card p-4 hover:bg-[#111113]/80 transition-colors group">
      <div className="flex items-start gap-3">
        <div className={clsx('p-2 rounded-lg flex-shrink-0', config.bg)}>
          <Icon size={16} className={config.color} />
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-semibold text-[#F5F5F7] leading-tight">
            {insight.title}
          </h4>
          <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
            {insight.body}
          </p>

          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className={clsx(
              'text-[10px] font-medium px-1.5 py-0.5 rounded border',
              confidenceColor(insight.confidence),
            )}>
              {Math.round(insight.confidence * 100)}% confidence
            </span>
            <span className="text-[10px] text-[#A1A1A8]/40 font-mono">
              {insight.period}
            </span>
            {insight.data && Object.keys(insight.data).length > 0 && (
              <button
                onClick={() => setShowData(!showData)}
                className="flex items-center gap-0.5 text-[10px] text-[#A1A1A8]/40 hover:text-[#A1A1A8]/70 transition-colors"
              >
                data {showData ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
              </button>
            )}
          </div>

          {showData && insight.data && (
            <div className="mt-2 p-2 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
              <pre className="text-[10px] text-[#A1A1A8]/50 font-mono overflow-x-auto whitespace-pre-wrap">
                {JSON.stringify(insight.data, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
