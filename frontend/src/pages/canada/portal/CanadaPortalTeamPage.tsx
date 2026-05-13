import { useState, useEffect } from 'react'
import { Users, DollarSign, Target, CreditCard, Search, MoreVertical, X, Save, UserPlus, Clock, CheckCircle2, XCircle, Trophy, Crown, Medal, Award } from 'lucide-react'
import { clsx } from 'clsx'
import { supabase } from '@/lib/supabase'
import { useSalesAuth } from '@/lib/sales-auth'
import { deriveCommissionsFromLeads, type Commission, type Deal } from '@/lib/canada-sales-demo-data'
import { canadaLeadsService } from '@/lib/canada-leads-service'

interface TeamMember {
  id: string
  name: string
  email: string
  phone: string
  commission_rate: number
  deals_open: number
  deals_won: number
  total_mrr: number
  total_earned: number
  total_paid: number
  is_active: boolean
  joined: string
  role: 'admin' | 'active' | 'inactive' | 'onboarding'
  location: string
}

interface Applicant {
  id: string
  name: string
  email: string
  phone: string
  applied_at: string
  status: 'pending' | 'approved' | 'rejected'
}

const ADMIN_EMAILS = [
  'apierce@alphasale.co',
  'aidanpierce72@gmail.com',
  'aidanpierce@meridian.tips',
  'cheungenochmgmt@gmail.com',
  'aidanvietnguyen@gmail.com',
]

const DEMO_TEAM: TeamMember[] = [
  { id: '1', name: 'Aidan Pierce', email: 'apierce@alphasale.co', phone: '', commission_rate: 70, deals_open: 0, deals_won: 0, total_mrr: 0, total_earned: 0, total_paid: 0, is_active: true, joined: '2025-09-15', role: 'admin', location: 'Toronto, ON' },
  { id: '2', name: 'Enoch Cheung', email: 'cheungenochmgmt@gmail.com', phone: '', commission_rate: 70, deals_open: 0, deals_won: 0, total_mrr: 0, total_earned: 0, total_paid: 0, is_active: true, joined: '2026-05-03', role: 'admin', location: 'Vancouver, BC' },
  { id: '3', name: 'Aidan Nguyen', email: 'aidanvietnguyen@gmail.com', phone: '', commission_rate: 70, deals_open: 0, deals_won: 0, total_mrr: 0, total_earned: 0, total_paid: 0, is_active: true, joined: '2026-05-09', role: 'admin', location: 'Toronto, ON' },
]

function normalizeRate(v: number): number {
  return v <= 1 ? Math.round(v * 100) : v
}

const AVATAR_COLORS = ['#00d4aa', '#7c3aed', '#f59e0b', '#1a8fd6']
const AVG_LIFETIME_MONTHS = 18

function formatCad(amount: number): string {
  return 'CA$' + Math.round(amount).toLocaleString('en-CA')
}

