import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Building2, Users, ShieldCheck, Plus, Copy, Check,
  Wifi, WifiOff, Clock, RefreshCw, Search, ExternalLink,
} from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

interface Business {
  id: string
  name: string
  owner_name: string
  email: string
  business_type: string
  plan_tier: string
  status: string
  pos_provider: string | null
  pos_connected: boolean
  onboarded: boolean
  created_at: string
  activated_at: string | null
}

type Tab = 'businesses' | 'provision'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout>>()
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        clearTimeout(timer.current)
        timer.current = setTimeout(() => setCopied(false), 2000)
      }}
      className="p-1 rounded hover:bg-[#1F1F23] transition-colors"
    >
      {copied ? <Check size={12} className="text-[#17C5B0]" /> : <Copy size={12} className="text-[#A1A1A8]/40" />}
    </button>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    active: 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/20',
    pending: 'bg-amber-400/10 text-amber-400 border-amber-400/20',
    suspended: 'bg-red-500/10 text-red-400 border-red-500/20',
    churned: 'bg-[#A1A1A8]/10 text-[#A1A1A8] border-[#A1A1A8]/20',
  }
  return (
    <span className={clsx('text-[10px] font-medium px-1.5 py-0.5 rounded-full border', styles[status] || styles.pending)}>
      {status}
    </span>
  )
}

