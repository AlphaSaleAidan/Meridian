/**
 * The day as a route — for trades that drive to the customer.
 *
 * A grid of columns is the wrong picture for a mobile detailer. They do not
 * have bays; they have a van, a start point and an order to do things in. The
 * question they open the app to answer is not "which bay is free at two" but
 * "can I actually get from the ten o'clock to the twelve o'clock".
 *
 * SO THE DRIVE IS DRAWN AS A FIRST-CLASS THING, not as whitespace. Each leg
 * shows its own time, and a leg that does not fit in the gap before the next
 * job is called out — that is the failure this screen exists to prevent, and
 * it is invisible on a calendar grid.
 *
 * THE ESTIMATE IS LABELLED AS AN ESTIMATE. Distances here are straight-line
 * (haversine) with an urban speed assumption, because wiring a routing
 * provider is a separate decision with a bill attached. Straight-line is
 * always optimistic — real roads are longer — so the warning threshold is
 * deliberately generous rather than precise, and the copy never claims a
 * number it cannot stand behind.
 */
import { useState } from 'react'
import { AlertTriangle, Car, Clock3, Copy, CreditCard, MapPin, Navigation } from 'lucide-react'
import { bookingsApi, type Booking } from '@/lib/bookings-api'
import RouteMap from '@/components/RouteMap'

export interface Stop {
  booking: Booking
  address: string
  lat: number
  lng: number
}

export interface RouteOrigin {
  label: string
  lat: number
  lng: number
}

/** Average urban driving speed, km/h. Deliberately conservative: a route that
 *  under-promises is a route an owner keeps trusting. */
const URBAN_KMH = 32
/** Fixed cost per stop — parking, unloading, finding the door.
 *
 *  Six minutes is a detailer arriving at a job. A pizza handed over at a door
 *  is nothing like that, and charging the same made a 6km delivery run read
 *  as an hour of driving. Callers pass their own. */
const STOP_OVERHEAD_MIN = 6

export function haversineKm(
  a: { lat: number; lng: number },
  b: { lat: number; lng: number },
): number {
  const R = 6371
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(b.lat - a.lat)
  const dLng = toRad(b.lng - a.lng)
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(s))
}

export function driveMinutes(km: number, stopOverheadMin: number = STOP_OVERHEAD_MIN): number {
  return Math.round((km / URBAN_KMH) * 60 + stopOverheadMin)
}

interface Leg {
  fromLabel: string
  km: number
  minutes: number
  /** Minutes actually available before this stop starts. */
  available: number
  tight: boolean
}

/** The delays worth offering. Wider than this and you are rescheduling, not
 *  running late, and the customer should be asked rather than told. */
const LATE_OPTIONS = [15, 30, 45]

