import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  Plus, Search, X, ChevronRight, Store, Wifi,
} from 'lucide-react'
import { type Deal, type DealStage } from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'

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
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium border border-[#4a5550] text-[#6b7a74]">
        {STEP_LABELS[step]}
      </span>
    )
  }
  if (step <= 3) {
    return (
      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#00d4aa]/15 text-[#00d4aa]">
        {STEP_LABELS[step]}
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[11px] font-medium bg-[#00d4aa]/20 text-[#00d4aa] font-semibold">
      {STEP_LABELS[step]}
    </span>
  )
}

function ProgressBar({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex gap-1 mt-3">
      {[1, 2, 3, 4].map(seg => {
        let cls = 'h-1 flex-1 rounded-full '
        if (seg < currentStep) {
          cls += 'bg-[#00d4aa]'
        } else if (seg === currentStep) {
          cls += 'bg-[#00d4aa] animate-pulse'
        } else {
          cls += 'bg-[#1a2420]'
        }
        return <div key={seg} className={cls} />
      })}
    </div>
  )
}

export default function CanadaPortalLeadsPage() {
  const [searchParams] = useSearchParams()
  const [deals, setDeals] = useState<Deal[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState<'leads' | 'active'>('leads')
  const [showNew, setShowNew] = useState(searchParams.get('new') === 'true')

  const [newDeal, setNewDeal] = useState({
    business_name: '', contact_name: '', contact_email: '', contact_phone: '',
    vertical: 'Restaurant', commission_rate: '70', notes: '',
    source: 'Referral', city: '', province: '', pos_system: '',
  })
  const [addError, setAddError] = useState('')
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    if (searchParams.get('new') === 'true') setShowNew(true)
  }, [searchParams])

  useEffect(() => {
    canadaLeadsService.list().then(d => { setDeals(d); setLoading(false) })
  }, [])

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
      const saved = await canadaLeadsService.create(deal)
      setDeals(prev => [saved, ...prev])
      setShowNew(false)
      setNewDeal({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', vertical: 'Restaurant', commission_rate: '70', notes: '', source: 'Referral', city: '', province: '', pos_system: '' })
    } catch (err) {
      setAddError(err instanceof Error ? err.message : 'Failed to add lead')
    } finally {
      setAdding(false)
    }
  }

  const inputClass = 'w-full px-3 py-2 bg-[#0f1512] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#00d4aa]/15 border border-[#00d4aa]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#00d4aa] font-bold text-sm">S</span>
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
          <p className="text-sm text-[#6b7a74] mt-0.5">
            {leads.length} leads &middot; {activeDeals.length} active
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
        >
          <Plus size={16} /> New Lead
        </button>
      </div>

      {/* Tab Toggle */}
      <div className="flex gap-1 p-1 bg-[#0f1512] border border-[#1a2420] rounded-xl w-fit">
        <button
          onClick={() => setTab('leads')}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
            tab === 'leads' ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white'
          }`}
        >
          Leads ({leads.length})
        </button>
        <button
          onClick={() => setTab('active')}
          className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${
            tab === 'active' ? 'bg-[#00d4aa]/20 text-[#00d4aa] border border-[#00d4aa]/30' : 'text-[#6b7a74] hover:text-white'
          }`}
        >
          Active Deals ({activeDeals.length})
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#6b7a74]" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-11 pr-4 py-3 bg-[#0f1512] border border-[#1a2420] rounded-xl text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 transition-colors"
          placeholder="Search leads..."
        />
      </div>

      {/* New Lead Modal */}
      {showNew && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-lg bg-[#0f1512] border border-[#1a2420] rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-white">Add New Lead</h3>
              <button onClick={() => setShowNew(false)} className="p-1.5 rounded-lg hover:bg-[#1a2420] transition-colors">
                <X size={18} className="text-[#6b7a74]" />
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
                <button type="button" onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-[#6b7a74] hover:text-white transition-colors">Cancel</button>
                <button type="submit" disabled={adding} className="px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all disabled:opacity-50">{adding ? 'Adding...' : 'Add Lead'}</button>
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
          return (
            <Link
              key={deal.id}
              to={`/canada/portal/leads/${deal.id}`}
              className="block bg-[#0f1512] border border-[#1a2420] rounded-xl p-4 hover:border-[#00d4aa]/30 transition-all group"
            >
              <div className="flex items-center gap-3">
                {/* Icon */}
                <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[#1a2420] flex items-center justify-center">
                  {isConnected ? (
                    <Wifi size={18} className="text-[#00d4aa]" />
                  ) : (
                    <Store size={18} className="text-[#6b7a74]" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-white truncate">{deal.business_name}</span>
                    {deal.vertical && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-[#1a2420] text-[#6b7a74] font-medium">
                        {deal.vertical}
                      </span>
                    )}
                    <span className="text-[11px] px-2 py-0.5 rounded-full bg-[#f0b429]/10 text-[#f0b429] font-medium">
                      CA${deal.monthly_value.toLocaleString()}/mo
                    </span>
                  </div>
                  <p className="text-xs text-[#6b7a74] mt-0.5 truncate">{deal.contact_name}</p>
                </div>

                {/* Step pill + arrow */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <StepPill step={step} />
                  <ChevronRight size={16} className="text-[#4a5550] group-hover:text-[#6b7a74] transition-colors" />
                </div>
              </div>

              {/* Progress bar */}
              {step > 0 && <ProgressBar currentStep={step} />}
            </Link>
          )
        })}

        {displayed.length === 0 && (
          <div className="text-center py-16 text-sm text-[#6b7a74]">
            No leads found. {search ? 'Try adjusting your search.' : 'Click "New Lead" to add one.'}
          </div>
        )}
      </div>
    </div>
  )
}
