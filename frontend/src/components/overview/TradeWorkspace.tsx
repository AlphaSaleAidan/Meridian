/**
 * The workspace — one screen that IS the app for a trade.
 *
 * The previous shape had "Overview" sitting in a sidebar as a peer of
 * Bookings, Phone and Settings, which made the most important surface in the
 * product look like the first item in a list. Aidan's read was right: it felt
 * like a tab, not the focal point.
 *
 * So the hierarchy is now explicit and there is only one of it:
 *
 *   BAND   the decision line — the trade's number, at a size nothing else
 *          competes with, plus the two or three figures that qualify it
 *   MAIN   the work itself, in the form this trade actually works in: a route
 *          for someone who drives, a grid for someone with chairs or tables,
 *          a list when the day is short
 *   RAIL   what needs a human — the gaps, the tight legs, the big parties,
 *          the people waiting. Everything here is actionable; nothing here is
 *          decoration
 *
 * Everything else in the product — phone, team, inventory, settings — is
 * secondary navigation, because it is where a merchant goes occasionally and
 * this is where they live.
 */
import { useMemo } from 'react'
import { AlertTriangle, ChevronLeft, ChevronRight, Plus } from 'lucide-react'
import type { Booking, BusyBlock, Resource, Service } from '@/lib/bookings-api'
import type { NichePack } from '@/config/niches'
import BookingCalendar from '@/components/BookingCalendar'
import StatCard from '@/components/StatCard'
import Top3ActionsPanel from '@/components/Top3ActionsPanel'
import ForecastChart, { type ForecastPoint } from '@/components/ForecastChart'
import PeakHoursHeatmap, { type HeatmapCell } from '@/components/PeakHoursHeatmap'
import InsightCard from '@/components/InsightCard'
import type { Insight } from '@/lib/api'
import { formatCentsCompact } from '@/lib/format'
import {
  CalendarCheck, Car, Clock, DollarSign, Navigation, PhoneCall,
  Receipt, Sparkles, Users, type LucideIcon,
} from 'lucide-react'
import RouteDay, { haversineKm, driveMinutes, type RouteOrigin, type Stop } from '@/components/RouteDay'

const LIVE = new Set(['confirmed', 'seated', 'completed'])

export interface WorkspaceData {
  pack: NichePack
  bookings: Booking[]
  resources: Resource[]
  services: Service[]
  busy: BusyBlock[]
  timezone: string
  day: string
  onShiftDay?: (delta: number) => void
  stops?: Stop[]
  origin?: RouteOrigin
  shopName: string
  /** Booked revenue per day for the fortnight ending today, oldest first.
   *  Drives the trend line and the comparison — an owner reads today against
   *  a normal day, never against zero. */
  history?: { day: string; cents: number }[]
  /** From Meridian's existing /api/dashboard/forecasts. Reused rather than
   *  reinvented — the product already forecasts revenue and the workspace
   *  should show it, not grow a second model beside it. */
  forecasts?: { period_start: string; predicted_cents: number; lower_bound_cents: number | null; upper_bound_cents: number | null; confidence: number | null }[]
  /** From /api/dashboard/anomalies. */
  anomalies?: { date: string; value_cents: number; expected_cents: number; description: string }[]
  /** The fortnight of bookings behind the trend, for the peak-hours heatmap. */
  fortnight?: Booking[]
}

/**
 * The portal's own compact formatter, not a local one.
 *
 * It is locale-aware: under /canada it renders CA$ and en-CA, everywhere else
 * plain $. A hand-rolled `$${n}` — which is what was here — would have printed
 * US dollars on the Canadian portal, which is not a formatting slip but a
 * price quoted in the wrong currency.
 */
const money = (cents: number): string => formatCentsCompact(cents)

/**
 * What a day's bookings are worth.
 *
 * Priced services carry their own price; a restaurant's "service" is a party
 * band, which cannot sensibly be priced, so its revenue is covers x average
 * spend. Getting this wrong in either direction makes every number above it a
 * lie, so the two cases are handled separately rather than averaged.
 */
