import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Users,
  DollarSign,
  TrendingUp,
  ArrowRight,
  Plus,
  FileText,
  GraduationCap,
  MessageCircle,
  X,
  Rocket,
  Clock,
  CheckCircle2,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import {
  STAGE_CONFIG,
  deriveClientsFromLeads,
  type Deal,
  type DealStage,
} from '@/lib/canada-sales-demo-data'
import { useCanadaLeads, useCanadaLeadsRealtime } from '@/lib/canada-queries'
import { formatCad, formatCadMo } from '@/lib/format'
import { PortalPage } from './PortalPage'

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

const KANBAN_STAGES: DealStage[] = ['proposal_shown', 'customer_checkout', 'customer_walkthrough']
const MONTH1_MRR_GOAL = 2025

export default function CanadaPortalDashboardPage() {
  const { rep } = useSalesAuth()
  const navigate = useNavigate()
  const { data: deals = [], isLoading, error } = useCanadaLeads(rep?.rep_id)
  useCanadaLeadsRealtime(rep?.rep_id)

  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [welcomeDismissed, setWelcomeDismissed] = useState(() =>
    localStorage.getItem('meridian_ca_rep_welcomed') === '1'
  )

  const clients = useMemo(() => deriveClientsFromLeads(deals), [deals])

  const activeClients = clients.filter(c => c.is_active && c.pos_connected)
  const clientMrr = activeClients.reduce((sum, c) => sum + c.monthly_revenue, 0)
  const wonDealsMrr = deals.filter(d => d.stage === 'customer_walkthrough' || d.stage === 'closed_won' || d.stage === 'pos_connected').reduce((sum, d) => sum + d.monthly_value, 0)
  const mrr = Math.max(clientMrr, wonDealsMrr)
  const pipelineDeals = deals.filter(d => !['customer_walkthrough', 'pos_connected', 'closed_won', 'closed_lost'].includes(d.stage))
  const pipelineValue = pipelineDeals.reduce((sum, d) => sum + d.monthly_value, 0)

  const showFirst30Banner = rep?.created_at && isWithin30Days(rep.created_at) && !bannerDismissed
  const mrrProgress = Math.min((mrr / MONTH1_MRR_GOAL) * 100, 100)

  const recentActivity = [...deals]
    .sort((a, b) => b.updated_at.localeCompare(a.updated_at))
    .slice(0, 5)

  // PortalPage gates the empty state on !isLoading internally so the race
  // (#6) closes structurally — pass the raw predicate.
  const hasNoLeads = deals.length === 0

  const zeroLeadsEmptyState = (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl py-16 px-6 text-center">
      <div className="w-16 h-16 mx-auto mb-5 rounded-2xl bg-pm-accent/10 border border-pm-accent/20 flex items-center justify-center">
        <Rocket size={28} className="text-pm-accent" />
      </div>
      <h2 className="text-lg font-bold text-white mb-2">Your first deal is waiting.</h2>
      <p className="text-sm text-pm-canada-text-muted max-w-md mx-auto mb-6">
        Start building your pipeline by creating your first lead. Track every stage from appointment through onboarding.
      </p>
      <button
        onClick={() => navigate('/canada/portal/leads?new=true')}
        className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-pm-accent text-pm-canada-bg text-sm font-semibold hover:bg-pm-accent/90 transition-colors"
      >
        <Plus size={16} />
        Create Your First Lead
      </button>
    </div>
  )

  return (
    <div className="space-y-6">
      {/* ── Greeting ── */}
      <div>
        <h1 className="text-xl font-bold text-white">
          {getGreeting()}, {rep ? getFirstName(rep.name) : 'there'}.
        </h1>
        <p className="text-sm text-pm-canada-text-muted mt-1">{getFormattedDate()}</p>
      </div>

      {/* ── Welcome Walkthrough Banner ── */}
      {!welcomeDismissed && (
        <div className="relative rounded-xl p-5 border-l-4 border-pm-accent bg-gradient-to-br from-pm-accent/[0.08] to-pm-accent/[0.04]">
          <button
            onClick={() => { localStorage.setItem('meridian_ca_rep_welcomed', '1'); setWelcomeDismissed(true) }}
            className="absolute top-3 right-3 text-pm-canada-text-muted hover:text-white transition-colors"
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
          <h3 className="text-base font-bold text-white mb-4">Welcome to Meridian!</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="flex items-start gap-2.5">
              <div className="w-6 h-6 rounded-full bg-pm-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <CheckCircle2 size={14} className="text-pm-accent" />
              </div>
              <div>
                <Link to="/canada/portal/leads?new=true" className="text-sm font-semibold text-pm-accent hover:underline">
                  1. Add your first lead
                </Link>
                <p className="text-xs text-pm-canada-text-muted mt-0.5">Open the leads page and create a new lead to get started.</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <div className="w-6 h-6 rounded-full bg-pm-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <CheckCircle2 size={14} className="text-pm-accent" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">2. Send a proposal</p>
                <p className="text-xs text-pm-canada-text-muted mt-0.5">Open a lead and send a proposal to start the sales process.</p>
              </div>
            </div>
            <div className="flex items-start gap-2.5">
              <div className="w-6 h-6 rounded-full bg-pm-accent/20 flex items-center justify-center flex-shrink-0 mt-0.5">
                <CheckCircle2 size={14} className="text-pm-accent" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">3. Activate your customer</p>
                <p className="text-xs text-pm-canada-text-muted mt-0.5">Send your customer their login and guide them through the Meridian onboarding to activate their account.</p>
              </div>
            </div>
          </div>
          <button
            onClick={() => { localStorage.setItem('meridian_ca_rep_welcomed', '1'); setWelcomeDismissed(true) }}
            className="mt-4 px-4 py-1.5 text-xs font-medium text-pm-canada-text-muted border border-pm-canada-border rounded-lg hover:text-white hover:border-pm-canada-text-muted transition-colors"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* ── Pending Approval Banner ── */}
      {rep && !rep.is_active && (
        <div className="bg-[#1a1a10] border border-[#c8a82c]/30 rounded-xl p-5">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#c8a82c]/15 flex items-center justify-center flex-shrink-0">
              <Clock size={18} className="text-[#c8a82c]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">Application Pending Approval</h3>
              <p className="text-xs text-pm-canada-text-muted mt-0.5">Your account is being reviewed by the team. You'll get full access once an admin approves your application.</p>
            </div>
          </div>
        </div>
      )}

      {/* ── First 30 Days Banner ── */}
      {showFirst30Banner && rep?.is_active && (
        <div className="relative bg-pm-canada-surface border border-pm-accent/30 rounded-xl p-5 overflow-hidden">
          <button
            onClick={() => setBannerDismissed(true)}
            className="absolute top-3 right-3 text-pm-canada-text-muted hover:text-white transition-colors"
            aria-label="Dismiss"
          >
            <X size={16} />
          </button>
          <div className="flex items-center gap-2 mb-2">
            <Rocket size={16} className="text-pm-accent" />
            <span className="text-xs font-semibold text-pm-accent uppercase tracking-wider">Month 1 Goal</span>
          </div>
          <p className="text-sm text-white mb-3">
            Target: <span className="font-semibold text-pm-amber-gold">CA$2,025</span> MRR
            <span className="mx-2 text-pm-canada-text-muted">|</span>
            Your current MRR: <span className="font-semibold text-pm-amber-gold">CA${mrr.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
          </p>
          <div className="w-full h-2 rounded-full bg-pm-canada-border overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${mrrProgress}%`,
                background: 'linear-gradient(90deg, #00d4aa, #17C5B0)',
              }}
            />
          </div>
          <p className="text-2xs text-pm-canada-text-muted mt-2">
            {mrrProgress >= 100
              ? 'Goal reached! Outstanding work.'
              : `${Math.round(mrrProgress)}% of your Month 1 target`}
          </p>
        </div>
      )}

      {/* ── Stat Cards (4 across) ──
          Rendered OUTSIDE <PortalPage> so a zero-leads account still sees the
          stat cards (zeros) and the empty-state CTA appears BELOW them rather
          than replacing them. */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          label="Active Accounts"
          value={String(activeClients.length)}
          subtitle="POS connected & billing"
          icon={<Users size={18} className="text-pm-accent" />}
          iconBg="bg-pm-accent/15"
          bars={[40, 60, 35, 80, 55, 70]}
          barClass="bg-pm-accent"
        />
        <StatCard
          label="MRR"
          value={formatCad(mrr)}
          subtitle="Monthly recurring revenue"
          icon={<DollarSign size={18} className="text-pm-amber-gold" />}
          iconBg="bg-pm-amber-gold/15"
          valueClass="text-pm-amber-gold"
          bars={[30, 45, 50, 65, 55, 72]}
          barClass="bg-pm-amber-gold"
        />
        <StatCard
          label="In Pipeline"
          value={String(pipelineDeals.length)}
          subtitle={`CA$${Math.round(pipelineValue).toLocaleString('en-CA')}/mo potential`}
          icon={<TrendingUp size={18} className="text-pm-accent" />}
          iconBg="bg-pm-accent/15"
          bars={[55, 40, 70, 60, 85, 50]}
          barClass="bg-pm-accent"
        />
      </div>

      <PortalPage isLoading={isLoading} error={error} isEmpty={hasNoLeads} emptyState={zeroLeadsEmptyState}>
      {/* ── Pipeline Kanban (compact) ── */}
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl">
        <div className="px-5 py-4 border-b border-pm-canada-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Deal Pipeline</h2>
          <Link
            to="/canada/portal/leads"
            className="text-xs text-pm-accent hover:text-pm-accent/80 flex items-center gap-1 transition-colors"
          >
            View all <ArrowRight size={12} />
          </Link>
        </div>
        <div className="px-4 py-4 overflow-x-auto">
          <div className="grid grid-cols-3 gap-3 min-w-[800px]">
            {KANBAN_STAGES.map(stage => {
              const cfg = STAGE_CONFIG[stage]
              const stageDeals = deals.filter(d => d.stage === stage)
              const visibleDeals = stageDeals.slice(0, 3)
              const remaining = stageDeals.length - visibleDeals.length
              return (
                <div key={stage} className="flex flex-col">
                  <div className="flex items-center gap-2 mb-3 px-1">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${cfg.dotClass}`} />
                    <span className="text-xs font-medium text-pm-canada-text-muted truncate">
                      {cfg.label}
                    </span>
                    <span className={`text-2xs font-semibold px-1.5 py-0.5 rounded-full flex-shrink-0 ${cfg.textClass} ${cfg.softBgClass}`}>
                      {stageDeals.length}
                    </span>
                  </div>
                  <div className="space-y-2 flex-1">
                    {visibleDeals.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-pm-canada-border bg-pm-canada-bg px-3 py-4 text-center">
                        <p className="text-2xs text-pm-canada-text-faint">No deals</p>
                      </div>
                    ) : (
                      <>
                        {visibleDeals.map(deal => (
                          <Link
                            key={deal.id}
                            to={`/canada/portal/leads/${deal.id}`}
                            className="block rounded-lg border border-pm-canada-border bg-pm-canada-bg px-3 py-2.5 hover:border-[#2a3430] transition-colors"
                          >
                            <p className="text-xs font-medium text-white truncate">
                              {deal.business_name}
                            </p>
                            <p className="text-2xs text-pm-canada-text-muted truncate mt-0.5">
                              {deal.contact_name}
                            </p>
                            <p className={`text-2xs font-semibold mt-1.5 ${cfg.textClass}`}>
                              {formatCadMo(deal.monthly_value)}
                            </p>
                          </Link>
                        ))}
                        {remaining > 0 && (
                          <Link
                            to="/canada/portal/leads"
                            className="block rounded-lg border border-dashed border-pm-canada-border bg-pm-canada-bg px-3 py-2.5 text-center hover:border-[#2a3430] transition-colors"
                          >
                            <p className="text-2xs text-pm-accent">+{remaining} more</p>
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
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl">
          <div className="px-5 py-4 border-b border-pm-canada-border flex items-center justify-between">
            <h2 className="text-sm font-semibold text-white">Active Accounts</h2>
            <Link
              to="/canada/portal/accounts"
              className="text-xs text-pm-accent hover:text-pm-accent/80 flex items-center gap-1 transition-colors"
            >
              View all <ArrowRight size={12} />
            </Link>
          </div>
          <div className="divide-y divide-pm-canada-border">
            {activeClients.map(client => (
              <Link
                key={client.id}
                to="/canada/portal/accounts"
                className="px-5 py-3 flex items-center gap-3 hover:bg-pm-canada-bg/50 transition-colors block"
              >
                <div className="w-8 h-8 rounded-lg bg-pm-accent/10 flex items-center justify-center flex-shrink-0">
                  <Users size={14} className="text-pm-accent" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{client.business_name}</p>
                  <p className="text-2xs text-pm-canada-text-muted">
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
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl">
        <div className="px-5 py-4 border-b border-pm-canada-border flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Recent Activity</h2>
          <Link
            to="/canada/portal/leads"
            className="text-xs text-pm-accent hover:text-pm-accent/80 flex items-center gap-1 transition-colors"
          >
            View all <ArrowRight size={12} />
          </Link>
        </div>
        <div className="divide-y divide-pm-canada-border">
          {recentActivity.length === 0 ? (
            <div className="px-5 py-6 text-center text-sm text-pm-canada-text-faint">
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
                  className="px-5 py-3 flex items-center gap-3 hover:bg-pm-canada-bg/50 transition-colors block"
                >
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${cfg.softBgClass}`}>
                    <div className={`w-2.5 h-2.5 rounded-full ${cfg.dotClass}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">{deal.business_name}</p>
                    <p className="text-2xs text-pm-canada-text-muted">
                      <span className={cfg.textClass}>{cfg.label}</span>
                      <span className="mx-1.5 text-[#2a3430]">|</span>
                      {formatCadMo(deal.monthly_value)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 text-2xs text-pm-canada-text-faint flex-shrink-0">
                    <Clock size={11} />
                    {timeAgo}
                  </div>
                </Link>
              )
            })
          )}
        </div>
      </div>
      </PortalPage>

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
  valueClass,
  bars,
  barClass,
}: {
  label: string
  value: string
  subtitle: string
  icon: React.ReactNode
  iconBg: string
  valueClass?: string
  bars: number[]
  barClass: string
}) {
  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5 flex flex-col justify-between">
      <div className="flex items-start justify-between mb-3">
        <p className="text-xs font-medium text-pm-canada-text-muted">{label}</p>
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${iconBg}`}>
          {icon}
        </div>
      </div>
      <p className={`text-2xl font-bold mb-1 ${valueClass ?? 'text-white'}`}>
        {value}
      </p>
      {/* Sparkline bar chart */}
      <div className="flex items-end gap-[3px] h-5 mb-2">
        {bars.map((h, i) => (
          <div
            key={i}
            className={`flex-1 rounded-sm transition-all ${barClass}`}
            style={{
              height: `${h}%`,
              opacity: 0.25 + (i / bars.length) * 0.55,
            }}
          />
        ))}
      </div>
      <p className="text-2xs text-pm-canada-text-faint truncate">{subtitle}</p>
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
      className="flex items-center gap-2.5 bg-pm-canada-surface border border-pm-canada-border rounded-xl px-4 py-3.5 text-sm font-medium text-white hover:border-pm-accent/40 hover:text-pm-accent transition-colors w-full"
    >
      <span className="text-pm-canada-text-muted group-hover:text-pm-accent">{icon}</span>
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
