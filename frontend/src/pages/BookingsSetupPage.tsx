/**
 * Booking setup — what we can hold, when we're open, and what else to talk to.
 *
 * The integrations section deliberately shows the tools we CANNOT connect to
 * alongside the ones we can, with the reason and the workaround. A merchant on
 * Booksy who sees nothing about Booksy assumes we haven't got round to it and
 * asks their rep; a merchant who reads "Booksy publishes no API — connect your
 * Google Calendar instead" can act on it in the same minute.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  AlertCircle, Armchair, Calendar, Check, Copy, ExternalLink, Info, Link2,
  MessageSquare, Plus, Trash2,
} from 'lucide-react'
import { Select } from '@/components/ui/Select'
import BookingsWizard from '@/pages/BookingsWizard'
import { useOrgId } from '@/hooks/useOrg'
import {
  bookingsApi,
  type AvailableProvider, type BookingLink, type Connection, type HoursRow,
  type Resource, type ResourceKind, type Service, type SquareOptions,
  type UnavailableTool,
} from '@/lib/bookings-api'

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

const KIND_LABEL: Record<ResourceKind, string> = {
  table: 'Table',
  chair: 'Chair',
  staff: 'Staff member',
  bay: 'Bay',
  room: 'Room',
}

export default function BookingsSetupPage() {
  const merchantId = useOrgId()
  const [resources, setResources] = useState<Resource[]>([])
  const [services, setServices] = useState<Service[]>([])
  const [hours, setHours] = useState<HoursRow[]>([])
  const [connections, setConnections] = useState<Connection[]>([])
  const [available, setAvailable] = useState<AvailableProvider[]>([])
  const [unavailable, setUnavailable] = useState<UnavailableTool[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  /** Set once the wizard is finished or skipped, so the forms take over. */
  const [manual, setManual] = useState(false)

  const load = useCallback(async () => {
    if (!merchantId) return
    setLoading(true)
    try {
      const [r, s, h, i] = await Promise.all([
        bookingsApi.listResources(merchantId),
        bookingsApi.listServices(merchantId),
        bookingsApi.listHours(merchantId),
        bookingsApi.integrations(merchantId),
      ])
      setResources(r)
      setServices(s)
      setHours(h)
      setConnections(i.connections)
      setAvailable(i.available)
      setUnavailable(i.unavailable)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load booking setup')
    } finally {
      setLoading(false)
    }
  }, [merchantId])

  useEffect(() => { load() }, [load])

  if (loading) {
    return (
      <div className="space-y-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-32 animate-pulse rounded-lg border border-[#1F1F23] bg-[#111113]" />
        ))}
      </div>
    )
  }

  // A merchant who has never set anything up gets asked questions, not shown
  // four empty forms. Configured merchants never see this — the wizard is for
  // the first five minutes, and `manual` is the way out of it at any point.
  const unconfigured = resources.length === 0 && services.length === 0
  if (unconfigured && !manual) {
    return (
      <BookingsWizard
        merchantId={merchantId}
        onDone={() => { setManual(true); load() }}
        onSkip={() => setManual(true)}
      />
    )
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-[#F5F5F7]">
          Booking setup
        </h1>
        <p className="mt-0.5 text-sm text-[#A1A1A8]">
          Tell us what you can hold and when you're open. The phone agent will
          only ever offer times that fit.
        </p>
      </header>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-[#E5484D]/30 bg-[#E5484D]/10 px-3 py-2.5 text-sm text-[#E5484D]">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* First, because it is the fastest thing a merchant can switch on:
          it needs one URL and no resources, services or hours at all. */}
      <BookingLinkCard merchantId={merchantId} />

      <ResourcesCard
        merchantId={merchantId}
        resources={resources}
        onChanged={load}
      />
      <ServicesCard
        merchantId={merchantId}
        services={services}
        onChanged={load}
      />
      <HoursCard merchantId={merchantId} hours={hours} onChanged={load} />
      <IntegrationsCard
        merchantId={merchantId}
        connections={connections}
        available={available}
        unavailable={unavailable}
        onChanged={load}
      />
    </div>
  )
}

function Card({ title, subtitle, icon: Icon, children }: {
  title: string
  subtitle?: string
  icon: typeof Armchair
  children: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
      <div className="mb-4 flex items-start gap-3">
        <Icon className="mt-0.5 h-4 w-4 shrink-0 text-[#1A8FD6]" />
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">{title}</h2>
          {subtitle && (
            <p className="mt-0.5 text-sm text-[#A1A1A8]">{subtitle}</p>
          )}
        </div>
      </div>
      {children}
    </section>
  )
}

