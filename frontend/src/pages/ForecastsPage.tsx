import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatDate, formatConfidence } from '@/lib/format'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

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
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Forecasts</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            <span className="font-mono">{data.total}</span> active forecasts • AI-powered revenue predictions
          </p>
        </div>
      </ScrollReveal>

      {/* Summary */}
      <StaggerContainer className="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4 sm:p-5">
            <p className="stat-label">Forecasted Revenue</p>
            <p className="text-lg sm:text-2xl font-bold font-mono text-[#1A8FD6] mt-1">{formatCentsCompact(totalPredicted)}</p>
            <p className="text-xs text-[#A1A1A8]/50 mt-1">next forecast period</p>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4 sm:p-5">
            <p className="stat-label">Active Forecasts</p>
            <p className="text-lg sm:text-2xl font-bold font-mono text-[#F5F5F7] mt-1">{data.total}</p>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4 sm:p-5">
            <p className="stat-label">Avg Confidence</p>
            <p className="text-lg sm:text-2xl font-bold font-mono text-[#F5F5F7] mt-1">
              {data.forecasts.length > 0
                ? formatConfidence(
                    data.forecasts.reduce((s, f) => s + (f.confidence || 0), 0) / data.forecasts.length
                  )
                : '—'}
            </p>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* Chart: Historical + Forecast */}
      {chartData.length > 0 && (
        <ScrollReveal variant="fadeUp" delay={0.1}>
          <div className="card p-4 sm:p-5">
            <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Revenue: Actual vs Forecast</h3>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={chartData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="actualGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#1A8FD6" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#1A8FD6" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="forecastGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#17C5B0" stopOpacity={0.2} />
                    <stop offset="100%" stopColor="#17C5B0" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
                <XAxis dataKey="date" tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false}
                  tickFormatter={(v: string) => { const d = new Date(v); return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }); }}
                  interval="preserveStartEnd" />
                <YAxis tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false}
                  tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`} width={45} />
                <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }}
                  formatter={(v: any, name: string) => [v != null ? formatCents(v * 100) : '—', name]}
                  cursor={{ stroke: '#1A8FD6', strokeWidth: 1, strokeDasharray: '4 4' }} />
                <Area type="monotone" dataKey="actual" stroke="#1A8FD6" strokeWidth={2} fill="url(#actualGrad)" dot={false}
                  activeDot={{ r: 4, fill: '#1A8FD6', stroke: '#0A0A0B', strokeWidth: 2 }} name="Actual" connectNulls={false} />
                <Area type="monotone" dataKey="predicted" stroke="#17C5B0" strokeWidth={2} strokeDasharray="6 3" fill="url(#forecastGrad)" dot={false}
                  activeDot={{ r: 4, fill: '#17C5B0', stroke: '#0A0A0B', strokeWidth: 2 }} name="Forecast" connectNulls={false} />
                {forecastData.some(d => d.upper != null) && (
                  <Area type="monotone" dataKey="upper" stroke="none" fill="#17C5B0" fillOpacity={0.04} dot={false} name="Upper Bound" connectNulls={false} />
                )}
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ScrollReveal>
      )}

      {/* Forecast Details — cards on mobile, table on desktop */}
      {data.forecasts.length > 0 ? (
        <ScrollReveal variant="fadeUp" delay={0.15}>
          {/* Mobile: cards */}
          <div className="space-y-2 sm:hidden">
            {data.forecasts.map(f => (
              <div key={f.id} className="card-hover p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="badge-blue">{f.type.replace(/_/g, ' ')}</span>
                  <span className="text-xs font-mono text-[#A1A1A8]/60">{formatConfidence(f.confidence)}</span>
                </div>
                <p className="text-lg font-bold font-mono text-[#F5F5F7]">{formatCents(f.predicted_cents)}</p>
                <p className="text-xs text-[#A1A1A8]/50 mt-0.5">
                  {formatDate(f.period_start)} – {formatDate(f.period_end)}
                </p>
                {f.lower_bound_cents && f.upper_bound_cents && (
                  <p className="text-xs font-mono text-[#A1A1A8]/40 mt-1">
                    Range: {formatCents(f.lower_bound_cents)} – {formatCents(f.upper_bound_cents)}
                  </p>
                )}
              </div>
            ))}
          </div>

          {/* Desktop: table */}
          <div className="card overflow-hidden hidden sm:block">
            <div className="px-5 py-4 border-b border-[#1F1F23]">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Forecast Details</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="pm-table min-w-[500px]">
                <thead>
                  <tr>
                    <th className="text-left">Type</th>
                    <th className="text-left">Period</th>
                    <th className="text-right">Predicted</th>
                    <th className="text-right">Range</th>
                    <th className="text-right">Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {data.forecasts.map(f => (
                    <tr key={f.id}>
                      <td>
                        <span className="badge-blue">{f.type.replace(/_/g, ' ')}</span>
                      </td>
                      <td className="text-[#A1A1A8]">
                        {formatDate(f.period_start)} – {formatDate(f.period_end)}
                      </td>
                      <td className="text-right font-medium font-mono text-[#F5F5F7]">
                        {formatCents(f.predicted_cents)}
                      </td>
                      <td className="text-right font-mono text-[#A1A1A8]/60 text-xs">
                        {f.lower_bound_cents && f.upper_bound_cents
                          ? `${formatCents(f.lower_bound_cents)} – ${formatCents(f.upper_bound_cents)}`
                          : '—'}
                      </td>
                      <td className="text-right font-mono text-[#A1A1A8]">
                        {formatConfidence(f.confidence)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </ScrollReveal>
      ) : (
        <EmptyState
          title="No forecasts yet"
          description="Forecasts are generated after enough historical data has been analyzed."
        />
      )}
    </div>
  )
}