function getInitials(name: string): string {
  const parts = name.split(' ')
  return (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
}

function getAvatarColor(name: string): string {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
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

function VisionPro3D() {
  return (
    <div className="relative w-[140px] h-[100px] flex-shrink-0" style={{ perspective: '600px' }}>
      <div
        className="absolute inset-0"
        style={{
          transformStyle: 'preserve-3d',
          animation: 'visionSpin 6s ease-in-out infinite',
        }}
      >
        {/* Main visor — front face */}
        <div
          className="absolute"
          style={{
            width: '120px',
            height: '52px',
            top: '20px',
            left: '10px',
            borderRadius: '26px',
            background: 'linear-gradient(135deg, #2a2a3e 0%, #1a1a2e 30%, #0d0d1a 70%, #1a1a2e 100%)',
            boxShadow: '0 0 30px rgba(124,58,237,0.15), inset 0 1px 0 rgba(255,255,255,0.08)',
            border: '1px solid rgba(124,58,237,0.2)',
            transform: 'translateZ(12px)',
          }}
        >
          {/* Glass lens gradient */}
          <div
            className="absolute"
            style={{
              inset: '3px',
              borderRadius: '23px',
              background: 'linear-gradient(145deg, rgba(124,58,237,0.15) 0%, rgba(26,143,214,0.1) 40%, rgba(23,197,176,0.08) 70%, rgba(124,58,237,0.12) 100%)',
              backdropFilter: 'blur(4px)',
            }}
          >
            {/* Reflection sweep */}
            <div
              style={{
                position: 'absolute',
                top: '4px',
                left: '15%',
                width: '70%',
                height: '40%',
                borderRadius: '50%',
                background: 'linear-gradient(180deg, rgba(255,255,255,0.12) 0%, transparent 100%)',
              }}
            />
          </div>
        </div>

        {/* Top frame edge */}
        <div
          className="absolute"
          style={{
            width: '120px',
            height: '52px',
            top: '20px',
            left: '10px',
            borderRadius: '26px',
            background: 'linear-gradient(180deg, #3a3a4e 0%, #2a2a3e 100%)',
            transform: 'translateZ(14px)',
            clipPath: 'inset(0 0 85% 0)',
          }}
        />

        {/* Back face — cushion */}
        <div
          className="absolute"
          style={{
            width: '110px',
            height: '44px',
            top: '24px',
            left: '15px',
            borderRadius: '22px',
            background: 'linear-gradient(135deg, #1a1a1a 0%, #111 100%)',
            border: '1px solid rgba(255,255,255,0.03)',
            transform: 'translateZ(-4px)',
          }}
        />

        {/* Side band — left */}
        <div
          className="absolute"
          style={{
            width: '24px',
            height: '8px',
            top: '42px',
            left: '0px',
            borderRadius: '4px',
            background: 'linear-gradient(90deg, #4a4a5e, #3a3a4e)',
            transform: 'rotateY(-25deg) translateZ(6px)',
          }}
        />

        {/* Side band — right */}
        <div
          className="absolute"
          style={{
            width: '24px',
            height: '8px',
            top: '42px',
            right: '0px',
            borderRadius: '4px',
            background: 'linear-gradient(270deg, #4a4a5e, #3a3a4e)',
            transform: 'rotateY(25deg) translateZ(6px)',
          }}
        />

        {/* Digital crown — right side */}
        <div
          className="absolute"
          style={{
            width: '6px',
            height: '6px',
            top: '40px',
            right: '4px',
            borderRadius: '50%',
            background: 'radial-gradient(circle, #5a5a6e, #3a3a4e)',
            border: '1px solid rgba(255,255,255,0.1)',
            transform: 'translateZ(10px)',
          }}
        />

        {/* Ambient glow under the device */}
        <div
          className="absolute"
          style={{
            width: '80px',
            height: '20px',
            bottom: '6px',
            left: '30px',
            borderRadius: '50%',
            background: 'radial-gradient(ellipse, rgba(124,58,237,0.2) 0%, transparent 70%)',
            filter: 'blur(6px)',
            transform: 'translateZ(-8px)',
          }}
        />
      </div>

      <style>{`
        @keyframes visionSpin {
          0%, 100% { transform: rotateY(-15deg) rotateX(5deg); }
          50% { transform: rotateY(15deg) rotateX(-3deg); }
        }
      `}</style>
    </div>
  )
}

function isAdmin(email: string | undefined): boolean {
  if (!email) return false
  return ADMIN_EMAILS.some(a => a.toLowerCase() === email.toLowerCase())
}

function computeTeamStats(team: TeamMember[], deals: Deal[]) {
  const assignedDealIds = new Set<string>()
  const enriched = team.map(member => {
    const repDeals = deals.filter(d => (d as any).rep_id === member.id)
    repDeals.forEach(d => assignedDealIds.add(d.id))

    const openDeals = repDeals.filter(d => d.stage !== 'customer_walkthrough' && d.stage !== 'pos_connected' && d.stage !== 'closed_won' && d.stage !== 'closed_lost')
    const wonDeals = repDeals.filter(d => d.stage === 'customer_walkthrough' || d.stage === 'pos_connected' || d.stage === 'closed_won')

    const monthlyMrr = wonDeals.reduce((s, d) => s + d.monthly_value, 0)
    const mrrCad = Math.round(monthlyMrr)

    // Total Commission = SR% / 100 * MRR * lifetime months
    const lifetimeCommission = Math.round((member.commission_rate / 100) * mrrCad * AVG_LIFETIME_MONTHS)

    return {
      ...member,
      deals_open: openDeals.length,
      deals_won: wonDeals.length,
      total_mrr: mrrCad,
      total_earned: lifetimeCommission,
      // Balance Owed = SR% of MRR per month (current month unpaid)
      // Accumulate: months since first won deal * monthly commission - total_paid
    }
  })

  return enriched
}

export default function CanadaPortalTeamPage() {
  const { rep } = useSalesAuth()
  const admin = isAdmin(rep?.email)
  const [search, setSearch] = useState('')
  const [team, setTeam] = useState<TeamMember[]>(DEMO_TEAM)
  const [deals, setDeals] = useState<Deal[]>([])
  const [commissions, setCommissions] = useState<Commission[]>([])
  const [applicants, setApplicants] = useState<Applicant[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'reps' | 'leaderboard' | 'payouts' | 'applications'>('reps')
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null)
  const [editRate, setEditRate] = useState('')
  const [editName, setEditName] = useState('')

  useEffect(() => {
    async function fetchData() {
      // Fetch team from Supabase
      if (supabase) {
        try {
          const { data, error } = await supabase
            .from('sales_reps')
            .select('*')
            .in('portal_context', ['canada', 'all'])
            .order('created_at', { ascending: true })

          if (data && !error && data.length > 0) {
            setTeam(data.map((r: Record<string, unknown>) => {
              const email = (r.email as string) || ''
              const adminRole = ADMIN_EMAILS.some(a => a.toLowerCase() === email.toLowerCase())
              return {
                id: r.id as string || r.rep_id as string || '',
                name: r.name as string,
                email,
                phone: (r.phone as string) || '',
                commission_rate: normalizeRate(Number(r.commission_rate) || 0.7),
                deals_open: 0,
                deals_won: 0,
                total_mrr: 0,
                total_earned: Math.round(Number(r.total_earned || 0)),
                total_paid: Math.round(Number(r.total_paid || 0)),
                is_active: r.is_active as boolean,
                joined: (r.created_at as string || '').slice(0, 10),
                role: adminRole ? 'admin' : (r.is_active ? 'active' : 'inactive') as 'admin' | 'active' | 'inactive',
                location: (r as any).location || 'Canada',
              }
            }))
          }
        } catch {
          // fall back to demo data
        }
      }

      // Fetch deals for real pipeline calculation
      let fetchedDeals: Deal[] = []
      try {
        fetchedDeals = await canadaLeadsService.list()
        setDeals(fetchedDeals)
      } catch {
        // ignore
      }

      // Fetch applicants (new signups not yet activated)
      if (supabase) {
        try {
          const { data } = await supabase
            .from('sales_reps')
            .select('*')
            .eq('is_active', false)
            .in('portal_context', ['canada', 'all'])
            .order('created_at', { ascending: false })

          if (data && data.length > 0) {
            setApplicants(data.map((r: Record<string, unknown>) => ({
              id: r.id as string || r.rep_id as string || '',
              name: r.name as string || 'Unknown',
              email: (r.email as string) || '',
              phone: (r.phone as string) || '',
              applied_at: (r.created_at as string || '').slice(0, 10),
              status: 'pending' as const,
            })))
          }
        } catch {
          // ignore
        }
      }

      // Derive commissions from leads data
      const comms = deriveCommissionsFromLeads(fetchedDeals)
      setCommissions(comms)
      setLoading(false)
    }
    fetchData()
  }, [])

  // Enrich team with computed deal stats
  const enrichedTeam = computeTeamStats(team, deals)

  const filtered = enrichedTeam.filter(m => {
    if (!search) return true
    const s = search.toLowerCase()
    return m.name.toLowerCase().includes(s) || m.email.toLowerCase().includes(s)
  })

  // ── Stat card formulas ──
  const totalActive = enrichedTeam.filter(m => m.is_active).length
  const totalOnboarding = enrichedTeam.filter(m => m.role === 'onboarding').length

  // Pipeline = all open deals from signed reps
  const openDeals = deals.filter(d => d.stage !== 'customer_walkthrough' && d.stage !== 'pos_connected' && d.stage !== 'closed_won' && d.stage !== 'closed_lost')
  const wonDeals = deals.filter(d => d.stage === 'customer_walkthrough' || d.stage === 'pos_connected' || d.stage === 'closed_won')
  const pipelineMrr = Math.round(openDeals.reduce((s, d) => s + d.monthly_value, 0))

  // Total Commission = sum of each rep's (commission_rate% * their won MRR * avg lifetime)
  const totalCommission = enrichedTeam.reduce((s, m) => s + m.total_earned, 0)

  // Total paid (from team data)
  const totalPaid = enrichedTeam.reduce((s, m) => s + m.total_paid, 0)

  // Balance Owed = sum of each rep's (commission_rate% * their MRR per month) - total_paid
  const monthlyCommissionOwed = enrichedTeam.reduce((s, m) => s + Math.round((m.commission_rate / 100) * m.total_mrr), 0)
  const balanceOwed = totalCommission - totalPaid

  async function handleApproveApplicant(applicant: Applicant) {
    if (supabase) {
      await supabase.from('sales_reps').update({ is_active: true }).eq('id', applicant.id)
    }
    setApplicants(prev => prev.filter(a => a.id !== applicant.id))
    setTeam(prev => [...prev, {
      id: applicant.id, name: applicant.name, email: applicant.email, phone: applicant.phone,
      commission_rate: 70, deals_open: 0, deals_won: 0, total_mrr: 0, total_earned: 0,
      total_paid: 0, is_active: true, joined: applicant.applied_at, role: 'active', location: 'Canada',
    }])
  }

  async function handleRejectApplicant(applicant: Applicant) {
    if (supabase) {
      await supabase.from('sales_reps').delete().eq('id', applicant.id)
    }
    setApplicants(prev => prev.filter(a => a.id !== applicant.id))
  }

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
              <p className="text-lg font-bold text-white">{enrichedTeam.length}</p>
              <p className="text-[10px] text-[#4a5550]">{totalActive} active{totalOnboarding > 0 ? ` / ${totalOnboarding} onboarding` : ''}</p>
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
              <p className="text-lg font-bold text-white">{openDeals.length} deals</p>
              <p className="text-[10px] text-[#4a5550]">{formatCad(pipelineMrr)}/mo MRR</p>
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
              <p className="text-lg font-bold text-white">{formatCad(totalCommission)}</p>
              <p className="text-[10px] text-[#4a5550]">{formatCad(totalPaid)} paid · {formatCad(monthlyCommissionOwed)}/mo rate</p>
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
                {formatCad(balanceOwed)}
              </p>
              <p className="text-[10px] text-[#4a5550]">{wonDeals.length} signed deals</p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-[#0f1512] border border-[#1a2420] rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab('reps')}
          className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'reps' ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white')}
        >
          Sales Reps
        </button>
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'leaderboard' ? 'bg-[#f59e0b]/20 text-[#f59e0b]' : 'text-[#6b7a74] hover:text-white')}
        >
          Leaderboard
        </button>
        {admin && (
          <button
            onClick={() => setActiveTab('payouts')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'payouts' ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white')}
          >
            Payouts
          </button>
        )}
        {admin && (
          <button
            onClick={() => setActiveTab('applications')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors relative', activeTab === 'applications' ? 'bg-[#1a2420] text-white' : 'text-[#6b7a74] hover:text-white')}
          >
            Applications
            {applicants.length > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-[#f59e0b] text-[#0a0f0d] text-[9px] font-bold flex items-center justify-center">
                {applicants.length}
              </span>
            )}
          </button>
        )}
      </div>

      {/* Sales Reps Tab */}
      {activeTab === 'reps' && (
        <>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6b7a74]/60" />
            <input
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 bg-[#0f1512] border border-[#1a2420] rounded-xl text-sm text-white placeholder-[#4a5550] focus:outline-none focus:border-[#00d4aa]/50"
              placeholder="Search team members..."
            />
          </div>

          <div className="space-y-3">
            {filtered.map(member => {
              const badge = getRoleBadge(member.role)
              const avatarColor = getAvatarColor(member.name)
              const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)

              return (
                <div key={member.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: avatarColor + '20' }}>
                      <span className="text-xs font-bold" style={{ color: avatarColor }}>{getInitials(member.name)}</span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white truncate">{member.name}</p>
                        <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium border', badge.bg, badge.textColor, badge.border)}>
                          {badge.text}
                        </span>
                      </div>
                      {admin && <p className="text-xs text-[#6b7a74] mt-0.5">{member.email}</p>}
                      <p className="text-[10px] text-[#4a5550]">{member.location}</p>
                    </div>

                    {/* Stats */}
                    <div className="hidden sm:flex items-center gap-4 text-center">
                      <div>
                        <p className="text-[10px] text-[#4a5550]">Deals</p>
                        <p className="text-xs font-bold text-white">{member.deals_open + member.deals_won}</p>
                      </div>
                      {admin && (
                        <>
                          <div>
                            <p className="text-[10px] text-[#4a5550]">MRR</p>
                            <p className="text-xs font-bold text-[#00d4aa]">{formatCad(member.total_mrr)}</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-[#4a5550]">Comm/mo</p>
                            <p className="text-xs font-bold text-[#7c3aed]">{formatCad(monthlyComm)}</p>
                          </div>
                        </>
                      )}
                    </div>

                    {admin && (
                      <div className="hidden sm:block">
                        <span className="text-sm font-bold text-[#7c3aed]">{member.commission_rate}%</span>
                      </div>
                    )}

                    {admin && (
                      <button
                        onClick={() => { setEditingMember(member); setEditRate(String(member.commission_rate)); setEditName(member.name) }}
                        className="p-1.5 rounded-lg hover:bg-[#1a2420] text-[#6b7a74] transition-colors"
                      >
                        <MoreVertical size={14} />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </>
      )}

      {/* Leaderboard Tab */}
      {activeTab === 'leaderboard' && (
        <div className="space-y-4">
          {/* Apple Vision Pro Incentive Banner */}
          <div className="relative overflow-hidden bg-gradient-to-r from-[#1a1a2e] via-[#16213e] to-[#0f3460] border border-[#7c3aed]/30 rounded-xl p-5">
            <div className="absolute top-0 right-0 w-40 h-40 bg-[#7c3aed]/8 rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-1/4 w-32 h-32 bg-[#1a8fd6]/5 rounded-full blur-3xl" />
            <div className="relative flex items-center gap-2">
              <VisionPro3D />
              <div className="flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-base font-bold text-white">Apple Vision Pro</h3>
                  <span className="px-2 py-0.5 rounded-full bg-[#7c3aed]/20 text-[#a855f7] text-[10px] font-bold border border-[#7c3aed]/30 animate-pulse">ACTIVE INCENTIVE</span>
                </div>
                <p className="text-xs text-[#a1a1a8] mt-1.5 leading-relaxed">Top performing rep by <span className="text-white font-medium">December 31, 2026</span> wins an Apple Vision Pro. Ranked by total MRR signed.</p>
                <div className="mt-3 flex items-center gap-4 text-[10px] text-[#6b7a74]">
                  <span className="flex items-center gap-1"><Clock size={10} /> Ends: Dec 31, 2026</span>
                  <span className="flex items-center gap-1"><Award size={10} /> CA$5,499 value</span>
                  <span className="flex items-center gap-1"><Trophy size={10} /> Top MRR wins</span>
                </div>
              </div>
            </div>
          </div>

          {/* Ranked List */}
          <div className="space-y-2">
            {[...enrichedTeam]
              .sort((a, b) => b.total_mrr - a.total_mrr || b.deals_won - a.deals_won)
              .map((member, idx) => {
                const avatarColor = getAvatarColor(member.name)
                const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)
                const rankIcon = idx === 0 ? <Crown size={16} className="text-[#f59e0b]" /> : idx === 1 ? <Medal size={16} className="text-[#c0c0c0]" /> : idx === 2 ? <Medal size={16} className="text-[#cd7f32]" /> : <span className="text-xs text-[#6b7a74] font-bold w-4 text-center">{idx + 1}</span>

                return (
                  <div key={member.id} className={clsx(
                    'bg-[#0f1512] border rounded-xl px-5 py-4 transition-all',
                    idx === 0 ? 'border-[#f59e0b]/30 shadow-[0_0_20px_rgba(245,158,11,0.05)]' : 'border-[#1a2420]'
                  )}>
                    <div className="flex items-center gap-4">
                      <div className="w-8 flex items-center justify-center flex-shrink-0">
                        {rankIcon}
                      </div>
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: avatarColor + '20' }}>
                        <span className="text-xs font-bold" style={{ color: avatarColor }}>{getInitials(member.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white">{member.name}</p>
                          {idx === 0 && <Trophy size={12} className="text-[#f59e0b]" />}
                        </div>
                        <p className="text-[10px] text-[#6b7a74]">{member.location}</p>
                      </div>
                      <div className="flex items-center gap-6 text-center">
                        <div>
                          <p className="text-[10px] text-[#4a5550]">Deals Won</p>
                          <p className="text-sm font-bold text-white">{member.deals_won}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-[#4a5550]">MRR</p>
                          <p className="text-sm font-bold text-[#00d4aa]">{formatCad(member.total_mrr)}</p>
                        </div>
                        {admin && (
                          <div>
                            <p className="text-[10px] text-[#4a5550]">Comm/mo</p>
                            <p className="text-sm font-bold text-[#7c3aed]">{formatCad(monthlyComm)}</p>
                          </div>
                        )}
                        <div>
                          <p className="text-[10px] text-[#4a5550]">Pipeline</p>
                          <p className="text-sm font-bold text-[#f59e0b]">{member.deals_open}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Leaderboard Rules */}
          <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
            <h3 className="text-xs font-semibold text-[#6b7a74] uppercase tracking-wider mb-3">How Rankings Work</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-[11px] text-[#4a5550]">
              <div>
                <p className="text-white font-medium mb-1">Primary: Total MRR</p>
                <p>Ranked by total monthly recurring revenue from signed deals.</p>
              </div>
              <div>
                <p className="text-white font-medium mb-1">Tiebreaker: Deals Won</p>
                <p>If MRR is tied, the rep with more closed deals ranks higher.</p>
              </div>
              <div>
                <p className="text-white font-medium mb-1">Apple Vision Pro</p>
                <p>#1 ranked rep on Dec 31, 2026 wins the grand prize.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payouts Tab */}
      {activeTab === 'payouts' && (
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Rep Balances</h3>
            <div className="space-y-3">
              {enrichedTeam.map(member => {
                const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)
                const owed = member.total_earned - member.total_paid
                const avatarColor = getAvatarColor(member.name)

                return (
                  <div key={member.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: avatarColor + '20' }}>
                        <span className="text-xs font-bold" style={{ color: avatarColor }}>{getInitials(member.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{member.name}</p>
                        <p className="text-[10px] text-[#6b7a74]">
                          {member.deals_won} signed · {member.commission_rate}% rate · {formatCad(member.total_mrr)} MRR · {formatCad(monthlyComm)}/mo comm
                        </p>
                        <p className="text-[10px] text-[#4a5550]">
                          Lifetime est: {formatCad(member.total_earned)} ({AVG_LIFETIME_MONTHS}mo avg)
                        </p>
                      </div>
                      {owed <= 0 ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#00d4aa]/10 text-[#00d4aa] border border-[#00d4aa]/20">
                          Paid up &#10003;
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20">
                          {formatCad(owed)} owed
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Formulas Reference — admin only */}
          {admin && (
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-5">
              <h3 className="text-xs font-semibold text-[#6b7a74] uppercase tracking-wider mb-3">Commission Formulas</h3>
              <div className="space-y-2 text-[11px] font-mono text-[#4a5550]">
                <p><span className="text-[#7c3aed]">Monthly Comm</span> = Commission Rate % × MRR (CAD)</p>
                <p><span className="text-[#7c3aed]">Lifetime Est</span> = Commission Rate % × MRR × {AVG_LIFETIME_MONTHS} months</p>
                <p><span className="text-[#f59e0b]">Balance Owed</span> = Lifetime Est − Total Paid</p>
                <p><span className="text-[#00d4aa]">Pipeline MRR</span> = Sum of open deal monthly values (CAD)</p>
              </div>
            </div>
          )}

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
                        <p className="text-xs font-semibold text-white">{formatCad(comm.commission_amount)}</p>
                        <p className="text-[10px] text-[#6b7a74]">
                          {comm.client_name}{admin ? ` · ${comm.commission_rate}%` : ''}
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

      {/* Applications Tab — admin only */}
      {activeTab === 'applications' && admin && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold text-white">Sales Rep Applications</h3>
              <p className="text-xs text-[#6b7a74] mt-0.5">New reps who signed up at /canada/portal/signup appear here for approval.</p>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#0f1512] border border-[#1a2420] text-[10px] font-medium text-[#6b7a74]">
              <UserPlus size={12} /> {applicants.length} pending
            </div>
          </div>

          {applicants.length === 0 ? (
            <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-10 text-center">
              <div className="w-12 h-12 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                <UserPlus size={20} className="text-[#00d4aa]" />
              </div>
              <p className="text-sm text-[#6b7a74]">No pending applications.</p>
              <p className="text-[11px] text-[#4a5550] mt-1">New reps who sign up will appear here for your review.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {applicants.map(applicant => {
                const avatarColor = getAvatarColor(applicant.name)
                return (
                  <div key={applicant.id} className="bg-[#0f1512] border border-[#1a2420] rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: avatarColor + '20' }}>
                        <span className="text-xs font-bold" style={{ color: avatarColor }}>{getInitials(applicant.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{applicant.name}</p>
                        <p className="text-xs text-[#6b7a74]">{applicant.email}</p>
                        {applicant.phone && <p className="text-[10px] text-[#4a5550]">{applicant.phone}</p>}
                        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-[#4a5550]">
                          <Clock size={10} /> Applied {applicant.applied_at}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApproveApplicant(applicant)}
                          className="flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium bg-[#00d4aa] text-[#0a0f0d] rounded-lg hover:bg-[#00d4aa]/90 transition-colors"
                        >
                          <CheckCircle2 size={12} /> Approve
                        </button>
                        <button
                          onClick={() => handleRejectApplicant(applicant)}
                          className="flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors"
                        >
                          <XCircle size={12} /> Reject
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      )}

      {/* Admin Payout Editor Modal */}
      {editingMember && admin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-[#0f1512] border border-[#1a2420] rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-white">Edit Team Member</h3>
              <button onClick={() => setEditingMember(null)} className="p-1.5 rounded-lg hover:bg-[#1a2420] transition-colors">
                <X size={18} className="text-[#6b7a74]" />
              </button>
            </div>
            <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Display Name</label>
            <input
              type="text" value={editName} onChange={e => setEditName(e.target.value)}
              className="w-full px-3 py-2 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-sm text-white focus:outline-none focus:border-[#00d4aa]/50 mb-4"
            />
            <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Commission Rate (%)</label>
            <input
              type="number" min={0} max={100} value={editRate} onChange={e => setEditRate(e.target.value)}
              className="w-full px-3 py-2 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-sm text-white focus:outline-none focus:border-[#00d4aa]/50"
            />
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setEditingMember(null)} className="px-4 py-2 text-sm text-[#6b7a74] hover:text-white transition-colors">Cancel</button>
              <button
                onClick={async () => {
                  const rate = Math.max(0, Math.min(100, Number(editRate) || 0))
                  const name = editName.trim() || editingMember.name
                  setTeam(prev => prev.map(m => m.id === editingMember.id ? { ...m, name, commission_rate: rate } : m))
                  if (supabase) {
                    const { error } = await supabase.from('sales_reps').update({ name, commission_rate: rate / 100 }).eq('id', editingMember.id)
                    if (error) {
                      console.error('Failed to save:', error)
                      alert(`Save failed: ${error.message}`)
                      return
                    }
                  }
                  setEditingMember(null)
                }}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
              >
                <Save size={14} /> Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
