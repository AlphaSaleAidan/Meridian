import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Users,
  DollarSign,
  TrendingUp,
  CreditCard,
  Wifi,
  Target,
  ArrowRight,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { canadaSalesDemoData, type SalesOverview, type Deal, type SalesClient } from '@/lib/canada-sales-demo-data'

const CAD_RATE = 1.37

function formatCentsToCad(cents: number): string {
  const cad = (cents / 100) * CAD_RATE
  return 'CA$' + cad.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatDollarsCad(value: number): string {
  const cad = Math.round(value * CAD_RATE)
  return 'CA$' + cad.toLocaleString('en-CA') + '/mo'
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

const STAGE_STEP_MAP: Record<string, number> = {
  prospecting: 1,
  contacted: 2,
  demo_scheduled: 3,
  proposal_sent: 4,
  negotiation: 5,
  closed_won: 6,
}

export default function CanadaPortalDashboardPage() {
  const { rep } = useSalesAuth()
  const [overview, setOverview] = useState<SalesOverview | null>(null)
  const [deals, setDeals] = useState<Deal[]>([])
  const [clients, setClients] = useState<SalesClient[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      canadaSalesDemoData.overview(),
      canadaSalesDemoData.deals(),
      canadaSalesDemoData.clients(),
    ]).then(([o, d, c]) => {
      setOverview(o)
      setDeals(d)
      setClients(c)
      setLoading(false)
    })
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
  const mrr = activeClients.reduce((sum, c) => sum + c.monthly_revenue, 0)
  const pipelineDeals = deals.filter(d => !['closed_won', 'closed_lost'].includes(d.stage))
  const pipelineValue = pipelineDeals.reduce((sum, d) => sum + d.monthly_value, 0)
  const commissionRate = rep?.commission_rate ?? 35
  const pendingPayout = overview.pending_payout

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div>
        <h1 className="text-xl font-bold text-white">
          Welcome back, {rep ? getFirstName(rep.name) : 'there'}
        </h1>
        <p className="text-sm text-[#6b7a74] mt-1">Your sales overview at a glance.</p>
      </div>

      {/* Stat Cards - 2x2 grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Active Accounts */}
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-[#6b7a74] mb-1">Active Accounts</p>
              <p className="text-2xl font-bold text-white">{activeClients.length}</p>
              <p className="text-[11px] text-[#4a5550] mt-1">POS connected & billing active</p>
            </div>
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-[#00d4aa]/15">
              <Users size={20} className="text-[#00d4aa]" />
            </div>
          </div>
        </div>

        {/* Monthly Revenue */}
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-[#6b7a74] mb-1">Monthly Revenue</p>
              <p className="text-2xl font-bold text-white">{formatCentsToCad(mrr)}</p>
              <p className="text-[11px] text-[#4a5550] mt-1">MRR from active accounts</p>
            </div>
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-[#00d4aa]/15">
              <DollarSign size={20} className="text-[#00d4aa]" />
            </div>
          </div>
        </div>

        {/* In Pipeline */}
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-[#6b7a74] mb-1">In Pipeline</p>
              <p className="text-2xl font-bold text-white">{pipelineDeals.length}</p>
              <p className="text-[11px] text-[#4a5550] mt-1">
                ${pipelineValue.toLocaleString()}/mo potential
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-[#f59e0b]/15">
              <TrendingUp size={20} className="text-[#f59e0b]" />
            </div>
          </div>
        </div>

        {/* Commissions */}
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-[#6b7a74] mb-1">Commissions</p>
              <p className="text-2xl font-bold text-white">{formatCentsToCad(overview.total_earned)}</p>
              <p className="text-[11px] text-[#4a5550] mt-1">
                {formatCentsToCad(pendingPayout)} pending
              </p>
              <p className="text-[11px] text-[#00d4aa] mt-0.5 font-medium">
                {commissionRate}% commission rate
              </p>
            </div>
            <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-[#7c3aed]/15">
              <CreditCard size={20} className="text-[#7c3aed]" />
            </div>
          </div>
        </div>
      </div>

      {/* Active Accounts List */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl">
        <div className="px-5 py-4 border-b border-[#1a2420] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Active Accounts</h2>
          <Link
            to="/canada/portal/accounts"
            className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/80 flex items-center gap-1 transition-colors"
          >
            View All <ArrowRight size={12} />
          </Link>
        </div>
        <div className="divide-y divide-[#1a2420]">
          {activeClients.length === 0 ? (
            <div className="px-5 py-6 text-center text-sm text-[#4a5550]">
              No active accounts yet.
            </div>
          ) : (
            activeClients.map(client => (
              <div key={client.id} className="px-5 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center flex-shrink-0">
                  <Wifi size={14} className="text-[#00d4aa]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{client.business_name}</p>
                  <p className="text-[11px] text-[#6b7a74]">{client.pos_provider ?? 'POS'}</p>
                </div>
                <span className="text-xs font-semibold text-white bg-[#1a2420] px-2.5 py-1 rounded-lg flex-shrink-0">
                  {formatCentsToCad(client.monthly_revenue)}/mo
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Pipeline List */}
      <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl">
        <div className="px-5 py-4 border-b border-[#1a2420] flex items-center justify-between">
          <h2 className="text-sm font-semibold text-white">Pipeline</h2>
          <Link
            to="/canada/portal/leads"
            className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/80 flex items-center gap-1 transition-colors"
          >
            View All <ArrowRight size={12} />
          </Link>
        </div>
        <div className="divide-y divide-[#1a2420]">
          {pipelineDeals.length === 0 ? (
            <div className="px-5 py-6 text-center text-sm text-[#4a5550]">
              No deals in pipeline.
            </div>
          ) : (
            pipelineDeals.map(deal => (
              <div key={deal.id} className="px-5 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#f59e0b]/10 flex items-center justify-center flex-shrink-0">
                  <Target size={14} className="text-[#f59e0b]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white truncate">{deal.business_name}</p>
                  <p className="text-[11px] text-[#6b7a74]">{deal.contact_name}</p>
                </div>
                <span className="text-[11px] font-medium text-[#f59e0b] bg-[#f59e0b]/10 px-2.5 py-1 rounded-lg flex-shrink-0">
                  Step {STAGE_STEP_MAP[deal.stage] ?? 1}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* CTA Banner */}
      <div className="bg-[#0f1512] border border-[#00d4aa]/30 rounded-xl p-5 flex items-center justify-between">
        <p className="text-sm text-[#6b7a74]">
          <span className="text-white font-semibold">{pipelineDeals.length} deals</span> in progress
          {' '}&middot; Keep working through the SOP steps
        </p>
        <Link
          to="/canada/portal/leads"
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold hover:bg-[#00d4aa]/90 transition-colors flex-shrink-0"
        >
          Go to Leads <ArrowRight size={14} />
        </Link>
      </div>
    </div>
  )
}
