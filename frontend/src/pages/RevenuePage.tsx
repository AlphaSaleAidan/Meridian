import { useState, useCallback, useMemo, lazy, Suspense } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Download, Box, BarChart3 } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatNumber, formatChartDate, formatChartTick } from '@/lib/format'
import { LoadingPage, ErrorState } from '@/components/LoadingState'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import TransactionDrillDown from '@/components/TransactionDrillDown'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import DataPageSkeleton from '@/components/DataPageSkeleton'
import { useAuth } from '@/lib/auth'

const Revenue3D = lazy(() => import('@/components/Revenue3D'))

const periods = [
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
  { label: '1Y', days: 365 },
]

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

// Historical revenue by calendar year + monthly trend — lets merchants see
// prior-year revenue from the ~18 months the backfill pulls.
function HistoricalRevenueSection() {
  const orgId = useOrgId()
  const { data } = useApi<any>(() => api.annualRevenue(orgId), [orgId])
  const years = data?.years ?? []
  if (years.length === 0) return null

  const monthly = (data?.monthly ?? []).map((m: any) => ({
    label: m.month,
    revenue: (m.revenue_cents ?? 0) / 100,
  }))
  const cur = data?.current_year
  const prior = data?.prior_year
  const yoy = data?.yoy_pct

  return (
    <ScrollReveal variant="fadeUp" delay={0.05}>
      <div className="card p-4 sm:p-5">
        <div className="flex items-start justify-between mb-4 gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Historical Revenue</h3>
            <p className="text-[10px] text-[#A1A1A8]">Revenue by year — up to ~18 months of history</p>
          </div>
          {cur && prior && yoy != null && (
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCentsCompact(cur.revenue_cents)}</p>
              <p className={`text-[10px] font-mono ${yoy >= 0 ? 'text-[#17C5B0]' : 'text-amber-400'}`}>
                {yoy >= 0 ? '+' : ''}{yoy}% vs {prior.year}
              </p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {years.map((y: any) => (
            <div key={y.year} className="rounded-lg bg-[#1F1F23]/40 p-3">
              <p className="text-[10px] text-[#A1A1A8]/60 font-mono">{y.year}</p>
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCentsCompact(y.revenue_cents)}</p>
              <p className="text-[10px] text-[#A1A1A8]/40">{formatNumber(y.transaction_count)} txns</p>
            </div>
          ))}
        </div>

        {monthly.length > 1 && (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={monthly} margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: '#A1A1A8', fontSize: 9, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#A1A1A8', fontSize: 9, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} tickFormatter={formatChartTick} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number) => [formatCents(v * 100), 'Revenue']} cursor={{ fill: 'rgba(26,143,214,0.04)' }} />
              <Bar dataKey="revenue" fill="#1A8FD6" radius={[4, 4, 0, 0]} fillOpacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </ScrollReveal>
  )
}

export default function RevenuePage() {
  const [days, setDays] = useState(365)
  const [drillDate, setDrillDate] = useState<string | null>(null)
  const [view3D, setView3D] = useState(false)
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected
  const revenue = useApi(() => api.revenue(orgId, days), [orgId, days])

  const daily = revenue.data?.daily ?? []

  const chartData = useMemo(() => daily.map(d => ({
    rawDate: d.date,
    date: formatChartDate(d.date),
    revenue: d.revenue_cents / 100,
    transactions: d.transactions,
    avgTicket: d.avg_ticket_cents / 100,
    refunds: d.refund_cents / 100,
    tips: d.tip_cents / 100,
    discounts: d.discount_cents / 100,
  })), [daily])

  const totalRevenue = useMemo(() => daily.reduce((s, d) => s + (d.revenue_cents || 0), 0), [daily])
  const totalTxns = useMemo(() => daily.reduce((s, d) => s + (d.transactions || 0), 0), [daily])
  const totalRefunds = useMemo(() => daily.reduce((s, d) => s + (d.refund_cents || 0), 0), [daily])
  const totalTips = useMemo(() => daily.reduce((s, d) => s + (d.tip_cents || 0), 0), [daily])

  const handleBarClick = useCallback((barData: any) => {
    if (barData?.activePayload?.[0]?.payload?.rawDate) {
      setDrillDate(barData.activePayload[0].payload.rawDate)
    }
  }, [])

  const exportCsv = useCallback(() => {
    const esc = (v: string | number) => {
      const s = String(v)
      return s.includes(',') || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s
    }
    const header = 'Date,Revenue,Transactions,Avg Ticket,Refunds,Tips,Discounts'
    const rows = daily.map(d =>
      [d.date, (d.revenue_cents / 100).toFixed(2), d.transactions, (d.avg_ticket_cents / 100).toFixed(2), (d.refund_cents / 100).toFixed(2), (d.tip_cents / 100).toFixed(2), (d.discount_cents / 100).toFixed(2)].map(esc).join(',')
    )
    const csv = [header, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `meridian-revenue-${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [daily])

  if (!isDemo && !posConnected) return <DataPageSkeleton title="Revenue"><div /></DataPageSkeleton>
  if (revenue.loading) return <LoadingPage />
  if (revenue.error) return <ErrorState message={revenue.error} onRetry={revenue.refetch} />
  if (!revenue.data) return <LoadingPage />

  const data = revenue.data

  return (
    <DataPageSkeleton title="Revenue" layout="chart">
    <div className="space-y-6">
      {/* Transaction Drill-Down Modal */}
      {drillDate && (
        <TransactionDrillDown date={drillDate} onClose={() => setDrillDate(null)} />
      )}

      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Revenue Analytics</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              <span className="font-mono">{formatCentsCompact(totalRevenue)}</span> total • <span className="font-mono">{formatNumber(totalTxns)}</span> transactions
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="period-toggle">
              {periods.map(p => (
                <button
                  key={p.days}
                  onClick={() => setDays(p.days)}
                  className={days === p.days ? 'period-btn-active' : 'period-btn-inactive'}
                >
                  {p.label}
                </button>
              ))}
            </div>
            <button
              onClick={exportCsv}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#A1A1A8] bg-[#111113] border border-[#1F1F23] rounded-lg hover:border-[#1A8FD6]/40 hover:text-[#F5F5F7] transition-all"
            >
              <Download size={13} /> Export CSV
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Summary Cards */}
      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <p className="stat-label">Total Revenue</p>
            <p className="text-lg sm:text-2xl font-bold text-[#F5F5F7] font-mono mt-1">{formatCentsCompact(totalRevenue)}</p>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <p className="stat-label">Transactions</p>
            <p className="text-lg sm:text-2xl font-bold text-[#F5F5F7] font-mono mt-1">{formatNumber(totalTxns)}</p>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <p className="stat-label">Refunds</p>
            <p className="text-lg sm:text-2xl font-bold text-red-400 font-mono mt-1">{formatCentsCompact(totalRefunds)}</p>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <p className="stat-label">Tips</p>
            <p className="text-lg sm:text-2xl font-bold text-[#17C5B0] font-mono mt-1">{formatCentsCompact(totalTips)}</p>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* Historical revenue (prior-year) */}
      <HistoricalRevenueSection />

      {/* Revenue Chart */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-4 sm:p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Daily Revenue</h3>
            <button
              onClick={() => setView3D(v => !v)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#A1A1A8] bg-[#111113] border border-[#1F1F23] rounded-lg hover:border-[#1A8FD6]/40 hover:text-[#F5F5F7] transition-all"
              title={view3D ? 'Switch to 2D chart' : 'Switch to 3D view'}
            >
              {view3D ? <><BarChart3 size={13} /> 2D</> : <><Box size={13} /> 3D</>}
            </button>
          </div>
          {view3D ? (
            <Suspense fallback={<div className="h-[300px] bg-[#111113] rounded-xl animate-pulse" />}>
              <Revenue3D
                data={data.daily.slice(-14).map(d => {
                  const avgRevenue = data.daily.reduce((s, r) => s + r.revenue_cents, 0) / data.daily.length
                  return {
                    label: new Date(d.date).toLocaleDateString('en', { weekday: 'short' }),
                    value: d.revenue_cents,
                    color: d.revenue_cents > avgRevenue ? '#0066FF' : '#1F1F23',
                  }
                })}
              />
            </Suspense>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#1A8FD6" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#1A8FD6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false}
                  tickFormatter={formatChartTick} width={55} />
                <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number, name: string) => [formatCents(v * 100), name]}
                  cursor={{ stroke: '#1A8FD6', strokeWidth: 1, strokeDasharray: '4 4' }} />
                <Area type="monotone" dataKey="revenue" stroke="#1A8FD6" strokeWidth={2} fill="url(#revGrad)" dot={false}
                  activeDot={{ r: 5, fill: '#1A8FD6', stroke: '#0A0A0B', strokeWidth: 2 }} name="Revenue" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </ScrollReveal>

      {/* Transactions Chart — click a bar to drill down */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 sm:p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Daily Transactions</h3>
            <span className="text-[10px] text-[#1A8FD6] uppercase tracking-wider font-medium">Click a bar to drill down</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 5, left: -10, bottom: 0 }}
              onClick={handleBarClick}
              style={{ cursor: 'pointer' }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} width={35} />
              <Tooltip
                contentStyle={tooltipStyle}
                itemStyle={{ color: '#F5F5F7' }}
                labelStyle={{ color: '#A1A1A8' }}
                cursor={{ fill: 'rgba(26, 143, 214, 0.06)' }}
                formatter={(v: number, name: string) => [v, name]}
              />
              <Bar
                dataKey="transactions"
                fill="#17C5B0"
                radius={[3, 3, 0, 0]}
                name="Transactions"
                fillOpacity={0.8}
                className="cursor-pointer"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ScrollReveal>

      {/* Weekly Summary Table */}
      {data.weekly.length > 0 && (
        <ScrollReveal variant="fadeUp" delay={0.2}>
          <div className="card overflow-hidden">
            <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Weekly Summary</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="pm-table min-w-[400px]">
                <thead>
                  <tr>
                    <th className="text-left">Week</th>
                    <th className="text-right">Revenue</th>
                    <th className="text-right">Txns</th>
                    <th className="text-right">Avg Ticket</th>
                  </tr>
                </thead>
                <tbody>
                  {data.weekly.map((w, i) => (
                    <tr key={i}>
                      <td className="text-[#A1A1A8]">{formatChartDate(w.week)}</td>
                      <td className="text-right font-medium font-mono text-[#F5F5F7]">{formatCents(w.revenue_cents)}</td>
                      <td className="text-right font-mono text-[#A1A1A8]">{formatNumber(w.transactions)}</td>
                      <td className="text-right font-mono text-[#A1A1A8]">{formatCents(w.avg_ticket_cents)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </ScrollReveal>
      )}
    </div>
    </DataPageSkeleton>
  )
}
