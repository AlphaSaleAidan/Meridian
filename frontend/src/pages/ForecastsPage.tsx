import { useState } from 'react'
import { clsx } from 'clsx'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatDate, formatConfidence } from '@/lib/format'
import ForecastChart from '@/components/ForecastChart'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import { useOrgId, useTier, tierLimits } from '@/hooks/useOrg'
import { generateForecastPeriods, generateDailyForecast } from '@/lib/agent-data'
import { useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { TrendingUp, TrendingDown, Minus, Target, BarChart3 } from 'lucide-react'
import AwaitingDataBanner from '@/components/AwaitingDataBanner'

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

export default function ForecastsPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const posConnected = !!org?.pos_connected
  const tier = useTier()
  const limits = tierLimits[tier]
  const forecasts = useApi(() => api.forecasts(orgId), [orgId])
  const revenue = useApi(() => api.revenue(orgId, 30), [orgId])

  // Only surface loading / error once a POS is connected (or in demo). Before
  // that the analytics endpoint 401s — instead of a scaffold we render the real
  // (empty) forecast chart shell so the merchant sees exactly what fills in.
  if ((isDemo || posConnected) && forecasts.loading) return <LoadingPage />
  if ((isDemo || posConnected) && forecasts.error) return <ErrorState message={forecasts.error} onRetry={forecasts.refetch} />
  if ((isDemo || posConnected) && !forecasts.data) return <LoadingPage />

  const raw = forecasts.data ?? ({ forecasts: [], total: 0 } as NonNullable<typeof forecasts.data>)
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() + limits.forecastDays)
  const gatedForecasts = limits.forecastDays >= 999
    ? raw.forecasts
    : raw.forecasts.filter(f => new Date(f.period_start) <= cutoff)
  const data = { ...raw, forecasts: gatedForecasts, total: gatedForecasts.length }
  const awaitingData = !isDemo && data.forecasts.length === 0

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

      {awaitingData && <AwaitingDataBanner posConnected={posConnected} label="revenue forecast" />}

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

      {/* 7-Day Daily Forecast — weekday seasonality story */}
      {isDemo && (() => {
        const daily = generateDailyForecast()
        const maxCents = Math.max(...daily.map(d => d.predictedCents), 1)
        return (
          <ScrollReveal variant="fadeUp" delay={0.04}>
            <div className="card p-4 sm:p-5">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 size={14} className="text-[#17C5B0]" />
                <h3 className="text-sm font-semibold text-[#F5F5F7]">Next 7 Days — Daily Demand Forecast</h3>
                <span className="text-[9px] text-[#A1A1A8]/40 ml-auto font-mono">weekday seasonality + trend</span>
              </div>
              <div className="overflow-x-auto">
              <div className="grid grid-cols-7 gap-2 min-w-[480px]">
                {daily.map(d => {
                  const heightPct = Math.round((d.predictedCents / maxCents) * 100)
                  const above = d.vsAvgPct > 5
                  const below = d.vsAvgPct < -5
                  const fillColor = above ? '#17C5B0' : below ? '#D4A843' : '#1A8FD6'
                  return (
                    <div key={d.dayIndex} className="flex flex-col items-center">
                      <div className="w-full h-32 flex items-end mb-1.5">
                        <div className="w-full rounded-t-md transition-all" style={{ height: `${Math.max(heightPct, 4)}%`, backgroundColor: fillColor + '30', borderTop: `2px solid ${fillColor}` }} />
                      </div>
                      <span className="text-[10px] font-semibold text-[#F5F5F7]">{d.dayLabel}</span>
                      <span className="text-[10px] font-mono text-[#A1A1A8]">{formatCentsCompact(d.predictedCents)}</span>
                      <span className={clsx('text-[9px] font-mono', above ? 'text-[#17C5B0]' : below ? 'text-[#D4A843]' : 'text-[#A1A1A8]/40')}>
                        {d.vsAvgPct >= 0 ? '+' : ''}{d.vsAvgPct.toFixed(0)}%
                      </span>
                    </div>
                  )
                })}
              </div>
              </div>
              <p className="text-[10px] text-[#A1A1A8]/50 mt-3 font-mono">
                Δ vs weekly average — green = above, amber = below. Drives the schedule recommendations.
              </p>
            </div>
          </ScrollReveal>
        )
      })()}

      {/* Scenario Analysis + Ensemble Model Info */}
      {(() => {
        const periods = isDemo ? generateForecastPeriods() : []
        return (
          <ScrollReveal variant="fadeUp" delay={0.05}>
            <div className="card p-4 sm:p-5">
              <div className="flex items-center gap-2 mb-4">
                <Target size={14} className="text-[#7C5CFF]" />
                <h3 className="text-sm font-semibold text-[#F5F5F7]">Scenario Analysis</h3>
                <span className="text-[9px] text-[#A1A1A8]/40 ml-auto font-mono">{periods[0]?.modelMethod || 'ensemble'}</span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {periods.map(p => (
                  <div key={p.label} className="rounded-lg border border-[#1F1F23] p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-[#F5F5F7]">{p.label}</span>
                      {p.errorRate != null && (
                        <span className="text-[9px] font-mono text-[#A1A1A8]/40">{(p.errorRate * 100).toFixed(0)}% error rate</span>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <TrendingUp size={10} className="text-[#17C5B0]" />
                          <span className="text-[10px] text-[#A1A1A8]">Optimistic</span>
                        </div>
                        <span className="text-[11px] font-mono text-[#17C5B0]">{formatCentsCompact(p.scenarioOptimisticCents || Math.round(p.predictedCents * 1.15))}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Minus size={10} className="text-[#1A8FD6]" />
                          <span className="text-[10px] text-[#A1A1A8]">Expected</span>
                        </div>
                        <span className="text-[11px] font-mono font-semibold text-[#F5F5F7]">{formatCentsCompact(p.scenarioExpectedCents || p.predictedCents)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <TrendingDown size={10} className="text-red-400" />
                          <span className="text-[10px] text-[#A1A1A8]">Pessimistic</span>
                        </div>
                        <span className="text-[11px] font-mono text-red-400">{formatCentsCompact(p.scenarioPessimisticCents || Math.round(p.predictedCents * 0.85))}</span>
                      </div>
                    </div>
                    <div className="mt-2 pt-2 border-t border-[#1F1F23]/50 flex items-center justify-between">
                      <span className="text-[9px] text-[#A1A1A8]/40">Confidence</span>
                      <span className="text-[10px] font-mono text-[#F5F5F7]">{p.confidence}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </ScrollReveal>
        )
      })()}

      {/* Chart: Historical + Forecast */}
      {(chartData.length > 0 || awaitingData) && (
        <ScrollReveal variant="fadeUp" delay={0.1}>
          <div className="card p-4 sm:p-5" data-walkthrough="revenue-forecast-chart">
            <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Revenue: Actual vs Forecast</h3>
            <ForecastChart data={chartData} height={300} gradientId="forecasts-page" />
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
          description="Forecasts unlock after 30 days of POS data. Keep your POS connected and we'll start generating revenue predictions automatically."
        />
      )}
    </div>
  )
}
