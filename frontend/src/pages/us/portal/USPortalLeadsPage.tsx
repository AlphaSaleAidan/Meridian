import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Plus, Search, X, ChevronRight, Store, Wifi, AlertTriangle, Loader2, WifiOff,
} from 'lucide-react'
import { type Deal, type DealStage } from '@/lib/canada-sales-demo-data'
import { usLeadsService } from '@/lib/us-leads-service'
import { useSalesAuth } from '@/lib/sales-auth'
import { useToast } from '@/components/Toast'
import { queueIfOffline, setupOfflineSync, getPendingCount } from '@/lib/offline-queue'
import { requestNotificationPermission } from '@/lib/notifications'

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
  3: 'POS Connected',
  4: 'Active Deal',
}

function StepPill({ step }: { step: number }) {
  if (step <= 0) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium border border-red-500/30 text-red-400">
        Lost
      </span>
    )
  }
  if (step === 1) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium border border-[#4a5550] text-[#A1A1A8]">
        {STEP_LABELS[step]}
      </span>
    )
  }
  if (step <= 3) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#17C5B0]/15 text-[#17C5B0]">
        {STEP_LABELS[step]}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#17C5B0]/20 text-[#17C5B0] font-semibold">
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
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${
      isUrgent
        ? 'bg-red-500/10 text-red-400 border border-red-500/20'
        : 'bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20'
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
          cls += 'bg-[#17C5B0]'
        } else if (seg === currentStep) {
          cls += 'bg-[#17C5B0] animate-pulse'
        } else {
          cls += 'bg-[#1F1F23]'
        }
        return <div key={seg} className={cls} />
      })}
    </div>
  )
}