function BookingLinkCard({ merchantId }: { merchantId: string }) {
  const [link, setLink] = useState<BookingLink | null>(null)
  const [url, setUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!merchantId) return
    try {
      const l = await bookingsApi.bookingLink(merchantId)
      setLink(l)
      setUrl(l.url)
    } catch {
      /* The rest of the page is still usable without this card. */
    }
  }, [merchantId])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setBusy(true)
    setError('')
    try {
      await bookingsApi.saveBookingLink(merchantId, url.trim())
      setSaved(true)
      await load()
      window.setTimeout(() => setSaved(false), 2000)
    } catch {
      setError('That does not look like a web address.')
    } finally {
      setBusy(false)
    }
  }

  const on = !!link?.url
  // Rounded to whole percent: a merchant reading "71%" and a merchant reading
  // "70.6%" make the same decision, and the second one looks like a lie.
  const openRate = link && link.sent > 0
    ? Math.round((link.opened / link.sent) * 100)
    : null

  return (
    <Card
      title="If you already take bookings on your own website"
      subtitle="We text the caller your booking link instead of reading the address out loud. Leave this empty if you'd rather we took the booking ourselves."
      icon={MessageSquare}
    >
      <div className="flex flex-wrap items-end gap-2">
        <div className="min-w-[16rem] flex-1 space-y-1">
          <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">
            Your booking page
          </span>
          <input
            value={url}
            onChange={(e) => { setUrl(e.target.value); setSaved(false) }}
            placeholder="mapletandoor.ca/reservations"
            className="w-full rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
          />
        </div>
        <button
          onClick={save}
          disabled={busy || url.trim() === (link?.url || '')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-3 py-2 text-sm text-[#F5F5F7] transition-colors hover:border-[#1A8FD6]/40 disabled:opacity-40"
        >
          {saved ? <Check className="h-4 w-4 text-[#17C5B0]" /> : null}
          {saved ? 'Saved' : 'Save'}
        </button>
      </div>

      {error && <p className="mt-2 text-xs text-[#E5484D]">{error}</p>}

      {link?.inherited && (
        <p className="mt-2 flex items-start gap-1.5 text-xs text-[#A1A1A8]">
          <Info className="mt-px h-3.5 w-3.5 shrink-0" />
          This came from your setup questionnaire. Save it here to confirm it,
          or change it.
        </p>
      )}

      {on && (
        <div className="mt-4 rounded-lg border border-[#1F1F23] bg-[#0E0E11] p-3">
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
            <span className="text-sm text-[#F5F5F7]">
              <span className="font-semibold">{link.sent}</span>{' '}
              <span className="text-[#A1A1A8]">texted</span>
            </span>
            <span className="text-sm text-[#F5F5F7]">
              <span className="font-semibold text-[#17C5B0]">{link.opened}</span>{' '}
              <span className="text-[#A1A1A8]">opened</span>
              {openRate !== null && (
                <span className="text-[#A1A1A8]"> · {openRate}%</span>
              )}
            </span>
            {link.failed > 0 && (
              <span className="text-sm text-[#A1A1A8]">
                {link.failed} couldn't be delivered — usually a landline
              </span>
            )}
          </div>
          <p className="mt-2 text-xs text-[#A1A1A8]">
            {link.sent === 0
              ? 'Nothing texted yet. The next caller who asks about booking gets the link.'
              : 'Opens are the only evidence you get that the agent produced a booking — the booking itself lands in your own system under the customer’s name.'}
          </p>
        </div>
      )}

      {on && (
        <a
          href={link.url}
          target="_blank"
          rel="noreferrer noopener"
          className="mt-3 inline-flex items-center gap-1.5 text-xs text-[#1A8FD6] hover:underline"
        >
          <ExternalLink className="h-3.5 w-3.5" />
          Open the page callers land on
        </a>
      )}
    </Card>
  )
}

function ResourcesCard({ merchantId, resources, onChanged }: {
  merchantId: string
  resources: Resource[]
  onChanged: () => void
}) {
  const [name, setName] = useState('')
  const [kind, setKind] = useState<ResourceKind>('table')
  const [seats, setSeats] = useState(2)
  const [busy, setBusy] = useState(false)

  const add = async () => {
    if (!name.trim()) return
    setBusy(true)
    try {
      await bookingsApi.createResource({
        merchantId, name: name.trim(), kind,
        seats: kind === 'table' || kind === 'room' ? seats : 1,
      })
      setName('')
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="What can be booked"
      subtitle="A table, a chair, a bay, a person — anything that can hold one booking at a time. Two bookings can never land on the same one."
      icon={Armchair}
    >
      {resources.length > 0 && (
        <ul className="mb-4 divide-y divide-[#1F1F23] rounded-lg border border-[#1F1F23]">
          {resources.map((r) => (
            <li key={r.id} className="flex items-center justify-between px-3 py-2.5">
              <div className="min-w-0">
                <span className="text-sm text-[#F5F5F7]">{r.name}</span>
                <span className="ml-2 text-xs text-[#A1A1A8]">
                  {KIND_LABEL[r.kind]}
                  {r.seats > 1 ? ` · seats ${r.seats}` : ''}
                </span>
              </div>
              <button
                onClick={async () => {
                  await bookingsApi.updateResource(r.id, { active: false })
                  onChanged()
                }}
                aria-label={`Remove ${r.name}`}
                className="p-1 text-[#A1A1A8] transition-colors hover:text-[#E5484D]"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <label className="flex-1 min-w-[10rem] space-y-1">
          <span className="text-xs uppercase tracking-wide text-[#A1A1A8]">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Table 4"
            className="w-full rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
          />
        </label>
        <div className="w-36 space-y-1">
          <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">Type</span>
          <Select
            ariaLabel="Type of thing being booked"
            value={kind}
            onChange={(v) => setKind(v as ResourceKind)}
            options={Object.entries(KIND_LABEL).map(([k, label]) => ({
              value: k, label,
            }))}
          />
        </div>
        {(kind === 'table' || kind === 'room') && (
          <label className="space-y-1">
            <span className="text-xs uppercase tracking-wide text-[#A1A1A8]">Seats</span>
            <input
              type="number"
              min={1}
              max={100}
              value={seats}
              onChange={(e) => setSeats(Math.max(1, Number(e.target.value) || 1))}
              className="w-20 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
            />
          </label>
        )}
        <button
          onClick={add}
          disabled={busy || !name.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-[#1A8FD6] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1A8FD6]/90 disabled:opacity-40"
        >
          <Plus className="h-4 w-4" />
          Add
        </button>
      </div>
    </Card>
  )
}

function ServicesCard({ merchantId, services, onChanged }: {
  merchantId: string
  services: Service[]
  onChanged: () => void
}) {
  const [name, setName] = useState('')
  const [duration, setDuration] = useState(30)
  const [maxParty, setMaxParty] = useState(1)
  const [busy, setBusy] = useState(false)

  const add = async () => {
    if (!name.trim()) return
    setBusy(true)
    try {
      await bookingsApi.createService({
        merchantId, name: name.trim(),
        durationMinutes: duration, minParty: 1, maxParty,
      })
      setName('')
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="How long a booking takes"
      subtitle="For a salon or a detailer this is your service list. For a restaurant, add one line per party size — “Table for 1–4, 90 minutes” — and we'll pick the right one."
      icon={Calendar}
    >
      {services.length > 0 && (
        <ul className="mb-4 divide-y divide-[#1F1F23] rounded-lg border border-[#1F1F23]">
          {services.map((s) => (
            <li key={s.id} className="px-3 py-2.5">
              <span className="text-sm text-[#F5F5F7]">{s.name}</span>
              <span className="ml-2 text-xs text-[#A1A1A8]">
                {s.durationMinutes} min
                {s.bufferMinutes ? ` + ${s.bufferMinutes} min turnaround` : ''}
                {s.maxParty > 1 ? ` · parties ${s.minParty}–${s.maxParty}` : ''}
              </span>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-end gap-2">
        <label className="min-w-[10rem] flex-1 space-y-1">
          <span className="text-xs uppercase tracking-wide text-[#A1A1A8]">Name</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Haircut"
            className="w-full rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs uppercase tracking-wide text-[#A1A1A8]">Minutes</span>
          <input
            type="number"
            min={5}
            max={1440}
            step={5}
            value={duration}
            onChange={(e) => setDuration(Math.max(5, Number(e.target.value) || 30))}
            className="w-24 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
          />
        </label>
        <label className="space-y-1">
          <span className="text-xs uppercase tracking-wide text-[#A1A1A8]">Max party</span>
          <input
            type="number"
            min={1}
            max={100}
            value={maxParty}
            onChange={(e) => setMaxParty(Math.max(1, Number(e.target.value) || 1))}
            className="w-24 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
          />
        </label>
        <button
          onClick={add}
          disabled={busy || !name.trim()}
          className="inline-flex items-center gap-1.5 rounded-lg bg-[#1A8FD6] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1A8FD6]/90 disabled:opacity-40"
        >
          <Plus className="h-4 w-4" />
          Add
        </button>
      </div>
    </Card>
  )
}

function HoursCard({ merchantId, hours, onChanged }: {
  merchantId: string
  hours: HoursRow[]
  onChanged: () => void
}) {
  const [rows, setRows] = useState<Record<number, HoursRow | null>>(() => {
    const map: Record<number, HoursRow | null> = {}
    for (let d = 0; d < 7; d++) map[d] = hours.find((h) => h.weekday === d) || null
    return map
  })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  const set = (d: number, patch: Partial<HoursRow> | null) => {
    setSaved(false)
    setRows((prev) => ({
      ...prev,
      [d]: patch === null
        ? null
        : { weekday: d, opensAt: '09:00', closesAt: '17:00', slotMinutes: 15,
            ...(prev[d] || {}), ...patch },
    }))
  }

  const save = async () => {
    setSaving(true)
    try {
      await bookingsApi.replaceHours(
        merchantId,
        Object.values(rows).filter(Boolean) as HoursRow[],
      )
      setSaved(true)
      onChanged()
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card
      title="When you take bookings"
      subtitle="Bookings can start any time inside these hours, and must finish before you close."
      icon={Calendar}
    >
      <div className="space-y-1.5">
        {DAYS.map((label, d) => {
          const row = rows[d]
          return (
            <div key={d} className="flex flex-wrap items-center gap-2">
              <label className="flex w-32 shrink-0 items-center gap-2">
                <input
                  type="checkbox"
                  checked={!!row}
                  onChange={(e) => set(d, e.target.checked ? {} : null)}
                  className="accent-[#1A8FD6]"
                />
                <span className="text-sm text-[#F5F5F7]">{label}</span>
              </label>
              {row ? (
                <>
                  <input
                    type="time"
                    value={row.opensAt}
                    onChange={(e) => set(d, { opensAt: e.target.value })}
                    className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-2 py-1.5 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                  />
                  <span className="text-xs text-[#A1A1A8]">to</span>
                  <input
                    type="time"
                    value={row.closesAt}
                    onChange={(e) => set(d, { closesAt: e.target.value })}
                    className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-2 py-1.5 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
                  />
                </>
              ) : (
                <span className="text-sm text-[#A1A1A8]">Closed</span>
              )}
            </div>
          )
        })}
      </div>

      <p className="mt-3 flex items-start gap-1.5 text-xs text-[#A1A1A8]">
        <Info className="mt-0.5 h-3 w-3 shrink-0" />
        Open past midnight? Add the late hours to the following day — a 1 AM
        booking belongs to that day.
      </p>

      <button
        onClick={save}
        disabled={saving}
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-[#1A8FD6] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1A8FD6]/90 disabled:opacity-40"
      >
        {saved ? <Check className="h-4 w-4" /> : null}
        {saving ? 'Saving…' : saved ? 'Saved' : 'Save hours'}
      </button>
    </Card>
  )
}

function SquarePanel({ merchantId, connections, onChanged }: {
  merchantId: string
  connections: Connection[]
  onChanged: () => void
}) {
  const connected = connections.find((c) => c.provider === 'square_appointments')
  const [opts, setOpts] = useState<SquareOptions | null>(null)
  const [busy, setBusy] = useState(false)
  const [service, setService] = useState('')
  const [member, setMember] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!connected) return
    bookingsApi.squareOptions(merchantId).then((o) => {
      setOpts(o)
      setService(o.defaultService?.serviceVariationId || o.services[0]?.serviceVariationId || '')
      setMember(o.defaultService?.teamMemberId || o.teamMembers[0]?.teamMemberId || '')
    }).catch(() => setOpts(null))
  }, [connected, merchantId])

  const connect = async () => {
    setBusy(true)
    try {
      const url = await bookingsApi.squareAuthorizeUrl(
        merchantId, window.location.pathname + window.location.search)
      window.location.href = url
    } finally {
      setBusy(false)
    }
  }

  const saveMapping = async () => {
    const chosen = opts?.services.find((s) => s.serviceVariationId === service)
    if (!chosen || !member) return
    setBusy(true)
    try {
      await bookingsApi.saveSquareMapping(merchantId, {
        serviceVariationId: chosen.serviceVariationId,
        serviceVariationVersion: chosen.serviceVariationVersion,
        teamMemberId: member,
      })
      setSaved(true)
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  if (!connected) {
    return (
      <div className="mb-4 rounded-lg border border-[#1F1F23] p-3.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-[#F5F5F7]">Square Appointments</p>
            <p className="mt-0.5 text-xs text-[#A1A1A8]">
              The phone agent books straight into Square, so your staff see it in
              the app they already use.
            </p>
          </div>
          <button
            onClick={connect}
            disabled={busy}
            className="shrink-0 rounded-lg bg-[#1A8FD6] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-[#1A8FD6]/90 disabled:opacity-40"
          >
            {busy ? 'Opening…' : 'Connect Square'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mb-4 rounded-lg border border-[#1F1F23] p-3.5 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-medium text-[#F5F5F7]">Square Appointments</p>
        <span className="rounded border border-[#17C5B0]/30 bg-[#17C5B0]/10 px-2 py-0.5 text-[11px] text-[#17C5B0]">
          Connected
        </span>
      </div>

      {opts && !opts.bookingEnabled && (
        <p className="flex items-start gap-1.5 text-xs text-[#D9A441]">
          <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
          Online booking is switched off in your Square account, so we can't book
          into it yet. Turn it on in Square, then hit refresh below.
        </p>
      )}

      {opts && (
        <p className="text-xs text-[#A1A1A8]">
          {opts.accessLevel === 'seller'
            ? 'Full access — we can also see bookings you take elsewhere in Square, so we never double-book.'
            : "We can check your availability and add bookings. Reading bookings you take elsewhere needs Square's Appointments Plus or Premium plan — everything else works today."}
        </p>
      )}

      {opts && opts.services.length > 0 && (
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-[9rem] flex-1 space-y-1">
            <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">
              Book this service
            </span>
            <Select
              ariaLabel="Square service to book"
              value={service}
              onChange={(v) => { setService(v); setSaved(false) }}
              options={opts.services.map((s) => ({
                value: s.serviceVariationId,
                label: s.name,
                hint: s.durationMinutes ? `${s.durationMinutes} min` : undefined,
              }))}
            />
          </div>
          <div className="min-w-[8rem] flex-1 space-y-1">
            <span className="block text-xs uppercase tracking-wide text-[#A1A1A8]">With</span>
            <Select
              ariaLabel="Staff member the booking is assigned to"
              value={member}
              onChange={(v) => { setMember(v); setSaved(false) }}
              options={opts.teamMembers.filter((t) => t.isBookable).map((t) => ({
                value: t.teamMemberId,
                label: t.displayName || t.teamMemberId,
              }))}
            />
          </div>
          <button
            onClick={saveMapping}
            disabled={busy || !service || !member}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-3 py-2 text-sm text-[#F5F5F7] transition-colors hover:border-[#1A8FD6]/40 disabled:opacity-40"
          >
            {saved ? <Check className="h-4 w-4" /> : null}
            {saved ? 'Saved' : 'Save'}
          </button>
        </div>
      )}

      <button
        onClick={async () => { await bookingsApi.refreshSquare(merchantId); onChanged() }}
        className="text-xs text-[#A1A1A8] underline-offset-2 transition-colors hover:text-[#F5F5F7] hover:underline"
      >
        Re-read my Square services and staff
      </button>
    </div>
  )
}

function IntegrationsCard({
  merchantId, connections, available, unavailable, onChanged,
}: {
  merchantId: string
  connections: Connection[]
  available: AvailableProvider[]
  unavailable: UnavailableTool[]
  onChanged: () => void
}) {
  const [feedUrl, setFeedUrl] = useState('')
  const [icsUrl, setIcsUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState('')

  const otherConnections = connections.filter((c) => c.provider !== 'square_appointments')

  const connectIcs = async () => {
    if (!icsUrl.trim()) return
    setBusy(true)
    setError('')
    try {
      const r = await bookingsApi.connectIcsFeed(merchantId, icsUrl.trim())
      if (!r.sync?.ok) {
        setError(r.sync?.error || 'Connected, but we could not read that feed yet.')
      }
      setIcsUrl('')
      onChanged()
    } catch {
      setError('That feed could not be reached. Check the link and try again.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card
      title="Works with what you already use"
      subtitle="Connect your existing calendar so the phone agent never books over something you've already committed to."
      icon={Link2}
    >
      {/* Square is deliberately excluded: SquarePanel below renders its own
          status row with the service mapping, so listing it here too showed
          the merchant "Square Appointments — Connected" twice in a row. */}
      {otherConnections.length > 0 && (
        <ul className="mb-4 divide-y divide-[#1F1F23] rounded-lg border border-[#1F1F23]">
          {otherConnections.map((c) => (
            <li key={c.id} className="flex items-center justify-between px-3 py-2.5">
              <div className="min-w-0">
                <span className="text-sm text-[#F5F5F7]">
                  {available.find((a) => a.key === c.provider)?.label || c.provider}
                </span>
                {c.lastError && (
                  <p className="mt-0.5 text-xs text-[#E5484D]">{c.lastError}</p>
                )}
              </div>
              <span
                className={`rounded border px-2 py-0.5 text-[11px] ${
                  c.status === 'connected'
                    ? 'border-[#17C5B0]/30 bg-[#17C5B0]/10 text-[#17C5B0]'
                    : 'border-[#E5484D]/30 bg-[#E5484D]/10 text-[#E5484D]'
                }`}
              >
                {c.status === 'connected' ? 'Connected' : 'Needs attention'}
              </span>
            </li>
          ))}
        </ul>
      )}

      {available.some((a) => a.key === 'square_appointments') && (
        <SquarePanel merchantId={merchantId} connections={connections} onChanged={onChanged} />
      )}

      <div className="space-y-2">
        <label className="block text-xs uppercase tracking-wide text-[#A1A1A8]">
          Paste a calendar link (.ics)
        </label>
        <div className="flex flex-wrap gap-2">
          <input
            value={icsUrl}
            onChange={(e) => setIcsUrl(e.target.value)}
            placeholder="https://calendar.google.com/…/basic.ics"
            className="min-w-[14rem] flex-1 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
          />
          <button
            onClick={connectIcs}
            disabled={busy || !icsUrl.trim()}
            className="rounded-lg border border-[#1F1F23] px-3 py-2 text-sm text-[#F5F5F7] transition-colors hover:border-[#1A8FD6]/40 disabled:opacity-40"
          >
            {busy ? 'Checking…' : 'Connect'}
          </button>
        </div>
        <p className="text-xs text-[#A1A1A8]">
          Read-only. We block out the times on it and never write to it.
        </p>
        {error && (
          <p className="flex items-start gap-1.5 text-xs text-[#E5484D]">
            <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
            {error}
          </p>
        )}
      </div>

      <div className="mt-5 border-t border-[#1F1F23] pt-4">
        <p className="text-sm font-medium text-[#F5F5F7]">
          See bookings in your own calendar
        </p>
        <p className="mt-0.5 text-xs text-[#A1A1A8]">
          Get a private link and subscribe to it in Google, Outlook or Apple
          Calendar. Your calendar decides how often it refreshes — usually a few
          hours, so treat this page as the live view.
        </p>
        {feedUrl ? (
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <code className="min-w-0 flex-1 truncate rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-xs text-[#A1A1A8]">
              {feedUrl}
            </code>
            <button
              onClick={() => {
                navigator.clipboard?.writeText(feedUrl)
                setCopied(true)
                setTimeout(() => setCopied(false), 1500)
              }}
              className="inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-3 py-2 text-sm text-[#F5F5F7] transition-colors hover:border-[#1A8FD6]/40"
            >
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        ) : (
          <button
            onClick={async () => setFeedUrl(await bookingsApi.enableFeed(merchantId))}
            className="mt-2 rounded-lg border border-[#1F1F23] px-3 py-2 text-sm text-[#F5F5F7] transition-colors hover:border-[#1A8FD6]/40"
          >
            Get my calendar link
          </button>
        )}
      </div>

      {unavailable.length > 0 && (
        <details className="mt-5 border-t border-[#1F1F23] pt-4">
          <summary className="cursor-pointer text-sm text-[#A1A1A8] transition-colors hover:text-[#F5F5F7]">
            Using OpenTable, Resy, Booksy or something else?
          </summary>
          <ul className="mt-3 space-y-3">
            {unavailable.map((t) => (
              <li key={t.key}>
                <p className="text-sm text-[#F5F5F7]">{t.label}</p>
                <p className="mt-0.5 text-xs text-[#A1A1A8]">{t.reason}</p>
                <p className="mt-0.5 text-xs text-[#17C5B0]">{t.workaround}</p>
              </li>
            ))}
          </ul>
        </details>
      )}
    </Card>
  )
}