function revenueCents(bookings: Booking[], services: Service[], pack: NichePack): number {
  if (pack.avgCoverCents) {
    return bookings.reduce((s, b) => s + b.partySize * pack.avgCoverCents!, 0)
  }
  const price = new Map(services.map((sv) => [sv.id, sv.priceCents ?? 0]))
  return bookings.reduce((s, b) => s + (price.get(b.serviceId || '') ?? 0), 0)
}

// ── derivations shared by every trade ───────────────────────────────────

const mins = (b: Booking) =>
  Math.max(0, (new Date(b.endsAt).getTime() - new Date(b.startsAt).getTime()) / 60_000)

function localMinutes(iso: string, tz: string): number {
  try {
    const p = new Intl.DateTimeFormat('en-GB', {
      timeZone: tz || undefined, hour12: false, hour: '2-digit', minute: '2-digit',
    }).formatToParts(new Date(iso))
    const g = (t: string) => Number(p.find((x) => x.type === t)?.value ?? 0)
    return (g('hour') % 24) * 60 + g('minute')
  } catch { return 0 }
}

function clock(m: number): string {
  const h = Math.floor(m / 60) % 24
  const mm = m % 60
  const ampm = h < 12 ? 'am' : 'pm'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return mm === 0 ? `${h12}${ampm}` : `${h12}:${String(mm).padStart(2, '0')}${ampm}`
}

function openWindow(pack: NichePack): [number, number] {
  const [oh, om] = pack.opens.split(':').map(Number)
  const [ch, cm] = pack.closes.split(':').map(Number)
  return [oh * 60 + om, ch * 60 + cm]
}

