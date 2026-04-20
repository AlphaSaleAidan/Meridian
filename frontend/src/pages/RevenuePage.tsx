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

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const periods = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
]

export default function RevenuePage() {
  const [days, setDays] = useState(30)
  const revenue = useApi(() => api.revenue(ORG_ID, days), [days])

  if (revenue.loading) return <LoadingPage />
  if (revenue.error) return <ErrorState message={revenue.error} onRetry={revenue.refetch} />

  const data = revenue.data!

  const chartData = data.daily.map(d => ({
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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Revenue Analytics</h1>
          <p className="text-sm text-slate-400 mt-1">
            {formatCentsCompact(totalRevenue)} total • {formatNumber(totalTxns)} transactions
          </p>
        </div>
        <div className="flex gap-1 bg-slate-800/60 rounded-lg p-1 self-start">
          {periods.map(p => (
            <button
              key={p.days}
              onClick={() => setDays(p.days)}
              className={clsx(
                'px-3 py-2 sm:py-1.5 text-xs font-medium rounded-md transition-colors',
                days === p.days
                  ? 'bg-meridian-700 text-white'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="card p-4">
          <p className="stat-label">Total Revenue</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl">{formatCentsCompact(totalRevenue)}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Transactions</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl">{formatNumber(totalTxns)}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Refunds</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl text-red-400">{formatCentsCompact(totalRefunds)}</p>
        </div>
        <div className="card p-4">
          <p className="stat-label">Tips</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl text-emerald-400">{formatCentsCompact(totalTips)}</p>
        </div>
      </div>

      {/* Revenue Chart */}
      <div className="card p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Daily Revenue</h3>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#1454e1" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#1454e1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false}
              tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`} width={45} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
              formatter={(v: number, name: string) => [formatCents(v * 100), name]}
            />
            <Area type="monotone" dataKey="revenue" stroke="#1454e1" strokeWidth={2} fill="url(#revGrad)" dot={false} name="Revenue" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Transactions Chart */}
      <div className="card p-4 sm:p-5">
        <h3 className="text-sm font-semibold text-white mb-4">Daily Transactions</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
            <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false} width={35} />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
            />
            <Bar dataKey="transactions" fill="#338bff" radius={[3, 3, 0, 0]} name="Transactions" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Weekly Summary Table */}
      {data.weekly.length > 0 && (
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-slate-800/60">
            <h3 className="text-sm font-semibold text-white">Weekly Summary</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm min-w-[400px]">
              <thead>
                <tr className="border-b border-slate-800/40">
                  <th className="px-4 sm:px-5 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Week</th>
                  <th className="px-4 sm:px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Revenue</th>
                  <th className="px-4 sm:px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Txns</th>
                  <th className="px-4 sm:px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Avg Ticket</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/30">
                {data.weekly.map((w, i) => (
                  <tr key={i} className="hover:bg-slate-800/20">
                    <td className="px-4 sm:px-5 py-3 text-slate-300">{formatChartDate(w.week)}</td>
                    <td className="px-4 sm:px-5 py-3 text-right font-medium text-white">{formatCents(w.revenue_cents)}</td>
                    <td className="px-4 sm:px-5 py-3 text-right text-slate-300">{formatNumber(w.transactions)}</td>
                    <td className="px-4 sm:px-5 py-3 text-right text-slate-300">{formatCents(w.avg_ticket_cents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