export default function USPortalLeadsPage() {
  const { rep } = useSalesAuth()
  const { toast } = useToast()
  const [searchParams] = useSearchParams()
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<'leads' | 'active'>('leads')
  const [showNew, setShowNew] = useState(searchParams.get('new') === 'true')
  const [pendingSync, setPendingSync] = useState(getPendingCount())

  const [newDeal, setNewDeal] = useState({
    business_name: '', contact_name: '', contact_email: '', contact_phone: '',
    vertical: 'Restaurant', commission_rate: '70', notes: '',
    source: 'Referral', city: '', province: '',
  })
  const [addError, setAddError] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    if (searchParams.get('new') === 'true') setShowNew(true)
  }, [searchParams])

  const [listError, setListError] = useState('')

  useEffect(() => {
    usLeadsService.list(rep?.rep_id)
      .then(d => { setDeals(d); setLoading(false) })
      .catch(err => { setListError(err?.message || 'Could not load leads.'); setLoading(false) })
    const channel = usLeadsService.subscribe(rep?.rep_id, setDeals)
    return () => { usLeadsService.unsubscribe(channel) }
  }, [rep?.rep_id])

  useEffect(() => {
    const cleanup = setupOfflineSync((count) => {
      toast(`${count} queued lead${count > 1 ? 's' : ''} synced`, 'success')
      setPendingSync(getPendingCount())
      usLeadsService.list(rep?.rep_id).then(setDeals).catch(() => {})
    })
    return cleanup
  }, [rep?.rep_id, toast])

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
    setAdding(true)
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
        setDeals(prev => [deal, ...prev])
        setPendingSync(getPendingCount())
        toast('Saved offline — will sync when back online', 'warning')
      } else {
        const saved = await usLeadsService.create(deal, rep?.rep_id)
        setDeals(prev => [saved, ...prev])
        toast('Lead added', 'success')
      }
      setShowNew(false)
      setNewDeal({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', vertical: 'Restaurant', commission_rate: '70', notes: '', source: 'Referral', city: '', province: '' })
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add lead')
      toast('Failed to save lead', 'error')
    } finally {
      setAdding(false)
    }
  }

  const inputClass = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-white placeholder-[#A1A1A8] focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors'

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#17C5B0] font-bold text-sm">S</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-white">Leads</h1>
          <p className="text-sm text-[#A1A1A8] mt-0.5">
            {leads.length} leads &middot; {activeDeals.length} active
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
        >
          <Plus size={16} /> New Lead
        </button>
      </div>

      {/* Offline sync banner */}
      {pendingSync > 0 && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#f0b429]/10 border border-[#f0b429]/20">
          <WifiOff size={14} className="text-[#f0b429]" />
          <span className="text-xs text-[#f0b429] font-medium">
            {pendingSync} lead{pendingSync > 1 ? 's' : ''} waiting to sync
          </span>
        </div>
      )}

      {/* Tab Toggle */}
      <div className="flex gap-1 p-1 bg-[#111113] border border-[#1F1F23] rounded-xl w-fit">
        <button
          onClick={() => setTab('leads')}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
            tab === 'leads' ? 'bg-[#1F1F23] text-white' : 'text-[#A1A1A8] hover:text-white'
          }`}
        >
          Leads ({leads.length})
        </button>
        <button
          onClick={() => setTab('active')}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
            tab === 'active' ? 'bg-[#17C5B0]/20 text-[#17C5B0] border border-[#17C5B0]/30' : 'text-[#A1A1A8] hover:text-white'
          }`}
        >
          Active Deals ({activeDeals.length})
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#A1A1A8]" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-11 pr-4 py-3 bg-[#111113] border border-[#1F1F23] rounded-xl text-sm text-white placeholder-[#A1A1A8] focus:outline-none focus:border-[#17C5B0]/50 transition-colors"
          placeholder="Search leads..."
        />
      </div>

      {/* New Lead Modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#111113] border border-[#1F1F23] rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-white">Add New Lead</h3>
              <button onClick={() => setShowNew(false)} className="p-1.5 rounded-lg hover:bg-[#1F1F23] transition-colors">
                <X size={18} className="text-[#A1A1A8]" />
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
                <option value="">State</option>
                {['Alabama','Alaska','Arizona','Arkansas','California','Colorado','Connecticut','Delaware','Florida','Georgia','Hawaii','Idaho','Illinois','Indiana','Iowa','Kansas','Kentucky','Louisiana','Maine','Maryland','Massachusetts','Michigan','Minnesota','Mississippi','Missouri','Montana','Nebraska','Nevada','New Hampshire','New Jersey','New Mexico','New York','North Carolina','North Dakota','Ohio','Oklahoma','Oregon','Pennsylvania','Rhode Island','South Carolina','South Dakota','Tennessee','Texas','Utah','Vermont','Virginia','Washington','West Virginia','Wisconsin','Wyoming'].map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
              <textarea value={newDeal.notes} onChange={e => setNewDeal(p => ({ ...p, notes: e.target.value }))} className={inputClass + ' sm:col-span-2 resize-none h-20'} placeholder="Notes (optional)" />
              {addError && <p className="sm:col-span-2 text-sm text-red-400">{addError}</p>}
              <div className="sm:col-span-2 flex justify-end gap-2 mt-2">
                <button type="button" onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-[#A1A1A8] hover:text-white transition-colors">Cancel</button>
                <button type="submit" disabled={adding} className="px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all disabled:opacity-50">{adding ? 'Adding...' : 'Add Lead'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Lead Cards */}
      <div className="space-y-3">
        {displayed.map(deal => {
          const step = STAGE_TO_STEP[deal.stage]
          const isConnected = step >= 4
          const daysSinceUpdate = getDaysSince(deal.updated_at)
          return (
            <Link
              key={deal.id}
              to={`/us/portal/leads/${deal.id}`}
              className="block bg-[#111113] border border-[#1F1F23] rounded-xl p-4 hover:border-[#17C5B0]/30 transition-all group"
            >
              <div className="flex items-center gap-3">
                {/* Icon */}
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#1F1F23] flex items-center justify-center">
                  {isConnected ? (
                    <Wifi size={18} className="text-[#17C5B0]" />
                  ) : (
                    <Store size={18} className="text-[#A1A1A8]" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white truncate">{deal.business_name}</span>
                    {deal.vertical && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1F1F23] text-[#A1A1A8] font-medium">
                        {deal.vertical}
                      </span>
                    )}
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#f0b429]/10 text-[#f0b429] font-medium">
                      ${deal.monthly_value.toLocaleString()}/mo
                    </span>
                    {!isConnected && <StaleBadge days={daysSinceUpdate} />}
                  </div>
                  <p className="text-xs text-[#A1A1A8] mt-0.5 truncate">
                    {deal.contact_name}
                    {daysSinceUpdate >= 3 && !isConnected && (
                      <span className="text-[#f59e0b] ml-2">Follow up needed</span>
                    )}
                  </p>
                </div>

                {/* Step pill + arrow */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StepPill step={step} />
                  <ChevronRight size={16} className="text-[#4a5550] group-hover:text-[#A1A1A8] transition-colors" />
                </div>
              </div>

              {/* Progress bar */}
              {step > 0 && <ProgressBar currentStep={step} />}
            </Link>
          )
        })}

        {listError && (
          <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center gap-3">
            <AlertTriangle size={16} className="text-red-400 flex-shrink-0" />
            <p className="text-sm text-red-400">{listError}</p>
            <button onClick={() => window.location.reload()} className="ml-auto px-3 py-1 text-xs text-white border border-red-500/30 rounded-lg hover:bg-red-500/10">Retry</button>
          </div>
        )}
        {!listError && displayed.length === 0 && (
          <div className="text-center py-16 text-sm text-[#A1A1A8]">
            No leads found. {search ? 'Try adjusting your search.' : 'Click "New Lead" to add one.'}
          </div>
        )}
      </div>
    </div>
  )
}
