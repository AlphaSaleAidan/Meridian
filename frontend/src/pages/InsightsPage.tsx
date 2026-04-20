import { useState } from 'react'
import { clsx } from 'clsx'
import { Filter } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCentsCompact } from '@/lib/format'
import InsightCard from '@/components/InsightCard'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import ScrollReveal from '@/components/ScrollReveal'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const insightTypes = [
  { key: '', label: 'All' },
  { key: 'money_left', label: 'Money Left' },
  { key: 'product_recommendation', label: 'Products' },
  { key: 'pricing', label: 'Pricing' },
  { key: 'staffing', label: 'Staffing' },
  { key: 'anomaly', label: 'Anomalies' },
  { key: 'seasonal', label: 'Seasonal' },
]

export default function InsightsPage() {
  const [typeFilter, setTypeFilter] = useState('')
  const insights = useApi(() => api.insights(ORG_ID, 50), [])

  if (insights.loading) return <LoadingPage />
  if (insights.error) return <ErrorState message={insights.error} onRetry={insights.refetch} />

  const data = insights.data!
  const filtered = typeFilter
    ? data.insights.filter(i => i.type === typeFilter)
    : data.insights

  const totalImpact = filtered.reduce((s, i) => s + (i.impact_cents || 0), 0)
  const actionable = filtered.filter(i => i.action_status === 'pending').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">AI Insights</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            <span className="font-mono">{data.total}</span> active • <span className="font-mono">{actionable}</span> actionable • <span className="font-mono">{formatCentsCompact(totalImpact)}</span>/mo impact
          </p>
        </div>
      </ScrollReveal>

      {/* Filters — scrollable on mobile */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="flex items-center gap-2 overflow-x-auto pb-1 -mx-4 px-4 sm:mx-0 sm:px-0 no-scrollbar">
          <Filter size={14} className="text-[#A1A1A8]/50 flex-shrink-0" />
          {insightTypes.map(t => (
            <button
              key={t.key}
              onClick={() => setTypeFilter(t.key)}
              className={clsx(
                'px-3 py-2 sm:py-1.5 text-xs font-medium rounded-full transition-all duration-200 whitespace-nowrap border',
                typeFilter === t.key
                  ? 'bg-[#7C5CFF]/10 text-[#7C5CFF] border-[#7C5CFF]/20 shadow-[0_0_12px_rgba(124,92,255,0.1)]'
                  : 'text-[#A1A1A8] border-[#1F1F23] hover:text-[#F5F5F7] hover:border-[#2A2A30]'
              )}
            >
              {t.label}
            </button>
          ))}
        </div>
      </ScrollReveal>

      {/* Insights List */}
      {filtered.length > 0 ? (
        <ScrollReveal variant="fadeUp" delay={0.1}>
          <div className="space-y-2">
            {filtered.map(insight => (
              <InsightCard key={insight.id} insight={insight} />
            ))}
          </div>
        </ScrollReveal>
      ) : (
        <EmptyState
          title="No insights found"
          description={typeFilter ? 'Try a different filter' : 'Insights will appear after your data is analyzed.'}
        />
      )}
    </div>
  )
}
