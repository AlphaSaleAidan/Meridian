import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatDate, formatConfidence } from '@/lib/format'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

export default function ForecastsPage() {
  const forecasts = useApi(() => api.forecasts(ORG_ID), [])
  const revenue = useApi(() => api.revenue(ORG_ID, 30), [])

  if (forecasts.loading) return <LoadingPage />
  if (forecasts.error) return <ErrorState message={forecasts.error} onRetry={forecasts.refetch} />

  const data = forecasts.data!

  const historicalData = (revenue.data?.daily || []).map(d => ({
    date: d.date.slice(0, 10),
    actual: d.revenue_cents / 100,
    predicted: null as number | null,
    lower: null as number | null,
    upper: null as number | null,
  }))

  const forecastData = data.forecasts
    .filter(f => f.type === 'daily_revenue')
    .map(f => ({
      date: f.period_start,
      actual: null as number | null,
      predicted: f.predicted_cents / 100,
      lower: f.lower_bound_cents ? f.lower_bound_cents / 100 : null,
      upper: f.upper_bound_cents ? f.upper_bound_cents / 100 : null,
    }))

  const chartData = [...historicalData, ...forecastData]

  const totalPredicted = data.forecasts
    .filter(f => f.type === 'daily_revenue')
    .reduce((s, f) => s + f.predicted_cents, 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Forecasts</h1>
        <p className="text-sm text-slate-400 mt-1">
          {data.total} active forecasts • AI-powered revenue predictions
        </p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <div className="card p-4 sm:p-5">
          <p className="stat-label">Forecasted Revenue</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl text-meridian-400">{formatCentsCompact(totalPredicted)}</p>
          <p className="text-xs text-slate-500 mt-1">next forecast period</p>
        </div>
        <div className="card p-4 sm:p-5">
          <p className="stat-label">Active Forecasts</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl">{data.total}</p>
        </div>
        <div className="card p-4 sm:p-5">
          <p className="stat-label">Avg Confidence</p>
          <p className="stat-value mt-1 text-lg sm:text-2xl">
            {data.forecasts.length > 0
              ? formatConfidence(
                  data.forecasts.reduce((s, f) => s + (f.confidence || 0), 0) / data.forecasts.length
                )
              : '—'}
          </p>
        </div>
      </div>

      {/* Chart: Historical + Forecast */}
      {chartData.length > 0 && (
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Revenue: Actual vs Forecast</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <defs>
                <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#1454e1" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#1454e1" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10b981" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
              <XAxis dataKey="date" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false}
                tickFormatter={(v: string) => { const d = new Date(v); return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); }}
                interval="preserveStartEnd" />
              <YAxis tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false}
                tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`} width={45} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                formatter={(v: any, name: string) => [v != null ? formatCents(v * 100) : '—', name]}
              />
              <Area type="monotone" dataKey="actual" stroke="#1454e1" strokeWidth={2} fill="url(#actualGrad)" dot={false} name="Actual" connectNulls={false} />
              <Area type="monotone" dataKey="predicted" stroke="#10b981" strokeWidth={2} strokeDasharray="6 3" fill="url(#forecastGrad)" dot={false} name="Forecast" connectNulls={false} />
              {forecastData.some(d => d.upper != null) && (
                <Area type="monotone" dataKey="upper" stroke="none" fill="#10b981" fillOpacity={0.05} dot={false} name="Upper Bound" connectNulls={false} />
              )}
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Forecast Details — cards on mobile, table on desktop */}
      {data.forecasts.length > 0 ? (
        <>
          {/* Mobile: cards */}
          <div className="space-y-2 sm:hidden">
            {data.forecasts.map(f => (
              <div key={f.id} className="card p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="badge-blue">{f.type.replace(/_/g, ' ')}</span>
                  <span className="text-xs text-slate-400">{formatConfidence(f.confidence)}</span>
                </div>
                <p className="text-lg font-bold text-white">{formatCents(f.predicted_cents)}</p>
                <p className="text-xs text-slate-500 mt-0.5">
                  {formatDate(f.period_start)} – {formatDate(f.period_end)}
                </p>
                {f.lower_bound_cents && f.upper_bound_cents && (
                  <p className="text-xs text-slate-500 mt-1">
                    Range: {formatCents(f.lower_bound_cents)} – {formatCents(f.upper_bound_cents)}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Desktop: table */}
          <div className="card overflow-hidden hidden sm:block">
            <div className="px-5 py-4 border-b border-slate-800/60">
              <h3 className="text-sm font-semibold text-white">Forecast Details</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[500px]">
                <thead>
                  <tr className="border-b border-slate-800/40">
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-400 uppercase">Type</th>
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-400 uppercase">Period</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase">Predicted</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase">Range</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase">Confidence</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/30">
                  {data.forecasts.map(f => (
                    <tr key={f.id} className="hover:bg-slate-800/20">
                      <td className="px-5 py-3">
                        <span className="badge-blue">{f.type.replace(/_/g, ' ')}</span>
                      </td>
                      <td className="px-5 py-3 text-slate-300">
                        {formatDate(f.period_start)} – {formatDate(f.period_end)}
                      </td>
                      <td className="px-5 py-3 text-right font-medium text-white">
                        {formatCents(f.predicted_cents)}
                      </td>
                      <td className="px-5 py-3 text-right text-slate-400 text-xs">
                        {f.lower_bound_cents && f.upper_bound_cents
                          ? `${formatCents(f.lower_bound_cents)} – ${formatCents(f.upper_bound_cents)}`
                          : '—'}
                      </td>
                      <td className="px-5 py-3 text-right text-slate-300">
                        {formatConfidence(f.confidence)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <EmptyState
          title="No forecasts yet"
          description="Forecasts are generated after enough historical data has been analyzed."
        />
      )}
    </div>
  )
}
