import { useState, useRef } from 'react'
import {
  Package, AlertTriangle, TrendingUp, TrendingDown, Minus,
  Upload, Search, ArrowUpDown, Box, Layers,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useApi } from '@/hooks/useApi'
import { api, InventoryItem } from '@/lib/api'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import { formatNumber, formatRelative } from '@/lib/format'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

type SortField = 'product_name' | 'current_stock' | 'days_until_reorder' | 'predicted_daily_usage' | 'trend_pct'
type SortDir = 'asc' | 'desc'
type Filter = 'all' | 'low_stock' | 'overstocked' | 'trending_up'

function TrendBadge({ trend, pct }: { trend: string; pct: number }) {
  const Icon = trend === 'rising' ? TrendingUp : trend === 'falling' ? TrendingDown : Minus
  const color = trend === 'rising' ? 'text-[#17C5B0]' : trend === 'falling' ? 'text-red-400' : 'text-[#A1A1A8]/50'
  const bg = trend === 'rising' ? 'bg-[#17C5B0]/10' : trend === 'falling' ? 'bg-red-400/10' : 'bg-[#1F1F23]'

  return (
    <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-medium', color, bg)}>
      <Icon size={10} />
      {pct > 0 ? '+' : ''}{pct}%
    </span>
  )
}

function StockBar({ current, reorder, max }: { current: number; reorder: number; max: number }) {
  const pct = Math.min((current / max) * 100, 100)
  const reorderPct = Math.min((reorder / max) * 100, 100)
  const isLow = current <= reorder
  const isHigh = current > max * 0.85

  return (
    <div className="relative w-full h-2 bg-[#1F1F23] rounded-full overflow-hidden">
      {/* Reorder line */}
      <div
        className="absolute top-0 h-full w-px bg-amber-400/40 z-10"
        style={{ left: `${reorderPct}%` }}
      />
      <div
        className="h-full rounded-full transition-all duration-700"
        style={{
          width: `${pct}%`,
          background: isLow
            ? 'linear-gradient(90deg, #ef4444, #f87171)'
            : isHigh
              ? 'linear-gradient(90deg, #f59e0b, #fbbf24)'
              : 'linear-gradient(90deg, #1A8FD6, #17C5B0)',
        }}
      />
    </div>
  )
}