export default function AdminPage() {
  const navigate = useNavigate()
  const { isAdmin, authenticated, ready } = useAuth()
  const [tab, setTab] = useState<Tab>('businesses')
  const [businesses, setBusinesses] = useState<Business[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  const [provName, setProvName] = useState('')
  const [provOwner, setProvOwner] = useState('')
  const [provEmail, setProvEmail] = useState('')
  const [provType, setProvType] = useState('coffee_shop')
  const [provPlan, setProvPlan] = useState('trial')
  const [provLoading, setProvLoading] = useState(false)
  const [provResult, setProvResult] = useState<{ token: string; activation_url: string; business_id: string } | null>(null)
  const [provError, setProvError] = useState<string | null>(null)

  const [genTokenBizId, setGenTokenBizId] = useState<string | null>(null)
  const [genTokenResult, setGenTokenResult] = useState<{ token: string; activation_url: string } | null>(null)

  const fetchBusinesses = useCallback(async () => {
    if (!supabase) return
    setLoading(true)
    const { data, error } = await supabase.rpc('admin_list_businesses')
    if (!error && data) setBusinesses(data)
    setLoading(false)
  }, [])

  useEffect(() => {
    if (ready && !authenticated) { navigate('/portal', { replace: true }); return }
    if (ready && !isAdmin) { navigate('/app', { replace: true }); return }
    if (ready && isAdmin) fetchBusinesses()
  }, [ready, authenticated, isAdmin, navigate, fetchBusinesses])

  async function handleProvision(e: React.FormEvent) {
    e.preventDefault()
    setProvError(null)
    setProvResult(null)
    if (!supabase) return
    setProvLoading(true)
    const { data, error } = await supabase.rpc('provision_business', {
      biz_name: provName,
      biz_owner_name: provOwner,
      biz_email: provEmail,
      biz_type: provType,
      biz_plan: provPlan,
    })
    setProvLoading(false)
    if (error) { setProvError(error.message); return }
    setProvResult(data)
    setProvName('')
    setProvOwner('')
    setProvEmail('')
    fetchBusinesses()
  }

  async function handleGenerateToken(bizId: string) {
    if (!supabase) return
    setGenTokenBizId(bizId)
    setGenTokenResult(null)
    const { data, error } = await supabase.rpc('admin_generate_token', { biz_id: bizId })
    if (!error && data) setGenTokenResult(data)
  }

  if (!ready) return null

  const filtered = businesses.filter(b =>
    b.name.toLowerCase().includes(search.toLowerCase()) ||
    b.email.toLowerCase().includes(search.toLowerCase()) ||
    b.owner_name.toLowerCase().includes(search.toLowerCase())
  )

  const active = businesses.filter(b => b.status === 'active').length
  const connected = businesses.filter(b => b.pos_connected).length
  const pending = businesses.filter(b => b.status === 'pending').length

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors'

  return (
    <div className="min-h-screen bg-[#0A0A0B]">
      <header className="h-14 flex items-center gap-3 px-6 border-b border-[#1F1F23] bg-[#0A0A0B]">
        <MeridianEmblem size={24} />
        <MeridianWordmark className="text-sm" />
        <span className="text-[10px] font-medium text-[#7C5CFF] bg-[#7C5CFF]/10 border border-[#7C5CFF]/20 px-1.5 py-0.5 rounded ml-1">ADMIN</span>
        <div className="flex-1" />
        <button onClick={() => navigate('/app')} className="text-[11px] text-[#A1A1A8] hover:text-[#1A8FD6] transition-colors flex items-center gap-1">
          <ExternalLink size={10} /> Dashboard
        </button>
      </header>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Total Businesses', value: businesses.length, icon: Building2, color: '#1A8FD6' },
            { label: 'Active', value: active, icon: ShieldCheck, color: '#17C5B0' },
            { label: 'POS Connected', value: connected, icon: Wifi, color: '#7C5CFF' },
            { label: 'Pending', value: pending, icon: Clock, color: '#FBBF24' },
          ].map(s => (
            <div key={s.label} className="card p-4">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${s.color}15` }}>
                  <s.icon size={16} style={{ color: s.color }} />
                </div>
                <div>
                  <p className="text-[10px] text-[#A1A1A8]/60 font-medium">{s.label}</p>
                  <p className="text-lg font-bold text-[#F5F5F7] font-mono">{s.value}</p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Tabs */}
        <div className="flex items-center gap-2 border-b border-[#1F1F23] pb-2">
          {([
            { id: 'businesses' as const, label: 'Businesses', icon: Users },
            { id: 'provision' as const, label: 'Provision New', icon: Plus },
          ]).map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={clsx(
                'flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all',
                tab === t.id ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]'
              )}
            >
              <t.icon size={14} /> {t.label}
            </button>
          ))}
          <div className="flex-1" />
          <button onClick={fetchBusinesses} className="p-1.5 text-[#A1A1A8]/40 hover:text-[#1A8FD6] transition-colors">
            <RefreshCw size={14} />
          </button>
        </div>

        {/* Businesses Tab */}
        {tab === 'businesses' && (
          <div className="space-y-3">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/40" />
              <input
                type="text" value={search} onChange={e => setSearch(e.target.value)}
                placeholder="Search businesses..."
                className="w-full pl-9 pr-3 py-2 text-xs bg-[#111113] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/30"
              />
            </div>

            {loading ? (
              <div className="text-center py-12 text-[#A1A1A8]/40 text-sm">Loading...</div>
            ) : filtered.length === 0 ? (
              <div className="text-center py-12">
                <Building2 size={32} className="text-[#A1A1A8]/20 mx-auto mb-2" />
                <p className="text-sm text-[#A1A1A8]/40">No businesses found</p>
              </div>
            ) : (
              <div className="space-y-2">
                {filtered.map(biz => (
                  <div key={biz.id} className="card p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm font-semibold text-[#F5F5F7] truncate">{biz.name}</h4>
                          <StatusBadge status={biz.status} />
                          {biz.pos_connected ? (
                            <span className="text-[9px] text-[#17C5B0] flex items-center gap-0.5"><Wifi size={8} /> POS</span>
                          ) : (
                            <span className="text-[9px] text-[#A1A1A8]/30 flex items-center gap-0.5"><WifiOff size={8} /> No POS</span>
                          )}
                        </div>
                        <p className="text-[11px] text-[#A1A1A8]">{biz.owner_name} &middot; {biz.email}</p>
                        <div className="flex flex-wrap items-center gap-3 mt-2 text-[10px] text-[#A1A1A8]/40">
                          <span>{biz.business_type}</span>
                          <span>{biz.plan_tier}</span>
                          <span className="font-mono">{biz.id}</span>
                          <span>{new Date(biz.created_at).toLocaleDateString()}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => handleGenerateToken(biz.id)}
                        className="text-[10px] text-[#A1A1A8]/50 hover:text-[#1A8FD6] border border-[#1F1F23] hover:border-[#1A8FD6]/20 rounded-lg px-2 py-1 transition-colors flex-shrink-0"
                      >
                        New Token
                      </button>
                    </div>
                    {genTokenBizId === biz.id && genTokenResult && (
                      <div className="mt-3 p-3 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/10 space-y-1">
                        <div className="flex items-center gap-2">
                          <p className="text-[10px] text-[#A1A1A8]">Activation URL:</p>
                          <CopyButton text={genTokenResult.activation_url} />
                        </div>
                        <p className="text-xs font-mono text-[#17C5B0] break-all">{genTokenResult.activation_url}</p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Provision Tab */}
        {tab === 'provision' && (
          <div className="card p-5 sm:p-6 max-w-md">
            <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Provision New Business</h3>

            {provResult && (
              <div className="mb-4 p-4 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/10 space-y-2">
                <p className="text-xs font-semibold text-[#17C5B0]">Business provisioned successfully</p>
                <div>
                  <p className="text-[10px] text-[#A1A1A8]">Activation URL:</p>
                  <div className="flex items-center gap-1 mt-1">
                    <p className="text-xs font-mono text-[#F5F5F7] break-all">{provResult.activation_url}</p>
                    <CopyButton text={provResult.activation_url} />
                  </div>
                </div>
                <div>
                  <p className="text-[10px] text-[#A1A1A8]">Token:</p>
                  <div className="flex items-center gap-1 mt-1">
                    <p className="text-xs font-mono text-[#F5F5F7]">{provResult.token}</p>
                    <CopyButton text={provResult.token} />
                  </div>
                </div>
              </div>
            )}

            {provError && (
              <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{provError}</div>
            )}

            <form onSubmit={handleProvision} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1">Business Name</label>
                <input type="text" required value={provName} onChange={e => setProvName(e.target.value)} className={inputClass} placeholder="The Daily Grind" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1">Owner Name</label>
                <input type="text" required value={provOwner} onChange={e => setProvOwner(e.target.value)} className={inputClass} placeholder="Jane Doe" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1">Email</label>
                <input type="email" required value={provEmail} onChange={e => setProvEmail(e.target.value)} className={inputClass} placeholder="jane@business.com" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-medium text-[#A1A1A8] mb-1">Business Type</label>
                  <select value={provType} onChange={e => setProvType(e.target.value)} className={inputClass}>
                    <option value="coffee_shop">Coffee Shop</option>
                    <option value="restaurant">Restaurant</option>
                    <option value="fast_casual">Fast Casual</option>
                    <option value="bakery">Bakery</option>
                    <option value="retail">Retail</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#A1A1A8] mb-1">Plan</label>
                  <select value={provPlan} onChange={e => setProvPlan(e.target.value)} className={inputClass}>
                    <option value="trial">Trial</option>
                    <option value="starter">Starter</option>
                    <option value="growth">Growth</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
              </div>
              <button type="submit" disabled={provLoading} className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all">
                {provLoading ? 'Provisioning...' : 'Create Business & Generate Token'}
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  )
}
