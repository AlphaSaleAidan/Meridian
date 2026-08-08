import { useCallback, useEffect, useMemo, useState } from 'react'
import { clsx } from 'clsx'
import { Globe, ExternalLink, Clock, Check, Send, Zap, Wrench } from 'lucide-react'
import { useIsDemo, useOrgId } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import ScrollReveal from '@/components/ScrollReveal'
import {
  SITE_REQUEST_TYPES, RUSH_TURNAROUND, STATUS_LABELS,
  requestType, type SiteChangeRequest, type SiteRequestKind, type SiteRequestStatus,
} from '@/config/site-care'

interface ManagedSite {
  name: string
  domain: string
  live: boolean
  liveSince: string
}

/**
 * Site Care — the surface a merchant whose website Meridian built uses to
 * manage it and raise paid change requests.
 *
 * Requests are held client-side for now: there is no /api/website/requests
 * endpoint yet, and no charge is taken. There is deliberately no published
 * rate card — scope varies too much to price up front, so the surface commits
 * to a turnaround and quotes the cost before any work starts.
 */
export default function SiteCarePage() {
  const isDemo = useIsDemo()
  const orgId = useOrgId()
  const { org } = useAuth()

  // Only the demo has a site to manage today. A real merchant sees the
  // not-enrolled state rather than an invented site.
  const site: ManagedSite | null = useMemo(() => {
    if (!isDemo) return null
    return {
      name: org?.business_name || 'Your business',
      domain: 'maple-tandoor.ca',
      live: true,
      liveSince: 'March 2026',
    }
  }, [isDemo, org?.business_name])

  const storageKey = `meridian_site_requests_${orgId || 'anon'}`
  const [requests, setRequests] = useState<SiteChangeRequest[]>([])
  const [kind, setKind] = useState<SiteRequestKind>('content')
  const [details, setDetails] = useState('')
  const [rush, setRush] = useState(false)
  const [justSent, setJustSent] = useState(false)

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey)
      if (raw) { setRequests(JSON.parse(raw)); return }
    } catch { /* unreadable storage — start clean */ }
    setRequests(isDemo ? seedRequests() : [])
  }, [storageKey, isDemo])

  const persist = useCallback((next: SiteChangeRequest[]) => {
    setRequests(next)
    try { localStorage.setItem(storageKey, JSON.stringify(next)) } catch { /* quota — in-memory only */ }
  }, [storageKey])

  const submit = () => {
    if (!details.trim()) return
    const next: SiteChangeRequest = {
      id: `req_${requests.length + 1}_${details.length}`,
      kind,
      details: details.trim(),
      rush,
      status: 'submitted',
      submittedAt: new Date().toISOString(),
    }
    persist([next, ...requests])
    setDetails('')
    setRush(false)
    setJustSent(true)
    window.setTimeout(() => setJustSent(false), 4000)
  }

  if (!site) return <NotEnrolled />

  const openCount = requests.filter(r => r.status !== 'complete').length

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">My Website</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Manage the site we built you and request changes whenever you need them.
          </p>
        </div>
      </ScrollReveal>

      {/* Site card */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="card p-5">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-11 h-11 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
                <Globe size={19} className="text-[#1A8FD6]" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-semibold text-[#F5F5F7] truncate">{site.domain}</p>
                  {site.live && (
                    <span className="px-1.5 py-0.5 rounded-full bg-[#17C5B0]/10 text-[#17C5B0] text-[9px] font-bold uppercase tracking-wider border border-[#17C5B0]/25">
                      Live
                    </span>
                  )}
                </div>
                <p className="text-xs text-[#A1A1A8] mt-0.5">Built by Meridian · live since {site.liveSince}</p>
              </div>
            </div>
            <a
              href={`https://${site.domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-[#A1A1A8] bg-[#111113] border border-[#1F1F23] rounded-lg hover:border-[#1A8FD6]/40 hover:text-[#F5F5F7] transition-all flex-shrink-0"
            >
              Visit site <ExternalLink size={12} />
            </a>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-5 pt-5 border-t border-[#1F1F23]">
            <Stat label="Open requests" value={String(openCount)} />
            <Stat label="Total requests" value={String(requests.length)} />
            <Stat label="Typical turnaround" value="1–3 days" />
          </div>
        </div>
      </ScrollReveal>

      {/* Request a change */}
      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Request a change</h2>
          <p className="text-xs text-[#A1A1A8] mt-1">
            Tell us what you need. We confirm the final price before starting — you're never charged automatically.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 mt-4">
            {SITE_REQUEST_TYPES.map(t => (
              <button
                key={t.kind}
                onClick={() => setKind(t.kind)}
                aria-pressed={kind === t.kind}
                className={clsx(
                  'text-left rounded-xl border px-3.5 py-3 transition-all',
                  kind === t.kind
                    ? 'border-[#1A8FD6]/50 bg-[#1A8FD6]/[0.07]'
                    : 'border-[#1F1F23] bg-[#111113] hover:border-[#1A8FD6]/25',
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] font-medium text-[#F5F5F7]">{t.label}</span>
                  <span className="text-[11px] text-[#A1A1A8]/70 flex-shrink-0">
                    Quoted
                  </span>
                </div>
                <p className="text-[11px] leading-relaxed text-[#A1A1A8] mt-1">{t.description}</p>
                <p className="text-[10px] text-[#A1A1A8]/55 mt-1.5 flex items-center gap-1">
                  <Clock size={9} /> {t.turnaround}
                </p>
              </button>
            ))}
          </div>

          <label htmlFor="site-request-details" className="block text-xs font-medium text-[#A1A1A8] mt-5 mb-1.5">
            What would you like changed?
          </label>
          <textarea
            id="site-request-details"
            value={details}
            onChange={e => setDetails(e.target.value)}
            rows={4}
            placeholder="Be as specific as you like — page, section, and the exact wording or images if you have them."
            className="w-full px-3.5 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-xl text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 resize-y"
          />

          <button
            onClick={() => setRush(r => !r)}
            aria-pressed={rush}
            className={clsx(
              'flex items-center gap-2 mt-3 px-3 py-2 rounded-lg border text-xs font-medium transition-all',
              rush
                ? 'border-[#1A8FD6]/50 bg-[#1A8FD6]/[0.07] text-[#F5F5F7]'
                : 'border-[#1F1F23] bg-[#111113] text-[#A1A1A8] hover:text-[#F5F5F7]',
            )}
          >
            <Zap size={13} className={rush ? 'text-[#1A8FD6]' : ''} />
            Rush it — {RUSH_TURNAROUND}
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mt-5 pt-4 border-t border-[#1F1F23]">
            <div>
              <p className="text-[10px] uppercase tracking-wider text-[#A1A1A8]/60">Cost</p>
              <p className="text-base font-semibold text-[#F5F5F7] mt-0.5">
                Quoted before we start
              </p>
              <p className="text-[10px] text-[#A1A1A8]/55 mt-0.5">
                We price each request against its scope and confirm in writing.
                Nothing is charged until you approve it.
              </p>
            </div>
            <button
              onClick={submit}
              disabled={!details.trim()}
              className="flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-35 disabled:cursor-not-allowed"
            >
              {justSent ? <><Check size={14} /> Request sent</> : <><Send size={14} /> Send request</>}
            </button>
          </div>
          {justSent && (
            <p className="text-xs text-[#17C5B0] mt-3">
              Thanks — we'll confirm scope and price by email, usually within one business day.
            </p>
          )}
        </div>
      </ScrollReveal>

      {/* History */}
      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card overflow-hidden">
          <div className="px-5 py-4 border-b border-[#1F1F23]">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Your requests</h2>
          </div>
          {requests.length === 0 ? (
            <p className="px-5 py-8 text-sm text-[#A1A1A8] text-center">
              No change requests yet. Anything you send will show up here with its status.
            </p>
          ) : (
            <ul className="divide-y divide-[#1F1F23]">
              {requests.map(r => (
                <li key={r.id} className="px-5 py-4 flex items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[13px] font-medium text-[#F5F5F7]">{requestType(r.kind).label}</span>
                      <StatusChip status={r.status} />
                      {r.rush && (
                        <span className="text-[9px] font-bold uppercase tracking-wider text-[#1A8FD6]">Rush</span>
                      )}
                    </div>
                    <p className="text-xs text-[#A1A1A8] mt-1 line-clamp-2">{r.details}</p>
                    <p className="text-[10px] text-[#A1A1A8]/50 mt-1.5">
                      {new Date(r.submittedAt).toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </ScrollReveal>
    </div>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-[#A1A1A8]/60">{label}</p>
      <p className="text-base font-bold text-[#F5F5F7] font-mono mt-0.5">{value}</p>
    </div>
  )
}

const STATUS_STYLES: Record<SiteRequestStatus, string> = {
  submitted: 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/25',
  in_review: 'bg-[#A1A1A8]/10 text-[#A1A1A8] border-[#A1A1A8]/25',
  in_progress: 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/25',
  complete: 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/25',
}

function StatusChip({ status }: { status: SiteRequestStatus }) {
  return (
    <span className={clsx(
      'px-1.5 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider border',
      STATUS_STYLES[status],
    )}>
      {STATUS_LABELS[status]}
    </span>
  )
}

/** Shown to a merchant whose site we did not build. */
function NotEnrolled() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[#F5F5F7]">My Website</h1>
        <p className="text-sm text-[#A1A1A8] mt-1">Managed websites, built and maintained by Meridian.</p>
      </div>
      <div className="card p-8 text-center">
        <div className="w-14 h-14 rounded-2xl bg-[#1A8FD6]/10 flex items-center justify-center mx-auto mb-4">
          <Wrench size={24} className="text-[#1A8FD6]" />
        </div>
        <h2 className="text-lg font-semibold text-[#F5F5F7]">No managed site yet</h2>
        <p className="text-sm text-[#A1A1A8] mt-2 max-w-md mx-auto leading-relaxed">
          Once Meridian builds your website, this is where you manage it — request copy changes,
          new pages, photo swaps or menu updates, and track each one through to done.
        </p>
        <p className="text-xs text-[#A1A1A8]/60 mt-4">Talk to your rep to get started.</p>
      </div>
    </div>
  )
}

/**
 * Demo-only history so the surface shows its full lifecycle. Never rendered
 * for a real merchant — see the `isDemo` guard at the call site.
 */
function seedRequests(): SiteChangeRequest[] {
  return [
    {
      id: 'seed_3',
      kind: 'menu',
      details: 'Add the new fall tasting menu under Dinner, and take down the summer patio specials.',
      rush: false,
      status: 'in_progress',
      submittedAt: '2026-08-04T15:20:00.000Z',
    },
    {
      id: 'seed_2',
      kind: 'media',
      details: 'Swap the hero photo for the new interior shots from the weekend shoot.',
      rush: true,
      status: 'complete',
      submittedAt: '2026-07-22T09:05:00.000Z',
    },
    {
      id: 'seed_1',
      kind: 'content',
      details: 'Update holiday hours — closed Aug 4, opening at 4pm on long weekends.',
      rush: false,
      status: 'complete',
      submittedAt: '2026-07-09T11:40:00.000Z',
    },
  ]
}