export default function InventoryPage() {
  const inventory = useApi(() => api.inventory(ORG_ID), [])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<Filter>('all')
  const [sortField, setSortField] = useState<SortField>('days_until_reorder')
  const [sortDir, setSortDir] = useState<SortDir>('asc')
  const [showUpload, setShowUpload] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  if (inventory.loading) return <LoadingPage />
  if (inventory.error) return <ErrorState message={inventory.error} onRetry={inventory.refetch} />

  const data = inventory.data!

  // Filter
  let items = [...data.items]
  if (search) {
    const q = search.toLowerCase()
    items = items.filter(i =>
      i.product_name.toLowerCase().includes(q) ||
      i.sku.toLowerCase().includes(q) ||
      i.category.toLowerCase().includes(q)
    )
  }
  if (filter === 'low_stock') items = items.filter(i => i.days_until_reorder !== null && i.days_until_reorder <= 2)
  if (filter === 'overstocked') items = items.filter(i => i.current_stock > i.predicted_daily_usage * 12)
  if (filter === 'trending_up') items = items.filter(i => i.trend === 'rising')

  // Sort
  items.sort((a, b) => {
    let va: number, vb: number
    switch (sortField) {
      case 'product_name': return sortDir === 'asc' ? a.product_name.localeCompare(b.product_name) : b.product_name.localeCompare(a.product_name)
      case 'current_stock': va = a.current_stock; vb = b.current_stock; break
      case 'days_until_reorder': va = a.days_until_reorder ?? 999; vb = b.days_until_reorder ?? 999; break
      case 'predicted_daily_usage': va = a.predicted_daily_usage; vb = b.predicted_daily_usage; break
      case 'trend_pct': va = a.trend_pct; vb = b.trend_pct; break
      default: va = 0; vb = 0
    }
    return sortDir === 'asc' ? va - vb : vb - va
  })

  const toggleSort = (field: SortField) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('asc') }
  }

  const maxStock = Math.max(...data.items.map(i => i.current_stock), 1)

  const filters: { key: Filter; label: string; count?: number }[] = [
    { key: 'all', label: 'All Items' },
    { key: 'low_stock', label: 'Low Stock', count: data.alerts.low_stock },
    { key: 'overstocked', label: 'Overstocked', count: data.alerts.overstocked },
    { key: 'trending_up', label: 'Trending Up', count: data.alerts.trending_up },
  ]

  const handleUpload = () => {
    setShowUpload(true)
    setTimeout(() => setShowUpload(false), 3000)
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Inventory</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              <span className="font-mono">{formatNumber(data.total)}</span> products tracked • AI-predicted optimal levels
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input type="file" ref={fileRef} className="hidden" accept=".csv,.xlsx" onChange={handleUpload} />
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-[#A1A1A8] bg-[#111113] border border-[#1F1F23] rounded-lg hover:border-[#1A8FD6]/40 hover:text-[#F5F5F7] transition-all"
            >
              <Upload size={13} /> Upload Stock
            </button>
          </div>
        </div>
      </ScrollReveal>

      {showUpload && (
        <div className="card p-3 border-[#17C5B0]/20 bg-[#17C5B0]/[0.03] flex items-center gap-2 animate-fade-in">
          <span className="text-xs text-[#17C5B0]">✓ Stock levels uploaded successfully. AI will recalculate predictions.</span>
        </div>
      )}

      {/* Alert Cards */}
      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Layers size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Total SKUs</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{formatNumber(data.total)}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-red-400/10 flex items-center justify-center">
                <AlertTriangle size={16} className="text-red-400" />
              </div>
              <div>
                <p className="stat-label">Low Stock</p>
                <p className="text-lg font-bold text-red-400 font-mono">{data.alerts.low_stock}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <Box size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Overstocked</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{data.alerts.overstocked}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <TrendingUp size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Trending Up</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{data.alerts.trending_up}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* Filters + Search */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="period-toggle">
            {filters.map(f => (
              <button
                key={f.key}
                onClick={() => setFilter(f.key)}
                className={clsx(
                  filter === f.key ? 'period-btn-active' : 'period-btn-inactive',
                  'flex items-center gap-1'
                )}
              >
                {f.label}
                {f.count !== undefined && f.count > 0 && (
                  <span className={clsx(
                    'text-[10px] font-mono px-1.5 py-0 rounded-full',
                    filter === f.key ? 'bg-white/20' : 'bg-[#1F1F23]'
                  )}>{f.count}</span>
                )}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <div className="relative w-full sm:w-56">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search products..."
              className="w-full pl-8 pr-3 py-2 text-xs bg-[#111113] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:border-[#1A8FD6]/40 focus:outline-none transition-colors"
            />
          </div>
        </div>
      </ScrollReveal>

      {/* Inventory Table */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[700px]">
              <thead>
                <tr>
                  <th className="text-left cursor-pointer select-none" onClick={() => toggleSort('product_name')}>
                    <span className="flex items-center gap-1">Product <ArrowUpDown size={10} className="text-[#A1A1A8]/30" /></span>
                  </th>
                  <th className="text-center cursor-pointer select-none" onClick={() => toggleSort('current_stock')}>
                    <span className="flex items-center justify-center gap-1">Stock <ArrowUpDown size={10} className="text-[#A1A1A8]/30" /></span>
                  </th>
                  <th className="text-left w-[140px]">Level</th>
                  <th className="text-center cursor-pointer select-none" onClick={() => toggleSort('predicted_daily_usage')}>
                    <span className="flex items-center justify-center gap-1">Daily Usage <ArrowUpDown size={10} className="text-[#A1A1A8]/30" /></span>
                  </th>
                  <th className="text-center cursor-pointer select-none" onClick={() => toggleSort('days_until_reorder')}>
                    <span className="flex items-center justify-center gap-1">Reorder In <ArrowUpDown size={10} className="text-[#A1A1A8]/30" /></span>
                  </th>
                  <th className="text-center cursor-pointer select-none" onClick={() => toggleSort('trend_pct')}>
                    <span className="flex items-center justify-center gap-1">Trend <ArrowUpDown size={10} className="text-[#A1A1A8]/30" /></span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => {
                  const isLow = item.days_until_reorder !== null && item.days_until_reorder <= 2
                  const isOver = item.current_stock > item.predicted_daily_usage * 12

                  return (
                    <tr key={item.id} className={clsx(isLow && 'bg-red-400/[0.02]')}>
                      <td>
                        <div className="flex items-center gap-2.5">
                          <div className={clsx(
                            'w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0',
                            item.category === 'drinks' ? 'bg-[#1A8FD6]/10' : 'bg-[#17C5B0]/10'
                          )}>
                            <Package size={12} className={item.category === 'drinks' ? 'text-[#1A8FD6]' : 'text-[#17C5B0]'} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-[#F5F5F7]">{item.product_name}</p>
                            <p className="text-[10px] text-[#A1A1A8]/40 font-mono">{item.sku}</p>
                          </div>
                        </div>
                      </td>
                      <td className="text-center">
                        <span className={clsx(
                          'font-mono text-sm font-medium',
                          isLow ? 'text-red-400' : 'text-[#F5F5F7]'
                        )}>
                          {formatNumber(item.current_stock)}
                        </span>
                        <span className="text-[10px] text-[#A1A1A8]/30 ml-1">{item.unit}</span>
                      </td>
                      <td>
                        <StockBar current={item.current_stock} reorder={item.reorder_point} max={maxStock} />
                        <div className="flex justify-between mt-0.5">
                          <span className="text-[9px] text-[#A1A1A8]/20">0</span>
                          <span className="text-[9px] text-[#A1A1A8]/20">reorder: {item.reorder_point}</span>
                        </div>
                      </td>
                      <td className="text-center font-mono text-sm text-[#A1A1A8]">
                        {item.predicted_daily_usage}
                        <span className="text-[10px] text-[#A1A1A8]/30 ml-0.5">/day</span>
                      </td>
                      <td className="text-center">
                        {item.days_until_reorder !== null ? (
                          <span className={clsx(
                            'font-mono text-sm font-medium',
                            item.days_until_reorder <= 1 ? 'text-red-400' :
                            item.days_until_reorder <= 3 ? 'text-amber-400' :
                            'text-[#F5F5F7]'
                          )}>
                            {item.days_until_reorder}d
                          </span>
                        ) : (
                          <span className="text-[#A1A1A8]/30">—</span>
                        )}
                      </td>
                      <td className="text-center">
                        <TrendBadge trend={item.trend} pct={item.trend_pct} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {items.length === 0 && (
            <div className="py-12">
              <EmptyState title="No items match" description="Try adjusting your filters or search." />
            </div>
          )}
        </div>
      </ScrollReveal>

      {/* AI Predictions Info */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card p-4 sm:p-5 border-[#1A8FD6]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <TrendingUp size={16} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">AI-Predicted Optimal Levels</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Meridian analyzes your sales velocity, seasonal patterns, and demand trends to predict optimal stock levels.
                The <span className="text-amber-400 font-mono">reorder point</span> is calculated as a 3-day buffer based on predicted daily usage.
                Items flagged <span className="text-red-400">low stock</span> need reordering within 48 hours.
                Upload your current stock levels (CSV or Excel) to keep predictions accurate.
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
