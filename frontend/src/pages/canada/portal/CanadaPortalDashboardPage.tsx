import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  DollarSign, TrendingUp, Users, Target,
  ArrowUpRight, Briefcase, CircleDollarSign, Plus,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'
import { STAGE_CONFIG, STAGE_ORDER, type DealStage } from '@/lib/sales-demo-data'

interface CanadaDeal {
  id: string
  business_name: string
  contact_name: string
  stage: DealStage
  monthly_value: number
  commission_rate: number
  vertical: string
  notes: string
}

interface CanadaOverview {
  total_deals: number
  pipeline_value: number
  closed_this_month: number
  monthly_commission_earned: number
  total_earned: number
  total_paid: number
  pending_payout: number
  active_clients: number
  conversion_rate: number
}

function formatCurrency(cents: number): string {
  return 'CA$' + (cents / 100).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatCompact(value: number): string {
  return 'CA$' + value.toLocaleString('en-CA')
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

const EMPTY_OVERVIEW: CanadaOverview = {
  total_deals: 0, pipeline_value: 0, closed_this_month: 0,
  monthly_commission_earned: 0, total_earned: 0, total_paid: 0,
  pending_payout: 0, active_clients: 0, conversion_rate: 0,
}

export default function CanadaPortalDashboardPage() {
  const { rep } = useSalesAuth()
  const [overview, setOverview] = useState<CanadaOverview>(EMPTY_OVERVIEW)
  const [deals, setDeals] = useState<CanadaDeal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      if (!supabase || !rep) { setLoading(false); return }
      try {
        const { data: dbDeals } = await supabase
          .from('deals')
          .select('*')
          .eq('country', 'CA')
          .eq('rep_id', rep.rep_id)
        if (dbDeals && dbDeals.length > 0) {
          setDeals(dbDeals as CanadaDeal[])
          const active = dbDeals.filter((d: any) => !['closed_won', 'closed_lost'].includes(d.stage))
          const won = dbDeals.filter((d: any) => d.stage === 'closed_won')
          setOverview({
            total_deals: active.length,
            pipeline_value: active.reduce((s: number, d: any) => s + (d.monthly_value || 0), 0),
            closed_this_month: won.length,
            monthly_commission_earned: 0,
            total_earned: 0,
            total_paid: 0,
            pending_payout: 0,
            active_clients: won.length,
            conversion_rate: dbDeals.length > 0 ? Math.round((won.length / dbDeals.length) * 100) : 0,
          })
        }
      } catch { /* empty state is fine */ }
      setLoading(false)
    }
    load()
  }, [rep])

  if (loading) {
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

  const isEmpty = deals.length === 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">
          Welcome back{rep ? `, ${rep.name.split(' ')[0]}` : ''}
        </h1>
        <p className="text-sm text-[#A1A1A8] mt-1">
          {isEmpty ? 'Your Canadian pipeline is empty. Add your first lead to get started.' : "Here's your sales pipeline at a glance."}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatCard label="Active Deals" value={String(overview.total_deals)} sub={overview.conversion_rate > 0 ? `${overview.conversion_rate}% close rate` : 'No deals yet'} icon={Target} color="#1A8FD6" />
        <StatCard label="Pipeline Value" value={formatCompact(overview.pipeline_value)} sub={overview.total_deals > 0 ? `${overview.total_deals} deals in progress` : 'CA$0'} icon={Briefcase} color="#7C5CFF" />
        <StatCard label="Commissions Earned" value={formatCurrency(overview.monthly_commission_earned)} sub="This month" icon={DollarSign} color="#17C5B0" />
        <StatCard label="Pending Payout" value={formatCurrency(overview.pending_payout)} sub={overview.total_paid > 0 ? formatCurrency(overview.total_paid) + ' paid to date' : 'No payouts yet'} icon={CircleDollarSign} color="#F59E0B" />
      </div>

      {isEmpty ? (
        <div className="card border border-[#1F1F23] p-12 text-center">
          <div className="w-12 h-12 rounded-xl bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center mx-auto mb-4">
            <Plus size={20} className="text-[#17C5B0]" />
          </div>
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">No deals in your pipeline yet</h3>
          <p className="text-[12px] text-[#A1A1A8] mb-4 max-w-sm mx-auto">
            Start building your Canadian pipeline by adding your first lead. All amounts are tracked in CAD.
          </p>
          <Link
            to="/canada/portal/leads"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
          >
            <Plus size={16} /> Add Your First Lead
          </Link>
        </div>
      ) : (
        <>
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
                            {formatCompact(deal.monthly_value)} CAD/mo
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
                {deals.filter(d => d.stage === 'closed_won').length === 0 ? (
                  <div className="px-4 sm:px-5 py-8 text-center text-[11px] text-[#A1A1A8]/40">No closed deals yet.</div>
                ) : (
                  deals.filter(d => d.stage === 'closed_won').map(deal => (
                    <div key={deal.id} className="px-4 sm:px-5 py-3 flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center flex-shrink-0">
                        <TrendingUp size={14} className="text-[#17C5B0]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-[11px] font-medium text-[#F5F5F7] truncate">{deal.business_name}</p>
                        <p className="text-[10px] text-[#A1A1A8]/50">{deal.vertical} &middot; {deal.commission_rate}% commission</p>
                      </div>
                      <p className="text-[11px] font-semibold text-[#17C5B0] flex-shrink-0">{formatCompact(deal.monthly_value)} CAD/mo</p>
                    </div>
                  ))
                )}
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
        </>
      )}
    </div>
  )
}
