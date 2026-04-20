import { useLocation, Link } from 'react-router-dom'
import {
  DollarSign, ShoppingCart, Receipt, TrendingUp, ArrowUpRight, ArrowDownRight,
} from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatNumber, formatPercent } from '@/lib/format'
import StatCard from '@/components/StatCard'
import MoneyLeftCard from '@/components/MoneyLeftCard'
import RevenueChart from '@/components/RevenueChart'
import InsightCard from '@/components/InsightCard'
import ConnectionBadge from '@/components/ConnectionBadge'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

export default function OverviewPage() {
  const location = useLocation()
  const basePath = location.pathname.startsWith('/app') ? '/app' : '/demo'

  const overview = useApi(() => api.overview(ORG_ID), [])
  const revenue = useApi(() => api.revenue(ORG_ID, 30), [])
  const insights = useApi(() => api.insights(ORG_ID, 5), [])

  if (overview.loading) return <LoadingPage />
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />

  const data = overview.data!

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Last 30 days • {data.days_with_data} days with data
          </p>
        </div>
        <ConnectionBadge
          status={data.connection.status}
          provider={data.connection.provider}
          lastSync={data.connection.last_sync_at}
        />
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StatCard
          label="Total Revenue"
          value={formatCentsCompact(data.revenue_cents_30d)}
          change={formatPercent(data.revenue_change_pct)}
          changeType={data.revenue_change_pct >= 0 ? 'positive' : 'negative'}
          icon={DollarSign}
          iconColor="text-emerald-400"
        />
        <StatCard
          label="Transactions"
          value={formatNumber(data.transaction_count_30d)}
          icon={ShoppingCart}
          iconColor="text-blue-400"
        />
        <StatCard
          label="Avg Ticket"
          value={formatCents(data.avg_ticket_cents)}
          icon={Receipt}
          iconColor="text-purple-400"
        />
        <StatCard
          label="Revenue Trend"
          value={formatPercent(data.revenue_change_pct)}
          icon={data.revenue_change_pct >= 0 ? ArrowUpRight : ArrowDownRight}
          iconColor={data.revenue_change_pct >= 0 ? 'text-emerald-400' : 'text-red-400'}
          subtitle="vs prior 30 days"
        />
      </div>

      {/* Money Left + Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 sm:gap-6">
        <div className="lg:col-span-2">
          <MoneyLeftCard score={data.money_left_score} />
        </div>
        <div className="lg:col-span-3">
          {revenue.data ? (
            <RevenueChart data={revenue.data.daily} height={280} />
          ) : (
            <div className="card p-5 h-[280px] sm:h-[340px] flex items-center justify-center">
              <p className="text-sm text-slate-500">Loading chart...</p>
            </div>
          )}
        </div>
      </div>

      {/* Recent Insights */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">Recent Insights</h2>
          <Link
            to={`${basePath}/insights`}
            className="text-xs text-meridian-400 hover:text-meridian-300 font-medium"
          >
            View all →
          </Link>
        </div>
        {insights.data && insights.data.insights.length > 0 ? (
          <div className="space-y-2">
            {insights.data.insights.map(insight => (
              <InsightCard key={insight.id} insight={insight} compact />
            ))}
          </div>
        ) : (
          <EmptyState
            title="No insights yet"
            description="Insights will appear here once your POS data is synced and analyzed."
          />
        )}
      </div>
    </div>
  )
}