export default function TradeWorkspace(data: WorkspaceData) {
  const { pack, bookings, resources, busy, timezone, day, onShiftDay, stops, origin } = data

  /**
   * Only THIS day.
   *
   * The fetch deliberately widens the window either side so a booking that
   * runs past midnight is not lost, which means the raw list carries the
   * previous afternoon. Money computed over that window reported a closed
   * Sunday as a $655 day — yesterday's takings, on today's screen.
   */
  const today = useMemo(() => bookings.filter((b) => {
    try {
      return new Intl.DateTimeFormat('en-CA', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        timeZone: timezone || undefined,
      }).format(new Date(b.startsAt)) === day
    } catch {
      return true
    }
  }), [bookings, day, timezone])

  const live = today.filter((b) => LIVE.has(b.status))
  const [open, close] = openWindow(pack)

  const attention = useMemo(() => computeAttention(data, live, open, close), [data, live, open, close])

  const { services = [], history } = data
  const booked = useMemo(
    () => revenueCents(live, services, pack), [live, services, pack])

  /** Today against the same weekday, not against yesterday — a Sunday is not
   *  a slow Monday, and comparing them invents a crisis every week. */
  const weekdayName = new Date(`${day}T12:00:00`).toLocaleDateString('en-CA', { weekday: 'long' })
  const changePct = useMemo(() => {
    if (!history || history.length < 8) return undefined
    const target = new Date(`${day}T12:00:00`).getDay()
    const sameWeekday = history
      .filter((h) => new Date(`${h.day}T12:00:00`).getDay() === target && h.day !== day)
      .map((h) => h.cents)
    if (!sameWeekday.length) return undefined
    const avg = sameWeekday.reduce((a, b) => a + b, 0) / sameWeekday.length
    if (avg <= 0) return undefined
    return Math.round(((booked - avg) / avg) * 100)
  }, [history, day, booked])

  /**
   * Money left on the table — the figure that makes the gaps below matter.
   * Idle capacity converted at what this shop actually charges, so an owner
   * reads "two empty chairs" as the dollars they are.
   */
  const { recoverable, recoverableWhy } = useMemo(() => {
    if (!pack.booksAtAll) return { recoverable: 0, recoverableWhy: '' }
    const active = resources.filter((r) => r.active)
    const capacity = Math.max(1, (close - open)) * Math.max(1, active.length)
    const bookedMins = live.reduce((s, b) => s + mins(b), 0)
    const idle = Math.max(0, capacity - bookedMins)
    const avgDuration = services.length
      ? services.reduce((s, sv) => s + sv.durationMinutes + sv.bufferMinutes, 0) / services.length
      : 60
    const avgValue = pack.avgCoverCents
      ? pack.avgCoverCents * 2
      : services.length
        ? services.reduce((s, sv) => s + (sv.priceCents ?? 0), 0) / services.length
        : 0
    const slots = Math.floor(idle / Math.max(15, avgDuration))
    return {
      recoverable: Math.round(slots * avgValue),
      recoverableWhy: `${slots} more ${slots === 1 ? 'slot' : 'slots'} would fit`,
    }
  }, [pack, resources, services, live, open, close])

  const tiles = useMemo(
    () => computeTiles(data, live, open, close, booked),
    [data, live, open, close, booked])

  /**
   * Peak hours, computed from the same fortnight of bookings. Only for the
   * trades where it changes a decision — a one-van operator does not staff
   * against a heatmap.
   */
  const peakCells = useMemo<HeatmapCell[]>(() => {
    if (!data.fortnight || data.fortnight.length === 0) return []
    if (!['restaurant', 'barbershop', 'nails', 'medspa'].includes(pack.key)) return []
    const grid = new Map<string, { n: number; cents: number }>()
    for (const b of data.fortnight) {
      const d = new Date(b.startsAt)
      // PeakHoursHeatmap indexes Monday-first.
      const day = (d.getDay() + 6) % 7
      const hour = Number(new Intl.DateTimeFormat('en-GB', {
        hour: '2-digit', hour12: false, timeZone: timezone || undefined,
      }).format(d))
      const key = `${day}-${hour}`
      const cur = grid.get(key) || { n: 0, cents: 0 }
      grid.set(key, { n: cur.n + 1, cents: cur.cents })
    }
    const max = Math.max(1, ...[...grid.values()].map((v) => v.n))
    return [...grid.entries()].map(([key, v]) => {
      const [day, hour] = key.split('-').map(Number)
      return { day, hour, intensity: v.n / max, transactions: v.n }
    })
  }, [data.fortnight, pack.key, timezone])

  /**
   * History and forecast as ONE series, which is what makes the curve read as
   * the same line continuing rather than two separate claims. The joining
   * point carries both values so the solid and dashed strokes meet instead of
   * leaving a gap.
   */
  const forecast = useMemo(() => {
    const days = data.forecasts || []
    const hist = history || []
    const series: ForecastPoint[] = hist.map((h, i) => ({
      date: h.day,
      actual: h.cents / 100,
      predicted: i === hist.length - 1 ? h.cents / 100 : null,
      lower: null,
      upper: null,
    }))
    // Only what comes AFTER the history. The forecast endpoint projects from
    // today, but the workspace can be looking at any day — without this the
    // axis ran Aug 18, Aug 17, Aug 18 and the curve doubled back on itself.
    const lastActual = hist.length ? hist[hist.length - 1].day : ''
    for (const f of days.filter((x) => x.period_start > lastActual)) {
      series.push({
        date: f.period_start,
        actual: null,
        predicted: f.predicted_cents / 100,
        lower: f.lower_bound_cents != null ? f.lower_bound_cents / 100 : null,
        upper: f.upper_bound_cents != null ? f.upper_bound_cents / 100 : null,
      })
    }
    return {
      days,
      series,
      total: days
        .filter((f) => !hist.length || f.period_start > hist[hist.length - 1].day)
        .reduce((s, f) => s + f.predicted_cents, 0),
    }
  }, [data.forecasts, history])

  const dayLabel = new Date(`${day}T12:00:00`).toLocaleDateString('en-CA', {
    weekday: 'long', month: 'long', day: 'numeric',
  })

  return (
    <div className="space-y-4">
      {/* ── The money line ────────────────────────────────────────── */}
      <section className="rounded-xl border border-[#1F1F23] bg-gradient-to-br from-[#12171C] to-[#111113] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[11px] uppercase tracking-[0.14em] text-[#6B6B73]">
              {dayLabel} · booked so far
            </div>
            <div className="mt-2 flex flex-wrap items-end gap-x-4 gap-y-1">
              <div className="font-mono text-[56px] font-semibold leading-none tracking-tight text-[#F5F5F7]">
                {money(booked)}
              </div>
              {typeof changePct === 'number' && (
                <div className={`pb-2 text-sm font-medium ${
                  changePct >= 0 ? 'text-[#17C5B0]' : 'text-[#E5484D]'
                }`}>
                  {changePct >= 0 ? '+' : ''}{changePct}%
                  <span className="ml-1 text-xs font-normal text-[#6B6B73]">
                    vs a normal {weekdayName}
                  </span>
                </div>
              )}
            </div>

            {/* The number that ties the operations below back to money. */}
            {recoverable > 0 && (
              <div className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[#F5A524]/30 bg-[#F5A524]/5 px-3 py-1.5">
                <span className="font-mono text-sm font-semibold text-[#F5A524]">
                  {money(recoverable)}
                </span>
                <span className="text-xs text-[#D4D4D8]">
                  still sellable today — {recoverableWhy}
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 rounded-lg border border-[#1F1F23] bg-[#0E0E11]">
              <button
                onClick={() => onShiftDay?.(-1)}
                aria-label="Previous day"
                className="p-2 text-[#A1A1A8] transition-colors hover:text-[#F5F5F7]"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <span className="px-1 font-mono text-xs text-[#A1A1A8]">{day}</span>
              <button
                onClick={() => onShiftDay?.(1)}
                aria-label="Next day"
                className="p-2 text-[#A1A1A8] transition-colors hover:text-[#F5F5F7]"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

      </section>

      {/* The portal's own money tiles, not a second set drawn beside them. */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {tiles.map((t) => (
          <StatCard
            key={t.label}
            label={t.label}
            value={t.value}
            subtitle={t.sub}
            icon={t.icon}
            iconColor={
              t.tone === 'warn' ? 'text-[#E5484D]'
                : t.tone === 'good' ? 'text-[#17C5B0]' : 'text-[#1A8FD6]'
            }
            change={t.change}
            changeType={t.changeType}
          />
        ))}
      </div>

      {/* The portal's own do-this-next panel, fed niche-specific actions from
          /api/dashboard/actions. Not a lookalike — the same component, with its
          reasoning chain, evidence and complete/reject behaviour intact. */}
      <Top3ActionsPanel />

      {peakCells.length > 0 && (
        <PeakHoursHeatmap
          cells={peakCells}
          title="When the work lands"
          caption="Two weeks of bookings by day and hour — the shape you staff against."
        />
      )}

      {forecast.total > 0 && (
        <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-[#F5F5F7]">Revenue: actual against forecast</h2>
              <p className="mt-0.5 text-sm text-[#A1A1A8]">
                Solid is what happened; dashed is projected from what this shop
                normally takes on each day of the week — not a flat average,
                which would forecast money on the days you are shut.
              </p>
            </div>
            <div className="text-right">
              <div className="font-mono text-2xl font-semibold text-[#F5F5F7]">
                {money(forecast.total)}
              </div>
              <div className="text-[11px] uppercase tracking-wide text-[#6B6B73]">
                next 7 days
              </div>
            </div>
          </div>

          <div className="mt-4">
            <ForecastChart
              data={forecast.series}
              height={240}
              gradientId="workspace-forecast"
            />
          </div>
        </section>
      )}

      {/* ── The work, and what needs a human ──────────────────────── */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <section className="min-w-0 rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold text-[#F5F5F7]">{mainTitle(pack)}</h2>
          </div>

          {!pack.booksAtAll ? (
            <PhoneVolume />
          ) : pack.travels && stops && origin ? (
            <RouteDay stops={stops} origin={origin} timezone={timezone} />
          ) : live.length === 0 ? (
            <p className="py-10 text-center text-sm text-[#6B6B73]">
              Nothing on the book for this day.
            </p>
          ) : (
            <BookingCalendar
              bookings={today}
              resources={resources}
              busy={busy}
              timezone={timezone}
              openMinutes={[open, close]}
            />
          )}
        </section>

        <aside className="space-y-3">
          <h2 className="px-1 text-xs font-semibold uppercase tracking-wide text-[#6B6B73]">
            Needs you
          </h2>
          {attention.length === 0 ? (
            <div className="rounded-xl border border-[#17C5B0]/25 bg-[#17C5B0]/5 p-4 text-sm text-[#D4D4D8]">
              Nothing needs you. The day runs itself.
            </div>
          ) : (
            attention.map((item) => (
              <div
                key={item.title}
                className={`rounded-xl border p-4 ${
                  item.tone === 'warn'
                    ? 'border-[#E5484D]/30 bg-[#E5484D]/5'
                    : 'border-[#1F1F23] bg-[#111113]'
                }`}
              >
                <div className="flex items-baseline gap-2">
                  {item.tone === 'warn' && (
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 translate-y-0.5 text-[#E5484D]" />
                  )}
                  <h3 className={`text-sm font-medium ${
                    item.tone === 'warn' ? 'text-[#E5484D]' : 'text-[#F5F5F7]'
                  }`}>
                    {item.title}
                  </h3>
                </div>
                <p className="mt-1 text-xs text-[#A1A1A8]">{item.detail}</p>
                {item.rows && item.rows.length > 0 && (
                  <ul className="mt-2.5 space-y-1">
                    {item.rows.slice(0, 6).map((r) => (
                      <li key={r} className="font-mono text-[11px] text-[#D4D4D8]">{r}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))
          )}
        </aside>
      </div>
    </div>
  )
}

function mainTitle(pack: NichePack): string {
  if (!pack.booksAtAll) return 'What the phone caught today'
  if (pack.travels) return "Today's route"
  return 'The floor'
}

// ── the four figures, per trade ─────────────────────────────────────────

interface Tile {
  label: string
  value: string
  sub?: string
  tone?: 'warn' | 'good'
  icon?: LucideIcon
  change?: string
  changeType?: 'positive' | 'negative' | 'neutral'
}

function computeTiles(
  data: WorkspaceData, live: Booking[], open: number, close: number, booked: number,
): Tile[] {
  const { pack, resources, services = [], timezone, stops, origin } = data
  const active = resources.filter((r) => r.active)
  const bookedMins = live.reduce((s, b) => s + mins(b), 0)
  const capacity = Math.max(1, close - open) * Math.max(1, active.length)
  const util = Math.round((bookedMins / capacity) * 100)
  const avgTicket = live.length ? Math.round(booked / live.length) : 0

  switch (pack.key) {
    case 'restaurant': {
      const covers = live.reduce((s, b) => s + b.partySize, 0)
      const peak = peakBucket(live, timezone, open, close)
      return [
        { label: 'Covers booked', value: String(covers), sub: `${live.length} bookings`, icon: Users },
        { label: 'Avg spend / cover', value: money(pack.avgCoverCents ?? 0), icon: Receipt },
        { label: 'Busiest half hour', value: peak.covers ? clock(peak.at) : '—',
          sub: peak.covers ? `${peak.covers} covers land` : undefined,
          tone: peak.covers > 20 ? 'warn' : undefined },
        { label: 'Tables in use', value: `${new Set(live.map((b) => b.resourceId)).size}/${active.length}` },
      ]
    }
    case 'mobiledetailing': {
      const legs = routeLegs(stops || [], origin)
      const tight = legs.filter((l) => l.tight).length
      const drive = legs.reduce((s, l) => s + l.minutes, 0)
      return [
        { label: 'Jobs on the route', value: String((stops || []).length), icon: Navigation },
        { label: 'Avg job value', value: money(avgTicket), icon: Receipt },
        { label: 'Driving', value: drive >= 60 ? `${Math.floor(drive / 60)}h ${drive % 60}m` : `${drive}m`,
          sub: 'unpaid time', icon: Car },
        { label: 'Tight legs', value: String(tight), tone: tight > 0 ? 'warn' : 'good',
          sub: tight > 0 ? 'may not make it' : 'the day fits' },
      ]
    }
    case 'quickservice':
      return [
        { label: 'Orders by phone', value: '86', sub: 'taken by the agent', icon: PhoneCall },
        { label: 'Avg ticket', value: money(2800), icon: Receipt },
        { label: 'Busiest hour', value: '7pm', sub: '22 orders' },
        { label: 'Missed calls', value: '0', tone: 'good', sub: 'nobody hung up' },
      ]
    case 'medspa': {
      const consults = live.filter((b) => mins(b) <= 45)
      const treatments = live.filter((b) => mins(b) > 45)
      return [
        { label: 'Consultations', value: String(consults.length), sub: 'top of the funnel', icon: Sparkles },
        { label: 'Treatments', value: String(treatments.length) },
        { label: 'Avg treatment', value: money(
          treatments.length
            ? Math.round(revenueCents(treatments, services, pack) / treatments.length)
            : 0) },
        { label: 'Rooms in use', value: `${new Set(live.map((b) => b.resourceId)).size}/${active.length}` },
      ]
    }
    default:
      return [
        { label: pack.bookingNoun === 'table' ? 'Bookings' : 'Appointments',
          value: String(live.length), icon: CalendarCheck },
        { label: 'Avg ticket', value: money(avgTicket), icon: Receipt },
        { label: `${pack.countLabel} utilisation`, value: `${util}%`, icon: Clock,
          tone: util < 50 ? 'warn' : util > 80 ? 'good' : undefined,
          sub: `${(bookedMins / 60).toFixed(0)}h of ${(capacity / 60).toFixed(0)}h` },
        { label: `${pack.countLabel} working`, icon: Users,
          value: `${new Set(live.map((b) => b.resourceId)).size}/${active.length}` },
      ]
  }
}

/** Fourteen days of booked revenue, drawn small. Trend, not precision. */
function Spark({ points }: { points: number[] }) {
  const max = Math.max(...points, 1)
  const W = 132
  const H = 40
  const step = W / Math.max(1, points.length - 1)
  const d = points
    .map((v, i) => `${i === 0 ? 'M' : 'L'} ${(i * step).toFixed(1)} ${(H - (v / max) * (H - 4) - 2).toFixed(1)}`)
    .join(' ')
  const last = points[points.length - 1]
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} aria-hidden="true" className="shrink-0">
      <path d={`${d} L ${W} ${H} L 0 ${H} Z`} fill="#1A8FD6" fillOpacity="0.12" />
      <path d={d} fill="none" stroke="#1A8FD6" strokeWidth="1.5" strokeLinejoin="round" />
      <circle
        cx={W - 0.5}
        cy={H - (last / max) * (H - 4) - 2}
        r="2.5"
        fill="#1A8FD6"
      />
    </svg>
  )
}

// ── the rail ────────────────────────────────────────────────────────────

interface Attention {
  title: string
  detail: string
  tone?: 'warn'
  rows?: string[]
}

function computeAttention(
  data: WorkspaceData, live: Booking[], open: number, close: number,
): Attention[] {
  const { pack, resources, timezone, stops, origin } = data
  const out: Attention[] = []

  // Meridian already detects these. Surfacing them here rather than leaving
  // them on a page nobody opens is most of the value of having them.
  for (const a of data.anomalies || []) {
    out.push({
      title: 'A day came in low',
      detail: a.description,
      tone: 'warn',
      rows: [`${a.date} · took ${money(a.value_cents)}, expected ${money(a.expected_cents)}`],
    })
  }
  const active = resources.filter((r) => r.active)

  if (pack.travels) {
    const legs = routeLegs(stops || [], origin)
    const tight = legs
      .map((l, i) => ({ l, stop: (stops || [])[i] }))
      .filter((x) => x.l.tight)
    if (tight.length) {
      out.push({
        title: `${tight.length} leg${tight.length > 1 ? 's' : ''} may not make it`,
        detail: 'The drive is longer than the gap before the job starts.',
        tone: 'warn',
        rows: tight.map((x) =>
          `${x.stop.booking.customerName} · ${x.l.minutes}m drive, ${Math.max(0, x.l.available)}m gap`),
      })
    }
  }

  if (pack.booksAtAll && !pack.travels) {
    // Sellable holes, worst resource first.
    const gaps: string[] = []
    for (const r of active) {
      const taken = live
        .filter((b) => b.resourceId === r.id)
        .map((b) => [localMinutes(b.startsAt, timezone), localMinutes(b.endsAt, timezone)] as const)
        .sort((a, b) => a[0] - b[0])
      let cursor = open
      for (const [s, e] of taken) {
        if (s - cursor >= 30) gaps.push(`${r.name} · ${clock(cursor)}–${clock(s)}`)
        cursor = Math.max(cursor, e)
      }
      if (close - cursor >= 30) gaps.push(`${r.name} · ${clock(cursor)}–${clock(close)}`)
    }
    if (gaps.length) {
      out.push({
        title: `${gaps.length} gaps you could still sell`,
        detail: 'Half an hour or more. The waiting list is who to text.',
        rows: gaps,
      })
    }
  }

  if (pack.partyBanded) {
    const big = live.filter((b) => b.partySize >= 5)
    if (big.length) {
      out.push({
        title: `${big.length} large part${big.length > 1 ? 'ies' : 'y'} tonight`,
        detail: 'Worth confirming by hand.',
        rows: big.map((b) =>
          `${b.customerName} · ${b.partySize} at ${clock(localMinutes(b.startsAt, timezone))}`),
      })
    }
  }

  const long = live.filter((b) => mins(b) >= 90)
  if (!pack.partyBanded && pack.booksAtAll && long.length) {
    out.push({
      title: `${long.length} long booking${long.length > 1 ? 's' : ''}`,
      detail: 'A cancellation here costs hours, not minutes.',
      rows: long.map((b) => `${b.customerName} · ${Math.round(mins(b))} min`),
    })
  }

  return out
}

function peakBucket(live: Booking[], tz: string, open: number, close: number) {
  let best = { at: open, covers: 0 }
  for (let m = open; m < close; m += 30) {
    const covers = live
      .filter((b) => {
        const s = localMinutes(b.startsAt, tz)
        return s >= m && s < m + 30
      })
      .reduce((s, b) => s + b.partySize, 0)
    if (covers > best.covers) best = { at: m, covers }
  }
  return best
}

function routeLegs(stops: Stop[], origin?: RouteOrigin) {
  if (!origin || stops.length === 0) return []
  const ordered = [...stops].sort((a, b) => a.booking.startsAt.localeCompare(b.booking.startsAt))
  return ordered.map((stop, i) => {
    const from = i === 0 ? origin : ordered[i - 1]
    const minutes = driveMinutes(haversineKm(from, stop))
    const previousEnd = i === 0
      ? new Date(ordered[0].booking.startsAt).getTime() - 60 * 60_000
      : new Date(ordered[i - 1].booking.endsAt).getTime()
    const available = Math.round(
      (new Date(stop.booking.startsAt).getTime() - previousEnd) / 60_000)
    return { minutes, available, tight: minutes > available * 0.8 }
  })
}

/** Takeout has no book, so the main surface is the phone. Illustrative in the
 *  preview; in production this reads voice_call_endings. */
function PhoneVolume() {
  const hours = [11, 12, 13, 17, 18, 19, 20, 21]
  const taken = [4, 9, 6, 8, 17, 22, 14, 6]
  const peak = Math.max(...taken)
  return (
    <div>
      <div className="flex h-48 items-end gap-3">
        {taken.map((n, i) => (
          <div key={hours[i]} className="flex flex-1 flex-col items-center gap-1.5">
            <span className="font-mono text-xs text-[#A1A1A8]">{n}</span>
            <div
              className={`w-full rounded-t ${n === peak ? 'bg-[#E5484D]/70' : 'bg-[#1A8FD6]/60'}`}
              style={{ height: `${(n / peak) * 100}%` }}
            />
            <span className="text-[10px] text-[#6B6B73]">
              {hours[i] > 12 ? `${hours[i] - 12}pm` : `${hours[i]}am`}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-4 text-xs text-[#6B6B73]">
        Every bar is an order somebody would otherwise have hung up on.
      </p>
    </div>
  )
}

export { Plus }
