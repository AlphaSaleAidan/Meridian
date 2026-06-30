import { useState, useEffect } from 'react'
import { Users, DollarSign, Target, CreditCard, Search, MoreVertical, X, Save, UserPlus, Clock, CheckCircle2, XCircle, Trophy, Crown, Medal, Award, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { useSalesAuth } from '@/lib/sales-auth'
import { getAuthHeaders } from '@/lib/supabase'
import { deriveCommissionsFromLeads, type Commission, type Deal } from '@/lib/canada-sales-demo-data'
import { usLeadsService } from '@/lib/us-leads-service'
import { isUsAdmin } from '@/lib/us-admins'
import { useToast } from '@/components/Toast'

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

function normalizeRate(v: number): number {
  return v <= 1 ? Math.round(v * 100) : v
}

const AVATAR_COLORS = ['#17C5B0', '#7c3aed', '#f59e0b', '#1a8fd6']
const AVG_LIFETIME_MONTHS = 18

function formatUsd(amount: number): string {
  return '$' + Math.round(amount).toLocaleString('en-US')
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
      return { text: 'Active', bg: 'bg-[#17C5B0]/10', textColor: 'text-[#17C5B0]', border: 'border-[#17C5B0]/20' }
    case 'onboarding':
      return { text: 'Onboarding', bg: 'bg-[#f59e0b]/10', textColor: 'text-[#f59e0b]', border: 'border-[#f59e0b]/20' }
    default:
      return { text: 'Inactive', bg: 'bg-[#A1A1A8]/10', textColor: 'text-[#A1A1A8]', border: 'border-[#A1A1A8]/20' }
  }
}

const isAdmin = isUsAdmin

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

