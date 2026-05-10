import { useState, useEffect } from 'react'
import { DollarSign, TrendingUp, Clock, CheckCircle2, Search, ArrowUpRight, ArrowDownRight, Wallet } from 'lucide-react'
import { deriveCommissionsFromLeads, type Commission } from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'
import { useSalesAuth } from '@/lib/sales-auth'

function formatCurrency(value: number): string {
  return 'CA$' + value.toLocaleString('en-CA')
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  paid: { bg: 'bg-[#00d4aa]/10 border-[#00d4aa]/20', text: 'text-[#00d4aa]', label: 'Paid' },
  earned: { bg: 'bg-[#f0b429]/10 border-[#f0b429]/20', text: 'text-[#f0b429]', label: 'Earned' },
  pending: { bg: 'bg-[#7C5CFF]/10 border-[#7C5CFF]/20', text: 'text-[#7C5CFF]', label: 'Pending' },
  disputed: { bg: 'bg-red-500/10 border-red-500/20', text: 'text-red-400', label: 'Disputed' },
}

export default function CanadaPortalCommissionsPage() {
  const { rep } = useSalesAuth()
  const [commissions, setCommissions] = useState<Commission[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'paid' | 'earned' | 'pending'>('all')

  useEffect(() => {
    canadaLeadsService.list().then(deals => {
      setCommissions(deriveCommissionsFromLeads(deals))
      setLoading(false)
    })
  }, [])

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

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#00d4aa] font-bold text-sm">M</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Commissions</h1>
        <p className="text-sm text-[#6b7a74] mt-0.5">
          {commissionRate}% commission rate &middot; {commissions.length} transactions
        </p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f0b429]/10 flex items-center justify-center">
              <DollarSign size={16} className="text-[#f0b429]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Total Earned</p>
              <p className="text-lg font-bold text-[#f0b429]">{formatCurrency(totalEarned)}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <CheckCircle2 size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Paid Out</p>
              <p className="text-lg font-bold text-[#00d4aa]">{formatCurrency(totalPaid)}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
              <Clock size={16} className="text-[#7C5CFF]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Pending Payout</p>
              <p className="text-lg font-bold text-[#7C5CFF]">{formatCurrency(pendingPayout)}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f0b429]/10 flex items-center justify-center">
              <Wallet size={16} className="text-[#f0b429]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Your Rate</p>
              <p className="text-lg font-bold text-white">{commissionRate}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* How it works */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
        <p className="text-xs text-[#6b7a74]">
          <span className="text-white font-medium">How commissions work:</span> You earn {commissionRate}% of each client's monthly POS transaction revenue.
          Commissions are calculated weekly, move to "earned" after verification, and are paid out bi-weekly via direct deposit.
        </p>
      </div>

      {/* Filter Tabs + Search */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex gap-1 p-1 bg-[#0f1512] border border-[#1a2420] rounded-xl w-fit">
          {(['all', 'earned', 'pending', 'paid'] as const).map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-all capitalize ${
                filter === f ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white'
              }`}
            >
              {f === 'all' ? 'All' : f}
            </button>
          ))}
        </div>
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6b7a74]/60" />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[#0f1512] border border-[#1a2420] rounded-xl text-sm text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/50"
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
            <div key={comm.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4">
              <div className="flex items-center gap-4">
                {/* Direction icon */}
                <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${isIncome ? 'bg-[#00d4aa]/10' : 'bg-[#f0b429]/10'}`}>
                  {isIncome
                    ? <ArrowDownRight size={16} className="text-[#00d4aa]" />
                    : <ArrowUpRight size={16} className="text-[#f0b429]" />
                  }
                </div>

                {/* Details */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{comm.client_name}</p>
                  <p className="text-[11px] text-[#6b7a74]">
                    {comm.source_type.replace('_', ' ')} &middot; {formatDate(comm.created_at)}
                  </p>
                </div>

                {/* Gross + Rate */}
                <div className="hidden sm:block text-right">
                  <p className="text-[11px] text-[#6b7a74]">Gross: {formatCurrency(comm.gross_amount)}</p>
                  <p className="text-[10px] text-[#4a5550]">{comm.commission_rate}% rate</p>
                </div>

                {/* Commission Amount */}
                <div className="text-right min-w-[90px]">
                  <p className="text-sm font-bold text-[#f0b429]">{formatCurrency(comm.commission_amount)}</p>
                </div>

                {/* Status Badge */}
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium border flex-shrink-0 ${style.bg} ${style.text}`}>
                  {style.label}
                </span>
              </div>
            </div>
          )
        })}

        {filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-[#4a5550]">
            {search || filter !== 'all' ? 'No commissions match your filter.' : 'No commissions yet. Close deals and connect POS to start earning.'}
          </div>
        )}
      </div>

      {/* Payout Schedule */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
        <h2 className="text-sm font-semibold text-white mb-3">Payout Schedule</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-[10px] text-[#4a5550]">Frequency</p>
            <p className="text-xs text-white">Bi-weekly</p>
          </div>
          <div>
            <p className="text-[10px] text-[#4a5550]">Next Payout</p>
            <p className="text-xs text-white">{getNextPayout()}</p>
          </div>
          <div>
            <p className="text-[10px] text-[#4a5550]">Method</p>
            <p className="text-xs text-white">Direct Deposit</p>
          </div>
          <div>
            <p className="text-[10px] text-[#4a5550]">Est. Amount</p>
            <p className="text-xs font-semibold text-[#f0b429]">{formatCurrency(pendingPayout)}</p>
          </div>
        </div>
      </div>
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
