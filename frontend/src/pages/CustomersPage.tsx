import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Users, Shield, AlertTriangle, Heart, ArrowUpDown,
  TrendingUp, TrendingDown, Minus, Search, CalendarDays,
} from 'lucide-react'
import { generateRFMSegments, generateCustomerRankings, generateCohorts, type RFMSegment, type CustomerProfile, type CohortRow } from '@/lib/agent-data'
import { formatCents, formatCentsCompact } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

type SortKey = 'totalSpent' | 'avgOrder' | 'visits' | 'lastVisit'

function RiskBadge({ risk }: { risk: CustomerProfile['retentionRisk'] }) {
  const styles = {
    low: 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/20',
    medium: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
    high: 'bg-red-500/10 text-red-400 border-red-500/20',
  }
  return (
    <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded-full border', styles[risk])}>
      {risk === 'low' ? 'Stable' : risk === 'medium' ? 'Watch' : 'Urgent'}
    </span>
  )
}

function SegmentBar({ segments }: { segments: RFMSegment[] }) {
  const total = segments.reduce((s, seg) => s + seg.count, 0)
  return (
    <div className="card p-4 sm:p-5">
      <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Customer Segments</h3>
      <div className="flex h-6 rounded-lg overflow-hidden mb-4">
        {segments.map(seg => (
          <div
            key={seg.name}
            className="relative group cursor-default transition-opacity hover:opacity-90"
            style={{ width: `${(seg.count / total * 100)}%`, backgroundColor: seg.color }}
          >
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#F5F5F7] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
              {seg.name}: {seg.count} ({seg.percentage}%)
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {segments.slice(0, 5).map(seg => (
          <div key={seg.name} className="flex items-start gap-2">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5" style={{ backgroundColor: seg.color }} />
            <div>
              <p className="text-[11px] font-medium text-[#F5F5F7]">{seg.name}</p>
              <p className="text-[10px] text-[#A1A1A8]">{seg.count} customers</p>
              <p className="text-[10px] font-mono text-[#A1A1A8]/60">{formatCents(seg.avgSpendCents)} avg</p>
            </div>
          </div>
        ))}
      </div>
      {segments.length > 5 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3 mt-3 pt-3 border-t border-[#1F1F23]">
          {segments.slice(5).map(seg => (
            <div key={seg.name} className="flex items-start gap-2">
              <div className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-0.5" style={{ backgroundColor: seg.color }} />
              <div>
                <p className="text-[11px] font-medium text-[#F5F5F7]">{seg.name}</p>
                <p className="text-[10px] text-[#A1A1A8]">{seg.count} customers</p>
                <p className="text-[10px] font-mono text-[#A1A1A8]/60">{formatCents(seg.avgSpendCents)} avg</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function CustomerValueTiers({ segments }: { segments: RFMSegment[] }) {
  const tiers = [
    { label: 'High Value', description: 'Frequent visitors, high spend — your core revenue drivers', segments: ['Champions', 'Loyal'], color: '#17C5B0', icon: TrendingUp },
    { label: 'Growth Potential', description: 'New or moderately engaged — opportunity to build loyalty', segments: ['Potential Loyalists', 'Recent Customers', 'Promising'], color: '#1A8FD6', icon: TrendingUp },
    { label: 'Needs Action', description: 'Declining engagement — targeted outreach can recover them', segments: ['Needs Attention', 'At Risk'], color: '#FBBF24', icon: Minus },
    { label: 'Winback / Lost', description: 'Inactive for 30+ days — re-engagement campaign needed', segments: ['Hibernating', 'Lost'], color: '#EF4444', icon: TrendingDown },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {tiers.map(tier => {
        const matchedSegs = segments.filter(s => tier.segments.includes(s.name))
        const count = matchedSegs.reduce((s, seg) => s + seg.count, 0)
        const totalSpend = matchedSegs.reduce((s, seg) => s + seg.avgSpendCents * seg.count, 0)
        const avgRetention = count > 0
          ? Math.round(matchedSegs.reduce((s, seg) => s + seg.retentionScore * seg.count, 0) / count)
          : 0
        const Icon = tier.icon
        return (
          <DashboardTiltCard key={tier.label} className="card p-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${tier.color}15` }}>
                <Icon size={14} style={{ color: tier.color }} />
              </div>
              <h4 className="text-xs font-semibold text-[#F5F5F7]">{tier.label}</h4>
            </div>
            <p className="text-[10px] text-[#A1A1A8]/60 mb-3 leading-relaxed">{tier.description}</p>
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <span className="text-[10px] text-[#A1A1A8]">Customers</span>
                <span className="text-[10px] font-mono font-semibold text-[#F5F5F7]">{count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[10px] text-[#A1A1A8]">Total Spend</span>
                <span className="text-[10px] font-mono font-semibold text-[#F5F5F7]">{formatCentsCompact(totalSpend)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[10px] text-[#A1A1A8]">Retention</span>
                <span className={clsx('text-[10px] font-mono font-semibold', avgRetention >= 70 ? 'text-[#17C5B0]' : avgRetention >= 40 ? 'text-amber-400' : 'text-red-400')}>
                  {avgRetention}%
                </span>
              </div>
            </div>
          </DashboardTiltCard>
        )
      })}
    </div>
  )
}

function CohortTable({ cohorts }: { cohorts: CohortRow[] }) {
  const maxMonths = Math.max(...cohorts.map(c => c.retentionByMonth.length))
  return (
    <div className="card overflow-hidden">
      <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center gap-2">
        <CalendarDays size={14} className="text-[#7C5CFF]" />
        <div>
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Cohort Retention</h3>
          <p className="text-[10px] text-[#A1A1A8] mt-0.5">How well each signup cohort retains over time</p>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="pm-table min-w-[500px]">
          <thead>
            <tr>
              <th className="text-left">Cohort</th>
              <th className="text-right">Customers</th>
              {Array.from({ length: maxMonths }, (_, i) => (
                <th key={i} className="text-center">M{i}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cohorts.map(row => (
              <tr key={row.cohort}>
                <td className="text-xs font-medium text-[#F5F5F7] whitespace-nowrap">{row.cohort}</td>
                <td className="text-right font-mono text-xs text-[#A1A1A8]">{row.totalCustomers}</td>
                {Array.from({ length: maxMonths }, (_, i) => {
                  const val = row.retentionByMonth[i]
                  if (val == null) return <td key={i} />
                  const opacity = Math.max(0.1, val / 100)
                  const color = val >= 70 ? '#17C5B0' : val >= 50 ? '#1A8FD6' : val >= 30 ? '#FBBF24' : '#EF4444'
                  return (
                    <td key={i} className="text-center p-0">
                      <div
                        className="mx-auto w-full h-full flex items-center justify-center py-2"
                        style={{ backgroundColor: `${color}${Math.round(opacity * 40).toString(16).padStart(2, '0')}` }}
                      >
                        <span className="text-[11px] font-mono font-semibold" style={{ color }}>{val}%</span>
                      </div>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-3 border-t border-[#1F1F23] text-[10px] text-[#A1A1A8]/40">
        M0 = signup month (always 100%) • Colors indicate retention health
      </div>
    </div>
  )
}

export default function CustomersPage() {
  const segments = generateRFMSegments()
  const customers = generateCustomerRankings()
  const cohorts = generateCohorts()
  const [sortBy, setSortBy] = useState<SortKey>('totalSpent')
  const [search, setSearch] = useState('')

  const totalCustomers = segments.reduce((s, seg) => s + seg.count, 0)
  const vipCount = segments.filter(s => s.name === 'Champions' || s.name === 'Loyal').reduce((s, seg) => s + seg.count, 0)
  const atRiskCount = segments.filter(s => s.name === 'At Risk' || s.name === 'Needs Attention').reduce((s, seg) => s + seg.count, 0)
  const avgRetention = Math.round(segments.reduce((s, seg) => s + seg.retentionScore * seg.count, 0) / totalCustomers)

  const filtered = customers.filter(c =>
    c.name.toLowerCase().includes(search.toLowerCase()) ||
    c.segment.toLowerCase().includes(search.toLowerCase()) ||
    c.topItem.toLowerCase().includes(search.toLowerCase())
  )

  const sorted = [...filtered].sort((a, b) => {
    switch (sortBy) {
      case 'totalSpent': return b.totalSpentCents - a.totalSpentCents
      case 'avgOrder': return b.avgOrderCents - a.avgOrderCents
      case 'visits': return b.visitsPerMonth - a.visitsPerMonth
      case 'lastVisit': return a.daysSinceVisit - b.daysSinceVisit
      default: return 0
    }
  })

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Customer Intelligence</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Customer rankings, spend analysis & retention insights powered by AI agents
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Users size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Total</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{totalCustomers}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Shield size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">VIPs</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{vipCount}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <AlertTriangle size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">At Risk</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{atRiskCount}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <Heart size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Retention</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{avgRetention}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      {/* Customer Value Tiers */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <h2 className="text-lg font-semibold text-[#F5F5F7] mb-3">Customer Value Tiers</h2>
        <CustomerValueTiers segments={segments} />
      </ScrollReveal>

      {/* Segment Distribution */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <SegmentBar segments={segments} />
      </ScrollReveal>

      {/* Cohort Retention */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <CohortTable cohorts={cohorts} />
      </ScrollReveal>

      {/* Customer Rankings Table */}
      <ScrollReveal variant="fadeUp" delay={0.2}>
        <div className="card overflow-hidden">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1">
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Customer Rankings</h3>
              <p className="text-[10px] text-[#A1A1A8] mt-0.5">Ranked by spend, frequency & engagement</p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
                <input
                  type="text" value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search customers..."
                  className="pl-7 pr-3 py-1.5 text-[11px] bg-[#111113] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/30 w-40"
                />
              </div>
              <select
                value={sortBy}
                onChange={e => setSortBy(e.target.value as SortKey)}
                className="px-2 py-1.5 text-[11px] bg-[#111113] border border-[#1F1F23] rounded-lg text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/30"
              >
                <option value="totalSpent">Total Spent</option>
                <option value="avgOrder">Avg Order</option>
                <option value="visits">Visit Frequency</option>
                <option value="lastVisit">Most Recent</option>
              </select>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[700px]">
              <thead>
                <tr>
                  <th className="text-center w-8">#</th>
                  <th className="text-left">Customer</th>
                  <th className="text-left">Segment</th>
                  <th className="text-right">Avg Order</th>
                  <th className="text-right">Total Spent</th>
                  <th className="text-right">Visits/Mo</th>
                  <th className="text-left">Top Item</th>
                  <th className="text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((c, i) => (
                  <tr key={c.id}>
                    <td className="text-center">
                      <span className={clsx(
                        'text-[10px] font-bold font-mono w-5 h-5 rounded-md flex items-center justify-center mx-auto',
                        i === 0 ? 'bg-amber-400/10 text-amber-400' : i === 1 ? 'bg-[#A1A1A8]/10 text-[#A1A1A8]' : i === 2 ? 'bg-amber-700/10 text-amber-600' : 'text-[#A1A1A8]/40'
                      )}>
                        {i + 1}
                      </span>
                    </td>
                    <td>
                      <span className="font-medium text-[#F5F5F7]">{c.name}</span>
                      {c.daysSinceVisit <= 1 && (
                        <span className="ml-1.5 text-[8px] font-medium text-[#17C5B0] bg-[#17C5B0]/10 px-1 py-0.5 rounded">TODAY</span>
                      )}
                    </td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: c.segmentColor }} />
                        <span className="text-xs text-[#F5F5F7]">{c.segment}</span>
                      </div>
                    </td>
                    <td className="text-right font-mono font-semibold text-[#F5F5F7]">{formatCents(c.avgOrderCents)}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{formatCentsCompact(c.totalSpentCents)}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{c.visitsPerMonth}x</td>
                    <td className="text-xs text-[#A1A1A8] max-w-[140px] truncate">{c.topItem}</td>
                    <td className="text-center"><RiskBadge risk={c.retentionRisk} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="px-4 py-3 border-t border-[#1F1F23] flex items-center justify-between">
            <p className="text-[10px] text-[#A1A1A8]/40">
              Showing {sorted.length} of {customers.length} tracked customers
            </p>
            <p className="text-[10px] text-[#A1A1A8]/40 font-mono">
              Avg order: {formatCents(Math.round(customers.reduce((s, c) => s + c.avgOrderCents, 0) / customers.length))}
            </p>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
