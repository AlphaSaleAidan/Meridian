import { clsx } from 'clsx'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { DollarSign, TrendingDown, AlertTriangle, Target } from 'lucide-react'
import { generateMarginWaterfall, type MarginItem } from '@/lib/agent-data'
import { formatCents, formatCentsCompact } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

export default function MarginsPage() {
  const items = generateMarginWaterfall()

  const totalRevenue = items.reduce((s, i) => s + i.revenueCents, 0)
  const totalCost = items.reduce((s, i) => s + i.costCents, 0)
  const totalMargin = items.reduce((s, i) => s + i.marginCents, 0)
  const totalLeakage = items.reduce((s, i) => s + i.leakageCents, 0)
  const avgMarginPct = Math.round(totalMargin / totalRevenue * 100)

  const chartData = items.map(i => ({
    name: i.name.length > 12 ? i.name.slice(0, 10) + '..' : i.name,
    margin: i.marginPct,
    revenue: i.revenueCents / 100,
    cost: i.costCents / 100,
    leakage: i.leakageCents / 100,
  }))

  const waterfallData = [
    { name: 'Revenue', value: totalRevenue / 100, fill: '#1A8FD6' },
    { name: 'COGS', value: -totalCost / 100, fill: '#EF4444' },
    { name: 'Leakage', value: -totalLeakage / 100, fill: '#F97316' },
    { name: 'Net Margin', value: (totalMargin - totalLeakage) / 100, fill: '#17C5B0' },
  ]

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Margin Analysis</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Margin Optimizer agent • Identifies leakage and pricing opportunities
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <DollarSign size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Revenue</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatCentsCompact(totalRevenue)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Target size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Avg Margin</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{avgMarginPct}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <TrendingDown size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Leakage</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{formatCentsCompact(totalLeakage)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <DollarSign size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Net Margin</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{formatCentsCompact(totalMargin - totalLeakage)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Margin Waterfall</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={waterfallData} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
              <XAxis dataKey="name" tick={{ fill: '#A1A1A8', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false}
                tickFormatter={v => `$${Math.abs(v) >= 1000 ? `${(Math.abs(v)/1000).toFixed(0)}K` : Math.abs(v)}`} width={50} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [formatCents(Math.abs(v) * 100), '']} />
              <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                {waterfallData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} fillOpacity={0.8} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Margin by Product</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}%`} domain={[0, 100]} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#A1A1A8', fontSize: 10 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip contentStyle={tooltipStyle} formatter={(v: number) => [`${v}%`, 'Margin']} />
              <Bar dataKey="margin" radius={[0, 4, 4, 0]} fillOpacity={0.8}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.margin >= 70 ? '#17C5B0' : entry.margin >= 60 ? '#1A8FD6' : '#F97316'} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Leakage Details</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[500px]">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th className="text-right">Revenue</th>
                  <th className="text-right">Margin</th>
                  <th className="text-right">Leakage</th>
                </tr>
              </thead>
              <tbody>
                {items.filter(i => i.leakageCents > 0).sort((a, b) => b.leakageCents - a.leakageCents).map(item => (
                  <tr key={item.name}>
                    <td className="font-medium text-[#F5F5F7]">{item.name}</td>
                    <td className="text-right font-mono text-[#A1A1A8]">{formatCents(item.revenueCents)}</td>
                    <td className="text-right">
                      <span className={clsx('font-mono font-medium', item.marginPct >= 70 ? 'text-[#17C5B0]' : item.marginPct >= 60 ? 'text-[#F5F5F7]' : 'text-amber-400')}>
                        {item.marginPct}%
                      </span>
                    </td>
                    <td className="text-right font-mono text-red-400">{formatCents(item.leakageCents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
