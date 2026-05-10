import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Users,
  DollarSign,
  TrendingUp,
  CreditCard,
  ArrowRight,
  Plus,
  FileText,
  GraduationCap,
  MessageCircle,
  X,
  Rocket,
  Clock,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import {
  STAGE_CONFIG,
  STAGE_ORDER,
  deriveClientsFromLeads,
  deriveCommissionsFromLeads,
  type SalesOverview,
  type Deal,
  type DealStage,
  type SalesClient,
  type Commission,
} from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'

function formatCad(value: number): string {
  return 'CA$' + Math.round(value).toLocaleString('en-CA')
}

function formatCadMo(value: number): string {
  return 'CA$' + Math.round(value).toLocaleString('en-CA') + '/mo'
}

function titleCase(name: string): string {
  return name
    .split(' ')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(' ')
}

function getFirstName(name: string): string {
  const first = name.split(' ')[0]
  return titleCase(first)
}

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

function getFormattedDate(): string {
  return new Date().toLocaleDateString('en-CA', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

function isWithin30Days(dateStr: string): boolean {
  const created = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - created.getTime()
  return diffMs <= 30 * 24 * 60 * 60 * 1000
}

const KANBAN_STAGES: DealStage[] = ['prospecting', 'contacted', 'demo_scheduled', 'proposal_sent', 'negotiation']
const MONTH1_MRR_GOAL = 2025

export default function CanadaPortalDashboardPage() {
  const { rep } = useSalesAuth()
  const navigate = useNavigate()
  const [overview, setOverview] = useState<SalesOverview | null>(null)
  const [deals, setDeals] = useState<Deal[]>([])
  const [clients, setClients] = useState<SalesClient[]>([])
  const [commissions, setCommissions] = useState<Commission[]>([])
  const [loading, setLoading] = useState(true)
  const [bannerDismissed, setBannerDismissed] = useState(false)

  useEffect(() => {
    canadaLeadsService.list().then(d => {
      setDeals(d)

      const c = deriveClientsFromLeads(d)
      const cm = deriveCommissionsFromLeads(d)
      setClients(c)
      setCommissions(cm)

      const activePipeline = d.filter((deal: Deal) => !['closed_won', 'closed_lost'].includes(deal.stage))
      const closedWon = d.filter((deal: Deal) => deal.stage === 'closed_won')
      const allDeals = d.filter((deal: Deal) => deal.stage !== 'closed_lost')
      const totalEarned = cm.reduce((s: number, cItem: Commission) => s + cItem.commission_amount, 0)
      const totalPaid = cm.filter((cItem: Commission) => cItem.status === 'paid').reduce((s: number, cItem: Commission) => s + cItem.commission_amount, 0)

      setOverview({
        total_deals: activePipeline.length,
        pipeline_value: activePipeline.reduce((s: number, deal: Deal) => s + deal.monthly_value, 0),
        closed_this_month: closedWon.length,
        monthly_commission_earned: cm.filter((cItem: Commission) => cItem.status === 'earned').reduce((s: number, cItem: Commission) => s + cItem.commission_amount, 0),
        total_earned: totalEarned,
        total_paid: totalPaid,
        pending_payout: totalEarned - totalPaid,
        active_clients: c.filter((cl: SalesClient) => cl.is_active).length,
        conversion_rate: allDeals.length > 0 ? Math.round((closedWon.length / allDeals.length) * 100) : 0,
      })
    }).catch(() => {
      setOverview({
        total_deals: 0, pipeline_value: 0, closed_this_month: 0,
        monthly_commission_earned: 0, total_earned: 0, total_paid: 0,
        pending_payout: 0, active_clients: 0, conversion_rate: 0,
      })
    }).finally(() => setLoading(false))
  }, [])

  if (loading || !overview) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#00d4aa] font-bold text-sm">M</span>
        </div>
      </div>
    )
  }

  const activeClients = clients.filter(c => c.is_active && c.pos_connected)
  const clientMrr = activeClients.reduce((sum, c) => sum + c.monthly_revenue, 0)
  const wonDealsMrr = deals.filter(d => d.stage === 'closed_won').reduce((sum, d) => sum + d.monthly_value, 0)
  const mrr = Math.max(clientMrr, wonDealsMrr)
  const pipelineDeals = deals.filter(d => !['closed_won', 'closed_lost'].includes(d.stage))
  const pipelineValue = pipelineDeals.reduce((sum, d) => sum + d.monthly_value, 0)
  const commissionRate = rep?.commission_rate ?? 70
  const totalCommEarned = commissions.reduce((s, c) => s + c.commission_amount, 0)
  const pendingComm = commissions.filter(c => c.status === 'earned' || c.status === 'pending').reduce((s, c) => s + c.commission_amount, 0)

  const showFirst30Banner = rep?.created_at && isWithin30Days(rep.created_at) && !bannerDismissed
  const mrrProgress = Math.min((mrr / MONTH1_MRR_GOAL) * 100, 100)

  const recentActivity = [...deals]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 5)

  const hasZeroLeads = deals.length === 0

  return (
    <div className="space-y-6">
      {/* ── Greeting ── */}
      <div>
        <h1 className="text-xl font-bold text-white">
          {getGreeting()}, {rep ? getFirstName(rep.name) : 'there'}.
        </h1>
        <p className="text-sm text-[#6b7a74] mt-1">{getFormattedDate()}</p>
      </div>

      {/* ── First 30 Days Banner ── */}
      {showFirst30Banner && (
        <div className="relative bg-[#0f1512] border border-[#00d4aa]/30 rounded-xl p-5 overflow-hidden">
          <button
            onClick={() => setBannerDismissed(true)}
            className="absolute top-3 right-3 text-[#6b7a74] hover:text-white transition-colors"
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
          <div className="flex items-center gap-2 mb-2">
            <Rocket size={16} className="text-[#00d4aa]" />
            <span className="text-xs font-semibold text-[#00d4aa] uppercase tracking-wider">Month 1 Goal</span>
          </div>
          <p className="text-sm text-white mb-3">
            Target: <span className="font-semibold text-[#f0b429]">CA$2,025</span> MRR
            <span className="mx-2 text-[#6b7a74]">|</span>
            Your current MRR: <span className="font-semibold text-[#f0b429]">CA${mrr.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </p>
          <div className="w-full h-2 rounded-full bg-[#1a2420] overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${mrrProgress}%`,
                background: 'linear-gradient(90deg, #00d4aa, #17C5B0)',
              }}
            />
          </div>
          <p className="text-[11px] text-[#6b7a74] mt-2">
            {mrrProgress >= 100
              ? 'Goal reached! Outstanding work.'
              : `${Math.round(mrrProgress)}% of your Month 1 target`}
          </p>
        </div>
      )}

      {/* ── Stat Cards (4 across) ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Active Accounts"
          value={String(activeClients.length)}
          subtitle="POS connected & billing"
          icon={<Users size={18} className="text-[#00d4aa]" />}
          iconBg="bg-[#00d4aa]/15"
          bars={[40, 60, 35, 80, 55, 70]}
          barColor="#00d4aa"
        />
        <StatCard
          label="MRR"
          value={formatCad(mrr)}
          subtitle="Monthly recurring revenue"
          icon={<DollarSign size={18} className="text-[#f0b429]" />}
          iconBg="bg-[#f0b429]/15"
          valueColor="#f0b429"
          bars={[30, 45, 50, 65, 55, 72]}
          barColor="#f0b429"
        />
        <StatCard
          label="In Pipeline"
          value={String(pipelineDeals.length)}
          subtitle={`CA$${Math.round(pipelineValue).toLocaleString('en-CA')}/mo potential`}
          icon={<TrendingUp size={18} className="text-[#00d4aa]" />}
          iconBg="bg-[#00d4aa]/15"
          bars={[55, 40, 70, 60, 85, 50]}
          barColor="#00d4aa"
        />
        <StatCard
          label="Commissions"
          value={formatCad(totalCommEarned)}
          subtitle={`${commissionRate}% rate | ${formatCad(pendingComm)} pending`}
          icon={<CreditCard size={18} className="text-[#f0b429]" />}
          iconBg="bg-[#f0b429]/15"
          valueColor="#f0b429"
          bars={[60, 45, 70, 50, 80, 65]}
          barColor="#f0b429"
        />
      </div>

      {/* ── Empty State (zero leads) ── */}
      {hasZeroLeads ? (
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl py-16 px-6 text-center">
          <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center">
            <Rocket size={28} className="text-[#00d4aa]" />
          </div>
          <h2 className="text-lg font-bold text-white mb-2">Your first deal is waiting.</h2>
          <p className="text-sm text-[#6b7a74] max-w-md mx-auto mb-6">
            Start building your pipeline by creating your first lead. Track every stage from prospecting through close.
          </p>
          <button
            onClick={() => navigate('/canada/portal/leads?new=true')}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold hover:bg-[#00d4aa]/90 transition-colors"
          >
            <Plus size={16} />
            Create Your First Lead
          </button>
        </div>
      ) : (
        <>
          {/* ── Pipeline Kanban (compact) ── */}
          <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl">
            <div className="px-5 py-4 border-b border-[#1a2420] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Deal Pipeline</h2>
              <Link
                to="/canada/portal/leads"
                className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/80 flex items-center gap-1 transition-colors"
              >
                View all <ArrowRight size={12} />
              </Link>
            </div>
            <div className="px-4 py-4 overflow-x-auto">
              <div className="grid grid-cols-5 gap-3 min-w-[800px]">
                {KANBAN_STAGES.map(stage => {
                  const cfg = STAGE_CONFIG[stage]
                  const stageDeals = deals.filter(d => d.stage === stage)
                  const visibleDeals = stageDeals.slice(0, 3)
                  const remaining = stageDeals.length - visibleDeals.length
                  return (
                    <div key={stage} className="flex flex-col">
                      <div className="flex items-center gap-2 mb-3 px-1">
                        <div
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{ backgroundColor: cfg.color }}
                        />
                        <span className="text-xs font-medium text-[#6b7a74] truncate">
                          {cfg.label}
                        </span>
                        <span
                          className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0"
                          style={{ color: cfg.color, backgroundColor: `${cfg.color}15` }}
                        >
                          {stageDeals.length}
                        </span>
                      </div>
                      <div className="space-y-2 flex-1">
                        {visibleDeals.length === 0 ? (
                          <div className="rounded-lg border border-dashed border-[#1a2420] bg-[#0a0f0d] px-3 py-4 text-center">
                            <p className="text-[11px] text-[#4a5550]">No deals</p>
                          </div>
                        ) : (
                          <>
                            {visibleDeals.map(deal => (
                              <Link
                                key={deal.id}
                                to={`/canada/portal/leads/${deal.id}`}
                                className="block rounded-lg border border-[#1a2420] bg-[#0a0f0d] px-3 py-2.5 hover:border-[#2a3430] transition-colors"
                              >
                                <p className="text-xs font-medium text-white truncate">
                                  {deal.business_name}
                                </p>
                                <p className="text-[11px] text-[#6b7a74] truncate mt-0.5">
                                  {deal.contact_name}
                                </p>
                                <p
                                  className="text-[11px] font-semibold mt-1.5"
                                  style={{ color: cfg.color }}
                                >
                                  {formatCadMo(deal.monthly_value)}
                                </p>
                              </Link>
                            ))}
                            {remaining > 0 && (
                              <Link
                                to="/canada/portal/leads"
                                className="block rounded-lg border border-dashed border-[#1a2420] bg-[#0a0f0d] px-3 py-2.5 text-center hover:border-[#2a3430] transition-colors"
                              >
                                <p className="text-[11px] text-[#00d4aa]">+{remaining} more</p>
                              </Link>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* ── Active Accounts ── */}
          {activeClients.length > 0 && (
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl">
              <div className="px-5 py-4 border-b border-[#1a2420] flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">Active Accounts</h2>
                <Link
                  to="/canada/portal/accounts"
                  className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/80 flex items-center gap-1 transition-colors"
                >
                  View all <ArrowRight size={12} />
                </Link>
              </div>
              <div className="divide-y divide-[#1a2420]">
                {activeClients.map(client => (
                  <Link
                    key={client.id}
                    to="/canada/portal/accounts"
                    className="px-5 py-3 flex items-center gap-3 hover:bg-[#0a0f0d]/50 transition-colors block"
                  >
                    <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center flex-shrink-0">
                      <Users size={14} className="text-[#00d4aa]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white truncate">{client.business_name}</p>
                      <p className="text-[11px] text-[#6b7a74]">
                        {client.pos_provider ? client.pos_provider.charAt(0).toUpperCase() + client.pos_provider.slice(1) : 'No POS'}
                        <span className="mx-1.5 text-[#2a3430]">|</span>
                        {formatCadMo(client.monthly_revenue)}
                      </p>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* ── Recent Activity Feed ── */}
          <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl">
            <div className="px-5 py-4 border-b border-[#1a2420] flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Recent Activity</h2>
              <Link
                to="/canada/portal/leads"
                className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/80 flex items-center gap-1 transition-colors"
              >
                View all <ArrowRight size={12} />
              </Link>
            </div>
            <div className="divide-y divide-[#1a2420]">
              {recentActivity.length === 0 ? (
                <div className="px-5 py-6 text-center text-sm text-[#4a5550]">
                  No recent activity.
                </div>
              ) : (
                recentActivity.map(deal => {
                  const cfg = STAGE_CONFIG[deal.stage]
                  const updated = new Date(deal.updated_at)
                  const timeAgo = getRelativeTime(updated)
                  return (
                    <Link
                      key={deal.id}
                      to={`/canada/portal/leads/${deal.id}`}
                      className="px-5 py-3 flex items-center gap-3 hover:bg-[#0a0f0d]/50 transition-colors block"
                    >
                      <div
                        className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: `${cfg.color}18` }}
                      >
                        <div
                          className="w-2.5 h-2.5 rounded-full"
                          style={{ backgroundColor: cfg.color }}
                        />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{deal.business_name}</p>
                        <p className="text-[11px] text-[#6b7a74]">
                          <span style={{ color: cfg.color }}>{cfg.label}</span>
                          <span className="mx-1.5 text-[#2a3430]">|</span>
                          {formatCadMo(deal.monthly_value)}
                        </p>
                      </div>
                      <div className="flex items-center gap-1 text-[11px] text-[#4a5550] flex-shrink-0">
                        <Clock size={11} />
                        {timeAgo}
                      </div>
                    </Link>
                  )
                })
              )}
            </div>
          </div>
        </>
      )}

      {/* ── Quick Actions ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <QuickAction
          icon={<Plus size={16} />}
          label="New Lead"
          onClick={() => navigate('/canada/portal/leads?new=true')}
        />
        <QuickAction
          icon={<FileText size={16} />}
          label="Generate Proposal"
          onClick={() => navigate('/canada/portal/new-customer')}
        />
        <QuickAction
          icon={<GraduationCap size={16} />}
          label="View Training"
          onClick={() => navigate('/canada/portal/training')}
        />
        <QuickAction
          icon={<MessageCircle size={16} />}
          label="Contact Manager"
          onClick={() => navigate('/canada/portal/team')}
        />
      </div>
    </div>
  )
}

/* ── Stat Card ── */
function StatCard({
  label,
  value,
  subtitle,
  icon,
  iconBg,
  valueColor,
  bars,
  barColor,
}: {
  label: string
  value: string
  subtitle: string
  icon: React.ReactNode
  iconBg: string
  valueColor?: string
  bars: number[]
  barColor: string
}) {
  return (
    <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5 flex flex-col justify-between">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-[#6b7a74]">{label}</p>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>
          {icon}
        </div>
      </div>
      <p
        className="text-2xl font-bold mb-1"
        style={{ color: valueColor || '#ffffff' }}
      >
        {value}
      </p>
      {/* Sparkline bar chart */}
      <div className="flex items-end gap-[3px] h-5 mb-2">
        {bars.map((h, i) => (
          <div
            key={i}
            className="flex-1 rounded-sm transition-all"
            style={{
              height: `${h}%`,
              backgroundColor: barColor,
              opacity: 0.25 + (i / bars.length) * 0.55,
            }}
          />
        ))}
      </div>
      <p className="text-[11px] text-[#4a5550] truncate">{subtitle}</p>
    </div>
  )
}

/* ── Quick Action Button ── */
function QuickAction({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2.5 bg-[#0f1512] border border-[#1a2420] rounded-xl px-4 py-3.5 text-sm font-medium text-white hover:border-[#00d4aa]/40 hover:text-[#00d4aa] transition-colors w-full"
    >
      <span className="text-[#6b7a74] group-hover:text-[#00d4aa]">{icon}</span>
      {label}
    </button>
  )
}

/* ── Relative Time Helper ── */
function getRelativeTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return 'just now'
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  if (diffDay === 1) return 'yesterday'
  if (diffDay < 7) return `${diffDay}d ago`
  return date.toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })
}
