import { useState, useEffect } from 'react'
import {
  Plus, Search, Mail, X, ArrowUpDown,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'
import { STAGE_CONFIG, STAGE_ORDER, type DealStage } from '@/lib/sales-demo-data'

interface CanadaDeal {
  id: string
  business_name: string
  contact_name: string
  contact_email: string
  contact_phone: string
  vertical: string
  stage: DealStage
  monthly_value: number
  commission_rate: number
  expected_close_date: string
  notes: string
  created_at: string
  updated_at: string
}

function formatCompact(value: number): string {
  return 'CA$' + value.toLocaleString('en-CA')
}

function StageBadge({ stage }: { stage: DealStage }) {
  const cfg = STAGE_CONFIG[stage]
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium"
      style={{ backgroundColor: cfg.color + '15', color: cfg.color, border: `1px solid ${cfg.color}30` }}
    >
      <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: cfg.color }} />
      {cfg.label}
    </span>
  )
}

export default function CanadaPortalLeadsPage() {
  const { rep } = useSalesAuth()
  const [deals, setDeals] = useState<CanadaDeal[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [stageFilter, setStageFilter] = useState<DealStage | 'all'>('all')
  const [showNew, setShowNew] = useState(false)
  const [sortBy, setSortBy] = useState<'date' | 'value'>('date')

  const [newDeal, setNewDeal] = useState({
    business_name: '', contact_name: '', contact_email: '', contact_phone: '',
    vertical: 'Restaurant', monthly_value: '', commission_rate: '35', notes: '',
  })

  useEffect(() => {
    async function load() {
      if (!supabase || !rep) { setLoading(false); return }
      try {
        const { data } = await supabase
          .from('deals')
          .select('*')
          .eq('country', 'CA')
          .eq('rep_id', rep.rep_id)
          .order('created_at', { ascending: false })
        if (data) setDeals(data as CanadaDeal[])
      } catch { /* empty state */ }
      setLoading(false)
    }
    load()
  }, [rep])

  const filtered = deals
    .filter(d => stageFilter === 'all' || d.stage === stageFilter)
    .filter(d => {
      if (!search) return true
      const s = search.toLowerCase()
      return d.business_name.toLowerCase().includes(s) || d.contact_name.toLowerCase().includes(s) || d.contact_email.toLowerCase().includes(s)
    })
    .sort((a, b) => sortBy === 'value' ? b.monthly_value - a.monthly_value : b.created_at.localeCompare(a.created_at))

  async function handleAddDeal(e: React.FormEvent) {
    e.preventDefault()
    const deal: CanadaDeal = {
      id: crypto.randomUUID(),
      ...newDeal,
      monthly_value: Number(newDeal.monthly_value) || 0,
      commission_rate: Number(newDeal.commission_rate) || 35,
      stage: 'prospecting',
      expected_close_date: new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10),
      created_at: new Date().toISOString().slice(0, 10),
      updated_at: new Date().toISOString().slice(0, 10),
    }
    setDeals(prev => [deal, ...prev])
    setShowNew(false)
    setNewDeal({ business_name: '', contact_name: '', contact_email: '', contact_phone: '', vertical: 'Restaurant', monthly_value: '', commission_rate: '35', notes: '' })
    if (supabase && rep) {
      try {
        await supabase.from('deals').insert({
          id: deal.id, business_name: deal.business_name, contact_name: deal.contact_name,
          contact_email: deal.contact_email, contact_phone: deal.contact_phone,
          vertical: deal.vertical, stage: deal.stage, monthly_value: deal.monthly_value,
          commission_rate: deal.commission_rate, expected_close_date: deal.expected_close_date,
          notes: deal.notes, rep_id: rep.rep_id, country: 'CA',
        })
      } catch { /* table may not exist yet */ }
    }
  }

  async function moveDeal(id: string, newStage: DealStage) {
    const now = new Date().toISOString().slice(0, 10)
    setDeals(prev => prev.map(d => d.id === id ? { ...d, stage: newStage, updated_at: now } : d))
    if (supabase) {
      try {
        await supabase.from('deals').update({ stage: newStage, updated_at: now }).eq('id', id)
      } catch { /* table may not exist yet */ }
    }
  }

  const inputClass = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors'

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
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-[#F5F5F7]">Leads</h1>
          <p className="text-sm text-[#A1A1A8] mt-0.5">
            {deals.length === 0 ? 'No leads yet — add your first Canadian lead below.' : `${filtered.length} leads in pipeline`}
          </p>
        </div>
        <button
          onClick={() => setShowNew(true)}
          className="flex items-center gap-2 px-3.5 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
        >
          <Plus size={16} /> New Lead
        </button>
      </div>

      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50"
            placeholder="Search leads..."
          />
        </div>
        <select
          value={stageFilter} onChange={e => setStageFilter(e.target.value as DealStage | 'all')}
          className="px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#A1A1A8] focus:outline-none focus:border-[#17C5B0]/50"
        >
          <option value="all">All Stages</option>
          {STAGE_ORDER.map(s => <option key={s} value={s}>{STAGE_CONFIG[s].label}</option>)}
        </select>
        <button
          onClick={() => setSortBy(sortBy === 'date' ? 'value' : 'date')}
          className="flex items-center gap-1.5 px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
        >
          <ArrowUpDown size={14} />
          {sortBy === 'date' ? 'Newest' : 'Highest Value'}
        </button>
      </div>

      {showNew && (
        <div className="card border border-[#17C5B0]/30 p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Add New Lead</h3>
            <button onClick={() => setShowNew(false)} className="p-1 rounded hover:bg-[#1F1F23] transition-colors">
              <X size={16} className="text-[#A1A1A8]" />
            </button>
          </div>
          <form onSubmit={handleAddDeal} className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <input required value={newDeal.business_name} onChange={e => setNewDeal(p => ({ ...p, business_name: e.target.value }))} className={inputClass} placeholder="Business Name *" />
            <input required value={newDeal.contact_name} onChange={e => setNewDeal(p => ({ ...p, contact_name: e.target.value }))} className={inputClass} placeholder="Contact Name *" />
            <input type="email" required value={newDeal.contact_email} onChange={e => setNewDeal(p => ({ ...p, contact_email: e.target.value }))} className={inputClass} placeholder="Contact Email *" />
            <input type="tel" value={newDeal.contact_phone} onChange={e => setNewDeal(p => ({ ...p, contact_phone: e.target.value }))} className={inputClass} placeholder="Phone" />
            <select value={newDeal.vertical} onChange={e => setNewDeal(p => ({ ...p, vertical: e.target.value }))} className={inputClass}>
              {['Restaurant', 'Smoke Shop', 'Cafe', 'Bar', 'Food Truck', 'Salon', 'Boutique', 'Convenience Store', 'Other'].map(v => (
                <option key={v} value={v}>{v}</option>
              ))}
            </select>
            <input type="number" required value={newDeal.monthly_value} onChange={e => setNewDeal(p => ({ ...p, monthly_value: e.target.value }))} className={inputClass} placeholder="Est. Monthly Revenue (CA$) *" />
            <textarea value={newDeal.notes} onChange={e => setNewDeal(p => ({ ...p, notes: e.target.value }))} className={inputClass + ' sm:col-span-2 resize-none h-20'} placeholder="Notes (optional)" />
            <div className="sm:col-span-2 flex justify-end gap-2">
              <button type="button" onClick={() => setShowNew(false)} className="px-4 py-2 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">Cancel</button>
              <button type="submit" className="px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all">Add Lead</button>
            </div>
          </form>
        </div>
      )}

      <div className="card border border-[#1F1F23] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[#1F1F23]">
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Business</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Contact</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Stage</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Value</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Vertical</th>
                <th className="px-4 py-3 text-[10px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1F1F23]">
              {filtered.map(deal => (
                <tr key={deal.id} className="hover:bg-[#111113] transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-[11px] font-medium text-[#F5F5F7]">{deal.business_name}</p>
                    <p className="text-[10px] text-[#A1A1A8]/40">{deal.notes.slice(0, 60)}{deal.notes.length > 60 ? '...' : ''}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-[11px] text-[#F5F5F7]">{deal.contact_name}</p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <Mail size={10} className="text-[#A1A1A8]/30" />
                      <span className="text-[10px] text-[#A1A1A8]/50">{deal.contact_email}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StageBadge stage={deal.stage} />
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-[11px] font-semibold text-[#F5F5F7]">{formatCompact(deal.monthly_value)} CAD/mo</p>
                    <p className="text-[10px] text-[#A1A1A8]/40">{deal.commission_rate}% rate</p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="text-[11px] text-[#A1A1A8]">{deal.vertical}</span>
                  </td>
                  <td className="px-4 py-3">
                    <select
                      value={deal.stage}
                      onChange={e => moveDeal(deal.id, e.target.value as DealStage)}
                      className="px-2 py-1 bg-[#111113] border border-[#1F1F23] rounded text-[10px] text-[#A1A1A8] focus:outline-none focus:border-[#17C5B0]/50"
                    >
                      {STAGE_ORDER.map(s => <option key={s} value={s}>{STAGE_CONFIG[s].label}</option>)}
                    </select>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-sm text-[#A1A1A8]/40">
                    {search || stageFilter !== 'all' ? 'No leads match your filters.' : 'No leads yet. Click "New Lead" to add your first Canadian prospect.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
