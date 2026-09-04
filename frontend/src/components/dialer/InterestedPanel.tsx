// The rep's warm list — every lead they marked Interested (plus callbacks and
// booked meetings), kept out of the dial flow so nothing warm gets lost in the
// queue. Region chips break the list down by state/province — built for
// vertical campaigns (e.g. golf courses across year-round states) where WHERE
// the interested clients cluster decides where to focus next.
import { useEffect, useMemo, useState } from 'react'
import { ArrowRightCircle, CalendarCheck, Check, ExternalLink, MapPin, Phone, Star } from 'lucide-react'
import { dialerApi, fmtCents, type Disposition, type PhoneLead } from '@/lib/dialer-api'
import { BookingModal } from './BookingModal'

const WARM_DISPOSITIONS: ReadonlySet<Disposition | string> = new Set(['interested', 'callback', 'meeting_booked'])

const BADGE: Record<string, { label: string; cls: string }> = {
  interested: { label: 'Interested', cls: 'bg-pm-accent/10 text-pm-accent' },
  callback: { label: 'Callback', cls: 'bg-pm-amber-orange/10 text-pm-amber-orange' },
  meeting_booked: { label: 'Meeting booked', cls: 'bg-emerald-500/10 text-emerald-400' },
  booked: { label: 'Meeting booked', cls: 'bg-emerald-500/10 text-emerald-400' },
}

function verticalLabel(v: string) {
  return v.replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase())
}

function isWarm(l: PhoneLead) {
  if (l.converted_lead_id) return false
  return l.status === 'booked' || WARM_DISPOSITIONS.has(l.last_disposition ?? '')
}

