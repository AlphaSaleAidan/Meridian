import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import {
  Plus, Search, X, ChevronRight, Store, Wifi, AlertTriangle, WifiOff, Trash2, Loader2,
} from 'lucide-react'
import { type Deal } from '@/lib/canada-sales-demo-data'
import {
  useCanadaLeads,
  useCanadaLeadsRealtime,
  useCreateCanadaLead,
  useDeleteCanadaLead,
  canadaKeys,
} from '@/lib/canada-queries'
import { useSalesAuth } from '@/lib/sales-auth'
import { useToast } from '@/components/Toast'
import { queueIfOffline, setupOfflineSync, getPendingCount } from '@/lib/offline-queue'
import { requestNotificationPermission } from '@/lib/notifications'
import { PortalPage } from './PortalPage'

const STAGE_TO_STEP: Record<string, number> = {
  proposal_shown: 1,
  customer_checkout: 2,
  pos_connected: 3,
  customer_walkthrough: 4,
  closed_lost: 0,
  // Legacy
  appointment_set: 1,
  prospecting: 1,
  contacted: 1,
  demo_scheduled: 1,
  proposal_sent: 1,
  negotiation: 2,
  closed_won: 4,
}

const STEP_LABELS: Record<number, string> = {
  1: 'Proposal Shown',
  2: 'Customer Checkout',
  3: 'Active Deal',
  4: 'Active Deal',
}

function StepPill({ step }: { step: number }) {
  if (step <= 0) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium border border-red-500/30 text-red-400">
        Lost
      </span>
    )
  }
  if (step === 1) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium border border-pm-canada-text-faint text-pm-canada-text-muted">
        {STEP_LABELS[step]}
      </span>
    )
  }
  if (step <= 3) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium bg-pm-accent/15 text-pm-accent">
        {STEP_LABELS[step]}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium bg-pm-accent/20 text-pm-accent font-semibold">
      {STEP_LABELS[step]}
    </span>
  )
}

function getDaysSince(dateStr: string): number {
  const d = new Date(dateStr)
  const now = new Date()
  return Math.floor((now.getTime() - d.getTime()) / 86400000)
}

