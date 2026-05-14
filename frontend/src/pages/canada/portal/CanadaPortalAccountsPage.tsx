import { useState, useEffect } from 'react'
import { Users, DollarSign, TrendingUp, BarChart3, Search, CheckCircle2, Wifi, Calendar, ChevronRight, RefreshCw, AlertTriangle, CreditCard, Loader2, Send } from 'lucide-react'
import { deriveClientsFromLeads, type SalesClient } from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'
import { useSalesAuth } from '@/lib/sales-auth'

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

const API_BASE = import.meta.env.VITE_API_URL || ''

type BillingStatus = 'unchecked' | 'checking' | 'active' | 'pending' | 'past_due' | 'none'

export default function CanadaPortalAccountsPage() {
  const { rep } = useSalesAuth()
  const [clients, setClients] = useState<SalesClient[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [syncingId, setSyncingId] = useState<string | null>(null)
  const [billingStatuses, setBillingStatuses] = useState<Record<string, BillingStatus>>({})
  const [notifyingId, setNotifyingId] = useState<string | null>(null)
  const [notifiedIds, setNotifiedIds] = useState<Set<string>>(new Set())
  const [cardUpdateId, setCardUpdateId] = useState<string | null>(null)

  useEffect(() => {
    canadaLeadsService.list().then(deals => {
      setClients(deriveClientsFromLeads(deals))
      setLoading(false)
    })
  }, [])

  async function checkBilling(clientId: string) {
    setBillingStatuses(prev => ({ ...prev, [clientId]: 'checking' }))
    try {
      const res = await fetch(`${API_BASE}/api/billing/status/${clientId}`)
      if (!res.ok) { setBillingStatuses(prev => ({ ...prev, [clientId]: 'none' })); return }
      const data = await res.json()
      const s = data.status as string
      if (s === 'active') setBillingStatuses(prev => ({ ...prev, [clientId]: 'active' }))
      else if (s === 'past_due') setBillingStatuses(prev => ({ ...prev, [clientId]: 'past_due' }))
      else if (s === 'pending_payment') setBillingStatuses(prev => ({ ...prev, [clientId]: 'pending' }))
      else setBillingStatuses(prev => ({ ...prev, [clientId]: 'none' }))
    } catch {
      setBillingStatuses(prev => ({ ...prev, [clientId]: 'none' }))
    }
  }

  async function notifyClient(client: SalesClient) {
    setNotifyingId(client.id)
    try {
      const res = await fetch(`${API_BASE}/api/billing/notify-payment-failed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: client.id,
          customer_email: client.contact_email,
          contact_name: client.contact_name,
          business_name: client.business_name,
          rep_name: rep?.name || '',
          rep_email: rep?.email || '',
        }),
      })
      if (res.ok) setNotifiedIds(prev => new Set(prev).add(client.id))
    } catch {
      window.alert('Failed to send notification. Please try again.')
    }
    setNotifyingId(null)
  }

  async function sendCardUpdate(client: SalesClient) {
    setCardUpdateId(client.id)
    try {
      await fetch(`${API_BASE}/api/billing/update-payment-method`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: client.id,
          customer_email: client.contact_email,
          customer_name: client.contact_name,
          business_name: client.business_name,
        }),
      })
    } catch {
      window.alert('Failed to send card update request. Please try again.')
    }
    setCardUpdateId(null)
  }

  const filtered = clients.filter(c => {
    if (!search) return true
    const s = search.toLowerCase()
    return c.business_name.toLowerCase().includes(s) || c.contact_name.toLowerCase().includes(s)
  })

  const activeCount = clients.filter(c => c.is_active).length
  const totalMRR = clients.reduce((s, c) => s + c.monthly_revenue, 0)
  const annualRevenue = totalMRR * 12
  const avgRevPerAccount = activeCount > 0 ? Math.round(totalMRR / activeCount) : 0

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
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Annual Revenue</p>
              <p className="text-lg font-bold text-[#f0b429]">{formatCurrency(annualRevenue)}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <BarChart3 size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Avg per Account</p>
              <p className="text-lg font-bold text-[#f0b429]">{formatCurrency(avgRevPerAccount)}/mo</p>
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

                  {/* Payment Status Badge */}
                  {billingStatuses[client.id] === 'active' && (
                    <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#00d4aa]/10 border border-[#00d4aa]/20">
                      <CheckCircle2 size={10} className="text-[#00d4aa]" />
                      <span className="text-[10px] text-[#00d4aa] font-medium">Paid</span>
                    </div>
                  )}
                  {billingStatuses[client.id] === 'pending' && (
                    <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-[#f0b429]/10 border border-[#f0b429]/20">
                      <span className="text-[10px] text-[#f0b429] font-medium">Pending</span>
                    </div>
                  )}
                  {billingStatuses[client.id] === 'past_due' && (
                    <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20">
                      <AlertTriangle size={10} className="text-red-400" />
                      <span className="text-[10px] text-red-400 font-medium">Past Due</span>
                    </div>
                  )}

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

                  {/* Billing Actions */}
                  <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-white flex items-center gap-1.5">
                        <CreditCard size={12} className="text-[#00d4aa]" /> Payment
                      </h4>
                      <button
                        onClick={() => checkBilling(client.id)}
                        disabled={billingStatuses[client.id] === 'checking'}
                        className="text-[10px] text-[#6b7a74] hover:text-[#00d4aa] transition-colors flex items-center gap-1"
                      >
                        <RefreshCw size={10} className={billingStatuses[client.id] === 'checking' ? 'animate-spin' : ''} />
                        Check Status
                      </button>
                    </div>

                    {billingStatuses[client.id] === 'checking' && (
                      <div className="flex items-center gap-2 text-xs text-[#6b7a74]">
                        <Loader2 size={12} className="animate-spin" /> Checking...
                      </div>
                    )}
                    {billingStatuses[client.id] === 'active' && (
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-[#00d4aa]/10 border border-[#00d4aa]/20">
                        <CheckCircle2 size={14} className="text-[#00d4aa]" />
                        <span className="text-[11px] text-[#00d4aa] font-medium">Payment active — card on file</span>
                      </div>
                    )}
                    {billingStatuses[client.id] === 'pending' && (
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-[#f0b429]/10 border border-[#f0b429]/20">
                        <span className="text-[11px] text-[#f0b429] font-medium">Invoice sent — awaiting payment</span>
                      </div>
                    )}
                    {billingStatuses[client.id] === 'past_due' && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-red-500/10 border border-red-500/20">
                          <AlertTriangle size={14} className="text-red-400" />
                          <span className="text-[11px] text-red-400 font-medium">Payment past due</span>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => notifyClient(client)}
                            disabled={notifyingId === client.id || notifiedIds.has(client.id)}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] font-medium text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 disabled:opacity-50 transition-all"
                          >
                            {notifyingId === client.id ? <Loader2 size={12} className="animate-spin" /> : notifiedIds.has(client.id) ? <CheckCircle2 size={12} /> : <Send size={12} />}
                            {notifiedIds.has(client.id) ? 'Notified' : 'Notify'}
                          </button>
                          <button
                            onClick={() => sendCardUpdate(client)}
                            disabled={cardUpdateId === client.id}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-[11px] font-medium text-[#0a0f0d] bg-[#00d4aa] rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all"
                          >
                            {cardUpdateId === client.id ? <Loader2 size={12} className="animate-spin" /> : <CreditCard size={12} />}
                            Update Card
                          </button>
                        </div>
                      </div>
                    )}
                    {(!billingStatuses[client.id] || billingStatuses[client.id] === 'unchecked' || billingStatuses[client.id] === 'none') && billingStatuses[client.id] !== 'checking' && (
                      <p className="text-[11px] text-[#4a5550]">Click "Check Status" to see billing status.</p>
                    )}
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
