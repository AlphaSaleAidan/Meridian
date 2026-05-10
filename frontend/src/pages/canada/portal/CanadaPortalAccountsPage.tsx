import { useState, useEffect } from 'react'
import { Users, DollarSign, TrendingUp, BarChart3, Search, CheckCircle2, Wifi, Calendar, ChevronRight, RefreshCw } from 'lucide-react'
import { canadaSalesDemoData, type SalesClient } from '@/lib/canada-sales-demo-data'

function formatCurrency(value: number): string {
  return 'CA$' + value.toLocaleString('en-CA')
}

function daysUntilBilling(assignedAt: string): number {
  const assigned = new Date(assignedAt)
  const nextBilling = new Date(assigned)
  nextBilling.setDate(nextBilling.getDate() + 30)
  const now = new Date()
  const diff = Math.ceil((nextBilling.getTime() - now.getTime()) / (1000 * 60 * 60 * 24))
  return diff > 0 ? diff : 0
}

function getNextBillingDate(assignedAt: string): string {
  const assigned = new Date(assignedAt)
  const nextBilling = new Date(assigned)
  nextBilling.setDate(nextBilling.getDate() + 30)
  return nextBilling.toISOString().slice(0, 10)
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-CA', { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function CanadaPortalAccountsPage() {
  const [clients, setClients] = useState<SalesClient[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [syncingId, setSyncingId] = useState<string | null>(null)

  useEffect(() => {
    canadaSalesDemoData.clients().then(c => { setClients(c); setLoading(false) })
  }, [])

  const filtered = clients.filter(c => {
    if (!search) return true
    const s = search.toLowerCase()
    return c.business_name.toLowerCase().includes(s) || c.contact_name.toLowerCase().includes(s)
  })

  const activeCount = clients.filter(c => c.is_active).length
  const totalMRR = clients.reduce((s, c) => s + c.monthly_revenue, 0)
  const weeklyRevenue = Math.round(totalMRR / 4)

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
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white">Accounts</h1>
        <p className="text-sm text-[#6b7a74] mt-0.5">{activeCount} active accounts generating revenue</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <Users size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Active Accounts</p>
              <p className="text-lg font-bold text-white">{activeCount}</p>
              <p className="text-[10px] text-[#4a5550]">{activeCount} weekly / {activeCount} monthly</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <DollarSign size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Monthly Recurring</p>
              <p className="text-lg font-bold text-[#f0b429]">{formatCurrency(totalMRR)}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <TrendingUp size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Weekly Revenue</p>
              <p className="text-lg font-bold text-[#f0b429]">{formatCurrency(weeklyRevenue)}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <BarChart3 size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Monthly Revenue</p>
              <p className="text-lg font-bold text-[#f0b429]">{formatCurrency(totalMRR)}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6b7a74]/60" />
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-xl text-sm text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/50"
          placeholder="Search accounts..."
        />
      </div>

      {/* Account List */}
      <div className="space-y-3">
        {filtered.map(client => {
          const isExpanded = expandedId === client.id
          const daysLeft = daysUntilBilling(client.assigned_at)
          const nextBilling = getNextBillingDate(client.assigned_at)

          return (
            <div key={client.id}>
              {/* Account Row Card */}
              <div
                className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4 cursor-pointer hover:border-[#00d4aa]/30 transition-colors"
                onClick={() => setExpandedId(isExpanded ? null : client.id)}
              >
                <div className="flex items-center gap-4">
                  {/* Status Icon */}
                  <CheckCircle2 size={18} className="text-[#00d4aa] flex-shrink-0" />

                  {/* Business + Contact */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{client.business_name}</p>
                    <p className="text-xs text-[#6b7a74]">{client.contact_name}</p>
                  </div>

                  {/* POS Badge */}
                  <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#1a2420] border border-[#1a2420]">
                    <Wifi size={10} className="text-[#6b7a74]" />
                    <span className="text-[10px] text-[#6b7a74] font-medium">{client.pos_provider || 'N/A'}</span>
                  </div>

                  {/* Revenue Badge */}
                  <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#00d4aa]/10 border border-[#00d4aa]/20">
                    <DollarSign size={10} className="text-[#00d4aa]" />
                    <span className="text-[10px] text-[#f0b429] font-medium">CA${client.monthly_revenue.toLocaleString()}/mo</span>
                  </div>

                  {/* Next Billing */}
                  <div className="hidden md:flex items-center gap-1.5 text-[#6b7a74]">
                    <Calendar size={10} />
                    <span className="text-[10px]">{formatDate(nextBilling)}</span>
                  </div>

                  {/* Due In Badge */}
                  <div className="hidden md:flex items-center px-2.5 py-1 rounded-full bg-[#00d4aa]/10">
                    <span className="text-[10px] text-[#00d4aa] font-medium">Due in {daysLeft}d</span>
                  </div>

                  {/* Chevron */}
                  <ChevronRight size={16} className={`text-[#4a5550] transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </div>
              </div>

              {/* Expanded Detail */}
              {isExpanded && (
                <div className="bg-[#0a0f0d] border border-[#1a2420] border-t-0 rounded-b-xl px-5 py-5 -mt-1 space-y-5">
                  {/* Top row: back + active badge */}
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setExpandedId(null)}
                      className="text-xs text-[#00d4aa] hover:text-[#00d4aa]/80 transition-colors"
                    >
                      &larr; Back to accounts
                    </button>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-medium bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20">
                      Active
                    </span>
                  </div>

                  {/* Business Info */}
                  <div>
                    <h3 className="text-base font-bold text-white">{client.business_name}</h3>
                    <p className="text-xs text-[#6b7a74] mt-0.5">{client.contact_name} &middot; {client.contact_email}</p>
                  </div>

                  {/* Inline Stats Row */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-[#0f1512] border border-[#1a2420] rounded-lg px-3 py-2">
                      <p className="text-[10px] text-[#4a5550]">Revenue / Plan</p>
                      <p className="text-xs font-semibold text-white">{formatCurrency(client.monthly_revenue)} <span className="text-[#6b7a74] capitalize">({client.plan})</span></p>
                    </div>
                    <div className="bg-[#0f1512] border border-[#1a2420] rounded-lg px-3 py-2">
                      <p className="text-[10px] text-[#4a5550]">Next Billing</p>
                      <p className="text-xs font-semibold text-white">{formatDate(nextBilling)}</p>
                    </div>
                    <div className="bg-[#0f1512] border border-[#1a2420] rounded-lg px-3 py-2">
                      <p className="text-[10px] text-[#4a5550]">POS System</p>
                      <p className="text-xs font-semibold text-white capitalize">{client.pos_provider || 'Not connected'}</p>
                    </div>
                    <div className="bg-[#0f1512] border border-[#1a2420] rounded-lg px-3 py-2">
                      <p className="text-[10px] text-[#4a5550]">Transactions</p>
                      <p className="text-xs font-semibold text-[#6b7a74]">&mdash;</p>
                    </div>
                  </div>

                  {/* Billing Schedule Card */}
                  <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
                    <h4 className="text-xs font-semibold text-white mb-3">Billing Schedule</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-[10px] text-[#4a5550]">Started</p>
                        <p className="text-xs text-white">{formatDate(client.assigned_at)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-[#4a5550]">Next Payment</p>
                        <p className="text-xs text-white">{formatDate(nextBilling)}</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-[#4a5550]">Cycle</p>
                        <p className="text-xs text-white">Monthly</p>
                      </div>
                      <div>
                        <p className="text-[10px] text-[#4a5550]">Amount</p>
                        <p className="text-xs text-white">{formatCurrency(client.monthly_revenue)}</p>
                      </div>
                    </div>
                  </div>

                  {/* POS Sync */}
                  <div className="space-y-3">
                    <p className="text-[10px] text-[#4a5550]">Last POS sync: {new Date(Date.now() - 1000 * 60 * 47).toLocaleString('en-CA')}</p>
                    <button
                      onClick={() => { setSyncingId(client.id); setTimeout(() => setSyncingId(null), 2000) }}
                      disabled={syncingId === client.id}
                      className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-[#1a2420] rounded-xl text-xs text-[#6b7a74] hover:border-[#00d4aa]/30 hover:text-[#00d4aa] disabled:opacity-50 transition-colors"
                    >
                      <RefreshCw size={12} className={syncingId === client.id ? 'animate-spin' : ''} />
                      {syncingId === client.id ? 'Syncing...' : 'Sync POS Data'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )
        })}

        {filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-[#4a5550]">
            {search ? 'No accounts match your search.' : 'No active accounts yet. Close some deals to see them here.'}
          </div>
        )}
      </div>
    </div>
  )
}
