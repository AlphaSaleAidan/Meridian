import { useState } from 'react'
import { clsx } from 'clsx'
import { Filter, Lock } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCentsCompact } from '@/lib/format'
import InsightCard from '@/components/InsightCard'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import ScrollReveal from '@/components/ScrollReveal'
import { useOrgId, useTier, tierLimits } from '@/hooks/useOrg'
import { useInsightsCooldown } from '@/hooks/useInsightsCooldown'

const insightTypes = [
  { key: '', label: 'All' },
  { key: 'money_left', label: 'Money Left' },
  { key: 'product_recommendation', label: 'Products' },
  { key: 'pricing', label: 'Pricing' },
  { key: 'staffing', label: 'Staffing' },
  { key: 'anomaly', label: 'Anomalies' },
  { key: 'seasonal', label: 'Seasonal' },
  { key: 'inventory', label: 'Inventory' },
  { key: 'benchmark', label: 'Benchmarks' },
  { key: 'general', label: 'General' },
]

export default function InsightsPage() {
  const [typeFilter, setTypeFilter] = useState('')
  const orgId = useOrgId()
  const tier = useTier()
  const limits = tierLimits[tier]
  const { coolingDown, timeDisplay } = useInsightsCooldown()
  const insights = useApi(() => api.insights(orgId, 50), [orgId])

  if (insights.loading) return <LoadingPage />
  if (insights.error) return <ErrorState message={insights.error} onRetry={insights.refetch} />

  const data = insights.data!
  const allFiltered = typeFilter
    ? data.insights.filter(i => i.type === typeFilter)
    : data.insights
  const isLimited = limits.insightLimit < allFiltered.length
  const filtered = allFiltered.slice(0, limits.insightLimit)

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

      {coolingDown && timeDisplay && (
        <ScrollReveal variant="fadeUp" delay={0.03}>
          <div className="p-4 rounded-xl bg-[#7C5CFF]/10 border border-[#7C5CFF]/20 flex items-center gap-3">
            <div className="text-2xl font-mono text-[#7C5CFF]">{timeDisplay}</div>
            <div>
              <p className="text-sm font-semibold text-[#7C5CFF]">AI Insights Generating</p>
              <p className="text-xs text-[#A1A1A8]">New insights will be ready soon. Our AI swarm is analyzing your data for the best possible recommendations.</p>
            </div>
          </div>
        </ScrollReveal>
      )}

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
                  ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20 shadow-[0_0_12px_rgba(124,92,255,0.1)]'
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
          {isLimited && (
            <div className="mt-4 p-4 rounded-xl border border-[#7C5CFF]/20 bg-[#7C5CFF]/5 flex items-center gap-3">
              <Lock size={16} className="text-[#7C5CFF] flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm font-medium text-[#F5F5F7]">
                  {allFiltered.length - limits.insightLimit} more insights available
                </p>
                <p className="text-xs text-[#A1A1A8]">Upgrade to Growth to unlock all insights</p>
              </div>
            </div>
          )}
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
