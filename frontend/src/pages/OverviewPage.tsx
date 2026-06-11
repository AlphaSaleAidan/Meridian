import { useLocation, Link } from 'react-router-dom'
import { useMemo } from 'react'
import {
  DollarSign, ShoppingCart, Receipt,
  Target, Bot, LineChart, Users, Percent,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatNumber, formatPercent } from '@/lib/format'
import StatCard from '@/components/StatCard'
import {
  DEMO_WEEKLY_REVENUE_CENTS, getLaborTarget, laborPctTone, computeWeeklyLaborCents,
} from '@/components/schedule/schedule-helpers'
import { useDemoContext, getActiveBusinessType } from '@/lib/demo-context'
import { generateScheduleShifts, generateScheduleStaff } from '@/lib/agent-data'
import MoneyLeftCard from '@/components/MoneyLeftCard'
import Top3ActionsPanel from '@/components/Top3ActionsPanel'
import RevenueChart from '@/components/RevenueChart'
import InsightCard from '@/components/InsightCard'
import ConnectionBadge from '@/components/ConnectionBadge'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import DataPageSkeleton from '@/components/DataPageSkeleton'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { generateTopActions, generateAgents, generateRFMSegments } from '@/lib/agent-data'
import { useOrgId, useTier, useIsDemo, tierLimits } from '@/hooks/useOrg'
import { AnalyzingSection } from '@/components/AnalyzingDataState'
import { useAuth } from '@/lib/auth'

