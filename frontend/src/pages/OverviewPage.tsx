import { useLocation, Link } from 'react-router-dom'
import {
  DollarSign, ShoppingCart, Receipt,
  Target, Bot, LineChart, Users,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatNumber, formatPercent } from '@/lib/format'
import StatCard from '@/components/StatCard'
import MoneyLeftCard from '@/components/MoneyLeftCard'
import RevenueChart from '@/components/RevenueChart'
import InsightCard from '@/components/InsightCard'
import ConnectionBadge from '@/components/ConnectionBadge'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { generateTopActions, generateAgents, generateRFMSegments } from '@/lib/agent-data'
import { useOrgId, useTier, useIsDemo, tierLimits } from '@/hooks/useOrg'
import { AnalyzingSection } from '@/components/AnalyzingDataState'

export default function OverviewPage() {
  const location = useLocation()
  const basePath = location.pathname.startsWith('/app') ? '/app'
    : location.pathname.startsWith('/canada/demo') ? '/canada/demo'
    : '/demo'
  const orgId = useOrgId()
  const tier = useTier()
  const limits = tierLimits[tier]
  const isDemo = useIsDemo()

  const overview = useApi(() => api.overview(orgId), [orgId])
  const revenue = useApi(() => api.revenue(orgId, 30), [orgId])
  const insights = useApi(() => api.insights(orgId, 5), [orgId])
  const forecastData = useApi(() => api.forecasts(orgId), [orgId])

  const topActions = isDemo ? generateTopActions() : []
  const agents = isDemo ? generateAgents() : []
  const segments = isDemo ? generateRFMSegments() : []
  const activeAgents = agents.filter(a => a.status === 'active' || a.status === 'running').length
  const avgRetention = segments.length > 0
    ? Math.round(
        segments.reduce((s, seg) => s + seg.retentionScore * seg.count, 0) /
        segments.reduce((s, seg) => s + seg.count, 0)
      )
    : 0

  if (overview.loading) return <LoadingPage />
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />

  const data = overview.data!

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Dashboard</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              Last 30 days • <span className="font-mono">{data.days_with_data}</span> days with data • <span className="font-mono">{activeAgents}</span> agents active
            </p>
          </div>
          <ConnectionBadge
            status={data.connection.status}
            provider={data.connection.provider}
            lastSync={data.connection.last_sync_at}
          />
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <StatCard
            label="Total Revenue"
            value={formatCentsCompact(data.revenue_cents_30d)}
            change={formatPercent(data.revenue_change_pct)}
            changeType={data.revenue_change_pct >= 0 ? 'positive' : 'negative'}
            icon={DollarSign}
            iconColor="text-[#17C5B0]"
          />
        </StaggerItem>
        <StaggerItem>
          <StatCard
            label="Transactions"
            value={formatNumber(data.transaction_count_30d)}
            icon={ShoppingCart}
            iconColor="text-[#1A8FD6]"
          />
        </StaggerItem>
        <StaggerItem>
          <StatCard
            label="Avg Ticket"
            value={formatCents(data.avg_ticket_cents)}
            icon={Receipt}
            iconColor="text-[#1A8FD6]"
          />
        </StaggerItem>
        <StaggerItem>
          <StatCard
            label="Retention Score"
            value={avgRetention > 0 ? `${avgRetention}%` : '—'}
            icon={Users}
            iconColor="text-[#7C5CFF]"
            subtitle={avgRetention > 0 ? 'weighted by segment' : 'analyzing...'}
          />
        </StaggerItem>
      </StaggerContainer>

      {/* Top 3 Actions Today */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Target size={18} className="text-amber-400" />
            <h2 className="text-lg font-semibold text-[#F5F5F7]">Top 3 Actions Today</h2>
          </div>
          <Link to={`${basePath}/actions`} className="text-xs text-[#1A8FD6] hover:text-[#17C5B0] font-medium transition-colors">
            Details →
          </Link>
        </div>
        {topActions.length > 0 ? (
          <div className="space-y-2">
            {topActions.map(action => (
              <DashboardTiltCard
                key={action.rank}
                className={clsx(
                  'card p-4 flex items-center gap-3',
                  action.priority === 'Critical' && 'border-red-500/10'
                )}
              >
                <div className={clsx(
                  'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 font-bold text-sm font-mono',
                  action.rank === 1 ? 'bg-red-500/10 text-red-400' : action.rank === 2 ? 'bg-amber-400/10 text-amber-400' : 'bg-[#1A8FD6]/10 text-[#1A8FD6]'
                )}>
                  {action.rank}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[#F5F5F7] truncate">{action.title}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className={clsx(
                      'text-[10px] font-medium px-1.5 py-0.5 rounded-full border',
                      action.priority === 'Critical' ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    )}>{action.priority}</span>
                    <span className="text-[10px] text-[#A1A1A8]/50 font-mono">{action.confidence}% conf</span>
                  </div>
                </div>
                <span className="text-sm font-bold font-mono text-[#17C5B0] flex-shrink-0">+{formatCents(action.impactCents)}/mo</span>
              </DashboardTiltCard>
            ))}
          </div>
        ) : (
          <AnalyzingSection title="Identifying your top actions..." description="Actions will appear once enough data is analyzed by our AI agents." />
        )}
      </ScrollReveal>

      {/* Revenue Forecast Widget + Money Left */}
      <div className={clsx('grid grid-cols-1 gap-4 sm:gap-6', limits.moneyLeft ? 'lg:grid-cols-5' : '')}>
        {limits.moneyLeft && (
          <ScrollReveal variant="fadeUp" delay={0.1} className="lg:col-span-2">
            <MoneyLeftCard score={data.money_left_score} />
          </ScrollReveal>
        )}
        <ScrollReveal variant="fadeUp" delay={0.15} className={limits.moneyLeft ? 'lg:col-span-3' : ''}>
          <DashboardTiltCard className="card p-5" glowColor="rgba(26, 143, 214, 0.06)">
            <div className="flex items-center gap-2 mb-4">
              <LineChart size={16} className="text-[#1A8FD6]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Revenue Forecast</h3>
            </div>
            {forecastData.data && forecastData.data.forecasts.length > 0 ? (() => {
              const fc = forecastData.data!.forecasts.filter(f => f.type === 'daily_revenue')
              const now = new Date()
              const buckets = [
                { label: '7-Day', days: 7 },
                ...(limits.forecastDays >= 30 ? [{ label: '30-Day', days: 30 }] : []),
                ...(limits.forecastDays >= 90 ? [{ label: '90-Day', days: 90 }] : []),
              ]
              return (
                <div className={clsx('grid gap-3', `grid-cols-${buckets.length}`)}>
                  {buckets.map(b => {
                    const cutoff = new Date(now)
                    cutoff.setDate(cutoff.getDate() + b.days)
                    const inRange = fc.filter(f => new Date(f.period_start) <= cutoff)
                    const total = inRange.reduce((s, f) => s + f.predicted_cents, 0)
                    const lower = inRange.reduce((s, f) => s + (f.lower_bound_cents || f.predicted_cents * 0.85), 0)
                    const upper = inRange.reduce((s, f) => s + (f.upper_bound_cents || f.predicted_cents * 1.15), 0)
                    const avgConf = inRange.length > 0
                      ? Math.round(inRange.reduce((s, f) => s + (f.confidence || 0.7) * 100, 0) / inRange.length)
                      : 0
                    return (
                      <div key={b.label} className="text-center">
                        <p className="text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider">{b.label}</p>
                        <p className="text-lg sm:text-xl font-bold font-mono text-[#F5F5F7] mt-1">{formatCentsCompact(total)}</p>
                        <p className="text-[9px] text-[#A1A1A8]/40 mt-0.5">{avgConf}% conf</p>
                        <p className="text-[9px] text-[#A1A1A8]/30 font-mono">
                          {formatCentsCompact(lower)} – {formatCentsCompact(upper)}
                        </p>
                      </div>
                    )
                  })}
                </div>
              )
            })() : (
              <p className="text-sm text-[#A1A1A8]/50">Forecasts will appear after enough data is analyzed.</p>
            )}
          </DashboardTiltCard>
        </ScrollReveal>
      </div>

      {/* Revenue Chart */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        {revenue.data ? (
          <RevenueChart data={revenue.data.daily} height={280} />
        ) : (
          <div className="card p-5 h-[280px] flex items-center justify-center">
            <p className="text-sm text-[#A1A1A8]/50">Loading chart...</p>
          </div>
        )}
      </ScrollReveal>

      {/* Agent Status Strip */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Bot size={18} className="text-[#7C5CFF]" />
            <h2 className="text-lg font-semibold text-[#F5F5F7]">Agent Activity</h2>
          </div>
          <Link to={`${basePath}/agents`} className="text-xs text-[#1A8FD6] hover:text-[#17C5B0] font-medium transition-colors">
            View all →
          </Link>
        </div>
        {agents.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
            {agents.slice(0, 5).map(agent => (
              <div key={agent.id} className="card p-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', agent.status === 'active' ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/30')} />
                  <p className="text-[11px] font-medium text-[#F5F5F7] truncate">{agent.name}</p>
                </div>
                <p className="text-[10px] text-[#A1A1A8]/50 line-clamp-2 leading-relaxed">{agent.latestFinding}</p>
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-[9px] font-mono text-[#A1A1A8]/40">{agent.findings} findings</span>
                  <span className="text-[9px] font-mono text-[#A1A1A8]/40">{agent.confidence}%</span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <AnalyzingSection title="Deploying agents..." description="AI agents are being initialized to analyze your business data." />
        )}
      </ScrollReveal>

      {/* Recent Insights */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-[#F5F5F7]">Recent Insights</h2>
          <Link
            to={`${basePath}/insights`}
            className="text-xs text-[#1A8FD6] hover:text-[#17C5B0] font-medium transition-colors"
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
      </ScrollReveal>
    </div>
  )
}
