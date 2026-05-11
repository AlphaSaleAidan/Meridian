import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { DailyRevenue } from '@/lib/api'
import { formatCents, formatChartDate } from '@/lib/format'

interface Props {
  data: DailyRevenue[]
  height?: number
}

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

export default function RevenueChart({ data, height = 300 }: Props) {
  const chartData = data.map(d => ({
    ...d,
    date: formatChartDate(d.date),
    revenue: d.revenue_cents / 100,
  }))

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Revenue Trend</h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7C5CFF" stopOpacity={0.25} />
              <stop offset="50%" stopColor="#7C5CFF" stopOpacity={0.08} />
              <stop offset="100%" stopColor="#7C5CFF" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1F1F23"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fill: '#A1A1A8', fontSize: 11, fontFamily: 'Geist Mono, monospace' }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
            angle={-35}
            textAnchor="end"
            height={50}
          />
          <YAxis
            tick={{ fill: '#A1A1A8', fontSize: 11, fontFamily: 'Geist Mono, monospace' }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(1)}K` : v}`}
            width={55}
            tickCount={5}
            domain={['dataMin', 'auto']}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            itemStyle={{ color: '#F5F5F7' }}
            labelStyle={{ color: '#A1A1A8' }}
            formatter={(value: number) => [`${formatCents(value * 100)}`, 'Revenue']}
            labelFormatter={(label: string) => label}
            cursor={{ stroke: '#7C5CFF', strokeWidth: 1, strokeDasharray: '4 4' }}
          />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#7C5CFF"
            strokeWidth={2}
            fill="url(#revenueGradient)"
            dot={false}
            activeDot={{
              r: 5,
              fill: '#7C5CFF',
              stroke: '#0A0A0B',
              strokeWidth: 2,
            }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