export default function RouteDay({
  stops, origin, timezone, onSelect, stopOverheadMin = STOP_OVERHEAD_MIN,
  paymentLinks = false,
}: {
  stops: Stop[]
  origin: RouteOrigin
  timezone: string
  onSelect?: (booking: Booking) => void
  /** Minutes lost at each stop. A detailer parks and unloads; a driver hands
   *  over a box. Six versus two is the difference between a believable run
   *  and an hour of phantom driving. */
  stopOverheadMin?: number
  /** Pack-driven (pack.paymentLinks): a per-stop "Send payment link" action
   *  for trades that get paid in a driveway rather than at a till. */
  paymentLinks?: boolean
}) {
  /**
   * "Running late" per stop.
   *
   * THE CALL THIS PREVENTS is the customer ringing to ask where the van is,
   * which lands while the detailer is under a wheel arch — so it becomes a
   * voicemail, a second call, and a review about communication rather than
   * about the work.
   *
   * Per stop, not "tell everyone left today": a delay is rarely uniform, and
   * telling someone who was five minutes behind that you are thirty behind is
   * worse than saying nothing.
   */
  const [lateFor, setLateFor] = useState<string | null>(null)
  const [sent, setSent] = useState<Record<string, string>>({})
  const [sending, setSending] = useState<string | null>(null)

  const notify = async (booking: Booking, minutes: number) => {
    setSending(booking.id)
    try {
      const res = await bookingsApi.notifyRunningLate(booking.id, minutes)
      setSent((prev) => ({
        ...prev,
        [booking.id]: res.sent
          ? `Told them ${minutes} min`
          : res.reason === 'no_phone' ? 'No number on file' : 'Could not send',
      }))
    } catch {
      setSent((prev) => ({ ...prev, [booking.id]: 'Could not send' }))
    } finally {
      setSending(null)
      setLateFor(null)
    }
  }
  /**
   * "Send payment link" per stop.
   *
   * THE MOMENT THIS SERVES is the hatch closing: the job is done, the
   * customer is standing there, and the alternative is "I'll Venmo you?"
   * shouted across a driveway. One tap texts them a real checkout for the
   * booked price.
   *
   * When the text cannot go (no number on file, carrier rejection — every US
   * merchant until 10DLC clears) the link still exists, so the fallback is a
   * copy button rather than a dead end: the operator pastes it into whatever
   * channel the customer actually answers.
   */
  const [payState, setPayState] = useState<Record<string, {
    label: string; url?: string; ok?: boolean
  }>>({})
  const [paying, setPaying] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  const sendPayLink = async (booking: Booking) => {
    setPaying(booking.id)
    try {
      const res = await bookingsApi.sendPaymentLink(booking.id)
      setPayState((prev) => ({
        ...prev,
        [booking.id]: res.sent
          ? { label: 'Payment link texted', ok: true }
          : res.url
            ? { label: res.reason === 'no_phone'
                  ? 'No number on file — copy the link instead'
                  : 'Could not text — copy the link instead',
                url: res.url }
            : { label: res.reason === 'no_price'
                  ? 'No price on this service'
                  : 'Could not create a link' },
      }))
    } catch {
      setPayState((prev) => ({
        ...prev, [booking.id]: { label: 'Could not create a link' },
      }))
    } finally {
      setPaying(null)
    }
  }

  const copyPayLink = async (id: string, url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(id)
      setTimeout(() => setCopied((c) => (c === id ? null : c)), 2000)
    } catch { /* clipboard denied — the url stays visible in the row */ }
  }

  // Pointing at a stop in either place highlights it in the other. On a map
  // with four pins in one suburb, "which of these is the 2pm" is the question
  // being asked constantly.
  const [hover, setHover] = useState<number | null>(null)

  const ordered = [...stops].sort((a, b) =>
    a.booking.startsAt.localeCompare(b.booking.startsAt))

  const fmt = (iso: string) => {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        hour: 'numeric', minute: '2-digit', hour12: true,
        timeZone: timezone || undefined,
      }).format(new Date(iso))
    } catch {
      return ''
    }
  }

  const legs: Leg[] = ordered.map((stop, i) => {
    const from = i === 0 ? origin : ordered[i - 1]
    const km = haversineKm(from, stop)
    const minutes = driveMinutes(km, stopOverheadMin)
    const previousEnd = i === 0
      ? new Date(ordered[0].booking.startsAt).getTime() - 60 * 60_000
      : new Date(ordered[i - 1].booking.endsAt).getTime()
    const available = Math.round(
      (new Date(stop.booking.startsAt).getTime() - previousEnd) / 60_000)
    // Two stops at the same minute are two DRIVERS, not one impossible leg.
    // A pizza shop runs three at once; chaining them into a single sequence
    // flagged seven of nine drops as tight on a run that is comfortable.
    const concurrent = i > 0
      && ordered[i - 1].booking.startsAt === stop.booking.startsAt
    return {
      fromLabel: i === 0 ? origin.label : ordered[i - 1].booking.customerName,
      km,
      minutes,
      available,
      // Straight-line under-states real driving, so flag anything that is even
      // close rather than only what fails outright.
      tight: !concurrent && minutes > available * 0.8,
    }
  })

  const totalDrive = legs.reduce((sum, l) => sum + l.minutes, 0)
  const totalKm = legs.reduce((sum, l) => sum + l.km, 0)
  const problems = legs.filter((l) => l.tight).length

  if (ordered.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#1F1F23] px-4 py-10 text-center text-sm text-[#6B6B73]">
        Nothing on the road today.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Stops" value={String(ordered.length)} />
        <Stat
          label="Driving"
          value={totalDrive >= 60
            ? `${Math.floor(totalDrive / 60)}h ${totalDrive % 60}m`
            : `${totalDrive}m`}
          sub={`${totalKm.toFixed(1)} km, estimated`}
        />
        <Stat
          label="Tight legs"
          value={String(problems)}
          tone={problems > 0 ? 'warn' : 'ok'}
          sub={problems > 0 ? 'May not make it on time' : 'The day fits'}
        />
      </div>

      {/* Side by side only where there is genuinely room for both. Below that
          the map takes the full width and the list sits under it — a 250px map
          is worse than no map, and squeezing one in beside a 460px list is how
          you get one. */}
      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(0,420px)]">
        <RouteMap
          height={380}
          origin={{ lat: origin.lat, lng: origin.lng, label: origin.label }}
          stops={ordered.map((s) => ({
            lat: s.lat,
            lng: s.lng,
            label: s.booking.customerName,
            sub: `${fmt(s.booking.startsAt)} · ${s.address}`,
          }))}
          tightLegs={legs.map((l, i) => (l.tight ? i : -1)).filter((i) => i >= 0)}
          activeIndex={hover}
          onHover={setHover}
        />

        <ol className="space-y-0">
          <li className="flex items-center gap-3 py-1.5">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[#1F1F23] text-[10px] text-[#6B6B73]">
              <Navigation className="h-3 w-3" />
            </span>
            <span className="text-xs text-[#6B6B73]">{origin.label}</span>
          </li>

          {ordered.map((stop, i) => (
            <li key={stop.booking.id}>
              <div className="flex items-stretch gap-3">
                <div className="flex w-6 shrink-0 justify-center">
                  <span className={`w-px ${legs[i].tight ? 'bg-[#E5484D]/40' : 'bg-[#1F1F23]'}`} />
                </div>
                <div className={`flex items-center gap-1.5 py-1.5 text-xs ${
                  legs[i].tight ? 'text-[#E5484D]' : 'text-[#6B6B73]'
                }`}>
                  <Car className="h-3.5 w-3.5" />
                  {legs[i].minutes} min · {legs[i].km.toFixed(1)} km
                  {legs[i].tight && (
                    <span className="inline-flex items-center gap-1">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      only {Math.max(0, legs[i].available)} min before this one
                    </span>
                  )}
                </div>
              </div>

              <button
                onClick={() => onSelect?.(stop.booking)}
                onMouseEnter={() => setHover(i)}
                onMouseLeave={() => setHover(null)}
                className={`flex w-full items-start gap-3 rounded-lg border bg-[#111113] p-3 text-left transition-colors ${
                  hover === i
                    ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/5'
                    : 'border-[#1F1F23] hover:border-[#1A8FD6]/40'
                }`}
              >
                <span className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full border font-mono text-[10px] ${
                  legs[i].tight
                    ? 'border-[#E5484D]/50 bg-[#E5484D]/15 text-[#E5484D]'
                    : 'border-[#1A8FD6]/40 bg-[#1A8FD6]/10 text-[#1A8FD6]'
                }`}>
                  {i + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-baseline gap-x-2">
                    <span className="font-mono text-sm text-[#F5F5F7]">
                      {fmt(stop.booking.startsAt)}
                    </span>
                    <span className="text-sm text-[#F5F5F7]">{stop.booking.customerName}</span>
                  </span>
                  <span className="mt-0.5 flex items-center gap-1 text-xs text-[#A1A1A8]">
                    <MapPin className="h-3 w-3 shrink-0" />
                    {stop.address}
                  </span>
                </span>
              </button>

              {/* Under the stop rather than inside it: the card is a link to
                  the booking, and burying a send-a-text control inside a
                  navigation target is how someone texts a customer by
                  accident. */}
              <div className="ml-9 mt-1 flex flex-wrap items-center gap-1.5">
                {sent[stop.booking.id] ? (
                  <span className="text-xs text-[#17C5B0]">
                    {sent[stop.booking.id]}
                  </span>
                ) : lateFor === stop.booking.id ? (
                  <>
                    <span className="text-xs text-[#A1A1A8]">How late?</span>
                    {LATE_OPTIONS.map((m) => (
                      <button
                        key={m}
                        disabled={sending === stop.booking.id}
                        onClick={() => notify(stop.booking, m)}
                        className="rounded-md border border-[#1A8FD6]/40 bg-[#1A8FD6]/10 px-2 py-1 text-xs font-medium text-[#1A8FD6] transition-colors hover:bg-[#1A8FD6]/20 disabled:opacity-50"
                      >
                        {m} min
                      </button>
                    ))}
                    <button
                      onClick={() => setLateFor(null)}
                      className="px-1.5 py-1 text-xs text-[#6B6B73] hover:text-[#A1A1A8]"
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setLateFor(stop.booking.id)}
                    className="inline-flex items-center gap-1.5 rounded-md border border-[#1F1F23] px-2 py-1 text-xs text-[#A1A1A8] transition-colors hover:border-[#F5A524]/40 hover:text-[#F5A524]"
                  >
                    <Clock3 className="h-3.5 w-3.5" />
                    Arriving late — notify customer
                  </button>
                )}

                {paymentLinks && (
                  payState[stop.booking.id] ? (
                    <span className={`inline-flex items-center gap-1.5 text-xs ${
                      payState[stop.booking.id].ok ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'
                    }`}>
                      {payState[stop.booking.id].label}
                      {payState[stop.booking.id].url && (
                        <button
                          onClick={() => copyPayLink(stop.booking.id, payState[stop.booking.id].url!)}
                          className="inline-flex items-center gap-1 rounded-md border border-[#1A8FD6]/40 bg-[#1A8FD6]/10 px-2 py-1 text-xs font-medium text-[#1A8FD6] transition-colors hover:bg-[#1A8FD6]/20"
                        >
                          <Copy className="h-3 w-3" />
                          {copied === stop.booking.id ? 'Copied' : 'Copy link'}
                        </button>
                      )}
                    </span>
                  ) : (
                    <button
                      disabled={paying === stop.booking.id}
                      onClick={() => sendPayLink(stop.booking)}
                      className="inline-flex items-center gap-1.5 rounded-md border border-[#1F1F23] px-2 py-1 text-xs text-[#A1A1A8] transition-colors hover:border-[#17C5B0]/40 hover:text-[#17C5B0] disabled:opacity-50"
                    >
                      <CreditCard className="h-3.5 w-3.5" />
                      {paying === stop.booking.id ? 'Creating link…' : 'Send payment link'}
                    </button>
                  )
                )}
              </div>
            </li>
          ))}
        </ol>
      </div>

      <p className="text-xs text-[#6B6B73]">
        Drive times are straight-line estimates at {URBAN_KMH} km/h plus{' '}
        {stopOverheadMin} minutes a stop — real roads are longer, so treat a
        tight leg as tighter than it looks. Connecting a routing provider
        replaces these with real ones.
      </p>
    </div>
  )
}

function Stat({ label, value, sub, tone }: {
  label: string
  value: string
  sub?: string
  tone?: 'ok' | 'warn'
}) {
  return (
    <div className="rounded-lg border border-[#1F1F23] bg-[#111113] p-3">
      <div className="text-[10px] uppercase tracking-wide text-[#A1A1A8]">{label}</div>
      <div className={`mt-0.5 font-mono text-xl font-semibold ${
        tone === 'warn' ? 'text-[#E5484D]' : tone === 'ok' ? 'text-[#17C5B0]' : 'text-[#F5F5F7]'
      }`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-[#6B6B73]">{sub}</div>}
    </div>
  )
}
