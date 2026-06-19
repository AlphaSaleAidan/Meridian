import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { useOrgId } from '@/hooks/useOrg'
import { formatCents, formatCentsCompact, formatNumber, formatChartTick } from '@/lib/format'
import ScrollReveal from '@/components/ScrollReveal'

const tooltipStyle = {
  backgroundColor: '#111113',
  border: '1px solid #1F1F23',
  borderRadius: '10px',
  fontSize: '12px',
  color: '#F5F5F7',
  boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
}

// Historical revenue by calendar year + monthly trend — lets merchants see
// prior-year revenue from the ~18 months the backfill pulls.
export function HistoricalRevenueSection() {
  const orgId = useOrgId()
  const { data } = useApi<any>(() => api.annualRevenue(orgId), [orgId])
  const years = data?.years ?? []
  if (years.length === 0) return null

  const monthly = (data?.monthly ?? []).map((m: any) => ({
    label: m.month,
    revenue: (m.revenue_cents ?? 0) / 100,
  }))
  const cur = data?.current_year
  const prior = data?.prior_year
  const yoy = data?.yoy_pct

  return (
    <ScrollReveal variant="fadeUp" delay={0.05}>
      <div className="card p-4 sm:p-5">
        <div className="flex items-start justify-between mb-4 gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Historical Revenue</h3>
            <p className="text-[10px] text-[#A1A1A8]">Revenue by year — up to ~18 months of history</p>
          </div>
          {cur && prior && yoy != null && (
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCentsCompact(cur.revenue_cents)}</p>
              <p className={`text-[10px] font-mono ${yoy >= 0 ? 'text-[#17C5B0]' : 'text-amber-400'}`}>
                {yoy >= 0 ? '+' : ''}{yoy}% vs {prior.year}
              </p>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {years.map((y: any) => (
            <div key={y.year} className="rounded-lg bg-[#1F1F23]/40 p-3">
              <p className="text-[10px] text-[#A1A1A8]/60 font-mono">{y.year}</p>
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCentsCompact(y.revenue_cents)}</p>
              <p className="text-[10px] text-[#A1A1A8]/40">{formatNumber(y.transaction_count)} txns</p>
            </div>
          ))}
        </div>

        {monthly.length > 1 && (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={monthly} margin={{ top: 0, right: 5, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1F1F23" vertical={false} />
              <XAxis dataKey="label" tick={{ fill: '#A1A1A8', fontSize: 9, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#A1A1A8', fontSize: 9, fontFamily: 'Geist Mono' }} axisLine={false} tickLine={false} tickFormatter={formatChartTick} />
              <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: '#F5F5F7' }} labelStyle={{ color: '#A1A1A8' }} formatter={(v: number) => [formatCents(v * 100), 'Revenue']} cursor={{ fill: 'rgba(26,143,214,0.04)' }} />
              <Bar dataKey="revenue" fill="#1A8FD6" radius={[4, 4, 0, 0]} fillOpacity={0.8} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </ScrollReveal>
  )
}

// Unpaid OPEN/DRAFT orders (pipeline) pulled live from the POS — shown
// separately from revenue because no payment has been taken.
export function OpenOrdersSection() {
  const orgId = useOrgId()
  const { data } = useApi<any>(() => api.openOrders(orgId), [orgId])
  const orders = data?.orders ?? []
  if (orders.length === 0) return null
  const s = data?.summary ?? {}
  const fmtDate = (iso: string) => iso ? new Date(iso).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' }) : '—'

  return (
    <ScrollReveal variant="fadeUp" delay={0.05}>
      <div className="card overflow-hidden">
        <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Open Orders &amp; Quotes</h3>
            <p className="text-[10px] text-[#A1A1A8] mt-0.5">
              Unpaid tickets &amp; drafts from your POS — pipeline, not yet counted as sales
            </p>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-sm font-bold font-mono text-pm-amber-gold">{formatCentsCompact(s.total_cents || 0)}</p>
            <p className="text-[10px] text-[#A1A1A8]/60">{s.open_count || 0} open · {s.draft_count || 0} draft</p>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="pm-table min-w-[520px]">
            <thead>
              <tr>
                <th className="text-left">Date</th>
                <th className="text-left">Status</th>
                <th className="text-left">Items</th>
                <th className="text-right">Value</th>
              </tr>
            </thead>
            <tbody>
              {orders.slice(0, 50).map((o: any) => (
                <tr key={o.id}>
                  <td className="font-mono text-xs text-[#A1A1A8]">{fmtDate(o.created_at)}</td>
                  <td>
                    <span className={`text-[9px] font-medium px-1.5 py-0.5 rounded-full border ${o.state === 'OPEN' ? 'text-[#1A8FD6] bg-[#1A8FD6]/10 border-[#1A8FD6]/20' : 'text-[#A1A1A8] bg-[#A1A1A8]/10 border-[#A1A1A8]/20'}`}>
                      {o.state === 'OPEN' ? 'Open ticket' : 'Draft'}
                    </span>
                  </td>
                  <td className="text-xs text-[#F5F5F7] max-w-[260px] truncate">
                    {(o.items && o.items.length) ? o.items.join(', ') : `${o.item_count} item${o.item_count === 1 ? '' : 's'}`}
                    {o.item_count > (o.items?.length || 0) ? ` +${o.item_count - o.items.length}` : ''}
                  </td>
                  <td className="text-right font-mono text-[#F5F5F7]">{formatCentsCompact(o.total_cents || 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3 border-t border-[#1F1F23] text-[10px] text-[#A1A1A8]/40">
          These become sales once payment is taken in your POS.
        </div>
      </div>
    </ScrollReveal>
  )
}
