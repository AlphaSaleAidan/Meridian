import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { DailyRevenue } from '@/lib/api'
import { formatCents, formatChartDate } from '@/lib/format'

interface Props {
  data: DailyRevenue[]
  height?: number
}

export default function RevenueChart({ data, height = 300 }: Props) {
  const chartData = data.map(d => ({
    ...d,
    date: formatChartDate(d.date),
    revenue: d.revenue_cents / 100,
  }))

  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-white mb-4">Revenue Trend</h3>
      <ResponsiveContainer width="100%" height={height}>
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1454e1" stopOpacity={0.3} />
              <stop offset="100%" stopColor="#1454e1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1e293b"
            vertical={false}
          />
          <XAxis
            dataKey="date"
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#0f172a',
              border: '1px solid #1e293b',
              borderRadius: '8px',
              fontSize: '12px',
            }}
            labelStyle={{ color: '#94a3b8' }}
            formatter={(value: number) => [formatCents(value * 100), 'Revenue']}
          />
          <Area
            type="monotone"
            dataKey="revenue"
            stroke="#1454e1"
            strokeWidth={2}
            fill="url(#revenueGradient)"
            dot={false}
            activeDot={{ r: 4, strokeWidth: 0, fill: '#338bff' }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
