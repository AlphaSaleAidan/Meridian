import { useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatNumber, formatChartDate } from '@/lib/format'
import { LoadingPage, ErrorState } from '@/components/LoadingState'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import TransactionDrillDown from '@/components/TransactionDrillDown'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const periods = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
]

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

export default function RevenuePage() {
  const [days, setDays] = useState(30)
  const [drillDate, setDrillDate] = useState<string | null>(null)
  const revenue = useApi(() => api.revenue(ORG_ID, days), [days])

  if (revenue.loading) return <LoadingPage />
  if (revenue.error) return <ErrorState message={revenue.error} onRetry={revenue.refetch} />

  const data = revenue.data!

  const chartData = data.daily.map(d => ({
    rawDate: d.date,
    date: formatChartDate(d.date),
    revenue: d.revenue_cents / 100,
    transactions: d.transactions,
    avgTicket: d.avg_ticket_cents / 100,
    refunds: d.refund_cents / 100,
    tips: d.tip_cents / 100,
    discounts: d.discount_cents / 100,
  }))

  const totalRevenue = data.daily.reduce((s, d) => s + d.revenue_cents, 0)
  const totalTxns = data.daily.reduce((s, d) => s + d.transactions, 0)
  const totalRefunds = data.daily.reduce((s, d) => s + d.refund_cents, 0)
  const totalTips = data.daily.reduce((s, d) => s + d.tip_cents, 0)

  const handleBarClick = (barData: any) => {
    if (barData?.activePayload?.[0]?.payload?.rawDate) {
      setDrillDate(barData.activePayload[0].payload.rawDate)
    }
  }

  return (
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

      {/* Revenue Chart */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Daily Revenue</h3>
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
                tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`} width={45} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number, name: string) => [formatCents(v * 100), name]}
                cursor={{ stroke: '#1A8FD6', strokeWidth: 1, strokeDasharray: '4 4' }} />
              <Area type="monotone" dataKey="revenue" stroke="#1A8FD6" strokeWidth={2} fill="url(#revGrad)" dot={false}
                activeDot={{ r: 5, fill: '#1A8FD6', stroke: '#0A0A0B', strokeWidth: 2 }} name="Revenue" />
            </AreaChart>
          </ResponsiveContainer>
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
  )
}
