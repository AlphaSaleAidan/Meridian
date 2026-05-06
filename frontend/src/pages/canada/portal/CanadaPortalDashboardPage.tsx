import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  DollarSign, TrendingUp, Users, Target,
  ArrowUpRight, Briefcase, CircleDollarSign,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { canadaSalesDemoData, STAGE_CONFIG, STAGE_ORDER, type SalesOverview, type Deal } from '@/lib/canada-sales-demo-data'

function formatCurrency(cents: number): string {
  return '$' + (cents / 100).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' CAD'
}

function formatCompact(value: number): string {
  return '$' + value.toLocaleString('en-CA') + ' CAD'
}

function StatCard({ label, value, sub, icon: Icon, color }: {
  label: string; value: string; sub?: string; icon: typeof DollarSign; color: string
}) {
  return (
    <div className="card p-4 border border-[#1F1F23]">
      <div className="flex items-center gap-3 mb-2">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: color + '15', border: `1px solid ${color}30` }}>
          <Icon size={16} style={{ color }} />
        </div>
        <span className="text-[11px] font-medium text-[#A1A1A8]">{label}</span>
      </div>
      <p className="text-lg font-bold text-[#F5F5F7]">{value}</p>
      {sub && <p className="text-[10px] text-[#A1A1A8]/50 mt-0.5">{sub}</p>}
    </div>
  )
}

export default function CanadaPortalDashboardPage() {
  const { rep } = useSalesAuth()
  const [overview, setOverview] = useState<SalesOverview | null>(null)
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([canadaSalesDemoData.overview(), canadaSalesDemoData.deals()]).then(([o, d]) => {
      setOverview(o)
      setDeals(d)
      setLoading(false)
    })
  }, [])

  if (loading || !overview) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#17C5B0] font-bold text-sm">S</span>
        </div>
      </div>
    )
  }

  const pipelineDeals = deals.filter(d => !['closed_won', 'closed_lost'].includes(d.stage))
  const pipelineByStage = STAGE_ORDER.filter(s => !['closed_won', 'closed_lost'].includes(s)).map(stage => ({
    stage,
    ...STAGE_CONFIG[stage],
    deals: pipelineDeals.filter(d => d.stage === stage),
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">
          Welcome back{rep ? `, ${rep.name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-sm text-[#A1A1A8] mt-1">Here's your sales pipeline at a glance.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Active Deals" value={String(overview.total_deals)} sub={`${overview.conversion_rate}% close rate`} icon={Target} color="#1A8FD6" />
        <StatCard label="Pipeline Value" value={formatCompact(overview.pipeline_value)} sub={`${overview.total_deals} deals in progress`} icon={Briefcase} color="#7C5CFF" />
        <StatCard label="Commissions Earned" value={formatCurrency(overview.monthly_commission_earned)} sub="This month" icon={DollarSign} color="#17C5B0" />
        <StatCard label="Pending Payout" value={formatCurrency(overview.pending_payout)} sub={formatCurrency(overview.total_paid) + ' paid to date'} icon={CircleDollarSign} color="#F59E0B" />
      </div>

      <div className="card border border-[#1F1F23]">
        <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Deal Pipeline</h2>
          <Link to="/canada/portal/leads" className="text-[11px] text-[#17C5B0] hover:text-[#17C5B0]/80 flex items-center gap-1 transition-colors">
            View all <ArrowUpRight size={12} />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 divide-y sm:divide-y-0 sm:divide-x divide-[#1F1F23]">
          {pipelineByStage.map(({ stage, label, color, deals: stageDeals }) => (
            <div key={stage} className="p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-[10px] font-semibold text-[#A1A1A8] uppercase tracking-wider">{label}</span>
                <span className="text-[10px] text-[#A1A1A8]/40 ml-auto">{stageDeals.length}</span>
              </div>
              <div className="space-y-2">
                {stageDeals.length === 0 ? (
                  <p className="text-[10px] text-[#A1A1A8]/30 italic">No deals</p>
                ) : (
                  stageDeals.map(deal => (
                    <div key={deal.id} className="p-2.5 rounded-lg bg-[#111113] border border-[#1F1F23] hover:border-[#2A2A2E] transition-colors">
                      <p className="text-[11px] font-medium text-[#F5F5F7] truncate">{deal.business_name}</p>
                      <p className="text-[10px] text-[#A1A1A8]/50 truncate">{deal.contact_name}</p>
                      <p className="text-[10px] font-semibold mt-1" style={{ color }}>
                        {formatCompact(deal.monthly_value)}/mo
                      </p>
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card border border-[#1F1F23]">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center justify-between">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Recent Wins</h2>
            <Link to="/canada/portal/accounts" className="text-[11px] text-[#17C5B0] hover:text-[#17C5B0]/80 flex items-center gap-1 transition-colors">
              All accounts <ArrowUpRight size={12} />
            </Link>
          </div>
          <div className="divide-y divide-[#1F1F23]">
            {deals.filter(d => d.stage === 'closed_won').map(deal => (
              <div key={deal.id} className="px-4 sm:px-5 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center flex-shrink-0">
                  <TrendingUp size={14} className="text-[#17C5B0]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-medium text-[#F5F5F7] truncate">{deal.business_name}</p>
                  <p className="text-[10px] text-[#A1A1A8]/50">{deal.vertical} &middot; {deal.commission_rate}% commission</p>
                </div>
                <p className="text-[11px] font-semibold text-[#17C5B0] flex-shrink-0">{formatCompact(deal.monthly_value)}/mo</p>
              </div>
            ))}
          </div>
        </div>

        <div className="card border border-[#1F1F23]">
          <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Your Stats</h2>
          </div>
          <div className="p-4 sm:p-5 space-y-3">
            {[
              { label: 'Active Clients', value: String(overview.active_clients), color: '#1A8FD6' },
              { label: 'Closed This Month', value: String(overview.closed_this_month), color: '#17C5B0' },
              { label: 'Total Earned (all time)', value: formatCurrency(overview.total_earned), color: '#7C5CFF' },
              { label: 'Total Paid Out', value: formatCurrency(overview.total_paid), color: '#F59E0B' },
              { label: 'Close Rate', value: overview.conversion_rate + '%', color: '#17C5B0' },
            ].map(s => (
              <div key={s.label} className="flex items-center justify-between">
                <span className="text-[11px] text-[#A1A1A8]">{s.label}</span>
                <span className="text-[11px] font-semibold" style={{ color: s.color }}>{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