export function InterestedPanel() {
  const [leads, setLeads] = useState<PhoneLead[] | null>(null)
  const [error, setError] = useState('')
  const [region, setRegion] = useState<string | null>(null)
  const [booking, setBooking] = useState<PhoneLead | null>(null)
  const [promotedIds, setPromotedIds] = useState<Set<string>>(new Set())

  const load = () => dialerApi.listLeads()
    .then(r => setLeads(r.leads.filter(isWarm)))
    .catch(e => setError(e instanceof Error ? e.message : 'Failed to load interested leads'))
  useEffect(() => { load() }, [])

  const regions = useMemo(() => {
    const counts = new Map<string, number>()
    for (const l of leads ?? []) {
      const r = l.province || '—'
      counts.set(r, (counts.get(r) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  }, [leads])

  const visible = useMemo(
    () => (leads ?? []).filter(l => !region || (l.province || '—') === region),
    [leads, region],
  )

  const promote = async (l: PhoneLead) => {
    await dialerApi.promoteLead(l.id)
    setPromotedIds(prev => new Set(prev).add(l.id))
  }

  const confirmBooking = async (spec: { scheduled_at: string; duration_min: number; title: string; notes: string }) => {
    if (!booking) return
    await dialerApi.book({ phone_lead_id: booking.id, ...spec })
    setBooking(null)
    load()
  }

  if (error) {
    return <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-xs text-red-400">{error}</div>
  }

  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-pm-canada-border flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-white flex items-center gap-2">
          <Star size={14} className="text-pm-accent" />Interested clients
        </h2>
        <span className="text-2xs text-pm-canada-text-faint">
          {leads ? `${visible.length}${region ? ` in ${region}` : ''} of ${leads.length}` : 'Loading…'}
        </span>
      </div>

      {/* Region breakdown — where the warm leads cluster */}
      {regions.length > 1 && (
        <div className="px-4 py-2.5 border-b border-pm-canada-border/60 flex items-center gap-1.5 flex-wrap">
          <MapPin size={12} className="text-pm-canada-text-faint shrink-0" />
          <RegionChip label="All" count={leads?.length ?? 0} active={region === null} onClick={() => setRegion(null)} />
          {regions.map(([r, n]) => (
            <RegionChip key={r} label={r} count={n} active={region === r} onClick={() => setRegion(region === r ? null : r)} />
          ))}
        </div>
      )}

      <div className="max-h-[560px] overflow-y-auto divide-y divide-pm-canada-border/60">
        {visible.map(l => (
          <Row
            key={l.id}
            lead={l}
            promoted={promotedIds.has(l.id) || Boolean(l.converted_lead_id)}
            onBook={() => setBooking(l)}
            onPromote={() => promote(l)}
          />
        ))}
        {leads && visible.length === 0 && (
          <div className="px-4 py-10 text-center text-sm text-pm-canada-text-muted">
            No interested clients yet — mark a call &ldquo;Interested&rdquo; and it lands here.
          </div>
        )}
      </div>

      <BookingModal
        open={booking !== null}
        entry={null}
        onCancel={() => setBooking(null)}
        onConfirm={confirmBooking}
      />
    </div>
  )
}

function RegionChip({ label, count, active, onClick }: {
  label: string; count: number; active: boolean; onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-0.5 rounded-full text-2xs font-medium transition-colors ${
        active
          ? 'bg-pm-accent/15 text-pm-accent'
          : 'bg-pm-canada-bg text-pm-canada-text-muted hover:text-white'
      }`}
    >
      {label} <span className="tabular-nums">{count}</span>
    </button>
  )
}

function Row({ lead, promoted, onBook, onPromote }: {
  lead: PhoneLead; promoted: boolean; onBook: () => void; onPromote: () => void
}) {
  const [promoting, setPromoting] = useState(false)
  const badge = BADGE[lead.last_disposition ?? ''] ?? BADGE[lead.status] ?? BADGE.interested
  const place = [lead.city, lead.province].filter(Boolean).join(', ')

  return (
    <div className="px-4 py-3 flex items-start gap-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <p className="text-sm text-white truncate">{lead.business_name || lead.contact_name || lead.phone_e164}</p>
          <span className={`px-2 py-0.5 rounded-full text-2xs font-medium shrink-0 ${badge.cls}`}>{badge.label}</span>
          {lead.vertical && (
            <span className="px-2 py-0.5 rounded-full bg-pm-canada-bg text-pm-canada-text-muted text-2xs shrink-0">
              {verticalLabel(lead.vertical)}
            </span>
          )}
        </div>
        <p className="text-2xs text-pm-canada-text-faint mt-0.5 flex items-center gap-1.5 flex-wrap">
          {place && <span>{place}</span>}
          <a href={`tel:${lead.phone_e164}`} className="inline-flex items-center gap-0.5 hover:text-pm-accent">
            <Phone size={10} />{lead.phone_e164}
          </a>
          {lead.website && (
            <a
              href={lead.website.startsWith('http') ? lead.website : `https://${lead.website}`}
              target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-0.5 hover:text-pm-accent"
            >
              <ExternalLink size={10} />site
            </a>
          )}
          {lead.est_monthly_value > 0 && <span>· {fmtCents(lead.est_monthly_value)}</span>}
          <span>· {lead.attempts} call{lead.attempts === 1 ? '' : 's'}</span>
        </p>
        {lead.notes && <p className="text-2xs text-pm-canada-text-muted mt-1 line-clamp-2">{lead.notes}</p>}
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        <button
          onClick={onBook}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-pm-canada-border text-2xs font-medium text-pm-canada-text-muted hover:text-pm-accent hover:border-pm-accent/40 transition-colors"
        >
          <CalendarCheck size={12} />Book
        </button>
        <button
          onClick={async () => { setPromoting(true); try { await onPromote() } finally { setPromoting(false) } }}
          disabled={promoting || promoted}
          className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border text-2xs font-medium transition-colors ${
            promoted
              ? 'border-emerald-500/30 text-emerald-400'
              : 'border-pm-canada-border text-pm-canada-text-muted hover:text-pm-accent hover:border-pm-accent/40'
          }`}
        >
          {promoted ? <Check size={12} /> : <ArrowRightCircle size={12} />}
          {promoted ? 'In pipeline' : 'Pipeline'}
        </button>
      </div>
    </div>
  )
}