export default function OverviewPage() {
  const location = useLocation()
  const basePath = location.pathname.startsWith('/app') ? '/app'
    : location.pathname.startsWith('/canada/demo') ? '/canada/demo'
    : '/demo'
  const orgId = useOrgId()
  const tier = useTier()
  const limits = tierLimits[tier]
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected

  const skip = !isDemo && !posConnected
  const overview = useApi(() => skip ? api.overview('') : api.overview(orgId), [orgId, skip])
  const revenue = useApi(() => skip ? api.revenue('', 30) : api.revenue(orgId, 30), [orgId, skip])
  const insights = useApi(() => skip ? api.insights('', 5) : api.insights(orgId, 5), [orgId, skip])
  const forecastData = useApi(() => skip ? api.forecasts('') : api.forecasts(orgId), [orgId, skip])

  const topActions = (isDemo ? generateTopActions() : []).slice(0, 3)
  const agents = isDemo ? generateAgents() : []
  const segments = isDemo ? generateRFMSegments() : []
  const activeAgents = agents.filter(a => a.status === 'active' || a.status === 'running').length
  const avgRetention = segments.length > 0
    ? Math.round(
        segments.reduce((s, seg) => s + seg.retentionScore * seg.count, 0) /
        segments.reduce((s, seg) => s + seg.count, 0)
      )
    : 0

  // Labor % of weekly revenue — computed for demo so the Overview KPI matches
  // the Schedule page. Live wiring (real shifts via /api/schedule) is a follow-up.
  const demoCtx = useDemoContext()
  const businessType = demoCtx.businessType ?? getActiveBusinessType()
  const labor = useMemo(() => {
    if (!isDemo) return null
    const weekStart = new Date()
    weekStart.setDate(weekStart.getDate() - ((weekStart.getDay() + 6) % 7))
    weekStart.setHours(0, 0, 0, 0)
    const shifts = generateScheduleShifts(weekStart)
    const staff = generateScheduleStaff()
    const cents = computeWeeklyLaborCents(shifts, staff)
    const rev = DEMO_WEEKLY_REVENUE_CENTS[businessType] ?? 0
    if (rev === 0) return null
    const pct = (cents / rev) * 100
    const target = getLaborTarget(businessType)
    const tone = laborPctTone(pct, target.targetPct, target.warningPct, target.floorPct)
    return { pct, tone, target }
  }, [isDemo, businessType])

  if (skip) return <DataPageSkeleton title="Overview"><div /></DataPageSkeleton>
  if (overview.loading) return <LoadingPage />
  if (overview.error) return <ErrorState message={overview.error} onRetry={overview.refetch} />
  if (!overview.data) return <LoadingPage />

  const data = overview.data

  return (
    <DataPageSkeleton title="Overview">
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Dashboard</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              Last 30 days • <span className="font-mono">{data.days_with_data}</span> days with data{activeAgents > 0 && (
                <> • <span className="font-mono">{activeAgents}</span> AI {activeAgents === 1 ? 'agent' : 'agents'} on duty</>
              )}
            </p>
          </div>
          <ConnectionBadge
            status={data.connection.status}
            provider={data.connection.provider}
            lastSync={data.connection.last_sync_at}
          />
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-5 gap-3 sm:gap-4" data-walkthrough="overview-stats">
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
        <StaggerItem>
          <StatCard
            label="Labor Cost %"
            value={labor ? `${labor.pct.toFixed(1)}%` : '—'}
            icon={Percent}
            iconColor={
              labor?.tone.label === 'on-target' ? 'text-[#17C5B0]'
              : labor?.tone.label === 'over' ? 'text-[#E06B5E]'
              : 'text-[#D4A843]'
            }
            subtitle={
              labor
                ? `target ${labor.target.floorPct}-${labor.target.warningPct}% · ${labor.tone.label}`
                : 'connect schedule'
            }
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
        <Top3ActionsPanel showHeader={false} />
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
              const fc = forecastData.data!.forecasts
                .filter(f => f.type === 'daily_revenue')
                .sort((a, b) => a.period_start.localeCompare(b.period_start))
              const now = new Date()
              const BUCKETS = [
                { label: '7-Day', days: 7 },
                { label: '30-Day', days: 30 },
                { label: '90-Day', days: 90 },
              ]
              // Build chart data over up to 90 days (or whatever exists)
              const chartPts = fc.slice(0, 90).map((f, i) => ({
                i,
                pred: f.predicted_cents,
                lo: f.lower_bound_cents || f.predicted_cents * 0.85,
                hi: f.upper_bound_cents || f.predicted_cents * 1.15,
              }))
              const W = 100, H = 32
              const maxY = chartPts.length > 0 ? Math.max(...chartPts.map(p => p.hi)) : 1
              const minY = chartPts.length > 0 ? Math.min(...chartPts.map(p => p.lo)) : 0
              const yRange = maxY - minY || 1
              const x = (i: number) => chartPts.length <= 1 ? 0 : (i / (chartPts.length - 1)) * W
              const y = (v: number) => H - ((v - minY) / yRange) * H
              const bandPath = chartPts.length > 1
                ? `M ${chartPts.map(p => `${x(p.i).toFixed(2)},${y(p.hi).toFixed(2)}`).join(' L ')} L ${[...chartPts].reverse().map(p => `${x(p.i).toFixed(2)},${y(p.lo).toFixed(2)}`).join(' L ')} Z`
                : ''
              const linePath = chartPts.length > 1
                ? `M ${chartPts.map(p => `${x(p.i).toFixed(2)},${y(p.pred).toFixed(2)}`).join(' L ')}`
                : ''
              return (
                <>
                  <div className="grid grid-cols-3 gap-3">
                    {BUCKETS.map(b => {
                      const cutoff = new Date(now)
                      cutoff.setDate(cutoff.getDate() + b.days)
                      const inRange = fc.filter(f => new Date(f.period_start) <= cutoff)
                      if (inRange.length === 0) {
                        return (
                          <div key={b.label} className="text-center opacity-60">
                            <p className="text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider">{b.label}</p>
                            <p className="text-lg sm:text-xl font-bold font-mono text-[#A1A1A8]/40 mt-1">—</p>
                            <p className="text-[9px] text-[#A1A1A8]/40 mt-0.5">not enough data</p>
                          </div>
                        )
                      }
                      const total = inRange.reduce((s, f) => s + f.predicted_cents, 0)
                      const lower = inRange.reduce((s, f) => s + (f.lower_bound_cents || f.predicted_cents * 0.85), 0)
                      const upper = inRange.reduce((s, f) => s + (f.upper_bound_cents || f.predicted_cents * 1.15), 0)
                      const avgConf = Math.round(inRange.reduce((s, f) => s + (f.confidence || 0.7) * 100, 0) / inRange.length)
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
                  {chartPts.length > 1 && (
                    <div className="mt-4 pt-3 border-t border-[#1F1F23]">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[9px] uppercase tracking-wider text-[#A1A1A8]/60">Forecast curve</span>
                        <span className="text-[9px] text-[#A1A1A8]/40 font-mono">predicted · 85–115% band</span>
                      </div>
                      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full h-12 sm:h-16">
                        <path d={bandPath} fill="#1A8FD6" fillOpacity="0.14" />
                        <path d={linePath} stroke="#1A8FD6" strokeWidth="0.7" fill="none" vectorEffect="non-scaling-stroke" />
                      </svg>
                    </div>
                  )}
                </>
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

      {isDemo && (
        <ScrollReveal variant="fadeUp" delay={0.2}>
          <div
            className="card p-6 border-[#17C5B0]/20 bg-gradient-to-r from-[#17C5B0]/5 to-transparent"
            data-walkthrough="connect-pos-cta"
          >
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-lg font-semibold text-[#F5F5F7]">See Your Real Numbers</h3>
                <p className="text-sm text-[#A1A1A8] mt-1">
                  Connect your POS and get your actual data in this dashboard — takes about 4 minutes.
                  First month free, no credit card required.
                </p>
              </div>
              <button className="flex-shrink-0 px-6 py-3 rounded-xl bg-[#17C5B0] text-black font-bold text-sm hover:bg-[#17C5B0]/90 transition-colors whitespace-nowrap">
                Connect Your POS
              </button>
            </div>
          </div>
        </ScrollReveal>
      )}
    </div>
    </DataPageSkeleton>
  )
}
