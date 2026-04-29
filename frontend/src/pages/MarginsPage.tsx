import { useState } from 'react'
import { clsx } from 'clsx'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts'
import { DollarSign, TrendingDown, AlertTriangle, Target, ChevronDown, ChevronUp, Calculator } from 'lucide-react'
import { generateMarginWaterfall, type MarginItem } from '@/lib/agent-data'
import { formatCents, formatCentsCompact } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

function FormulaBreakdown({ item }: { item: MarginItem }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="mt-2">
      <button onClick={() => setOpen(!open)} className="flex items-center gap-1.5 text-[10px] text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
        <Calculator size={10} />
        {open ? 'Hide' : 'View'} Cost Formulas
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>
      {open && (
        <div className="mt-2 p-3 bg-[#0A0A0B] rounded-lg border border-[#1F1F23] space-y-1.5">
          {item.ingredients.map(ing => (
            <div key={ing.name} className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">{ing.name}</span>
              <span className="font-mono text-[#F5F5F7]">
                {formatCents(Math.round(ing.batchCostCents / ing.batchServings))}/serving
              </span>
            </div>
          ))}
          <div className="border-t border-[#1F1F23] pt-1.5 space-y-1">
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Raw Cost/Serving</span>
              <span className="font-mono text-[#F5F5F7]">{formatCents(item.rawCostPerServingCents)}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Waste Factor</span>
              <span className="font-mono text-[#F5F5F7]">{(item.wasteFactor * 100).toFixed(1)}%</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Waste-Adj Cost</span>
              <span className="font-mono text-[#F5F5F7]">{formatCents(item.wasteAdjustedCostCents)}</span>
            </div>
            <div className="flex justify-between text-[10px]">
              <span className="text-[#A1A1A8]">Pour Cost %</span>
              <span className="font-mono text-[#F5F5F7]">{item.pourCostPct}%</span>
            </div>
            <div className="flex justify-between text-[10px] font-semibold">
              <span className="text-[#17C5B0]">Margin/Unit</span>
              <span className="font-mono text-[#17C5B0]">{formatCents(item.marginPerUnitCents)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
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


  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Margin Analysis</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Margin Optimizer agent • Formula-driven cost accounting with waste-adjusted margins
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
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{avgMarginPct}%</p>
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
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatCentsCompact(totalLeakage)}</p>
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
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatCentsCompact(totalMargin - totalLeakage)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* Margin Formulas Reference */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <DashboardTiltCard className="card p-4 sm:p-5">
          <div className="flex items-center gap-2 mb-3">
            <Calculator size={16} className="text-[#7C5CFF]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Active Margin Formulas</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-2">
            {[
              ['Raw Cost/Serving', 'Batch Cost ÷ Servings per Batch'],
              ['Pour Cost %', 'COGS ÷ Revenue × 100'],
              ['Waste Factor', 'Σ(Waste% × Ingredient Cost) ÷ Total Cost'],
              ['Waste-Adj Cost', 'Raw Cost ÷ (1 − Waste Factor)'],
              ['Margin/Unit', 'Selling Price − Waste-Adj Cost'],
              ['Leakage', 'Waste Delta + Discounts + Comps'],
            ].map(([label, formula]) => (
              <div key={label} className="flex items-baseline gap-2 py-1">
                <span className="text-[10px] font-semibold text-[#F5F5F7] whitespace-nowrap">{label}</span>
                <span className="text-[10px] text-[#A1A1A8] font-mono">{formula}</span>
              </div>
            ))}
          </div>
        </DashboardTiltCard>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Margin by Product</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#F5F5F7', fontSize: 10, fontFamily: 'Geist Mono, monospace' }} axisLine={false} tickLine={false}
                tickFormatter={v => `${v}%`} domain={[0, 100]} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#F5F5F7', fontSize: 10, fontFamily: 'Geist Mono, monospace' }} axisLine={false} tickLine={false} width={90} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number) => [`${v}%`, 'Margin']} />
              <Bar dataKey="margin" radius={[0, 4, 4, 0]} fillOpacity={0.85}>
                {chartData.map((entry, i) => (
                  <Cell key={i} fill={entry.margin >= 70 ? '#17C5B0' : entry.margin >= 60 ? '#1A8FD6' : '#F97316'} />
                ))}
                <LabelList
                  dataKey="margin"
                  position="right"
                  formatter={(v: number) => `${v}%`}
                  style={{ fill: '#F5F5F7', fontSize: 10, fontFamily: 'Geist Mono, monospace', fontWeight: 600 }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </ScrollReveal>

      {/* Product Cost Breakdown */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Product Cost Breakdown</h3>
            <p className="text-[10px] text-[#A1A1A8] mt-0.5">Click "View Cost Formulas" on any product to see ingredient-level calculations</p>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[700px]">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th className="text-right">Price</th>
                  <th className="text-right">Cost/Serving</th>
                  <th className="text-right">Pour Cost</th>
                  <th className="text-right">Margin</th>
                  <th className="text-right">Leakage</th>
                  <th className="text-right">Monthly Rev</th>
                </tr>
              </thead>
              <tbody>
                {items.sort((a, b) => b.revenueCents - a.revenueCents).map(item => (
                  <tr key={item.name}>
                    <td>
                      <span className="font-medium text-[#F5F5F7]">{item.name}</span>
                      <FormulaBreakdown item={item} />
                    </td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCents(item.sellingPriceCents)}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCents(item.wasteAdjustedCostCents)}</td>
                    <td className="text-right">
                      <span className={clsx('font-mono font-medium', item.pourCostPct <= 25 ? 'text-[#17C5B0]' : item.pourCostPct <= 35 ? 'text-[#F5F5F7]' : 'text-amber-400')}>
                        {item.pourCostPct}%
                      </span>
                    </td>
                    <td className="text-right">
                      <span className={clsx('font-mono font-semibold', item.marginPct >= 70 ? 'text-[#17C5B0]' : item.marginPct >= 60 ? 'text-[#F5F5F7]' : 'text-amber-400')}>
                        {item.marginPct}%
                      </span>
                    </td>
                    <td className="text-right font-mono text-red-400">
                      {item.leakageCents > 0 ? formatCents(item.leakageCents) : '—'}
                    </td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCentsCompact(item.revenueCents)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>

      {/* Leakage Details */}
      <ScrollReveal variant="fadeUp" delay={0.25}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <div className="flex items-center gap-2">
              <AlertTriangle size={14} className="text-amber-400" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Leakage Sources</h3>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[500px]">
              <thead>
                <tr>
                  <th className="text-left">Product</th>
                  <th className="text-right">Waste %</th>
                  <th className="text-right">Waste Cost</th>
                  <th className="text-right">Other Leakage</th>
                  <th className="text-right">Total Leakage</th>
                </tr>
              </thead>
              <tbody>
                {items.filter(i => i.leakageCents > 0).sort((a, b) => b.leakageCents - a.leakageCents).map(item => {
                  const wasteDelta = (item.wasteAdjustedCostCents - item.rawCostPerServingCents) * item.monthlySales
                  const otherLeakage = item.leakageCents - wasteDelta
                  return (
                    <tr key={item.name}>
                      <td className="font-medium text-[#F5F5F7]">{item.name}</td>
                      <td className="text-right font-mono text-[#F5F5F7]">{(item.wasteFactor * 100).toFixed(1)}%</td>
                      <td className="text-right font-mono text-amber-400">{formatCents(wasteDelta)}</td>
                      <td className="text-right font-mono text-red-400">{otherLeakage > 0 ? formatCents(otherLeakage) : '—'}</td>
                      <td className="text-right font-mono font-semibold text-red-400">{formatCents(item.leakageCents)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
