import { useMemo, useState } from 'react'
import { DollarSign, TrendingUp, Clock, CheckCircle2, Search, ArrowUpRight, ArrowDownRight, Wallet, Target } from 'lucide-react'
import { deriveCommissionsFromLeads, type Commission } from '@/lib/canada-sales-demo-data'
import { useCanadaLeads, useCanadaLeadsRealtime } from '@/lib/canada-queries'
import { useSalesAuth } from '@/lib/sales-auth'
import { formatCad as formatCurrency } from '@/lib/format'
import { PortalPage } from './PortalPage'

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  paid: { bg: 'bg-pm-accent/10 border-pm-accent/20', text: 'text-pm-accent', label: 'Paid' },
  earned: { bg: 'bg-pm-amber-gold/10 border-pm-amber-gold/20', text: 'text-pm-amber-gold', label: 'Earned' },
  pending: { bg: 'bg-pm-indigo/10 border-pm-indigo/20', text: 'text-pm-indigo', label: 'Pending' },
  disputed: { bg: 'bg-red-500/10 border-red-500/20', text: 'text-red-400', label: 'Disputed' },
}

export default function CanadaPortalCommissionsPage() {
  const { rep } = useSalesAuth()
  const { data: deals = [], isLoading, error } = useCanadaLeads(rep?.rep_id)
  useCanadaLeadsRealtime(rep?.rep_id)
  const commissions: Commission[] = useMemo(() => deriveCommissionsFromLeads(deals), [deals])
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'paid' | 'earned' | 'pending'>('all')

  const filtered = commissions.filter(c => {
    if (filter !== 'all' && c.status !== filter) return false
    if (search) {
      const s = search.toLowerCase()
      return c.client_name.toLowerCase().includes(s) || c.source_type.toLowerCase().includes(s)
    }
    return true
  })

  const totalEarned = commissions.reduce((s, c) => s + c.commission_amount, 0)
  const totalPaid = commissions.filter(c => c.status === 'paid').reduce((s, c) => s + c.commission_amount, 0)
  const pendingPayout = commissions.filter(c => c.status === 'earned' || c.status === 'pending').reduce((s, c) => s + c.commission_amount, 0)
  const commissionRate = rep?.commission_rate ?? 70

  const emptyState = (
    <div className="py-12 text-center text-sm text-pm-canada-text-faint">
      No commissions yet. Close deals and connect POS to start earning.
    </div>
  )

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Commissions</h1>
        <p className="text-sm text-pm-canada-text-muted mt-0.5">
          {commissionRate}% commission rate &middot; {commissions.length} transactions
        </p>
      </div>

      <PortalPage
        isLoading={isLoading}
        error={error}
        isEmpty={commissions.length === 0}
        emptyState={emptyState}
        errorTitle="Could not load commissions"
      >

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-amber-gold/10 flex items-center justify-center">
              <DollarSign size={16} className="text-pm-amber-gold" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Total Earned</p>
              <p className="text-lg font-bold text-pm-amber-gold">{formatCurrency(totalEarned)}</p>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
              <CheckCircle2 size={16} className="text-pm-accent" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Paid Out</p>
              <p className="text-lg font-bold text-pm-accent">{formatCurrency(totalPaid)}</p>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-indigo/10 flex items-center justify-center">
              <Clock size={16} className="text-pm-indigo" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Pending Payout</p>
              <p className="text-lg font-bold text-pm-indigo">{formatCurrency(pendingPayout)}</p>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-amber-gold/10 flex items-center justify-center">
              <Wallet size={16} className="text-pm-amber-gold" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Your Rate</p>
              <p className="text-lg font-bold text-white">{commissionRate}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Projected Earnings + Goal Tracker */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={14} className="text-pm-accent" />
            <h3 className="text-xs font-semibold text-white">Projected Earnings</h3>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-2xs text-pm-canada-text-muted">This month</span>
              <span className="text-sm font-bold text-pm-accent">{formatCurrency(Math.round(totalEarned * 1.15))}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-2xs text-pm-canada-text-muted">Next month (est.)</span>
              <span className="text-sm font-bold text-white">{formatCurrency(Math.round(totalEarned * 1.25))}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-2xs text-pm-canada-text-muted">Annual pace</span>
              <span className="text-sm font-bold text-pm-amber-gold">{formatCurrency(Math.round(totalEarned * 12))}</span>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-2 mb-3">
            <Target size={14} className="text-pm-indigo" />
            <h3 className="text-xs font-semibold text-white">Monthly Goal</h3>
          </div>
          {(() => {
            const goal = totalEarned > 8000 ? 15000 : totalEarned > 3000 ? 8000 : 5000
            const progress = Math.min(100, Math.round((totalEarned / goal) * 100))
            const dealsNeeded = totalEarned >= goal ? 0 : Math.ceil((goal - totalEarned) / (totalEarned / Math.max(commissions.length, 1)))
            return (
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-2xs text-pm-canada-text-muted">Target: {formatCurrency(goal)}/mo</span>
                  <span className={`text-sm font-bold ${progress >= 100 ? 'text-pm-accent' : 'text-pm-indigo'}`}>{progress}%</span>
                </div>
                <div className="w-full h-2 bg-pm-canada-border rounded-full overflow-hidden">
                  <div className={`h-full rounded-full transition-all ${progress >= 100 ? 'bg-pm-accent' : 'bg-pm-indigo'}`} style={{ width: `${progress}%` }} />
                </div>
                <p className="text-2xs text-pm-canada-text-faint">
                  {progress >= 100 ? 'Goal reached! Keep pushing for stretch targets.' : `~${dealsNeeded} more deal${dealsNeeded !== 1 ? 's' : ''} to hit CA$${goal.toLocaleString()}/mo`}
                </p>
              </div>
            )
          })()}
        </div>
      </div>

      {/* How it works */}
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
        <p className="text-xs text-pm-canada-text-muted">
          <span className="text-white font-medium">How commissions work:</span> You earn {commissionRate}% of each client's monthly POS transaction revenue.
          Commissions are calculated weekly, move to "earned" after verification, and are paid out bi-weekly via direct deposit.
        </p>
      </div>

      {/* Filter Tabs + Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-1 p-1 bg-pm-canada-surface border border-pm-canada-border rounded-xl w-fit">
          {(['all', 'earned', 'pending', 'paid'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all capitalize ${
                filter === f ? 'bg-pm-canada-border text-white' : 'text-pm-canada-text-muted hover:text-white'
              }`}
            >
              {f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-pm-canada-text-muted/60" />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-pm-canada-surface border border-pm-canada-border rounded-xl text-sm text-white placeholder-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50"
            placeholder="Search by client or source..."
          />
        </div>
      </div>

      {/* Commission List */}
      <div className="space-y-2">
        {filtered.map(comm => {
          const style = STATUS_STYLES[comm.status] || STATUS_STYLES.pending
          const isIncome = comm.status === 'paid'
          return (
            <div key={comm.id} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-4">
              <div className="flex items-center gap-4">
                {/* Direction icon */}
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${isIncome ? 'bg-pm-accent/10' : 'bg-pm-amber-gold/10'}`}>
                  {isIncome
                    ? <ArrowDownRight size={16} className="text-pm-accent" />
                    : <ArrowUpRight size={16} className="text-pm-amber-gold" />
                  }
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{comm.client_name}</p>
                  <p className="text-2xs text-pm-canada-text-muted">
                    {comm.source_type.replace('_', ' ')} &middot; {formatDate(comm.created_at)}
                  </p>
                </div>

                {/* Gross + Rate */}
                <div className="hidden sm:block text-right">
                  <p className="text-2xs text-pm-canada-text-muted">Gross: {formatCurrency(comm.gross_amount)}</p>
                  <p className="text-2xs text-pm-canada-text-faint">{comm.commission_rate}% rate</p>
                </div>

                {/* Commission Amount */}
                <div className="text-right min-w-[90px]">
                  <p className="text-sm font-bold text-pm-amber-gold">{formatCurrency(comm.commission_amount)}</p>
                </div>

                {/* Status Badge */}
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium border flex-shrink-0 ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
              </div>
            </div>
          )
        })}

        {/* When the rep has commissions but the active filter/search hides
            them all, show inline hint — the "no commissions at all" empty
            state is handled by PortalPage. */}
        {commissions.length > 0 && filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-pm-canada-text-faint">
            No commissions match your filter.
          </div>
        )}
      </div>

      {/* Payout Schedule */}
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Payout Schedule</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-2xs text-pm-canada-text-faint">Frequency</p>
            <p className="text-xs text-white">Bi-weekly</p>
          </div>
          <div>
            <p className="text-2xs text-pm-canada-text-faint">Next Payout</p>
            <p className="text-xs text-white">{getNextPayout()}</p>
          </div>
          <div>
            <p className="text-2xs text-pm-canada-text-faint">Method</p>
            <p className="text-xs text-white">Direct Deposit</p>
          </div>
          <div>
            <p className="text-2xs text-pm-canada-text-faint">Est. Amount</p>
            <p className="text-xs font-semibold text-pm-amber-gold">{formatCurrency(pendingPayout)}</p>
          </div>
        </div>
      </div>
      </PortalPage>
    </div>
  )
}

function getNextPayout(): string {
  const now = new Date()
  const day = now.getDate()
  const next = new Date(now)
  if (day <= 15) {
    next.setDate(15)
  } else {
    next.setMonth(next.getMonth() + 1, 1)
  }
  return next.toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}
