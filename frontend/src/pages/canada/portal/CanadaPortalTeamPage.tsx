import { useState, useEffect } from 'react'
import { Users, DollarSign, Target, CreditCard, Search, MoreVertical } from 'lucide-react'
import { clsx } from 'clsx'
import { supabase } from '@/lib/supabase'
import { canadaSalesDemoData, type Commission } from '@/lib/canada-sales-demo-data'

interface TeamMember {
  id: string
  name: string
  email: string
  phone: string
  commission_rate: number
  deals_open: number
  deals_won: number
  total_earned: number
  total_paid: number
  is_active: boolean
  joined: string
  role: 'admin' | 'active' | 'inactive' | 'onboarding'
  location: string
}

const DEMO_TEAM: TeamMember[] = [
  { id: '1', name: 'Aidan Pierce', email: 'apierce@alphasale.co', phone: '', commission_rate: 35, deals_open: 5, deals_won: 12, total_earned: 4280000, total_paid: 3500000, is_active: true, joined: '2025-09-15', role: 'admin', location: 'Toronto, ON' },
  { id: '2', name: 'Enoch Cheung', email: 'cheungenochmgmt@gmail.com', phone: '', commission_rate: 35, deals_open: 0, deals_won: 0, total_earned: 0, total_paid: 0, is_active: true, joined: '2026-05-03', role: 'active', location: 'Vancouver, BC' },
]

const AVATAR_COLORS = ['#00d4aa', '#7c3aed', '#f59e0b', '#1a8fd6']

const CAD_RATE = 1.37

