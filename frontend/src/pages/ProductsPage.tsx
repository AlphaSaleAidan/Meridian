import { useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { clsx } from 'clsx'
import { Package, Search } from 'lucide-react'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { formatCents, formatCentsCompact, formatNumber } from '@/lib/format'
import { LoadingPage, ErrorState, EmptyState } from '@/components/LoadingState'
import ScrollReveal from '@/components/ScrollReveal'
import { useOrgId } from '@/hooks/useOrg'
import { useDemoContext } from '@/lib/demo-context'

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

type SortKey = 'revenue' | 'quantity' | 'name'

export default function ProductsPage() {
  const [days, setDays] = useState(30)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('revenue')
  const orgId = useOrgId()
  const { businessType } = useDemoContext()
  const products = useApi(() => api.products(orgId, days), [orgId, days, businessType])

  if (products.loading) return <LoadingPage />
  if (products.error) return <ErrorState message={products.error} onRetry={products.refetch} />

  const data = products.data!
  const totalRevenue = data.products.reduce((s, p) => s + p.total_revenue_cents, 0)

  let filtered = data.products.filter(p =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )
  filtered.sort((a, b) => {
    if (sortBy === 'revenue') return b.total_revenue_cents - a.total_revenue_cents
    if (sortBy === 'quantity') return b.total_quantity - a.total_quantity
    return a.name.localeCompare(b.name)
  })

  const chartData = filtered.slice(0, 8).map(p => ({
    name: p.name.length > 16 ? p.name.slice(0, 14) + '...' : p.name,
    revenue: p.total_revenue_cents / 100,
    quantity: p.total_quantity,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Products</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              <span className="font-mono">{data.total_products}</span> active products • <span className="font-mono">{formatCentsCompact(totalRevenue)}</span> total revenue
            </p>
          </div>
          <div className="period-toggle">
            {[7, 30, 90].map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={days === d ? 'period-btn-active' : 'period-btn-inactive'}
              >
                {d}D
              </button>
            ))}
          </div>
        </div>
      </ScrollReveal>

      {/* Top Products Chart */}
      {chartData.length > 0 && (
        <ScrollReveal variant="fadeUp" delay={0.1}>
          <div className="card p-4 sm:p-5">
            <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Top Products by Revenue</h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" horizontal={false} />
                <XAxis type="number" tick={{ fill: '#A1A1A8', fontSize: 10, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false}
                  tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`} />
                <YAxis type="category" dataKey="name" tick={{ fill: '#A1A1A8', fontSize: 10 }} axisLine={false}
                  tickLine={false} width={110} />
                <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number) => [formatCents(v * 100), 'Revenue']}
                  cursor={{ fill: 'rgba(26, 143, 214, 0.04)' }} />
                <Bar dataKey="revenue" fill="#1A8FD6" radius={[0, 4, 4, 0]} fillOpacity={0.8} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </ScrollReveal>
      )}

      {/* Search + Sort */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
          <div className="relative flex-1 sm:max-w-sm">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/50" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search products..."
              className="w-full pl-9 pr-4 py-2.5 sm:py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/40 focus:shadow-[0_0_0_3px_rgba(124,92,255,0.08)] transition-all"
            />
          </div>
          <div className="period-toggle">
            {([['revenue', 'Revenue'], ['quantity', 'Qty'], ['name', 'Name']] as [SortKey, string][]).map(([key, label]) => (
              <button
                key={key}
                onClick={() => setSortBy(key)}
                className={sortBy === key ? 'period-btn-active' : 'period-btn-inactive'}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </ScrollReveal>

      {/* Products — cards on mobile, table on desktop */}
      {filtered.length > 0 ? (
        <ScrollReveal variant="fadeUp" delay={0.2}>
          {/* Mobile: cards */}
          <div className="space-y-2 sm:hidden">
            {filtered.map(p => {
              const pct = totalRevenue > 0 ? (p.total_revenue_cents / totalRevenue * 100) : 0
              return (
                <div key={p.product_id} className="card-hover p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-[#1F1F23] flex items-center justify-center flex-shrink-0">
                      <Package size={14} className="text-[#A1A1A8]/50" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-[#F5F5F7] text-sm truncate">{p.name}</p>
                      {p.sku && <p className="text-xs text-[#A1A1A8]/50 font-mono">{p.sku}</p>}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <p className="text-xs text-[#A1A1A8]/60">Revenue</p>
                      <p className="text-sm font-semibold font-mono text-[#F5F5F7]">{formatCents(p.total_revenue_cents)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#A1A1A8]/60">Qty Sold</p>
                      <p className="text-sm font-semibold font-mono text-[#F5F5F7]">{formatNumber(p.total_quantity)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#A1A1A8]/60">% Total</p>
                      <p className="text-sm font-semibold font-mono text-[#F5F5F7]">{pct.toFixed(1)}%</p>
                    </div>
                  </div>
                  <div className="mt-3 h-1.5 bg-[#1F1F23] rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] transition-all duration-700" style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop: table */}
          <div className="card overflow-hidden hidden sm:block">
            <div className="overflow-x-auto">
              <table className="pm-table">
                <thead>
                  <tr>
                    <th className="text-left">Product</th>
                    <th className="text-right">Price</th>
                    <th className="text-right">Revenue</th>
                    <th className="text-right">Qty Sold</th>
                    <th className="text-right">% of Total</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map(p => {
                    const pct = totalRevenue > 0 ? (p.total_revenue_cents / totalRevenue * 100) : 0
                    return (
                      <tr key={p.product_id}>
                        <td>
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-[#1F1F23] flex items-center justify-center flex-shrink-0">
                              <Package size={14} className="text-[#A1A1A8]/50" />
                            </div>
                            <div>
                              <p className="font-medium text-[#F5F5F7]">{p.name}</p>
                              {p.sku && <p className="text-xs text-[#A1A1A8]/50 font-mono">{p.sku}</p>}
                            </div>
                          </div>
                        </td>
                        <td className="text-right font-mono text-[#A1A1A8]">
                          {p.price_cents ? formatCents(p.price_cents) : '—'}
                        </td>
                        <td className="text-right font-medium font-mono text-[#F5F5F7]">
                          {formatCents(p.total_revenue_cents)}
                        </td>
                        <td className="text-right font-mono text-[#A1A1A8]">
                          {formatNumber(p.total_quantity)}
                        </td>
                        <td>
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-1.5 bg-[#1F1F23] rounded-full overflow-hidden">
                              <div className="h-full rounded-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0]" style={{ width: `${Math.min(pct, 100)}%` }} />
                            </div>
                            <span className="text-xs font-mono text-[#A1A1A8] w-10 text-right">{pct.toFixed(1)}%</span>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </ScrollReveal>
      ) : (
        <EmptyState
          title="No products found"
          description={search ? 'Try a different search term' : 'Products will appear here after your POS data syncs.'}
        />
      )}
    </div>
  )
}
