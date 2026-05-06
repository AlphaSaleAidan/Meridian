import { useState, useEffect } from 'react'
import { Building2, Wifi, WifiOff, Search, Plus } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { supabase } from '@/lib/supabase'

interface CanadaClient {
  id: string
  business_name: string
  contact_name: string
  contact_email: string
  vertical: string
  plan: string
  monthly_revenue: number
  commission_rate: number
  assigned_at: string
  is_active: boolean
  pos_provider: string | null
  pos_connected: boolean
}

function formatCurrency(cents: number): string {
  return 'CA$' + (cents / 100).toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function CanadaPortalAccountsPage() {
  const { rep } = useSalesAuth()
  const [clients, setClients] = useState<CanadaClient[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    async function load() {
      if (!supabase || !rep) { setLoading(false); return }
      try {
        const { data } = await supabase
          .from('clients')
          .select('*')
          .eq('country', 'CA')
          .eq('rep_id', rep.rep_id)
        if (data) setClients(data as CanadaClient[])
      } catch { /* empty state */ }
      setLoading(false)
    }
    load()
  }, [rep])

  const filtered = clients.filter(c => {
    if (!search) return true
    const s = search.toLowerCase()
    return c.business_name.toLowerCase().includes(s) || c.contact_name.toLowerCase().includes(s)
  })

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
      <div>
        <h1 className="text-xl font-bold text-[#F5F5F7]">Accounts</h1>
        <p className="text-sm text-[#A1A1A8] mt-0.5">
          {clients.length === 0
            ? 'No active accounts yet. Close deals to see them here.'
            : `${clients.length} active client${clients.length !== 1 ? 's' : ''} generating commissions`}
        </p>
      </div>

      {clients.length > 0 && (
        <div className="relative max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
          <input
            type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50"
            placeholder="Search accounts..."
          />
        </div>
      )}

      {clients.length === 0 ? (
        <div className="card border border-[#1F1F23] p-12 text-center">
          <div className="w-12 h-12 rounded-xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-4">
            <Building2 size={20} className="text-[#1A8FD6]" />
          </div>
          <h3 className="text-sm font-semibold text-[#F5F5F7] mb-1">No accounts yet</h3>
          <p className="text-[12px] text-[#A1A1A8] mb-4 max-w-sm mx-auto">
            Accounts appear here once you close deals. Start by adding leads to your Canadian pipeline.
          </p>
          <Link
            to="/canada/portal/leads"
            className="inline-flex items-center gap-2 px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
          >
            <Plus size={16} /> Go to Leads
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filtered.map(client => (
            <div key={client.id} className="card border border-[#1F1F23] p-5">
              <div className="flex items-start gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center flex-shrink-0">
                  <Building2 size={18} className="text-[#1A8FD6]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-[#F5F5F7] truncate">{client.business_name}</p>
                  <p className="text-[11px] text-[#A1A1A8]/50">{client.contact_name} &middot; {client.vertical}</p>
                </div>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  {client.pos_connected ? (
                    <>
                      <Wifi size={12} className="text-[#17C5B0]" />
                      <span className="text-[10px] text-[#17C5B0] font-medium">Connected</span>
                    </>
                  ) : (
                    <>
                      <WifiOff size={12} className="text-[#A1A1A8]/40" />
                      <span className="text-[10px] text-[#A1A1A8]/40 font-medium">Pending</span>
                    </>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <p className="text-[10px] text-[#A1A1A8]/50 mb-0.5">Monthly Revenue</p>
                  <p className="text-[11px] font-semibold text-[#F5F5F7]">{formatCurrency(client.monthly_revenue)}</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#A1A1A8]/50 mb-0.5">Commission Rate</p>
                  <p className="text-[11px] font-semibold text-[#7C5CFF]">{client.commission_rate}%</p>
                </div>
                <div>
                  <p className="text-[10px] text-[#A1A1A8]/50 mb-0.5">Plan</p>
                  <p className="text-[11px] font-semibold text-[#1A8FD6] capitalize">{client.plan}</p>
                </div>
              </div>

              <div className="mt-3 pt-3 border-t border-[#1F1F23] flex items-center justify-between">
                <span className="text-[10px] text-[#A1A1A8]/30">POS: {client.pos_provider || 'Not connected'}</span>
                <span className="text-[10px] text-[#A1A1A8]/30">Assigned {new Date(client.assigned_at).toLocaleDateString()}</span>
              </div>
            </div>
          ))}

          {filtered.length === 0 && clients.length > 0 && (
            <div className="col-span-full py-12 text-center text-sm text-[#A1A1A8]/40">
              No accounts match your search.
            </div>
          )}
        </div>
      )}
    </div>
  )
}
