import { useEffect, useState } from 'react'
import { Briefcase, Clock, UserPlus, Users } from 'lucide-react'
import { clsx } from 'clsx'
import { useSalesAuth } from '@/lib/sales-auth'
import { getAuthHeaders } from '@/lib/supabase'
import { getOrgRoleBadge } from '@/lib/role-colors'
import { PortalPage } from './PortalPage'

interface Application {
  id: string
  name: string
  email: string
  phone?: string
  position?: string
  city?: string
  state_province?: string
  country?: string
  stage: string
  region?: string | null
  recruiter_id?: string | null
  stage_history?: Array<{ stage: string; by: string; at: string }>
  created_at?: string
}

interface TeamRep {
  id: string
  name: string
  org_role?: string
}

const STAGE_ORDER = ['applied', 'screened', 'interview', 'offer', 'hired', 'rejected'] as const
const STAGE_LABELS: Record<string, string> = {
  applied: 'Applied', screened: 'Screened', interview: 'Interview',
  offer: 'Offer', hired: 'Hired', rejected: 'Rejected',
}
const STAGE_CHIPS: Record<string, string> = {
  applied: 'bg-pm-canada-text-muted/10 text-pm-canada-text-muted border-pm-canada-text-muted/20',
  screened: 'bg-pm-blue/10 text-pm-blue border-pm-blue/20',
  interview: 'bg-pm-indigo/10 text-pm-indigo border-pm-indigo/20',
  offer: 'bg-pm-amber-gold/10 text-pm-amber-gold border-pm-amber-gold/20',
  hired: 'bg-pm-accent/10 text-pm-accent border-pm-accent/20',
  rejected: 'bg-red-500/10 text-red-400 border-red-500/20',
}

/** Position applied for → role chip (wired to the shared 7-role palette). */
function positionBadge(position?: string) {
  return getOrgRoleBadge(position === 'team_lead' ? 'office_manager' : 'sales_rep')
}

function positionLabel(position?: string) {
  return position === 'team_lead' ? 'Team Lead' : 'Sales Rep'
}

