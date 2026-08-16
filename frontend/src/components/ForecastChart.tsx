/**
 * Revenue: actual against forecast.
 *
 * LIFTED, NOT REDRAWN. This is the chart that was already inline in
 * ForecastsPage — same monotone curves, same two gradients, same dashed
 * forecast stroke, same faint upper-bound band. It moved here so the Forecasts
 * page and the trade workspace draw the same picture from one implementation
 * rather than two that drift.
 *
 * The treatment carries meaning and is worth keeping exactly: what HAPPENED is
 * a solid blue line, what is PREDICTED is a dashed teal one, and the two are
 * one continuous curve so the eye reads the forecast as the same series
 * continuing rather than a separate claim. The upper bound sits behind at 4%
 * opacity — present enough to show the forecast is a range, faint enough that
 * nobody mistakes it for a promise.
 */
import {
  Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { formatCents, formatChartTick } from '@/lib/format'

export interface ForecastPoint {
  date: string
  actual: number | null
  predicted: number | null
  lower?: number | null
  upper?: number | null
}

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

export default function ForecastChart({
  data, height = 300, gradientId = 'fc',
}: {
  data: ForecastPoint[]
  height?: number
  /** Gradients are document-scoped, so two charts on one page need distinct
   *  ids or the second silently borrows the first's fill. */
  gradientId?: string
}) {
  const actualGrad = `${gradientId}-actual`
  const forecastGrad = `${gradientId}-forecast`

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
        <defs>
          <linearGradient id={actualGrad} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#1A8FD6" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#1A8FD6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id={forecastGrad} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#17C5B0" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#17C5B0" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: string) => {
            const d = new Date(v)
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
          }}
          interval="preserveStartEnd"
        />
        <YAxis
          tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={formatChartTick}
          width={55}
        />
        <Tooltip
          contentStyle={tooltipStyle}
          itemStyle={{ color: '#F5F5F7' }}
          labelStyle={{ color: '#A1A1A8' }}
          formatter={(v: any, name: string) => [v != null ? formatCents(v * 100) : '—', name]}
          cursor={{ stroke: '#1A8FD6', strokeWidth: 1, strokeDasharray: '4 4' }}
        />
        <Area
          type="monotone" dataKey="actual" stroke="#1A8FD6" strokeWidth={2}
          fill={`url(#${actualGrad})`} dot={false}
          activeDot={{ r: 4, fill: '#1A8FD6', stroke: '#0A0A0B', strokeWidth: 2 }}
          name="Actual" connectNulls={false}
        />
        <Area
          type="monotone" dataKey="predicted" stroke="#17C5B0" strokeWidth={2}
          strokeDasharray="6 3" fill={`url(#${forecastGrad})`} dot={false}
          activeDot={{ r: 4, fill: '#17C5B0', stroke: '#0A0A0B', strokeWidth: 2 }}
          name="Forecast" connectNulls={false}
        />
        {data.some((d) => d.upper != null) && (
          <Area
            type="monotone" dataKey="upper" stroke="none" fill="#17C5B0"
            fillOpacity={0.04} dot={false} name="Upper Bound" connectNulls={false}
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  )
}