function formatCurrency(cents: number): string {
  const cad = (cents / 100) * CAD_RATE
  return 'CA$' + cad.toLocaleString('en-CA', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function getInitials(name: string): string {
  const parts = name.split(' ')
  return (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
}

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

function getRoleBadge(role: string) {
  switch (role) {
    case 'admin':
      return { text: 'Admin', bg: 'bg-[#7c3aed]/10', textColor: 'text-[#7c3aed]', border: 'border-[#7c3aed]/20' }
    case 'active':
      return { text: 'Active', bg: 'bg-[#00d4aa]/10', textColor: 'text-[#00d4aa]', border: 'border-[#00d4aa]/20' }
    case 'onboarding':
      return { text: 'Onboarding', bg: 'bg-[#f59e0b]/10', textColor: 'text-[#f59e0b]', border: 'border-[#f59e0b]/20' }
    default:
      return { text: 'Inactive', bg: 'bg-[#6b7a74]/10', textColor: 'text-[#6b7a74]', border: 'border-[#6b7a74]/20' }
  }
}

export default function CanadaPortalTeamPage() {
  const [search, setSearch] = useState('')
  const [team, setTeam] = useState<TeamMember[]>(DEMO_TEAM)
  const [commissions, setCommissions] = useState<Commission[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'reps' | 'payouts'>('reps')

  useEffect(() => {
    async function fetchData() {
      // Try supabase first
      if (supabase) {
        try {
          const { data, error } = await supabase
            .from('sales_reps')
            .select('*')
            .order('created_at', { ascending: true })

          if (data && !error && data.length > 0) {
            setTeam(data.map((r: Record<string, unknown>) => ({
              id: r.id as string,
              name: r.name as string,
              email: r.email as string,
              phone: (r.phone as string) || '',
              commission_rate: Number(r.commission_rate) || 35,
              deals_open: 0,
              deals_won: 0,
              total_earned: Math.round(Number(r.total_earned || 0) * 100),
              total_paid: Math.round(Number(r.total_paid || 0) * 100),
              is_active: r.is_active as boolean,
              joined: (r.created_at as string || '').slice(0, 10),
              role: (r.is_active ? 'active' : 'inactive') as 'active' | 'inactive',
              location: 'Toronto, ON',
            })))
          }
        } catch {
          // fall back to demo data
        }
      }

      // Load commissions from demo data
      const comms = await canadaSalesDemoData.commissions()
      setCommissions(comms)
      setLoading(false)
    }
    fetchData()
  }, [])

  const filtered = team.filter(m => {
    if (!search) return true
    const s = search.toLowerCase()
    return m.name.toLowerCase().includes(s) || m.email.toLowerCase().includes(s)
  })

  const totalActive = team.filter(m => m.is_active).length
  const totalOnboarding = team.filter(m => m.role === 'onboarding').length
  const totalDeals = team.reduce((s, m) => s + m.deals_open + m.deals_won, 0)
  const pipelineValue = team.reduce((s, m) => s + m.deals_open * 15000, 0) // estimate per deal
  const totalEarned = team.reduce((s, m) => s + m.total_earned, 0)
  const totalPaid = team.reduce((s, m) => s + m.total_paid, 0)
  const balanceOwed = totalEarned - totalPaid

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
        <h1 className="text-xl font-bold text-white">Team Management</h1>
        <p className="text-sm text-[#6b7a74] mt-0.5">Manage your sales reps, commissions, and payouts.</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#00d4aa]/10 flex items-center justify-center">
              <Users size={16} className="text-[#00d4aa]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Total Reps</p>
              <p className="text-lg font-bold text-white">{team.length}</p>
              <p className="text-[10px] text-[#4a5550]">{totalActive} active / {totalOnboarding} onboarding</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f59e0b]/10 flex items-center justify-center">
              <Target size={16} className="text-[#f59e0b]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Pipeline</p>
              <p className="text-lg font-bold text-white">{totalDeals} deals</p>
              <p className="text-[10px] text-[#4a5550]">{formatCurrency(pipelineValue)}/mo value</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <DollarSign size={16} className="text-[#7c3aed]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Total Commissions</p>
              <p className="text-lg font-bold text-white">{formatCurrency(totalEarned)}</p>
              <p className="text-[10px] text-[#4a5550]">{formatCurrency(totalPaid)} paid out</p>
            </div>
          </div>
        </div>
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f59e0b]/10 flex items-center justify-center">
              <CreditCard size={16} className="text-[#f59e0b]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#6b7a74]">Balance Owed</p>
              <p className={clsx('text-lg font-bold', balanceOwed > 0 ? 'text-[#f59e0b]' : 'text-white')}>
                {formatCurrency(balanceOwed)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-[#0f1512] border border-[#1a2420] rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab('reps')}
          className={clsx(
            'px-4 py-1.5 rounded-lg text-xs font-medium transition-colors',
            activeTab === 'reps' ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white'
          )}
        >
          Sales Reps
        </button>
        <button
          onClick={() => setActiveTab('payouts')}
          className={clsx(
            'px-4 py-1.5 rounded-lg text-xs font-medium transition-colors',
            activeTab === 'payouts' ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white'
          )}
        >
          Payouts
        </button>
      </div>

      {/* Sales Reps Tab */}
      {activeTab === 'reps' && (
        <>
          {/* Search */}
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6b7a74]/60" />
            <input
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-xl text-sm text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/50"
              placeholder="Search team members..."
            />
          </div>

          {/* Rep Cards */}
          <div className="space-y-3">
            {filtered.map(member => {
              const badge = getRoleBadge(member.role)
              const avatarColor = getAvatarColor(member.name)

              return (
                <div key={member.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4">
                  <div className="flex items-center gap-4">
                    {/* Avatar */}
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: avatarColor + '20' }}
                    >
                      <span className="text-xs font-bold" style={{ color: avatarColor }}>
                        {getInitials(member.name)}
                      </span>
                    </div>

                    {/* Name + Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white truncate">{member.name}</p>
                        <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border', badge.bg, badge.textColor, badge.border)}>
                          {badge.text}
                        </span>
                      </div>
                      <p className="text-xs text-[#6b7a74] mt-0.5">{member.email}</p>
                      <p className="text-[10px] text-[#4a5550]">{member.location}</p>
                    </div>

                    {/* Commission Rate */}
                    <div className="hidden sm:block">
                      <span className="text-sm font-bold text-[#7c3aed]">{member.commission_rate}%</span>
                    </div>

                    {/* More Menu */}
                    <button className="p-1.5 rounded-lg hover:bg-[#1a2420] text-[#6b7a74] transition-colors">
                      <MoreVertical size={14} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Payouts Tab */}
      {activeTab === 'payouts' && (
        <div className="space-y-6">
          {/* Rep Balances */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Rep Balances</h3>
            <div className="space-y-3">
              {team.map(member => {
                const owed = member.total_earned - member.total_paid
                const avatarColor = getAvatarColor(member.name)

                return (
                  <div key={member.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      {/* Avatar */}
                      <div
                        className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                        style={{ backgroundColor: avatarColor + '20' }}
                      >
                        <span className="text-xs font-bold" style={{ color: avatarColor }}>
                          {getInitials(member.name)}
                        </span>
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{member.name}</p>
                        <p className="text-[10px] text-[#6b7a74]">
                          {member.deals_won} deals &middot; {member.commission_rate}% rate &middot; {formatCurrency(member.total_earned)} earned
                        </p>
                      </div>

                      {/* Status */}
                      {owed <= 0 ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20">
                          Paid up &#10003;
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20">
                          {formatCurrency(owed)} owed
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Commission Log */}
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Commission Log</h3>
            <div className="space-y-2">
              {commissions.map(comm => {
                const statusBadge = (() => {
                  switch (comm.status) {
                    case 'paid':
                      return { text: 'paid', bg: 'bg-[#00d4aa]/10', textColor: 'text-[#00d4aa]', border: 'border-[#00d4aa]/20' }
                    case 'earned':
                      return { text: 'earned', bg: 'bg-[#7c3aed]/10', textColor: 'text-[#7c3aed]', border: 'border-[#7c3aed]/20' }
                    case 'pending':
                      return { text: 'pending', bg: 'bg-[#f59e0b]/10', textColor: 'text-[#f59e0b]', border: 'border-[#f59e0b]/20' }
                    default:
                      return { text: comm.status, bg: 'bg-[#6b7a74]/10', textColor: 'text-[#6b7a74]', border: 'border-[#6b7a74]/20' }
                  }
                })()

                return (
                  <div key={comm.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-[#7c3aed]/10 flex items-center justify-center flex-shrink-0">
                        <DollarSign size={12} className="text-[#7c3aed]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-white">{formatCurrency(comm.commission_amount)}</p>
                        <p className="text-[10px] text-[#6b7a74]">
                          Aidan Pierce &middot; {comm.client_name} &middot; {comm.commission_rate}%
                        </p>
                      </div>
                      <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border', statusBadge.bg, statusBadge.textColor, statusBadge.border)}>
                        {statusBadge.text}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