export default function CanadaPortalRecruitingPage() {
  const { rep } = useSalesAuth()
  const [apps, setApps] = useState<Application[]>([])
  const [team, setTeam] = useState<TeamRep[]>([])
  const [isAdmin, setIsAdmin] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      const apiBase = import.meta.env.VITE_API_URL || ''
      try {
        const headers = await getAuthHeaders()
        const [pipeResp, teamResp] = await Promise.all([
          fetch(`${apiBase}/api/careers/pipeline`, { headers }),
          fetch(`${apiBase}/api/canada/team`, { headers }),
        ])
        if (!pipeResp.ok) throw new Error(`Failed to load pipeline (${pipeResp.status})`)
        const pipe = await pipeResp.json()
        if (cancelled) return
        setApps(pipe.applications || [])
        setIsAdmin(Boolean(pipe.viewer?.is_admin))
        if (teamResp.ok) {
          const t = await teamResp.json()
          setTeam([...(t.reps || []), ...(t.applicants || [])].map((r: Record<string, unknown>) => ({
            id: r.id as string, name: r.name as string, org_role: r.role as string | undefined,
          })))
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load the recruiting pipeline.')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [rep?.rep_id])

  const recruiterName = (id?: string | null) =>
    id ? (team.find(t => t.id === id)?.name || `${id.slice(0, 8)}…`) : '—'

  async function setStage(app: Application, stage: string) {
    if (stage === app.stage) return
    if (stage === 'hired' && !confirm(`Hire ${app.name}? This creates their rep account under ${recruiterName(app.recruiter_id)} in the org tree.`)) return
    setBusyId(app.id)
    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${apiBase}/api/careers/${app.id}/stage`, {
        method: 'POST', headers, body: JSON.stringify({ stage }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        alert(err.detail || 'Could not change stage')
        return
      }
      setApps(prev => prev.map(a => a.id === app.id
        ? { ...a, stage, stage_history: [...(a.stage_history || []), { stage, by: rep?.email || '', at: new Date().toISOString() }] }
        : a))
    } catch {
      alert('Network error — please try again')
    } finally {
      setBusyId(null)
    }
  }

  async function assignRecruiter(app: Application, recruiterId: string) {
    if (!recruiterId || recruiterId === app.recruiter_id) return
    setBusyId(app.id)
    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const headers = await getAuthHeaders()
      const resp = await fetch(`${apiBase}/api/careers/${app.id}/assign-recruiter`, {
        method: 'POST', headers, body: JSON.stringify({ recruiter_id: recruiterId }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        alert(err.detail || 'Could not assign recruiter')
        return
      }
      setApps(prev => prev.map(a => a.id === app.id ? { ...a, recruiter_id: recruiterId } : a))
    } catch {
      alert('Network error — please try again')
    } finally {
      setBusyId(null)
    }
  }

  const active = apps.filter(a => a.stage !== 'hired' && a.stage !== 'rejected')

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white">Recruiting</h1>
        <p className="text-sm text-pm-canada-text-muted mt-0.5">
          Applications move applied → screened → interview → offer → hired. A hire lands in the recruiter&apos;s downline.
          {!isAdmin && ' You see your branch only.'}
        </p>
      </div>

      <PortalPage isLoading={loading} error={error} isEmpty={apps.length === 0 && !loading} errorTitle="Could not load recruiting pipeline">
        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-blue/10 flex items-center justify-center"><Briefcase size={16} className="text-pm-blue" /></div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">In Pipeline</p>
                <p className="text-lg font-bold text-white">{active.length}</p>
              </div>
            </div>
          </div>
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-accent/10 flex items-center justify-center"><Users size={16} className="text-pm-accent" /></div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Hired</p>
                <p className="text-lg font-bold text-white">{apps.filter(a => a.stage === 'hired').length}</p>
              </div>
            </div>
          </div>
          <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-pm-amber-gold/10 flex items-center justify-center"><UserPlus size={16} className="text-pm-amber-gold" /></div>
              <div>
                <p className="text-2xs uppercase tracking-wider text-pm-canada-text-muted">Offers Out</p>
                <p className="text-lg font-bold text-white">{apps.filter(a => a.stage === 'offer').length}</p>
              </div>
            </div>
          </div>
        </div>

        {STAGE_ORDER.map(stage => {
          const rows = apps.filter(a => (a.stage || 'applied') === stage)
          if (rows.length === 0) return null
          return (
            <div key={stage} className="space-y-2">
              <div className="flex items-center gap-2">
                <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium border', STAGE_CHIPS[stage])}>
                  {STAGE_LABELS[stage]}
                </span>
                <span className="text-2xs text-pm-canada-text-faint">{rows.length}</span>
              </div>
              {rows.map(app => {
                const posBadge = positionBadge(app.position)
                const terminal = app.stage === 'hired'
                return (
                  <div key={app.id} className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-5 py-3.5">
                    <div className="flex flex-wrap items-center gap-3">
                      <div className="flex-1 min-w-[180px]">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-semibold text-white truncate">{app.name}</p>
                          <span className={clsx('inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium border', posBadge.bg, posBadge.textColor, posBadge.border)}>
                            {positionLabel(app.position)}
                          </span>
                          {app.region && (
                            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium border border-[#C9A24B]/40 bg-[#C9A24B]/10 text-[#C9A24B] capitalize">
                              {app.region} region
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-pm-canada-text-muted mt-0.5">{app.email}{app.city ? ` · ${app.city}` : ''}</p>
                        <p className="text-2xs text-pm-canada-text-faint flex items-center gap-1 mt-0.5">
                          <Clock size={10} /> {(app.created_at || '').slice(0, 10)}
                        </p>
                      </div>
                      <div className="min-w-[140px]">
                        <p className="text-2xs text-pm-canada-text-faint mb-0.5">Recruiter</p>
                        <select
                          value={app.recruiter_id || ''}
                          disabled={busyId === app.id || terminal}
                          onChange={e => assignRecruiter(app, e.target.value)}
                          className="w-full px-2 py-1.5 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-xs text-white focus:outline-none focus:border-pm-accent/50 disabled:opacity-50"
                        >
                          <option value="">{recruiterName(app.recruiter_id)}</option>
                          {team.map(t => (
                            <option key={t.id} value={t.id}>{t.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="min-w-[130px]">
                        <p className="text-2xs text-pm-canada-text-faint mb-0.5">Stage</p>
                        <select
                          value={app.stage}
                          disabled={busyId === app.id || terminal}
                          onChange={e => setStage(app, e.target.value)}
                          className="w-full px-2 py-1.5 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-xs text-white focus:outline-none focus:border-pm-accent/50 disabled:opacity-50"
                        >
                          {STAGE_ORDER.map(s => (
                            <option key={s} value={s}>{STAGE_LABELS[s]}</option>
                          ))}
                        </select>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )
        })}
      </PortalPage>
    </div>
  )
}