function StaleBadge({ days }: { days: number }) {
  if (days < 3) return null
  const isUrgent = days >= 7
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-medium ${
      isUrgent
        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
        : 'bg-pm-amber-orange/10 text-pm-amber-orange border border-pm-amber-orange/20'
    }`}>
      <AlertTriangle size={10} /> {days}d ago
    </span>
  )
}

function ProgressBar({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex gap-1 mt-3">
      {[1, 2, 3, 4].map(seg => {
        let cls = 'h-1 flex-1 rounded-full '
        if (seg < currentStep) {
          cls += 'bg-pm-accent'
        } else if (seg === currentStep) {
          cls += 'bg-pm-accent animate-pulse'
        } else {
          cls += 'bg-pm-canada-border'
        }
        return <div key={seg} className={cls} />
      })}
    </div>
  )
}

export default function CanadaPortalLeadsPage() {
  const { rep } = useSalesAuth()
  const { toast } = useToast()
  const [searchParams] = useSearchParams()
  const qc = useQueryClient()
  const { data: deals = [], isLoading, error } = useCanadaLeads(rep?.rep_id)
  useCanadaLeadsRealtime(rep?.rep_id)
  const createLead = useCreateCanadaLead(rep?.rep_id)
  const deleteLead = useDeleteCanadaLead()
  const [confirmDelete, setConfirmDelete] = useState<Deal | null>(null)
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<'leads' | 'active'>('leads')
  const [showNew, setShowNew] = useState(searchParams.get('new') === 'true')
  const [pendingSync, setPendingSync] = useState(getPendingCount())

  const [newDeal, setNewDeal] = useState({
    business_name: '', contact_name: '', contact_email: '', contact_phone: '',
    vertical: 'Restaurant', commission_rate: '70', notes: '',
    source: 'Referral', city: '', province: '', pos_system: '',
  })
  const [addError, setAddError] = useState('')

  useEffect(() => {
    if (searchParams.get('new') === 'true') setShowNew(true)
  }, [searchParams])

  useEffect(() => {
    const cleanup = setupOfflineSync((count) => {
      toast(`${count} queued lead${count > 1 ? 's' : ''} synced`, 'success')
      setPendingSync(getPendingCount())
      // Offline queue just flushed pending mutations through the service —
      // re-fetch via React Query so every page sees the result.
      qc.invalidateQueries({ queryKey: canadaKeys.leadsRoot() })
    })
    return cleanup
  }, [qc, toast])

  useEffect(() => { requestNotificationPermission() }, [])

  const leads = deals.filter(d => d.stage !== 'customer_walkthrough' && d.stage !== 'closed_won' && d.stage !== 'pos_connected' && d.stage !== 'closed_lost')
  const activeDeals = deals.filter(d => d.stage === 'customer_walkthrough' || d.stage === 'closed_won' || d.stage === 'pos_connected')

  const displayed = (tab === 'leads' ? leads : activeDeals)
    .filter(d => {
      if (!search) return true
      const s = search.toLowerCase()
      return d.business_name.toLowerCase().includes(s) || d.contact_name.toLowerCase().includes(s) || d.contact_email.toLowerCase().includes(s)
    })

  async function handleAddDeal(e: React.FormEvent) {
    e.preventDefault()
    setAddError('')
    try {
      const deal: Deal = {
        id: 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => { const r = Math.random() * 16 | 0; return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16) }),
        ...newDeal,
        monthly_value: 0,
        commission_rate: Number(newDeal.commission_rate) || 70,
        stage: 'proposal_shown',
        expected_close_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
        created_at: new Date().toISOString().slice(0, 10),
        updated_at: new Date().toISOString().slice(0, 10),
      }
      const queued = queueIfOffline('create', { deal, repId: rep?.rep_id })
      if (queued) {
        // Optimistically prepend to the leads cache; the offline queue's
        // setupOfflineSync handler above invalidates once the network returns.
        qc.setQueryData<Deal[]>(canadaKeys.leads(rep?.rep_id), (prev = []) => [deal, ...prev])
        setPendingSync(getPendingCount())
        toast('Saved offline — will sync when back online', 'warning')
      } else {
        await createLead.mutateAsync(deal)
        toast('Lead added', 'success')
      }
      setShowNew(false)
      setNewDeal({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', vertical: 'Restaurant', commission_rate: '70', notes: '', source: 'Referral', city: '', province: '', pos_system: '' })
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add lead')
      toast('Failed to save lead', 'error')
    }
  }
  const adding = createLead.isPending

  async function handleDeleteLead() {
    if (!confirmDelete) return
    try {
      await deleteLead.mutateAsync(confirmDelete.id)
      toast('Lead deleted', 'success')
      setConfirmDelete(null)
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Failed to delete lead', 'error')
    }
  }

  const inputClass = 'w-full px-3 py-2 bg-pm-canada-surface border border-pm-canada-border rounded-lg text-sm text-white placeholder-pm-canada-text-muted focus:outline-none focus:border-pm-accent/50 focus:ring-1 focus:ring-pm-accent/20 transition-colors'

  const emptyState = (
    <div className="text-center py-16 text-sm text-pm-canada-text-muted">
      No leads found. {search ? 'Try adjusting your search.' : 'Click "New Lead" to add one.'}
    </div>
  )

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">Leads</h1>
          <p className="text-sm text-pm-canada-text-muted mt-0.5">
            {leads.length} leads &middot; {activeDeals.length} active
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 transition-all"
        >
          <Plus size={16} /> New Lead
        </button>
      </div>

      {/* Offline sync banner */}
      {pendingSync > 0 && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-pm-amber-gold/10 border border-pm-amber-gold/20">
          <WifiOff size={14} className="text-pm-amber-gold" />
          <span className="text-xs text-pm-amber-gold font-medium">
            {pendingSync} lead{pendingSync > 1 ? 's' : ''} waiting to sync
          </span>
        </div>
      )}

      {/* Tab Toggle */}
      <div className="flex gap-1 p-1 bg-pm-canada-surface border border-pm-canada-border rounded-xl w-fit">
        <button
          onClick={() => setTab('leads')}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
            tab === 'leads' ? 'bg-pm-canada-border text-white' : 'text-pm-canada-text-muted hover:text-white'
          }`}
        >
          Leads ({leads.length})
        </button>
        <button
          onClick={() => setTab('active')}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
            tab === 'active' ? 'bg-pm-accent/20 text-pm-accent border border-pm-accent/30' : 'text-pm-canada-text-muted hover:text-white'
          }`}
        >
          Active Deals ({activeDeals.length})
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-pm-canada-text-muted" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-11 pr-4 py-3 bg-pm-canada-surface border border-pm-canada-border rounded-xl text-sm text-white placeholder-pm-canada-text-muted focus:outline-none focus:border-pm-accent/50 transition-colors"
          placeholder="Search leads..."
        />
      </div>

      {/* New Lead Modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-white">Add New Lead</h3>
              <button onClick={() => setShowNew(false)} className="p-1.5 rounded-lg hover:bg-pm-canada-border transition-colors">
                <X size={18} className="text-pm-canada-text-muted" />
              </button>
            </div>
            <form onSubmit={handleAddDeal} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input required value={newDeal.business_name} onChange={e => setNewDeal(p => ({ ...p, business_name: e.target.value }))} className={inputClass} placeholder="Business Name *" />
              <input required value={newDeal.contact_name} onChange={e => setNewDeal(p => ({ ...p, contact_name: e.target.value }))} className={inputClass} placeholder="Contact Name *" />
              <input type="email" value={newDeal.contact_email} onChange={e => setNewDeal(p => ({ ...p, contact_email: e.target.value }))} className={inputClass} placeholder="Contact Email" />
              <input type="tel" value={newDeal.contact_phone} onChange={e => setNewDeal(p => ({ ...p, contact_phone: e.target.value }))} className={inputClass} placeholder="Phone" />
              <select value={newDeal.vertical} onChange={e => setNewDeal(p => ({ ...p, vertical: e.target.value }))} className={inputClass}>
                {['Restaurant', 'Smoke Shop', 'Cafe', 'Bar', 'Food Truck', 'Salon', 'Boutique', 'Convenience Store', 'Other'].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
              <select value={newDeal.source} onChange={e => setNewDeal(p => ({ ...p, source: e.target.value }))} className={inputClass}>
                {['Referral', 'Cold Call', 'Walk-in', 'Social Media', 'Website', 'Trade Show', 'Partner', 'Other'].map(v => (
                  <option key={v} value={v}>{v}</option>
                ))}
              </select>
              <input value={newDeal.city} onChange={e => setNewDeal(p => ({ ...p, city: e.target.value }))} className={inputClass} placeholder="City" />
              <select value={newDeal.province} onChange={e => setNewDeal(p => ({ ...p, province: e.target.value }))} className={inputClass}>
                <option value="">Province / Territory</option>
                {['Alberta','British Columbia','Manitoba','New Brunswick','Newfoundland and Labrador','Northwest Territories','Nova Scotia','Nunavut','Ontario','Prince Edward Island','Quebec','Saskatchewan','Yukon'].map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <select required value={newDeal.pos_system} onChange={e => setNewDeal(p => ({ ...p, pos_system: e.target.value }))} className={inputClass}>
                <option value="">Current POS System *</option>
                {['Square', 'Clover', 'Toast', 'Moneris', 'Lightspeed', 'Shopify POS', 'TouchBistro', 'Revel', 'Heartland', 'Aloha', 'NCR Silver', 'SpotOn', 'Helcim', 'Dejavoo', 'Poynt', 'Payanywhere', 'SumUp', 'iZettle', 'Vend', 'Hike POS', 'Epos Now', 'Lavu', 'Upserve', 'Talech', 'PayPal Zettle', 'Stripe Terminal', 'None / Paper', 'Other'].map(v => (
                  <option key={v} value={v.toLowerCase()}>{v}</option>
                ))}
              </select>
              <textarea value={newDeal.notes} onChange={e => setNewDeal(p => ({ ...p, notes: e.target.value }))} className={inputClass + ' sm:col-span-2 resize-none h-20'} placeholder="Notes (optional)" />
              {addError && <p className="sm:col-span-2 text-sm text-red-400">{addError}</p>}
              <div className="sm:col-span-2 flex justify-end gap-2 mt-2">
                <button type="button" onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-pm-canada-text-muted hover:text-white transition-colors">Cancel</button>
                <button type="submit" disabled={adding} className="px-4 py-2 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 transition-all disabled:opacity-50">{adding ? 'Adding...' : 'Add Lead'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-white">Delete lead?</h3>
              <button onClick={() => setConfirmDelete(null)} className="p-1.5 rounded-lg hover:bg-pm-canada-border transition-colors">
                <X size={18} className="text-pm-canada-text-muted" />
              </button>
            </div>
            <p className="text-sm text-pm-canada-text-muted mb-5">
              This permanently removes &ldquo;{confirmDelete.business_name}&rdquo; and can&rsquo;t be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setConfirmDelete(null)}
                className="px-4 py-2 text-sm text-pm-canada-text-muted hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteLead}
                disabled={deleteLead.isPending}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/90 text-white text-sm font-semibold rounded-lg hover:bg-red-500 transition-all disabled:opacity-50"
              >
                {deleteLead.isPending && <Loader2 size={14} className="animate-spin" />}
                {deleteLead.isPending ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Lead Cards */}
      <PortalPage isLoading={isLoading} error={error} isEmpty={deals.length === 0} emptyState={emptyState}>
      <div className="space-y-3">
        {displayed.map(deal => {
          const step = STAGE_TO_STEP[deal.stage]
          const isConnected = step >= 4
          const daysSinceUpdate = getDaysSince(deal.updated_at)
          return (
            <Link
              key={deal.id}
              to={`/canada/portal/leads/${deal.id}`}
              data-testid={`lead-card-${deal.id}`}
              className="block bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4 hover:border-pm-accent/30 transition-all group"
            >
              <div className="flex items-center gap-3">
                {/* Icon */}
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-pm-canada-border flex items-center justify-center">
                  {isConnected ? (
                    <Wifi size={18} className="text-pm-accent" />
                  ) : (
                    <Store size={18} className="text-pm-canada-text-muted" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white truncate">{deal.business_name}</span>
                    {deal.vertical && (
                      <span className="text-2xs px-1.5 py-0.5 rounded bg-pm-canada-border text-pm-canada-text-muted font-medium">
                        {deal.vertical}
                      </span>
                    )}
                    <span className="text-2xs px-2 py-0.5 rounded-full bg-pm-amber-gold/10 text-pm-amber-gold font-medium">
                      CA${deal.monthly_value.toLocaleString()}/mo
                    </span>
                    {!isConnected && <StaleBadge days={daysSinceUpdate} />}
                  </div>
                  <p className="text-xs text-pm-canada-text-muted mt-0.5 truncate">
                    {deal.contact_name}
                    {daysSinceUpdate >= 3 && !isConnected && (
                      <span className="text-pm-amber-orange ml-2">Follow up needed</span>
                    )}
                  </p>
                </div>

                {/* Step pill + delete + arrow */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <span data-testid="lead-stage-badge"><StepPill step={step} /></span>
                  <button
                    type="button"
                    aria-label="Delete lead"
                    data-testid={`delete-lead-${deal.id}`}
                    onClick={(e) => {
                      e.preventDefault()
                      e.stopPropagation()
                      setConfirmDelete(deal)
                    }}
                    className="p-1.5 rounded-lg text-pm-canada-text-faint hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 size={15} />
                  </button>
                  <ChevronRight size={16} className="text-pm-canada-text-faint group-hover:text-pm-canada-text-muted transition-colors" />
                </div>
              </div>

              {/* Progress bar */}
              {step > 0 && <ProgressBar currentStep={step} />}
            </Link>
          )
        })}

        {/* Search/tab miss — rep has leads in the system, but the current
            tab + search returns nothing. The "no leads at all" case is
            handled by PortalPage's emptyState. */}
        {deals.length > 0 && displayed.length === 0 && (
          <div className="py-12 text-center text-sm text-pm-canada-text-faint">
            No leads match your filter.
          </div>
        )}
      </div>
      </PortalPage>
    </div>
  )
}
