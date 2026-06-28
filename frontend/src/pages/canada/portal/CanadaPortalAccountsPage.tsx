import { useMemo, useState } from 'react'
import { Users, DollarSign, TrendingUp, BarChart3, Search, CheckCircle2, Calendar, ChevronRight, RefreshCw, AlertTriangle, CreditCard, Loader2, Send } from 'lucide-react'
import { deriveClientsFromLeads, type SalesClient } from '@/lib/canada-sales-demo-data'
import { useCanadaLeads, useCanadaLeadsRealtime } from '@/lib/canada-queries'
import { useSalesAuth } from '@/lib/sales-auth'
import { useToast } from '@/components/Toast'
import { getAuthHeaders } from '@/lib/supabase'
import { formatCad as formatCurrency } from '@/lib/format'
import { PortalPage } from './PortalPage'

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
  const { toast } = useToast()
  const { data: deals = [], isLoading, error } = useCanadaLeads(rep?.rep_id)
  useCanadaLeadsRealtime(rep?.rep_id)
  const clients: SalesClient[] = useMemo(() => deriveClientsFromLeads(deals), [deals])
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [billingStatuses, setBillingStatuses] = useState<Record<string, BillingStatus>>({})
  const [notifyingId, setNotifyingId] = useState<string | null>(null)
  const [notifiedIds, setNotifiedIds] = useState<Set<string>>(new Set())
  const [cardUpdateId, setCardUpdateId] = useState<string | null>(null)

  async function checkBilling(clientId: string) {
    setBillingStatuses(prev => ({ ...prev, [clientId]: 'checking' }))
    try {
      const headers = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/billing/status/${clientId}`, { headers })
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
      const headers = await getAuthHeaders()
      const res = await fetch(`${API_BASE}/api/billing/notify-payment-failed`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          org_id: client.id,
          customer_email: client.contact_email,
          contact_name: client.contact_name,
          business_name: client.business_name,
          rep_name: rep?.name || '',
          rep_email: rep?.email || '',
        }),
      })
      if (res.ok) {
        setNotifiedIds(prev => new Set(prev).add(client.id))
        toast('Payment reminder sent', 'success')
      }
    } catch {
      toast('Failed to send notification', 'error')
    }
    setNotifyingId(null)
  }

  async function sendCardUpdate(client: SalesClient) {
    setCardUpdateId(client.id)
    try {
      const headers = await getAuthHeaders()
      await fetch(`${API_BASE}/api/billing/update-payment-method`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          org_id: client.id,
          customer_email: client.contact_email,
          customer_name: client.contact_name,
          business_name: client.business_name,
        }),
      })
    } catch {
      toast('Failed to send card update request', 'error')
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

  const emptyState = (
    <div className="py-12 text-center text-sm text-pm-canada-text-faint">
      No active accounts yet. Close some deals to see them here.
    </div>
  )

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white">Accounts</h1>
        <p className="text-sm text-pm-canada-text-muted mt-0.5">{activeCount} active accounts generating revenue</p>
      </div>

      <PortalPage
        isLoading={isLoading}
        error={error}
        isEmpty={clients.length === 0}
        emptyState={emptyState}
        errorTitle="Could not load your accounts"
      >

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
              <Users size={16} className="text-pm-accent" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Active Accounts</p>
              <p className="text-lg font-bold text-white">{activeCount}</p>
              <p className="text-2xs text-pm-canada-text-faint">{activeCount} weekly / {activeCount} monthly</p>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
              <DollarSign size={16} className="text-pm-accent" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Monthly Recurring</p>
              <p className="text-lg font-bold text-pm-amber-gold">{formatCurrency(totalMRR)}</p>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
              <TrendingUp size={16} className="text-pm-accent" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Annual Revenue</p>
              <p className="text-lg font-bold text-pm-amber-gold">{formatCurrency(annualRevenue)}</p>
            </div>
          </div>
        </div>
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
              <BarChart3 size={16} className="text-pm-accent" />
            </div>
            <div>
              <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Avg per Account</p>
              <p className="text-lg font-bold text-pm-amber-gold">{formatCurrency(avgRevPerAccount)}/mo</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-pm-canada-text-muted/60" />
        <input
          type="text" value={search} onChange={e => setSearch(e.target.value)}
          className="w-full pl-9 pr-3 py-2.5 bg-pm-canada-surface border border-pm-canada-border rounded-xl text-sm text-white placeholder-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50"
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
                className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-4 cursor-pointer hover:border-pm-accent/30 transition-colors"
                onClick={() => setExpandedId(isExpanded ? null : client.id)}
              >
                <div className="flex items-center gap-4">
                  {/* Status Icon */}
                  <CheckCircle2 size={18} className="text-pm-accent flex-shrink-0" />

                  {/* Business + Contact */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-white truncate">{client.business_name}</p>
                    <p className="text-xs text-pm-canada-text-muted">{client.contact_name}</p>
                  </div>

                  {/* Read-only sync status: reps see whether the customer has
                      connected — but cannot trigger or manage the POS connection. */}
                  {client.is_active && (
                    <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-pm-accent/10 border border-pm-accent/20">
                      <CheckCircle2 size={10} className="text-pm-accent" />
                      <span className="text-2xs text-pm-accent font-medium">Synced successfully ✓</span>
                    </div>
                  )}

                  {/* Revenue Badge */}
                  <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-pm-accent/10 border border-pm-accent/20">
                    <DollarSign size={10} className="text-pm-accent" />
                    <span className="text-2xs text-pm-amber-gold font-medium">CA${client.monthly_revenue.toLocaleString()}/mo</span>
                  </div>

                  {/* Next Billing */}
                  <div className="hidden md:flex items-center gap-1.5 text-pm-canada-text-muted">
                    <Calendar size={10} />
                    <span className="text-2xs">{formatDate(nextBilling)}</span>
                  </div>

                  {/* Payment Status Badge */}
                  {billingStatuses[client.id] === 'active' && (
                    <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-pm-accent/10 border border-pm-accent/20">
                      <CheckCircle2 size={10} className="text-pm-accent" />
                      <span className="text-2xs text-pm-accent font-medium">Paid</span>
                    </div>
                  )}
                  {billingStatuses[client.id] === 'pending' && (
                    <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-pm-amber-gold/10 border border-pm-amber-gold/20">
                      <span className="text-2xs text-pm-amber-gold font-medium">Pending</span>
                    </div>
                  )}
                  {billingStatuses[client.id] === 'past_due' && (
                    <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20">
                      <AlertTriangle size={10} className="text-red-400" />
                      <span className="text-2xs text-red-400 font-medium">Past Due</span>
                    </div>
                  )}

                  {/* Due In Badge */}
                  <div className="hidden md:flex items-center px-2.5 py-1 rounded-full bg-pm-accent/10">
                    <span className="text-2xs text-pm-accent font-medium">Due in {daysLeft}d</span>
                  </div>

                  {/* Chevron */}
                  <ChevronRight size={16} className={`text-pm-canada-text-faint transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </div>
              </div>

              {/* Expanded Detail */}
              {isExpanded && (
                <div className="bg-pm-canada-bg border border-pm-canada-border border-t-0 rounded-b-xl px-5 py-5 -mt-1 space-y-5">
                  {/* Top row: back + active badge */}
                  <div className="flex items-center justify-between">
                    <button
                      onClick={() => setExpandedId(null)}
                      className="text-xs text-pm-accent hover:text-pm-accent/80 transition-colors"
                    >
                      &larr; Back to accounts
                    </button>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-2xs font-medium bg-pm-accent/10 text-pm-accent border border-pm-accent/20">
                      Active
                    </span>
                  </div>

                  {/* Business Info */}
                  <div>
                    <h3 className="text-base font-bold text-white">{client.business_name}</h3>
                    <p className="text-xs text-pm-canada-text-muted mt-0.5">{client.contact_name} &middot; {client.contact_email}</p>
                  </div>

                  {/* Inline Stats Row */}
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-lg px-3 py-2">
                      <p className="text-2xs text-pm-canada-text-faint">Revenue / Plan</p>
                      <p className="text-xs font-semibold text-white">{formatCurrency(client.monthly_revenue)} <span className="text-pm-canada-text-muted capitalize">({client.plan})</span></p>
                    </div>
                    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-lg px-3 py-2">
                      <p className="text-2xs text-pm-canada-text-faint">Next Billing</p>
                      <p className="text-xs font-semibold text-white">{formatDate(nextBilling)}</p>
                    </div>
                    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-lg px-3 py-2">
                      <p className="text-2xs text-pm-canada-text-faint">Transactions</p>
                      <p className="text-xs font-semibold text-pm-canada-text-muted">&mdash;</p>
                    </div>
                  </div>

                  {/* Billing Schedule Card */}
                  <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
                    <h4 className="text-xs font-semibold text-white mb-3">Billing Schedule</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div>
                        <p className="text-2xs text-pm-canada-text-faint">Started</p>
                        <p className="text-xs text-white">{formatDate(client.assigned_at)}</p>
                      </div>
                      <div>
                        <p className="text-2xs text-pm-canada-text-faint">Next Payment</p>
                        <p className="text-xs text-white">{formatDate(nextBilling)}</p>
                      </div>
                      <div>
                        <p className="text-2xs text-pm-canada-text-faint">Cycle</p>
                        <p className="text-xs text-white">Monthly</p>
                      </div>
                      <div>
                        <p className="text-2xs text-pm-canada-text-faint">Amount</p>
                        <p className="text-xs text-white">{formatCurrency(client.monthly_revenue)}</p>
                      </div>
                    </div>
                  </div>

                  {/* Billing Actions */}
                  <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-semibold text-white flex items-center gap-1.5">
                        <CreditCard size={12} className="text-pm-accent" /> Payment
                      </h4>
                      <button
                        onClick={() => checkBilling(client.id)}
                        disabled={billingStatuses[client.id] === 'checking'}
                        className="text-2xs text-pm-canada-text-muted hover:text-pm-accent transition-colors flex items-center gap-1"
                      >
                        <RefreshCw size={10} className={billingStatuses[client.id] === 'checking' ? 'animate-spin' : ''} />
                        Check Status
                      </button>
                    </div>

                    {billingStatuses[client.id] === 'checking' && (
                      <div className="flex items-center gap-2 text-xs text-pm-canada-text-muted">
                        <Loader2 size={12} className="animate-spin" /> Checking...
                      </div>
                    )}
                    {billingStatuses[client.id] === 'active' && (
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-pm-accent/10 border border-pm-accent/20">
                        <CheckCircle2 size={14} className="text-pm-accent" />
                        <span className="text-2xs text-pm-accent font-medium">Payment active — card on file</span>
                      </div>
                    )}
                    {billingStatuses[client.id] === 'pending' && (
                      <div className="flex items-center gap-2 p-2.5 rounded-lg bg-pm-amber-gold/10 border border-pm-amber-gold/20">
                        <span className="text-2xs text-pm-amber-gold font-medium">Invoice sent — awaiting payment</span>
                      </div>
                    )}
                    {billingStatuses[client.id] === 'past_due' && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-red-500/10 border border-red-500/20">
                          <AlertTriangle size={14} className="text-red-400" />
                          <span className="text-2xs text-red-400 font-medium">Payment past due</span>
                        </div>
                        <div className="flex gap-2">
                          <button
                            onClick={() => notifyClient(client)}
                            disabled={notifyingId === client.id || notifiedIds.has(client.id)}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-2xs font-medium text-red-400 border border-red-500/30 rounded-lg hover:bg-red-500/10 disabled:opacity-50 transition-all"
                          >
                            {notifyingId === client.id ? <Loader2 size={12} className="animate-spin" /> : notifiedIds.has(client.id) ? <CheckCircle2 size={12} /> : <Send size={12} />}
                            {notifiedIds.has(client.id) ? 'Notified' : 'Notify'}
                          </button>
                          <button
                            onClick={() => sendCardUpdate(client)}
                            disabled={cardUpdateId === client.id}
                            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-2xs font-medium text-pm-canada-bg bg-pm-accent rounded-lg hover:bg-pm-accent/90 disabled:opacity-50 transition-all"
                          >
                            {cardUpdateId === client.id ? <Loader2 size={12} className="animate-spin" /> : <CreditCard size={12} />}
                            Update Card
                          </button>
                        </div>
                      </div>
                    )}
                    {(!billingStatuses[client.id] || billingStatuses[client.id] === 'unchecked' || billingStatuses[client.id] === 'none') && billingStatuses[client.id] !== 'checking' && (
                      <p className="text-2xs text-pm-canada-text-faint">Click "Check Status" to see billing status.</p>
                    )}
                  </div>

                </div>
              )}
            </div>
          )
        })}

        {/* When user is searching but no result, show inline hint — the
            "no accounts at all" empty state is handled by PortalPage. */}
        {clients.length > 0 && filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-pm-canada-text-faint">
            No accounts match your search.
          </div>
        )}
      </div>
      </PortalPage>
    </div>
  )
}