export default function USPortalTeamPage() {
  const { rep } = useSalesAuth()
  const { toast } = useToast()
  const admin = isAdmin(rep?.email)
  const [search, setSearch] = useState('')
  const [team, setTeam] = useState<TeamMember[]>([])
  const [deals, setDeals] = useState<Deal[]>([])
  const [commissions, setCommissions] = useState<Commission[]>([])
  const [applicants, setApplicants] = useState<Applicant[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'reps' | 'leaderboard' | 'payouts' | 'applications'>(admin ? 'reps' : 'leaderboard')
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null)
  const [editRate, setEditRate] = useState('')
  const [editName, setEditName] = useState('')
  const [removing, setRemoving] = useState(false)

  useEffect(() => {
    if (!rep?.rep_id) return
    async function fetchData() {
      const apiBase = import.meta.env.VITE_API_URL || ''

      // Fetch team + applicants from backend API (requires JWT)
      try {
        const headers = await getAuthHeaders()
        const resp = await fetch(`${apiBase}/api/us/team`, { headers })
        if (resp.ok) {
          const { reps, applicants: apps } = await resp.json()
          if (reps) {
            setTeam(reps.map((r: Record<string, unknown>) => {
              const email = (r.email as string) || ''
              const adminRole = isUsAdmin(email)
              return {
                id: r.id as string || '',
                name: r.name as string,
                email,
                phone: (r.phone as string) || '',
                commission_rate: normalizeRate(Number(r.commission_rate) || 0.7),
                deals_open: 0,
                deals_won: 0,
                total_mrr: 0,
                total_earned: 0,
                total_paid: 0,
                is_active: true,
                joined: (r.created_at as string || '').slice(0, 10),
                role: adminRole ? 'admin' : 'active' as 'admin' | 'active',
                location: 'US',
              }
            }))
          }
          if (apps && apps.length > 0) {
            setApplicants(apps.map((r: Record<string, unknown>) => ({
              id: r.id as string || '',
              name: r.name as string || 'Unknown',
              email: (r.email as string) || '',
              phone: (r.phone as string) || '',
              applied_at: (r.created_at as string || '').slice(0, 10),
              status: 'pending' as const,
            })))
          }
        }
      } catch {
        // leave team empty on error — no demo data in production
      }

      // Fetch deals for real pipeline calculation
      let fetchedDeals: Deal[] = []
      try {
        fetchedDeals = await usLeadsService.list(rep?.rep_id)
        setDeals(fetchedDeals)
      } catch {
        // ignore
      }

      // Derive commissions from leads data
      const comms = deriveCommissionsFromLeads(fetchedDeals)
      setCommissions(comms)
      setLoading(false)
    }
    fetchData()
  }, [rep?.rep_id])

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
    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${apiBase}/api/us/rep-approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ rep_id: applicant.id, admin_email: rep?.email }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        toast(err.detail || 'Failed to approve rep', 'error')
        return
      }
    } catch {
      toast('Network error — please try again', 'error')
      return
    }
    setApplicants(prev => prev.filter(a => a.id !== applicant.id))
    setTeam(prev => [...prev, {
      id: applicant.id, name: applicant.name, email: applicant.email, phone: applicant.phone,
      commission_rate: 70, deals_open: 0, deals_won: 0, total_mrr: 0, total_earned: 0,
      total_paid: 0, is_active: true, joined: applicant.applied_at, role: 'active', location: 'US',
    }])
  }

  async function handleRemoveMember(member: TeamMember) {
    if (!confirm(`Remove ${member.name} from the team? This deletes their rep profile and their login — they can't sign back in.`)) return
    setRemoving(true)
    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${apiBase}/api/us/rep-remove`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ rep_id: member.id, admin_email: rep?.email }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        toast(err.detail || 'Failed to remove rep', 'error')
        setRemoving(false)
        return
      }
      const data = await resp.json().catch(() => ({}))
      // login_removed=false here usually means the account still owns a business
      // (a real merchant, not a disposable test rep), so the login is preserved.
      if (data.login_removed === false) {
        toast('Rep removed — login kept (account still owns a business)', 'warning')
      } else {
        toast('Rep and login removed', 'success')
      }
    } catch {
      toast('Network error — please try again', 'error')
      setRemoving(false)
      return
    }
    setTeam(prev => prev.filter(m => m.id !== member.id))
    setEditingMember(null)
    setRemoving(false)
  }

  async function handleRejectApplicant(applicant: Applicant) {
    if (!confirm(`Reject ${applicant.name}? This will permanently remove their application.`)) return
    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${apiBase}/api/us/rep-reject`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ rep_id: applicant.id, admin_email: rep?.email }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        toast(err.detail || 'Failed to reject rep', 'error')
        return
      }
    } catch {
      toast('Network error — please try again', 'error')
      return
    }
    setApplicants(prev => prev.filter(a => a.id !== applicant.id))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/15 border border-[#17C5B0]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#17C5B0] font-bold text-sm">M</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white">{admin ? 'Team Management' : 'Leaderboard'}</h1>
        <p className="text-sm text-[#A1A1A8] mt-0.5">{admin ? 'Manage your sales reps, commissions, and payouts.' : 'See how you stack up against the team.'}</p>
      </div>

      {/* Stat Cards — admin only (non-admins go straight to the leaderboard) */}
      {admin && (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
              <Users size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#A1A1A8]">Total Reps</p>
              <p className="text-lg font-bold text-white">{enrichedTeam.length}</p>
              <p className="text-[10px] text-[#4a5550]">{totalActive} active{totalOnboarding > 0 ? ` / ${totalOnboarding} onboarding` : ''}</p>
            </div>
          </div>
        </div>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f59e0b]/10 flex items-center justify-center">
              <Target size={16} className="text-[#f59e0b]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#A1A1A8]">Pipeline</p>
              <p className="text-lg font-bold text-white">{openDeals.length} deals</p>
              <p className="text-[10px] text-[#4a5550]">{formatUsd(pipelineMrr)}/mo MRR</p>
            </div>
          </div>
        </div>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#7c3aed]/10 flex items-center justify-center">
              <DollarSign size={16} className="text-[#7c3aed]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#A1A1A8]">Total Commissions</p>
              <p className="text-lg font-bold text-white">{formatUsd(totalCommission)}</p>
              <p className="text-[10px] text-[#4a5550]">{formatUsd(totalPaid)} paid · {formatUsd(monthlyCommissionOwed)}/mo rate</p>
            </div>
          </div>
        </div>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#f59e0b]/10 flex items-center justify-center">
              <CreditCard size={16} className="text-[#f59e0b]" />
            </div>
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#A1A1A8]">Balance Owed</p>
              <p className={clsx('text-lg font-bold', balanceOwed > 0 ? 'text-[#f59e0b]' : 'text-white')}>
                {formatUsd(balanceOwed)}
              </p>
              <p className="text-[10px] text-[#4a5550]">{wonDeals.length} signed deals</p>
            </div>
          </div>
        </div>
      </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-[#111113] border border-[#1F1F23] rounded-xl p-1 w-fit">
        <button
          onClick={() => setActiveTab('reps')}
          className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'reps' ? 'bg-[#1F1F23] text-white' : 'text-[#A1A1A8] hover:text-white')}
        >
          Sales Reps
        </button>
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'leaderboard' ? 'bg-[#f59e0b]/20 text-[#f59e0b]' : 'text-[#A1A1A8] hover:text-white')}
        >
          Leaderboard
        </button>
        {admin && (
          <button
            onClick={() => setActiveTab('payouts')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'payouts' ? 'bg-[#1F1F23] text-white' : 'text-[#A1A1A8] hover:text-white')}
          >
            Payouts
          </button>
        )}
        {admin && (
          <button
            onClick={() => setActiveTab('applications')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors relative', activeTab === 'applications' ? 'bg-[#1F1F23] text-white' : 'text-[#A1A1A8] hover:text-white')}
          >
            Applications
            {applicants.length > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-[#f59e0b] text-[#0A0A0B] text-[9px] font-bold flex items-center justify-center">
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
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]/60" />
            <input
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-xl text-sm text-white placeholder-[#4a5550] focus:outline-none focus:border-[#17C5B0]/50"
              placeholder="Search team members..."
            />
          </div>

          <div className="space-y-3">
            {filtered.map(member => {
              const badge = getRoleBadge(member.role)
              const avatarColor = getAvatarColor(member.name)
              const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)

              return (
                <div key={member.id} className="bg-[#111113] border border-[#1F1F23] rounded-xl px-5 py-4">
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
                      {admin && <p className="text-xs text-[#A1A1A8] mt-0.5">{member.email}</p>}
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
                            <p className="text-xs font-bold text-[#17C5B0]">{formatUsd(member.total_mrr)}</p>
                          </div>
                          <div>
                            <p className="text-[10px] text-[#4a5550]">Comm/mo</p>
                            <p className="text-xs font-bold text-[#7c3aed]">{formatUsd(monthlyComm)}</p>
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
                        className="p-1.5 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8] transition-colors"
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
            <div className="relative">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold text-white">Apple Vision Pro</h3>
                <span className="px-2 py-0.5 rounded-full bg-[#7c3aed]/20 text-[#a855f7] text-[10px] font-bold border border-[#7c3aed]/30 animate-pulse">ACTIVE INCENTIVE</span>
              </div>
              <p className="text-xs text-[#a1a1a8] mt-1.5 leading-relaxed">Top performing rep by <span className="text-white font-medium">December 31, 2026</span> wins an Apple Vision Pro. Ranked by total MRR signed.</p>
              <div className="mt-3 flex items-center gap-4 text-[10px] text-[#A1A1A8]">
                <span className="flex items-center gap-1"><Clock size={10} /> Ends: Dec 31, 2026</span>
                <span className="flex items-center gap-1"><Award size={10} /> $5,499 value</span>
                <span className="flex items-center gap-1"><Trophy size={10} /> Top MRR wins</span>
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
                const rankIcon = idx === 0 ? <Crown size={16} className="text-[#f59e0b]" /> : idx === 1 ? <Medal size={16} className="text-[#c0c0c0]" /> : idx === 2 ? <Medal size={16} className="text-[#cd7f32]" /> : <span className="text-xs text-[#A1A1A8] font-bold w-4 text-center">{idx + 1}</span>

                return (
                  <div key={member.id} className={clsx(
                    'bg-[#111113] border rounded-xl px-5 py-4 transition-all',
                    idx === 0 ? 'border-[#f59e0b]/30 shadow-[0_0_20px_rgba(245,158,11,0.05)]' : 'border-[#1F1F23]'
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
                        <p className="text-[10px] text-[#A1A1A8]">{member.location}</p>
                      </div>
                      <div className="flex items-center gap-6 text-center">
                        <div>
                          <p className="text-[10px] text-[#4a5550]">Deals Won</p>
                          <p className="text-sm font-bold text-white">{member.deals_won}</p>
                        </div>
                        <div>
                          <p className="text-[10px] text-[#4a5550]">MRR</p>
                          <p className="text-sm font-bold text-[#17C5B0]">{formatUsd(member.total_mrr)}</p>
                        </div>
                        {admin && (
                          <div>
                            <p className="text-[10px] text-[#4a5550]">Comm/mo</p>
                            <p className="text-sm font-bold text-[#7c3aed]">{formatUsd(monthlyComm)}</p>
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
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
            <h3 className="text-xs font-semibold text-[#A1A1A8] uppercase tracking-wider mb-3">How Rankings Work</h3>
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
                  <div key={member.id} className="bg-[#111113] border border-[#1F1F23] rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: avatarColor + '20' }}>
                        <span className="text-xs font-bold" style={{ color: avatarColor }}>{getInitials(member.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{member.name}</p>
                        <p className="text-[10px] text-[#A1A1A8]">
                          {member.deals_won} signed · {member.commission_rate}% rate · {formatUsd(member.total_mrr)} MRR · {formatUsd(monthlyComm)}/mo comm
                        </p>
                        <p className="text-[10px] text-[#4a5550]">
                          Lifetime est: {formatUsd(member.total_earned)} ({AVG_LIFETIME_MONTHS}mo avg)
                        </p>
                      </div>
                      {owed <= 0 ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20">
                          Paid up &#10003;
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-medium bg-[#f59e0b]/10 text-[#f59e0b] border border-[#f59e0b]/20">
                          {formatUsd(owed)} owed
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
            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
              <h3 className="text-xs font-semibold text-[#A1A1A8] uppercase tracking-wider mb-3">Commission Formulas</h3>
              <div className="space-y-2 text-[11px] font-mono text-[#4a5550]">
                <p><span className="text-[#7c3aed]">Monthly Comm</span> = Commission Rate % × MRR (USD)</p>
                <p><span className="text-[#7c3aed]">Lifetime Est</span> = Commission Rate % × MRR × {AVG_LIFETIME_MONTHS} months</p>
                <p><span className="text-[#f59e0b]">Balance Owed</span> = Lifetime Est − Total Paid</p>
                <p><span className="text-[#17C5B0]">Pipeline MRR</span> = Sum of open deal monthly values (USD)</p>
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
                      return { text: 'paid', bg: 'bg-[#17C5B0]/10', textColor: 'text-[#17C5B0]', border: 'border-[#17C5B0]/20' }
                    case 'earned':
                      return { text: 'earned', bg: 'bg-[#7c3aed]/10', textColor: 'text-[#7c3aed]', border: 'border-[#7c3aed]/20' }
                    case 'pending':
                      return { text: 'pending', bg: 'bg-[#f59e0b]/10', textColor: 'text-[#f59e0b]', border: 'border-[#f59e0b]/20' }
                    default:
                      return { text: comm.status, bg: 'bg-[#A1A1A8]/10', textColor: 'text-[#A1A1A8]', border: 'border-[#A1A1A8]/20' }
                  }
                })()

                return (
                  <div key={comm.id} className="bg-[#111113] border border-[#1F1F23] rounded-xl px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-[#7c3aed]/10 flex items-center justify-center flex-shrink-0">
                        <DollarSign size={12} className="text-[#7c3aed]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-white">{formatUsd(comm.commission_amount)}</p>
                        <p className="text-[10px] text-[#A1A1A8]">
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
              <p className="text-xs text-[#A1A1A8] mt-0.5">New reps who signed up at /us/portal/signup appear here for approval.</p>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#111113] border border-[#1F1F23] text-[10px] font-medium text-[#A1A1A8]">
              <UserPlus size={12} /> {applicants.length} pending
            </div>
          </div>

          {applicants.length === 0 ? (
            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-10 text-center">
              <div className="w-12 h-12 rounded-full bg-[#17C5B0]/10 flex items-center justify-center mx-auto mb-3">
                <UserPlus size={20} className="text-[#17C5B0]" />
              </div>
              <p className="text-sm text-[#A1A1A8]">No pending applications.</p>
              <p className="text-[11px] text-[#4a5550] mt-1">New reps who sign up will appear here for your review.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {applicants.map(applicant => {
                const avatarColor = getAvatarColor(applicant.name)
                return (
                  <div key={applicant.id} className="bg-[#111113] border border-[#1F1F23] rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0" style={{ backgroundColor: avatarColor + '20' }}>
                        <span className="text-xs font-bold" style={{ color: avatarColor }}>{getInitials(applicant.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{applicant.name}</p>
                        <p className="text-xs text-[#A1A1A8]">{applicant.email}</p>
                        {applicant.phone && <p className="text-[10px] text-[#4a5550]">{applicant.phone}</p>}
                        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-[#4a5550]">
                          <Clock size={10} /> Applied {applicant.applied_at}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApproveApplicant(applicant)}
                          className="flex items-center gap-1.5 px-3 py-2 text-[11px] font-medium bg-[#17C5B0] text-[#0A0A0B] rounded-lg hover:bg-[#17C5B0]/90 transition-colors"
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
          <div className="w-full max-w-sm bg-[#111113] border border-[#1F1F23] rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-white">Edit Team Member</h3>
              <button onClick={() => setEditingMember(null)} className="p-1.5 rounded-lg hover:bg-[#1F1F23] transition-colors">
                <X size={18} className="text-[#A1A1A8]" />
              </button>
            </div>
            <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Display Name</label>
            <input
              type="text" value={editName} onChange={e => setEditName(e.target.value)}
              className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-sm text-white focus:outline-none focus:border-[#17C5B0]/50 mb-4"
            />
            <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Commission Rate (%)</label>
            <input
              type="number" min={0} max={100} value={editRate} onChange={e => setEditRate(e.target.value)}
              className="w-full px-3 py-2 bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-sm text-white focus:outline-none focus:border-[#17C5B0]/50"
            />
            <button
              onClick={() => editingMember && handleRemoveMember(editingMember)}
              disabled={removing}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 mb-4 text-[11px] font-medium text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors disabled:opacity-50"
            >
              <Trash2 size={12} /> {removing ? 'Removing...' : 'Remove from Team'}
            </button>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setEditingMember(null)} className="px-4 py-2 text-sm text-[#A1A1A8] hover:text-white transition-colors">Cancel</button>
              <button
                onClick={async () => {
                  const rate = Math.max(0, Math.min(100, Number(editRate) || 0))
                  const name = editName.trim() || editingMember.name
                  const apiBase = import.meta.env.VITE_API_URL || ''
                  try {
                    const headers = await getAuthHeaders()
                    const resp = await fetch(`${apiBase}/api/us/rep-update`, {
                      method: 'POST',
                      headers,
                      body: JSON.stringify({ rep_id: editingMember.id, admin_email: rep?.email, name, commission_rate: rate / 100 }),
                    })
                    if (!resp.ok) {
                      const err = await resp.json().catch(() => ({}))
                      toast(err.detail || 'Failed to save', 'error')
                      return
                    }
                  } catch {
                    toast('Network error — please try again', 'error')
                    return
                  }
                  setTeam(prev => prev.map(m => m.id === editingMember.id ? { ...m, name, commission_rate: rate } : m))
                  setEditingMember(null)
                }}
                className="flex items-center gap-1.5 px-4 py-2 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-all"
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
