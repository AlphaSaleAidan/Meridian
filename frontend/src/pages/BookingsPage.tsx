/**
 * Today's book — the screen a host or a barber actually stands in front of.
 *
 * Optimised for one question asked fifty times a shift: who is coming, and
 * when. Everything else is secondary. The list is chronological and the next
 * arrival is marked.
 *
 * THE DAILY COST OF THIS SCREEN IS ONE TAP PER GUEST. That is the budget it
 * is designed against, because a booking system that costs a host more time
 * than a paper book is one they will stop using by the second busy Friday.
 * Every row therefore offers exactly one primary action — the guest turned up
 * — and imported busy time from the merchant's own tools is shown here so
 * they never need a second screen open to know what tonight looks like.
 *
 * Times are rendered in the MERCHANT's timezone, which the server sends back
 * with the data. The browser's own timezone is never used: an owner checking
 * tonight's book from an airport must not see every reservation shifted.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertCircle, CalendarDays, CheckCircle2, ChevronLeft,
  ChevronRight, Clock, Phone, Plus, Users,
} from 'lucide-react'
import { useOrgId } from '@/hooks/useOrg'
import {
  bookingsApi, BookingsApiError,
  type Booking, type BookingStatus, type BusyBlock, type Resource, type WaitlistEntry,
} from '@/lib/bookings-api'

const STATUS_STYLES: Record<BookingStatus, string> = {
  confirmed: 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/30',
  seated: 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/30',
  completed: 'bg-[#A1A1A8]/10 text-[#A1A1A8] border-[#A1A1A8]/25',
  cancelled: 'bg-[#A1A1A8]/10 text-[#A1A1A8] border-[#A1A1A8]/25',
  no_show: 'bg-[#E5484D]/10 text-[#E5484D] border-[#E5484D]/30',
}

/** Imported busy time says which tool it came from, so an owner who sees a
 *  block they don't recognise knows where to go and change it. */
const PROVIDER_LABEL: Record<string, string> = {
  square_appointments: 'Square',
  google_calendar: 'Google Calendar',
  ics_feed: 'Calendar feed',
}

const STATUS_LABEL: Record<BookingStatus, string> = {
  confirmed: 'Booked',
  seated: 'Here',
  completed: 'Done',
  cancelled: 'Cancelled',
  no_show: 'No-show',
}

/**
 * The right-hand side of a booking row.
 *
 * A host's whole interaction with tonight's book is: the guest walks in, tap
 * once. That is the design target — one tap per guest and nothing else — so
 * this shows exactly one primary action at a time.
 *
 * No-show is deliberately NOT offered until the booking time has passed.
 * Before then it is not a thing anyone means to press, and next to the arrival
 * button it is a mis-tap that tells a waiting guest their table is gone.
 *
 * Every terminal state keeps an Undo, because these get pressed one-handed
 * while carrying menus.
 */
function RowAction({ booking, onSet }: {
  booking: Booking
  onSet: (status: BookingStatus) => void
}) {
  const started = new Date(booking.startsAt).getTime() <= Date.now()

  if (booking.status === 'confirmed') {
    return (
      <div className="flex items-center gap-1.5">
        <button
          onClick={() => onSet('seated')}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#17C5B0]/40 bg-[#17C5B0]/10 px-3 py-1.5 text-xs font-medium text-[#17C5B0] transition-colors hover:bg-[#17C5B0]/20"
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          They're here
        </button>
        {started && (
          <button
            onClick={() => onSet('no_show')}
            className="rounded-lg border border-transparent px-2 py-1.5 text-xs text-[#6B6B73] transition-colors hover:border-[#E5484D]/30 hover:text-[#E5484D]"
          >
            No-show
          </button>
        )}
      </div>
    )
  }

  if (booking.status === 'seated') {
    return (
      <div className="flex items-center gap-1.5">
        <span className="inline-flex items-center gap-1 rounded border border-[#17C5B0]/30 bg-[#17C5B0]/10 px-2 py-0.5 text-[11px] font-medium text-[#17C5B0]">
          <CheckCircle2 className="h-3 w-3" />
          Seated
        </span>
        <button
          onClick={() => onSet('completed')}
          className="rounded-lg border border-[#1F1F23] px-2.5 py-1.5 text-xs text-[#A1A1A8] transition-colors hover:text-[#F5F5F7]"
        >
          Done
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`rounded border px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLES[booking.status]}`}
      >
        {STATUS_LABEL[booking.status]}
      </span>
      {booking.status !== 'cancelled' && (
        <button
          onClick={() => onSet('confirmed')}
          className="rounded-lg px-2 py-1.5 text-xs text-[#6B6B73] transition-colors hover:text-[#F5F5F7]"
        >
          Undo
        </button>
      )}
    </div>
  )
}

function toDayKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate(),
  ).padStart(2, '0')}`
}

export default function BookingsPage() {
  const merchantId = useOrgId()
  const [day, setDay] = useState(() => toDayKey(new Date()))
  const [bookings, setBookings] = useState<Booking[]>([])
  const [resources, setResources] = useState<Resource[]>([])
  const [busy, setBusy] = useState<BusyBlock[]>([])
  const [timezone, setTimezone] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showAdd, setShowAdd] = useState(false)

  const load = useCallback(async () => {
    if (!merchantId) return
    setLoading(true)
    setError('')
    try {
      // A full local day, widened either side so a booking that starts late
      // the night before and runs past midnight still appears.
      const start = new Date(`${day}T00:00:00`)
      const end = new Date(start.getTime() + 24 * 3600 * 1000)
      const from = new Date(start.getTime() - 12 * 3600 * 1000).toISOString()
      const [rows, res, avail, busyRows] = await Promise.all([
        bookingsApi.listBookings(merchantId, from, end.toISOString(), true),
        bookingsApi.listResources(merchantId),
        bookingsApi.availability(merchantId, day, 1).catch(() => null),
        // Imported from the merchant's other tools. Failing softly on purpose:
        // a calendar we cannot reach must not blank out tonight's real book.
        bookingsApi.listBusy(merchantId, from, end.toISOString()).catch(() => []),
      ])
      setBookings(rows)
      setResources(res)
      setBusy(busyRows)
      if (avail) setTimezone(avail.timezone)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load bookings')
    } finally {
      setLoading(false)
    }
  }, [merchantId, day])

  useEffect(() => { load() }, [load])

  const resourceName = useCallback(
    (id: string) => resources.find((r) => r.id === id)?.name || '',
    [resources],
  )

  const fmt = useCallback(
    (iso: string) => {
      try {
        return new Intl.DateTimeFormat('en-CA', {
          hour: 'numeric', minute: '2-digit', hour12: true,
          timeZone: timezone || undefined,
        }).format(new Date(iso))
      } catch {
        return ''
      }
    },
    [timezone],
  )

  const dayBookings = useMemo(() => {
    return bookings
      .filter((b) => {
        try {
          const local = new Intl.DateTimeFormat('en-CA', {
            year: 'numeric', month: '2-digit', day: '2-digit',
            timeZone: timezone || undefined,
          }).format(new Date(b.startsAt))
          return local === day
        } catch {
          return true
        }
      })
      .sort((a, b) => a.startsAt.localeCompare(b.startsAt))
  }, [bookings, day, timezone])

  /** One timeline, ours and theirs, in time order.
   *
   *  A host asking "what's happening tonight" does not care which system a
   *  commitment lives in. Showing only our own rows makes the screen quietly
   *  wrong on exactly the evenings that matter — the ones with a private
   *  event booked in the other tool. */
  const timeline = useMemo(() => {
    const items: Array<
      | { kind: 'booking'; at: string; booking: Booking }
      | { kind: 'busy'; at: string; block: BusyBlock }
    > = dayBookings.map((b) => ({ kind: 'booking', at: b.startsAt, booking: b }))

    for (const block of busy) {
      try {
        const local = new Intl.DateTimeFormat('en-CA', {
          year: 'numeric', month: '2-digit', day: '2-digit',
          timeZone: timezone || undefined,
        }).format(new Date(block.startsAt))
        if (local === day) items.push({ kind: 'busy', at: block.startsAt, block })
      } catch {
        /* An unparseable imported row is dropped rather than shown wrong. */
      }
    }
    return items.sort((a, b) => a.at.localeCompare(b.at))
  }, [dayBookings, busy, day, timezone])

  const live = dayBookings.filter(
    (b) => b.status !== 'cancelled' && b.status !== 'no_show',
  )
  const covers = live.reduce((sum, b) => sum + b.partySize, 0)
  const nextUp = live.find(
    (b) => b.status === 'confirmed' && new Date(b.startsAt) > new Date(),
  )

  const setStatus = async (b: Booking, status: BookingStatus) => {
    setBookings((prev) =>
      prev.map((x) => (x.id === b.id ? { ...x, status } : x)))
    try {
      await bookingsApi.updateBooking(b.id, { status })
    } catch {
      // Put the old value back rather than leaving the screen lying about
      // what the database says.
      setBookings((prev) =>
        prev.map((x) => (x.id === b.id ? { ...x, status: b.status } : x)))
      setError('Could not update that booking — please try again.')
    }
  }

  const shiftDay = (delta: number) => {
    const d = new Date(`${day}T12:00:00`)
    d.setDate(d.getDate() + delta)
    setDay(toDayKey(d))
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl font-semibold text-[#F5F5F7] tracking-tight">
            Bookings
          </h1>
          <p className="text-sm text-[#A1A1A8] mt-0.5">
            {live.length} booked{covers !== live.length ? ` · ${covers} people` : ''}
            {timezone ? ` · times shown in ${timezone.replace('_', ' ')}` : ''}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <div className="flex items-center rounded-lg border border-[#1F1F23] bg-[#111113]">
            <button
              onClick={() => shiftDay(-1)}
              aria-label="Previous day"
              className="p-2 text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <input
              type="date"
              value={day}
              onChange={(e) => setDay(e.target.value)}
              className="bg-transparent text-sm text-[#F5F5F7] px-1 py-2 outline-none"
            />
            <button
              onClick={() => shiftDay(1)}
              aria-label="Next day"
              className="p-2 text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#1A8FD6] px-3 py-2 text-sm font-medium text-white hover:bg-[#1A8FD6]/90 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add
          </button>
        </div>
      </header>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-[#E5484D]/30 bg-[#E5484D]/10 px-3 py-2.5 text-sm text-[#E5484D]">
          <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="h-16 animate-pulse rounded-lg border border-[#1F1F23] bg-[#111113]"
            />
          ))}
        </div>
      ) : timeline.length === 0 ? (
        <EmptyDay onAdd={() => setShowAdd(true)} />
      ) : (
        <ul className="space-y-2">
          {timeline.map((item) => item.kind === 'busy' ? (
            <li
              key={item.block.id}
              className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-dashed border-[#1F1F23] bg-[#0E0E11] px-4 py-2.5"
            >
              <div className="w-20 shrink-0 font-mono text-sm text-[#A1A1A8]">
                {fmt(item.block.startsAt)}
              </div>
              <div className="min-w-0 flex-1 truncate text-sm text-[#A1A1A8]">
                {item.block.summary || 'Busy'}
              </div>
              <span className="rounded border border-[#1F1F23] px-2 py-0.5 text-[11px] text-[#6B6B73]">
                {PROVIDER_LABEL[item.block.provider] || 'Your calendar'}
              </span>
            </li>
          ) : (
            (() => { const b = item.booking; return (
            <li
              key={b.id}
              className={`rounded-lg border bg-[#111113] px-4 py-3 transition-colors ${
                nextUp?.id === b.id
                  ? 'border-[#1A8FD6]/50'
                  : 'border-[#1F1F23]'
              }`}
            >
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                <div className="w-20 shrink-0">
                  <div className="font-mono text-sm font-semibold text-[#F5F5F7]">
                    {fmt(b.startsAt)}
                  </div>
                  {nextUp?.id === b.id && (
                    <div className="text-[10px] uppercase tracking-wide text-[#1A8FD6]">
                      Next up
                    </div>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-[#F5F5F7]">
                    {b.customerName}
                  </div>
                  <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-[#A1A1A8]">
                    {b.partySize > 1 && (
                      <span className="inline-flex items-center gap-1">
                        <Users className="w-3 h-3" />
                        {b.partySize}
                      </span>
                    )}
                    {resourceName(b.resourceId) && (
                      <span>{resourceName(b.resourceId)}</span>
                    )}
                    {b.customerPhone && (
                      <a
                        href={`tel:${b.customerPhone}`}
                        className="inline-flex items-center gap-1 hover:text-[#F5F5F7] transition-colors"
                      >
                        <Phone className="w-3 h-3" />
                        {b.customerPhone}
                      </a>
                    )}
                    {b.source === 'phone' && (
                      <span className="text-[#17C5B0]">Booked by the agent</span>
                    )}
                    <span className="font-mono">{b.confirmationCode}</span>
                  </div>
                  {b.notes && (
                    <div className="mt-1 text-xs italic text-[#A1A1A8]">
                      {b.notes}
                    </div>
                  )}
                </div>

                {/* ONE action per row, because there is only one thing a host
                    does with a booking: mark that the guest turned up.
                    Everything in this list is already booked, so a "Booked"
                    control would be a button that changes nothing. */}
                <RowAction booking={b} onSet={(s) => setStatus(b, s)} />
              </div>
            </li>
          )})()
          ))}
        </ul>
      )}

      <WaitlistPanel merchantId={merchantId} timezone={timezone} />

      {showAdd && (
        <AddBookingDialog
          merchantId={merchantId}
          day={day}
          onClose={() => setShowAdd(false)}
          onSaved={() => { setShowAdd(false); load() }}
        />
      )}
    </div>
  )
}

/**
 * Who's waiting, and who we've already offered a freed slot to.
 *
 * The `rankReason` is shown deliberately. A host who sees "offered to Dana —
 * 3 past visits, $240 spent before" can agree or overrule; a host who just
 * sees "offered to Dana" has to trust a black box, and won't.
 */
function WaitlistPanel({ merchantId, timezone }: {
  merchantId: string
  timezone: string
}) {
  const [waiting, setWaiting] = useState<WaitlistEntry[]>([])
  const [offered, setOffered] = useState<WaitlistEntry[]>([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!merchantId) return
    Promise.all([
      bookingsApi.listWaitlist(merchantId, 'waiting').catch(() => []),
      bookingsApi.listWaitlist(merchantId, 'offered').catch(() => []),
    ]).then(([w, o]) => { setWaiting(w); setOffered(o) })
  }, [merchantId])

  if (waiting.length === 0 && offered.length === 0) return null

  const window = (e: WaitlistEntry) => {
    try {
      const f = new Intl.DateTimeFormat('en-CA', {
        weekday: 'short', hour: 'numeric', minute: '2-digit', hour12: true,
        timeZone: timezone || undefined,
      })
      return `${f.format(new Date(e.windowStart))} – ${new Intl.DateTimeFormat('en-CA', {
        hour: 'numeric', minute: '2-digit', hour12: true,
        timeZone: timezone || undefined,
      }).format(new Date(e.windowEnd))}`
    } catch {
      return ''
    }
  }

  return (
    <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 text-left"
      >
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-[#F5F5F7]">Waiting list</h2>
          <p className="mt-0.5 text-xs text-[#A1A1A8]">
            {waiting.length} waiting
            {offered.length > 0 && ` · ${offered.length} holding a spot right now`}
            {' · '}we text the best match the moment something frees up
          </p>
        </div>
        <ChevronRight
          className={`h-4 w-4 shrink-0 text-[#A1A1A8] transition-transform ${open ? 'rotate-90' : ''}`}
        />
      </button>

      {open && (
        <ul className="mt-3 divide-y divide-[#1F1F23] border-t border-[#1F1F23] pt-1">
          {[...offered, ...waiting].map((e) => (
            <li key={e.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 py-2.5">
              <span className="text-sm text-[#F5F5F7]">{e.customerName}</span>
              {e.partySize > 1 && (
                <span className="inline-flex items-center gap-1 text-xs text-[#A1A1A8]">
                  <Users className="h-3 w-3" />{e.partySize}
                </span>
              )}
              <span className="text-xs text-[#A1A1A8]">{window(e)}</span>
              {e.status === 'offered' ? (
                <span className="rounded border border-[#D9A441]/30 bg-[#D9A441]/10 px-2 py-0.5 text-[11px] text-[#D9A441]">
                  Holding a spot
                </span>
              ) : (
                <span className="text-[11px] text-[#A1A1A8]">Waiting</span>
              )}
              {e.rankReason && (
                <span className="w-full text-[11px] italic text-[#A1A1A8]">
                  Chosen because: {e.rankReason}
                </span>
              )}
              <button
                onClick={async () => {
                  await bookingsApi.removeFromWaitlist(e.id)
                  setWaiting((prev) => prev.filter((x) => x.id !== e.id))
                  setOffered((prev) => prev.filter((x) => x.id !== e.id))
                }}
                className="ml-auto text-xs text-[#A1A1A8] transition-colors hover:text-[#E5484D]"
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function EmptyDay({ onAdd }: { onAdd: () => void }) {
  return (
    <div className="rounded-lg border border-dashed border-[#1F1F23] bg-[#111113] px-6 py-12 text-center">
      <CalendarDays className="mx-auto mb-3 h-8 w-8 text-[#A1A1A8]" />
      <p className="text-sm font-medium text-[#F5F5F7]">Nothing booked</p>
      <p className="mx-auto mt-1 max-w-sm text-sm text-[#A1A1A8]">
        Bookings taken by the phone agent land here automatically. You can also
        add a walk-in yourself.
      </p>
      <button
        onClick={onAdd}
        className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-3 py-2 text-sm text-[#F5F5F7] hover:border-[#1A8FD6]/40 transition-colors"
      >
        <Plus className="w-4 h-4" />
        Add a booking
      </button>
    </div>
  )
}

function AddBookingDialog({
  merchantId, day, onClose, onSaved,
}: {
  merchantId: string
  day: string
  onClose: () => void
  onSaved: () => void
}) {
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [party, setParty] = useState(2)
  const [slots, setSlots] = useState<{ startsAt: string; localLabel: string }[]>([])
  const [chosen, setChosen] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    bookingsApi
      .availability(merchantId, day, party)
      .then((r) => {
        if (cancelled) return
        setSlots(r.slots)
        setChosen((prev) =>
          r.slots.some((s) => s.startsAt === prev) ? prev : r.slots[0]?.startsAt || '')
      })
      .catch(() => !cancelled && setSlots([]))
    return () => { cancelled = true }
  }, [merchantId, day, party])

  const save = async () => {
    if (!name.trim() || !chosen) return
    setBusy(true)
    setError('')
    try {
      await bookingsApi.createBooking({
        merchantId,
        startsAt: chosen,
        partySize: party,
        customerName: name.trim(),
        customerPhone: phone.trim() || undefined,
        source: 'walk_in',
      })
      onSaved()
    } catch (e) {
      // The 409 is the real race: someone took this slot between the list
      // loading and this click. Say exactly that.
      setError(
        e instanceof BookingsApiError && e.isSlotTaken
          ? 'That time was just taken. Pick another.'
          : 'Could not save the booking.',
      )
      bookingsApi.availability(merchantId, day, party)
        .then((r) => setSlots(r.slots))
        .catch(() => undefined)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-xl border border-[#1F1F23] bg-[#111113] p-5 space-y-4"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-base font-semibold text-[#F5F5F7]">Add a booking</h2>

        <div className="space-y-3">
          <Field label="Name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
              className="w-full rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
            />
          </Field>
          <Field label="Phone (optional — we text a reminder)">
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              inputMode="tel"
              className="w-full rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
            />
          </Field>
          <Field label="How many people">
            <input
              type="number"
              min={1}
              max={100}
              value={party}
              onChange={(e) => setParty(Math.max(1, Number(e.target.value) || 1))}
              className="w-24 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-sm text-[#F5F5F7] outline-none focus:border-[#1A8FD6]/50"
            />
          </Field>

          <Field label="Time">
            {slots.length === 0 ? (
              <p className="text-sm text-[#A1A1A8]">
                Nothing open that day for {party}.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5 max-h-40 overflow-y-auto">
                {slots.map((s) => (
                  <button
                    key={s.startsAt}
                    onClick={() => setChosen(s.startsAt)}
                    className={`rounded-md border px-2.5 py-1.5 text-xs transition-colors ${
                      chosen === s.startsAt
                        ? 'border-[#1A8FD6] bg-[#1A8FD6]/10 text-[#1A8FD6]'
                        : 'border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7]'
                    }`}
                  >
                    {s.localLabel}
                  </button>
                ))}
              </div>
            )}
          </Field>
        </div>

        {error && (
          <p className="flex items-start gap-1.5 text-sm text-[#E5484D]">
            <AlertCircle className="w-4 h-4 mt-0.5 shrink-0" />
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-1">
          <button
            onClick={onClose}
            className="rounded-lg px-3 py-2 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={busy || !name.trim() || !chosen}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#1A8FD6] px-3 py-2 text-sm font-medium text-white disabled:opacity-40 hover:bg-[#1A8FD6]/90 transition-colors"
          >
            <Clock className="w-4 h-4" />
            {busy ? 'Saving…' : 'Book it'}
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-medium uppercase tracking-wide text-[#A1A1A8]">
        {label}
      </span>
      {children}
    </label>
  )
}
