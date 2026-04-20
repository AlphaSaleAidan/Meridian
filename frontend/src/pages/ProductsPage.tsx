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

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

type SortKey = 'revenue' | 'quantity' | 'name'

export default function ProductsPage() {
  const [days, setDays] = useState(30)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<SortKey>('revenue')
  const products = useApi(() => api.products(ORG_ID, days), [days])

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Products</h1>
          <p className="text-sm text-slate-400 mt-1">
            {data.total_products} active products • {formatCentsCompact(totalRevenue)} total revenue
          </p>
        </div>
        <div className="flex gap-1 bg-slate-800/60 rounded-lg p-1 self-start">
          {[7, 30, 90].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={clsx(
                'px-3 py-2 sm:py-1.5 text-xs font-medium rounded-md transition-colors',
                days === d ? 'bg-meridian-700 text-white' : 'text-slate-400 hover:text-white'
              )}
            >
              {d}D
            </button>
          ))}
        </div>
      </div>

      {/* Top Products Chart */}
      {chartData.length > 0 && (
        <div className="card p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-white mb-4">Top Products by Revenue</h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
              <XAxis type="number" tick={{ fill: '#64748b', fontSize: 10 }} axisLine={false} tickLine={false}
                tickFormatter={v => `$${v >= 1000 ? `${(v/1000).toFixed(0)}K` : v}`} />
              <YAxis type="category" dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false}
                tickLine={false} width={110} />
              <Tooltip
                contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                formatter={(v: number) => [formatCents(v * 100), 'Revenue']}
              />
              <Bar dataKey="revenue" fill="#338bff" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Search + Sort */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="relative flex-1 sm:max-w-sm">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search products..."
            className="w-full pl-9 pr-4 py-2.5 sm:py-2 bg-slate-800/60 border border-slate-700/40 rounded-lg text-sm text-white placeholder-slate-500 focus:outline-none focus:border-meridian-600"
          />
        </div>
        <div className="flex items-center gap-1 bg-slate-800/60 rounded-lg p-1 self-start">
          {([['revenue', 'Revenue'], ['quantity', 'Qty'], ['name', 'Name']] as [SortKey, string][]).map(([key, label]) => (
            <button
              key={key}
              onClick={() => setSortBy(key)}
              className={clsx(
                'px-3 py-2 sm:py-1.5 text-xs font-medium rounded-md transition-colors',
                sortBy === key ? 'bg-slate-700 text-white' : 'text-slate-400 hover:text-white'
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Products — cards on mobile, table on desktop */}
      {filtered.length > 0 ? (
        <>
          {/* Mobile: cards */}
          <div className="space-y-2 sm:hidden">
            {filtered.map(p => {
              const pct = totalRevenue > 0 ? (p.total_revenue_cents / totalRevenue * 100) : 0
              return (
                <div key={p.product_id} className="card p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                      <Package size={14} className="text-slate-500" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-white text-sm truncate">{p.name}</p>
                      {p.sku && <p className="text-xs text-slate-500">{p.sku}</p>}
                    </div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div>
                      <p className="text-xs text-slate-500">Revenue</p>
                      <p className="text-sm font-semibold text-white">{formatCents(p.total_revenue_cents)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">Qty Sold</p>
                      <p className="text-sm font-semibold text-white">{formatNumber(p.total_quantity)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-slate-500">% Total</p>
                      <p className="text-sm font-semibold text-white">{pct.toFixed(1)}%</p>
                    </div>
                  </div>
                  <div className="mt-3 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-meridian-600 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Desktop: table */}
          <div className="card overflow-hidden hidden sm:block">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800/40">
                    <th className="px-5 py-3 text-left text-xs font-medium text-slate-400 uppercase tracking-wider">Product</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Price</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Revenue</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">Qty Sold</th>
                    <th className="px-5 py-3 text-right text-xs font-medium text-slate-400 uppercase tracking-wider">% of Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/30">
                  {filtered.map(p => {
                    const pct = totalRevenue > 0 ? (p.total_revenue_cents / totalRevenue * 100) : 0
                    return (
                      <tr key={p.product_id} className="hover:bg-slate-800/20">
                        <td className="px-5 py-3">
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center flex-shrink-0">
                              <Package size={14} className="text-slate-500" />
                            </div>
                            <div>
                              <p className="font-medium text-white">{p.name}</p>
                              {p.sku && <p className="text-xs text-slate-500">{p.sku}</p>}
                            </div>
                          </div>
                        </td>
                        <td className="px-5 py-3 text-right text-slate-300">
                          {p.price_cents ? formatCents(p.price_cents) : '—'}
                        </td>
                        <td className="px-5 py-3 text-right font-medium text-white">
                          {formatCents(p.total_revenue_cents)}
                        </td>
                        <td className="px-5 py-3 text-right text-slate-300">
                          {formatNumber(p.total_quantity)}
                        </td>
                        <td className="px-5 py-3">
                          <div className="flex items-center justify-end gap-2">
                            <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                              <div className="h-full bg-meridian-600 rounded-full" style={{ width: `${Math.min(pct, 100)}%` }} />
                            </div>
                            <span className="text-xs text-slate-400 w-10 text-right">{pct.toFixed(1)}%</span>
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <EmptyState
          title="No products found"
          description={search ? 'Try a different search term' : 'Products will appear here after your POS data syncs.'}
        />
      )}
    </div>
  )
}
