import { useState } from 'react'
import { clsx } from 'clsx'
import { Lightbulb, Filter } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCentsCompact } from '@/lib/format'
import InsightCard from '@/components/InsightCard'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'

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
      <div>
        <h1 className="text-2xl font-bold text-white">AI Insights</h1>
        <p className="text-sm text-slate-400 mt-1">
          {data.total} active insights • {actionable} actionable • {formatCentsCompact(totalImpact)}/mo potential impact
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        <Filter size={14} className="text-slate-500 flex-shrink-0" />
        {insightTypes.map(t => (
          <button
            key={t.key}
            onClick={() => setTypeFilter(t.key)}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium rounded-full transition-colors whitespace-nowrap border',
              typeFilter === t.key
                ? 'bg-meridian-700/20 text-meridian-400 border-meridian-700/30'
                : 'text-slate-400 border-slate-700/40 hover:text-white hover:border-slate-600'
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Insights List */}
      {filtered.length > 0 ? (
        <div className="space-y-2">
          {filtered.map(insight => (
            <InsightCard key={insight.id} insight={insight} />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No insights found"
          description={typeFilter ? 'Try a different filter' : 'Insights will appear after your data is analyzed.'}
        />
      )}
    </div>
  )
}
