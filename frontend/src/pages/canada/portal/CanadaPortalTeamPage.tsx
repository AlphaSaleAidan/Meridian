import { Link } from 'react-router-dom'
import { useState, useEffect, useMemo } from 'react'
import { Users, DollarSign, Target, CreditCard, Search, MoreVertical, X, Save, UserPlus, Clock, CheckCircle2, XCircle, Trophy, Crown, Medal, Award, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { useSalesAuth } from '@/lib/sales-auth'
import { getAuthHeaders } from '@/lib/supabase'
import { deriveCommissionsFromLeads, type Commission, type Deal } from '@/lib/canada-sales-demo-data'
import { useCanadaLeads, useCanadaLeadsRealtime } from '@/lib/canada-queries'
import { fetchLeaderboard, type LeaderboardEntry } from '@/lib/leaderboard'
import { formatCad } from '@/lib/format'
import { COMMISSION_TRACKING_PAUSED } from '@/lib/commission-flags'
import { getOrgRoleBadge, isOrgRole, ORG_ROLES, ROLE_LABELS, ROLE_LEVELS, type OrgRole } from '@/lib/role-colors'
import { PortalPage } from './PortalPage'

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
  /** 7-level org role from the hierarchy migration (absent pre-migration). */
  org_role?: string
  manager_id?: string | null
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

// Hash-derived avatar palette. softBg (~12.5% → /15) sits behind the bold
// text-color initials. Class-emitting so Tailwind keeps these in its pass.
type AvatarClasses = { text: string; softBg: string }
const AVATAR_CLASSES: AvatarClasses[] = [
  { text: 'text-pm-accent',        softBg: 'bg-pm-accent/15' },
  { text: 'text-pm-purple',        softBg: 'bg-pm-purple/15' },
  { text: 'text-pm-amber-orange',  softBg: 'bg-pm-amber-orange/15' },
  { text: 'text-pm-violet',        softBg: 'bg-pm-violet/15' },
]
const AVG_LIFETIME_MONTHS = 18

function getInitials(name: string): string {
  const parts = name.split(' ')
  return (parts[0]?.[0] || '') + (parts[1]?.[0] || '')
}

function getAvatarClasses(name: string): AvatarClasses {
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return AVATAR_CLASSES[Math.abs(hash) % AVATAR_CLASSES.length]
}

// Status badges (legacy). Org-role badges come from '@/lib/role-colors' —
// getMemberBadge below prefers the 7-level org role when the API provides it.
function getRoleBadge(role: string) {
  switch (role) {
    case 'admin':
      return { text: 'Admin', bg: 'bg-pm-purple/10', textColor: 'text-pm-purple', border: 'border-pm-purple/20' }
    case 'active':
      return { text: 'Active', bg: 'bg-pm-accent/10', textColor: 'text-pm-accent', border: 'border-pm-accent/20' }
    case 'onboarding':
      return { text: 'Onboarding', bg: 'bg-pm-amber-orange/10', textColor: 'text-pm-amber-orange', border: 'border-pm-amber-orange/20' }
    default:
      return { text: 'Inactive', bg: 'bg-pm-canada-text-muted/10', textColor: 'text-pm-canada-text-muted', border: 'border-pm-canada-text-muted/20' }
  }
}

function getMemberBadge(member: Pick<TeamMember, 'role' | 'org_role'>) {
  if (member.org_role && isOrgRole(member.org_role)) return getOrgRoleBadge(member.org_role)
  return getRoleBadge(member.role)
}

interface TreeRow<T extends TeamMember> {
  member: T
  depth: number
  directReports: number
}

/** Flatten the org tree into indent-annotated rows (roots = no visible manager). */
function buildTeamTree<T extends TeamMember>(members: T[]): TreeRow<T>[] {
  const ids = new Set(members.map(m => m.id))
  const byManager = new Map<string, T[]>()
  const roots: T[] = []
  for (const m of members) {
    const mid = m.manager_id || ''
    if (mid && ids.has(mid) && mid !== m.id) {
      byManager.set(mid, [...(byManager.get(mid) || []), m])
    } else {
      roots.push(m)
    }
  }
  const rank = (m: T) => (m.org_role && isOrgRole(m.org_role) ? ROLE_LEVELS[m.org_role] : ROLE_LEVELS.sales_rep)
  const sortFn = (a: T, b: T) => rank(a) - rank(b) || a.name.localeCompare(b.name)
  const out: TreeRow<T>[] = []
  const walk = (m: T, depth: number) => {
    const kids = [...(byManager.get(m.id) || [])].sort(sortFn)
    out.push({ member: m, depth, directReports: kids.length })
    kids.forEach(k => walk(k, depth + 1))
  }
  roots.sort(sortFn).forEach(r => walk(r, 0))
  return out
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
  const [applicants, setApplicants] = useState<Applicant[]>([])
  const [teamLoading, setTeamLoading] = useState(true)
  const [teamError, setTeamError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'reps' | 'leaderboard' | 'payouts' | 'applications'>(admin ? 'reps' : 'leaderboard')
  const [editingMember, setEditingMember] = useState<TeamMember | null>(null)
  const [editRate, setEditRate] = useState('')
  const [editName, setEditName] = useState('')
  const [editRole, setEditRole] = useState<OrgRole>('sales_rep')
  const [editManagerId, setEditManagerId] = useState('')
  const [removing, setRemoving] = useState(false)
  // Peer-visible aggregate board (non-admin Leaderboard): the scoped roster
  // collapses to self+downline+upline (#334), so a leaf rep saw a board of
  // one. /api/leaderboard returns ALL active portal reps with aggregate-only
  // fields. Admin Team Management keeps the scoped roster endpoints unchanged.
  const [board, setBoard] = useState<LeaderboardEntry[] | null>(null)
  const [boardLoading, setBoardLoading] = useState(!admin)

  // Deals come from the shared React Query cache so creates/updates on the
  // Leads page refresh team stats automatically.
  const { data: deals = [], isLoading: dealsLoading, error: dealsError } = useCanadaLeads(rep?.rep_id)
  useCanadaLeadsRealtime(rep?.rep_id)
  const commissions: Commission[] = useMemo(() => deriveCommissionsFromLeads(deals), [deals])

  // PortalPage wraps the page body; either source of failure surfaces the
  // banner, and the page only shows the skeleton on a truly cold start
  // (both team list and deals empty).
  const pageIsLoading = teamLoading || dealsLoading || boardLoading
  const pageError = teamError ?? dealsError ?? null
  const pageIsEmpty = team.length === 0 && deals.length === 0

  useEffect(() => {
    if (!rep?.rep_id) { setTeamLoading(false); return }
    let cancelled = false
    async function fetchTeam() {
      const apiBase = import.meta.env.VITE_API_URL || ''
      try {
        const headers = await getAuthHeaders()
        const resp = await fetch(`${apiBase}/api/canada/team`, { headers })
        if (!resp.ok) {
          throw new Error(`Failed to load team (${resp.status})`)
        }
        const { reps, applicants: apps } = await resp.json()
        if (cancelled) return
        if (reps && reps.length > 0) {
          setTeam(reps.map((r: Record<string, unknown>) => {
            const email = (r.email as string) || ''
            const adminRole = (r.role as string) === 'admin'
              || ADMIN_EMAILS.some(a => a.toLowerCase() === email.toLowerCase())
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
              org_role: (r.role as string) || (adminRole ? 'admin' : 'sales_rep'),
              manager_id: (r.manager_id as string) || null,
              location: 'Canada',
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
      } catch (err) {
        if (!cancelled) setTeamError(err instanceof Error ? err.message : 'Could not load team data.')
      } finally {
        if (!cancelled) setTeamLoading(false)
      }
    }
    fetchTeam()
    return () => { cancelled = true }
  }, [rep?.rep_id])

  useEffect(() => {
    if (admin || !rep?.rep_id) { setBoardLoading(false); return }
    let cancelled = false
    fetchLeaderboard()
      .then(entries => { if (!cancelled) setBoard(entries) })
      .catch(() => { /* board stays null → fall back to the scoped roster */ })
      .finally(() => { if (!cancelled) setBoardLoading(false) })
    return () => { cancelled = true }
  }, [admin, rep?.rep_id])

  // Enrich team with computed deal stats
  const enrichedTeam = computeTeamStats(team, deals)

  // Rows the Leaderboard tab (and non-admin stat cards) render: the aggregate
  // board for non-admins, the enriched scoped roster for admins (unchanged).
  const boardMembers: TeamMember[] = (admin || !board) ? enrichedTeam : board.map(e => ({
    id: e.id, name: e.name, email: '', phone: '', commission_rate: 0,
    deals_open: e.deals_open, deals_won: e.deals_won, total_mrr: e.total_mrr,
    total_earned: 0, total_paid: 0, is_active: true, joined: '',
    role: 'active' as const, org_role: e.role, manager_id: null, location: 'Canada',
  }))
  const isSelf = (m: TeamMember) => m.id === rep?.rep_id || (!!m.email && m.email === rep?.email)

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
      const resp = await fetch(`${apiBase}/api/canada/rep-approve`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ rep_id: applicant.id, admin_email: rep?.email }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        alert(err.detail || 'Failed to approve rep')
        return
      }
    } catch {
      alert('Network error — please try again')
      return
    }
    setApplicants(prev => prev.filter(a => a.id !== applicant.id))
    setTeam(prev => [...prev, {
      id: applicant.id, name: applicant.name, email: applicant.email, phone: applicant.phone,
      commission_rate: 70, deals_open: 0, deals_won: 0, total_mrr: 0, total_earned: 0,
      total_paid: 0, is_active: true, joined: applicant.applied_at, role: 'active', location: 'Canada',
    }])
  }

  async function handleRemoveMember(member: TeamMember) {
    if (!confirm(`Remove ${member.name} from the team? This deletes their rep profile and their login — they can't sign back in.`)) return
    setRemoving(true)
    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${apiBase}/api/canada/rep-remove`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ rep_id: member.id, admin_email: rep?.email }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        alert(err.detail || 'Failed to remove rep')
        setRemoving(false)
        return
      }
      const data = await resp.json().catch(() => ({}))
      // login_removed=false usually means the account still owns a business
      // (a real merchant, not a disposable test rep), so the login is preserved.
      if (data.login_removed === false) {
        alert('Rep removed — login kept (account still owns a business).')
      }
    } catch {
      alert('Network error — please try again')
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
      const resp = await fetch(`${apiBase}/api/canada/rep-reject`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ rep_id: applicant.id, admin_email: rep?.email }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        alert(err.detail || 'Failed to reject rep')
        return
      }
    } catch {
      alert('Network error — please try again')
      return
    }
    setApplicants(prev => prev.filter(a => a.id !== applicant.id))
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-bold text-white">{admin ? 'Team Management' : 'Leaderboard'}</h1>
          {/* Recruiting is deliberately not a nav tab — reachable from here. */}
          {admin && (
            <Link to="/canada/portal/recruiting" className="text-xs text-pm-accent hover:underline">
              Recruiting pipeline →
            </Link>
          )}
        </div>
        <p className="text-sm text-pm-canada-text-muted mt-0.5">{admin ? (COMMISSION_TRACKING_PAUSED ? 'Manage your sales reps and applications.' : 'Manage your sales reps, commissions, and payouts.') : 'See how you stack up against the team.'}</p>
        {COMMISSION_TRACKING_PAUSED && (
          <p className="text-2xs text-pm-canada-text-faint mt-1">Commission tracking is temporarily paused.</p>
        )}
      </div>

      <PortalPage
        isLoading={pageIsLoading}
        error={pageError}
        isEmpty={pageIsEmpty}
        errorTitle="Could not load team data"
      >

      {/* Stat Cards */}
      {admin ? (
        <div className={clsx('grid grid-cols-2 gap-4', COMMISSION_TRACKING_PAUSED ? 'lg:grid-cols-2' : 'lg:grid-cols-4')}>
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
                <Users size={16} className="text-pm-accent" />
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Total Reps</p>
                <p className="text-lg font-bold text-white">{enrichedTeam.length}</p>
                <p className="text-2xs text-pm-canada-text-faint">{totalActive} active{totalOnboarding > 0 ? ` / ${totalOnboarding} onboarding` : ''}</p>
              </div>
            </div>
          </div>
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-amber-orange/10 flex items-center justify-center">
                <Target size={16} className="text-pm-amber-orange" />
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Pipeline</p>
                <p className="text-lg font-bold text-white">{openDeals.length} deals</p>
                <p className="text-2xs text-pm-canada-text-faint">{formatCad(pipelineMrr)}/mo MRR</p>
              </div>
            </div>
          </div>
          {!COMMISSION_TRACKING_PAUSED && (
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-pm-purple/10 flex items-center justify-center">
                  <DollarSign size={16} className="text-pm-purple" />
                </div>
                <div>
                  <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Total Commissions</p>
                  <p className="text-lg font-bold text-white">{formatCad(totalCommission)}</p>
                  <p className="text-2xs text-pm-canada-text-faint">{formatCad(totalPaid)} paid · {formatCad(monthlyCommissionOwed)}/mo rate</p>
                </div>
              </div>
            </div>
          )}
          {!COMMISSION_TRACKING_PAUSED && (
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-pm-amber-orange/10 flex items-center justify-center">
                  <CreditCard size={16} className="text-pm-amber-orange" />
                </div>
                <div>
                  <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Balance Owed</p>
                  <p className={clsx('text-lg font-bold', balanceOwed > 0 ? 'text-pm-amber-orange' : 'text-white')}>
                    {formatCad(balanceOwed)}
                  </p>
                  <p className="text-2xs text-pm-canada-text-faint">{wonDeals.length} signed deals</p>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
                <Users size={16} className="text-pm-accent" />
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Team Size</p>
                <p className="text-lg font-bold text-white">{boardMembers.length}</p>
              </div>
            </div>
          </div>
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-amber-orange/10 flex items-center justify-center">
                <Trophy size={16} className="text-pm-amber-orange" />
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Your Rank</p>
                <p className="text-lg font-bold text-white">
                  #{[...boardMembers].sort((a, b) => b.total_mrr - a.total_mrr || b.deals_won - a.deals_won).findIndex(isSelf) + 1 || '—'}
                </p>
              </div>
            </div>
          </div>
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center">
                <Target size={16} className="text-pm-accent" />
              </div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Your Deals</p>
                <p className="text-lg font-bold text-white">{boardMembers.find(isSelf)?.deals_won || 0} won</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-1 bg-pm-canada-surface border border-pm-canada-border rounded-xl p-1 w-fit">
        {admin && (
          <button
            onClick={() => setActiveTab('reps')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'reps' ? 'bg-pm-canada-border text-white' : 'text-pm-canada-text-muted hover:text-white')}
          >
            Sales Reps
          </button>
        )}
        <button
          onClick={() => setActiveTab('leaderboard')}
          className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'leaderboard' ? 'bg-pm-amber-orange/20 text-pm-amber-orange' : 'text-pm-canada-text-muted hover:text-white')}
        >
          Leaderboard
        </button>
        {admin && !COMMISSION_TRACKING_PAUSED && (
          <button
            onClick={() => setActiveTab('payouts')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors', activeTab === 'payouts' ? 'bg-pm-canada-border text-white' : 'text-pm-canada-text-muted hover:text-white')}
          >
            Payouts
          </button>
        )}
        {admin && (
          <button
            onClick={() => setActiveTab('applications')}
            className={clsx('px-4 py-1.5 rounded-lg text-xs font-medium transition-colors relative', activeTab === 'applications' ? 'bg-pm-canada-border text-white' : 'text-pm-canada-text-muted hover:text-white')}
          >
            Applications
            {applicants.length > 0 && (
              <span className="absolute -top-1.5 -right-1.5 w-4 h-4 rounded-full bg-pm-amber-orange text-pm-canada-bg text-[9px] font-bold flex items-center justify-center">
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
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-pm-canada-text-muted/60" />
            <input
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2.5 bg-pm-canada-surface border border-pm-canada-border rounded-xl text-sm text-white placeholder-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50"
              placeholder="Search team members..."
            />
          </div>

          <div className="space-y-3">
            {(search ? filtered.map(m => ({ member: m, depth: 0, directReports: 0 })) : buildTeamTree(filtered)).map(({ member, depth, directReports }) => {
              const badge = getMemberBadge(member)
              const avatar = getAvatarClasses(member.name)
              const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)

              return (
                <div
                  key={member.id}
                  className={clsx('bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-4', depth > 0 && 'border-l-2 border-l-pm-canada-border')}
                  style={depth > 0 ? { marginLeft: Math.min(depth, 5) * 22 } : undefined}
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${avatar.softBg}`}>
                      <span className={`text-xs font-bold ${avatar.text}`}>{getInitials(member.name)}</span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-white truncate">{member.name}</p>
                        <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium border', badge.bg, badge.textColor, badge.border)}>
                          {badge.text}
                        </span>
                        {directReports > 0 && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-2xs font-medium bg-pm-canada-border/60 text-pm-canada-text-muted">
                            <Users size={10} /> {directReports}
                          </span>
                        )}
                      </div>
                      {admin && <p className="text-xs text-pm-canada-text-muted mt-0.5">{member.email}</p>}
                      <p className="text-2xs text-pm-canada-text-faint">{member.location}</p>
                    </div>

                    {/* Stats */}
                    <div className="hidden sm:flex items-center gap-4 text-center">
                      <div>
                        <p className="text-2xs text-pm-canada-text-faint">Deals</p>
                        <p className="text-xs font-bold text-white">{member.deals_open + member.deals_won}</p>
                      </div>
                      {admin && (
                        <>
                          <div>
                            <p className="text-2xs text-pm-canada-text-faint">MRR</p>
                            <p className="text-xs font-bold text-pm-accent">{formatCad(member.total_mrr)}</p>
                          </div>
                          {!COMMISSION_TRACKING_PAUSED && (
                            <div>
                              <p className="text-2xs text-pm-canada-text-faint">Comm/mo</p>
                              <p className="text-xs font-bold text-pm-purple">{formatCad(monthlyComm)}</p>
                            </div>
                          )}
                        </>
                      )}
                    </div>

                    {admin && !COMMISSION_TRACKING_PAUSED && (
                      <div className="hidden sm:block">
                        <span className="text-sm font-bold text-pm-purple">{member.commission_rate}%</span>
                      </div>
                    )}

                    {admin && (
                      <button
                        onClick={() => {
                          setEditingMember(member)
                          setEditRate(String(member.commission_rate))
                          setEditName(member.name)
                          setEditRole(isOrgRole(member.org_role) ? member.org_role : 'sales_rep')
                          setEditManagerId(member.manager_id || '')
                        }}
                        className="p-1.5 rounded-lg hover:bg-pm-canada-border text-pm-canada-text-muted transition-colors"
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
          <div className="relative overflow-hidden bg-gradient-to-r from-[#1a1a2e] via-[#16213e] to-[#0f3460] border border-pm-purple/30 rounded-xl p-5">
            <div className="absolute top-0 right-0 w-40 h-40 bg-pm-purple/[0.08] rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-1/4 w-32 h-32 bg-pm-blue/5 rounded-full blur-3xl" />
            <div className="relative">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-base font-bold text-white">Apple Vision Pro</h3>
                <span className="px-2 py-0.5 rounded-full bg-pm-purple/20 text-[#a855f7] text-2xs font-bold border border-pm-purple/30 animate-pulse">ACTIVE INCENTIVE</span>
              </div>
              <p className="text-xs text-pm-muted mt-1.5 leading-relaxed">Top performing rep by <span className="text-white font-medium">December 31, 2026</span> wins an Apple Vision Pro. Ranked by total MRR signed.</p>
              <div className="mt-3 flex items-center gap-4 text-2xs text-pm-canada-text-muted">
                <span className="flex items-center gap-1"><Clock size={10} /> Ends: Dec 31, 2026</span>
                <span className="flex items-center gap-1"><Award size={10} /> CA$5,499 value</span>
                <span className="flex items-center gap-1"><Trophy size={10} /> Top MRR wins</span>
              </div>
            </div>
          </div>

          {/* Ranked List */}
          <div className="space-y-2">
            {[...boardMembers]
              .sort((a, b) => b.total_mrr - a.total_mrr || b.deals_won - a.deals_won)
              .map((member, idx) => {
                const avatar = getAvatarClasses(member.name)
                const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)
                const rankIcon = idx === 0 ? <Crown size={16} className="text-pm-amber-orange" /> : idx === 1 ? <Medal size={16} className="text-[#c0c0c0]" /> : idx === 2 ? <Medal size={16} className="text-[#cd7f32]" /> : <span className="text-xs text-pm-canada-text-muted font-bold w-4 text-center">{idx + 1}</span>

                return (
                  <div key={member.id} className={clsx(
                    'bg-pm-canada-surface border rounded-xl px-5 py-4 transition-all',
                    idx === 0 ? 'border-pm-amber-orange/30 shadow-[0_0_20px_rgba(245,158,11,0.05)]' : 'border-pm-canada-border'
                  )}>
                    <div className="flex items-center gap-4">
                      <div className="w-8 flex items-center justify-center flex-shrink-0">
                        {rankIcon}
                      </div>
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${avatar.softBg}`}>
                        <span className={`text-xs font-bold ${avatar.text}`}>{getInitials(member.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white">{member.name}</p>
                          {idx === 0 && <Trophy size={12} className="text-pm-amber-orange" />}
                        </div>
                        <p className="text-2xs text-pm-canada-text-muted">{member.location}</p>
                      </div>
                      <div className="flex items-center gap-6 text-center">
                        <div>
                          <p className="text-2xs text-pm-canada-text-faint">Deals Won</p>
                          <p className="text-sm font-bold text-white">{member.deals_won}</p>
                        </div>
                        <div>
                          <p className="text-2xs text-pm-canada-text-faint">MRR</p>
                          <p className="text-sm font-bold text-pm-accent">{formatCad(member.total_mrr)}</p>
                        </div>
                        {admin && !COMMISSION_TRACKING_PAUSED && (
                          <div>
                            <p className="text-2xs text-pm-canada-text-faint">Comm/mo</p>
                            <p className="text-sm font-bold text-pm-purple">{formatCad(monthlyComm)}</p>
                          </div>
                        )}
                        <div>
                          <p className="text-2xs text-pm-canada-text-faint">Pipeline</p>
                          <p className="text-sm font-bold text-pm-amber-orange">{member.deals_open}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                )
              })}
          </div>

          {/* Leaderboard Rules */}
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5">
            <h3 className="text-xs font-semibold text-pm-canada-text-muted uppercase tracking-wider mb-3">How Rankings Work</h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-2xs text-pm-canada-text-faint">
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
      {activeTab === 'payouts' && !COMMISSION_TRACKING_PAUSED && (
        <div className="space-y-6">
          <div>
            <h3 className="text-sm font-semibold text-white mb-3">Rep Balances</h3>
            <div className="space-y-3">
              {enrichedTeam.map(member => {
                const monthlyComm = Math.round((member.commission_rate / 100) * member.total_mrr)
                const owed = member.total_earned - member.total_paid
                const avatar = getAvatarClasses(member.name)

                return (
                  <div key={member.id} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${avatar.softBg}`}>
                        <span className={`text-xs font-bold ${avatar.text}`}>{getInitials(member.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{member.name}</p>
                        <p className="text-2xs text-pm-canada-text-muted">
                          {member.deals_won} signed · {member.commission_rate}% rate · {formatCad(member.total_mrr)} MRR · {formatCad(monthlyComm)}/mo comm
                        </p>
                        <p className="text-2xs text-pm-canada-text-faint">
                          Lifetime est: {formatCad(member.total_earned)} ({AVG_LIFETIME_MONTHS}mo avg)
                        </p>
                      </div>
                      {owed <= 0 ? (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium bg-pm-accent/10 text-pm-accent border border-pm-accent/20">
                          Paid up &#10003;
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-2xs font-medium bg-pm-amber-orange/10 text-pm-amber-orange border border-pm-amber-orange/20">
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
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-5">
              <h3 className="text-xs font-semibold text-pm-canada-text-muted uppercase tracking-wider mb-3">Commission Formulas</h3>
              <div className="space-y-2 text-2xs font-mono text-pm-canada-text-faint">
                <p><span className="text-pm-purple">Monthly Comm</span> = Commission Rate % × MRR (CAD)</p>
                <p><span className="text-pm-purple">Lifetime Est</span> = Commission Rate % × MRR × {AVG_LIFETIME_MONTHS} months</p>
                <p><span className="text-pm-amber-orange">Balance Owed</span> = Lifetime Est − Total Paid</p>
                <p><span className="text-pm-accent">Pipeline MRR</span> = Sum of open deal monthly values (CAD)</p>
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
                      return { text: 'paid', bg: 'bg-pm-accent/10', textColor: 'text-pm-accent', border: 'border-pm-accent/20' }
                    case 'earned':
                      return { text: 'earned', bg: 'bg-pm-purple/10', textColor: 'text-pm-purple', border: 'border-pm-purple/20' }
                    case 'pending':
                      return { text: 'pending', bg: 'bg-pm-amber-orange/10', textColor: 'text-pm-amber-orange', border: 'border-pm-amber-orange/20' }
                    default:
                      return { text: comm.status, bg: 'bg-pm-canada-text-muted/10', textColor: 'text-pm-canada-text-muted', border: 'border-pm-canada-text-muted/20' }
                  }
                })()

                return (
                  <div key={comm.id} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full bg-pm-purple/10 flex items-center justify-center flex-shrink-0">
                        <DollarSign size={12} className="text-pm-purple" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-semibold text-white">{formatCad(comm.commission_amount)}</p>
                        <p className="text-2xs text-pm-canada-text-muted">
                          {comm.client_name}{admin ? ` · ${comm.commission_rate}%` : ''}
                        </p>
                      </div>
                      <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium border', statusBadge.bg, statusBadge.textColor, statusBadge.border)}>
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
              <p className="text-xs text-pm-canada-text-muted mt-0.5">New reps who signed up at /canada/portal/signup appear here for approval.</p>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-pm-canada-surface border border-pm-canada-border text-2xs font-medium text-pm-canada-text-muted">
              <UserPlus size={12} /> {applicants.length} pending
            </div>
          </div>

          {applicants.length === 0 ? (
            <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-10 text-center">
              <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mx-auto mb-3">
                <UserPlus size={20} className="text-pm-accent" />
              </div>
              <p className="text-sm text-pm-canada-text-muted">No pending applications.</p>
              <p className="text-2xs text-pm-canada-text-faint mt-1">New reps who sign up will appear here for your review.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {applicants.map(applicant => {
                const avatar = getAvatarClasses(applicant.name)
                return (
                  <div key={applicant.id} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-4">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${avatar.softBg}`}>
                        <span className={`text-xs font-bold ${avatar.text}`}>{getInitials(applicant.name)}</span>
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white">{applicant.name}</p>
                        <p className="text-xs text-pm-canada-text-muted">{applicant.email}</p>
                        {applicant.phone && <p className="text-2xs text-pm-canada-text-faint">{applicant.phone}</p>}
                        <div className="flex items-center gap-1.5 mt-1 text-2xs text-pm-canada-text-faint">
                          <Clock size={10} /> Applied {applicant.applied_at}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleApproveApplicant(applicant)}
                          className="flex items-center gap-1.5 px-3 py-2 text-2xs font-medium bg-pm-accent text-pm-canada-bg rounded-lg hover:bg-pm-accent/90 transition-colors"
                        >
                          <CheckCircle2 size={12} /> Approve
                        </button>
                        <button
                          onClick={() => handleRejectApplicant(applicant)}
                          className="flex items-center gap-1.5 px-3 py-2 text-2xs font-medium text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors"
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
      </PortalPage>

      {/* Admin Payout Editor Modal */}
      {editingMember && admin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-sm bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-base font-semibold text-white">Edit Team Member</h3>
              <button onClick={() => setEditingMember(null)} className="p-1.5 rounded-lg hover:bg-pm-canada-border transition-colors">
                <X size={18} className="text-pm-canada-text-muted" />
              </button>
            </div>
            <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Display Name</label>
            <input
              type="text" value={editName} onChange={e => setEditName(e.target.value)}
              className="w-full px-3 py-2 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-sm text-white focus:outline-none focus:border-pm-accent/50 mb-4"
            />
            {!COMMISSION_TRACKING_PAUSED && (
              <>
                <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Commission Rate (%)</label>
                <input
                  type="number" min={0} max={100} value={editRate} onChange={e => setEditRate(e.target.value)}
                  className="w-full px-3 py-2 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-sm text-white focus:outline-none focus:border-pm-accent/50"
                />
              </>
            )}
            {/* Org placement — role + manager, saved via POST /api/team/assign */}
            <div className="mt-4 pt-4 border-t border-pm-canada-border">
              <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Role</label>
              <select
                value={editRole}
                onChange={e => setEditRole(e.target.value as OrgRole)}
                className="w-full px-3 py-2 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-sm text-white focus:outline-none focus:border-pm-accent/50 mb-3"
              >
                {ORG_ROLES.map(r => (
                  <option key={r} value={r}>{ROLE_LABELS[r]}</option>
                ))}
              </select>
              <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Reports To</label>
              <select
                value={editManagerId}
                onChange={e => setEditManagerId(e.target.value)}
                className="w-full px-3 py-2 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-sm text-white focus:outline-none focus:border-pm-accent/50"
              >
                <option value="">— No manager (top level) —</option>
                {team
                  .filter(m => m.id !== editingMember.id)
                  .filter(m => {
                    const mgrRole = isOrgRole(m.org_role) ? m.org_role : 'sales_rep'
                    return ROLE_LEVELS[mgrRole] < ROLE_LEVELS[editRole]
                  })
                  .map(m => (
                    <option key={m.id} value={m.id}>
                      {m.name} ({isOrgRole(m.org_role) ? ROLE_LABELS[m.org_role] : 'Sales Rep'})
                    </option>
                  ))}
              </select>
              <p className="text-2xs text-pm-canada-text-faint mt-1.5">Only roles that outrank the selected role can be chosen as manager. Cycles are rejected server-side.</p>
            </div>
            <button
              onClick={() => editingMember && handleRemoveMember(editingMember)}
              disabled={removing}
              className="w-full flex items-center justify-center gap-1.5 px-3 py-2 mb-4 text-2xs font-medium text-red-400 border border-red-500/20 rounded-lg hover:bg-red-500/10 transition-colors disabled:opacity-50"
            >
              <Trash2 size={12} /> {removing ? 'Removing...' : 'Remove from Team'}
            </button>
            <div className="flex justify-end gap-2 mt-5">
              <button onClick={() => setEditingMember(null)} className="px-4 py-2 text-sm text-pm-canada-text-muted hover:text-white transition-colors">Cancel</button>
              <button
                onClick={async () => {
                  const rate = Math.max(0, Math.min(100, Number(editRate) || 0))
                  const name = editName.trim() || editingMember.name
                  const apiBase = import.meta.env.VITE_API_URL || ''
                  const orgChanged = editRole !== (editingMember.org_role || 'sales_rep')
                    || (editManagerId || null) !== (editingMember.manager_id || null)
                  try {
                    const headers = await getAuthHeaders()
                    const resp = await fetch(`${apiBase}/api/canada/rep-update`, {
                      method: 'POST',
                      headers,
                      body: JSON.stringify({ rep_id: editingMember.id, admin_email: rep?.email, name, commission_rate: rate / 100 }),
                    })
                    if (!resp.ok) {
                      const err = await resp.json().catch(() => ({}))
                      alert(err.detail || 'Failed to save')
                      return
                    }
                    if (orgChanged) {
                      const assignResp = await fetch(`${apiBase}/api/team/assign`, {
                        method: 'POST',
                        headers,
                        body: JSON.stringify({ rep_id: editingMember.id, role: editRole, manager_id: editManagerId || null }),
                      })
                      if (!assignResp.ok) {
                        const err = await assignResp.json().catch(() => ({}))
                        alert(err.detail || 'Saved profile, but the org placement was rejected')
                        return
                      }
                    }
                  } catch {
                    alert('Network error — please try again')
                    return
                  }
                  setTeam(prev => prev.map(m => m.id === editingMember.id
                    ? { ...m, name, commission_rate: rate, org_role: editRole, manager_id: editManagerId || null, role: editRole === 'admin' ? 'admin' : m.role }
                    : m))
                  setEditingMember(null)
                }}
                className="flex items-center gap-1.5 px-4 py-2 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 transition-all"
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
