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
import type { Booking, BusyBlock, Resource } from '@/lib/bookings-api'
import type { NichePack } from '@/config/niches'
import BookingCalendar from '@/components/BookingCalendar'
import RouteDay, { haversineKm, driveMinutes, type RouteOrigin, type Stop } from '@/components/RouteDay'

const LIVE = new Set(['confirmed', 'seated', 'completed'])

export interface WorkspaceData {
  pack: NichePack
  bookings: Booking[]
  resources: Resource[]
  busy: BusyBlock[]
  timezone: string
  day: string
  onShiftDay?: (delta: number) => void
  stops?: Stop[]
  origin?: RouteOrigin
  shopName: string
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
  const live = bookings.filter((b) => LIVE.has(b.status))
  const [open, close] = openWindow(pack)

  const headline = useMemo(() => computeHeadline(data, live, open, close), [data, live, open, close])
  const attention = useMemo(() => computeAttention(data, live, open, close), [data, live, open, close])

  const dayLabel = new Date(`${day}T12:00:00`).toLocaleDateString('en-CA', {
    weekday: 'long', month: 'long', day: 'numeric',
  })

  return (
    <div className="space-y-4">
      {/* ── The decision line ─────────────────────────────────────── */}
      <section className="rounded-xl border border-[#1F1F23] bg-gradient-to-br from-[#12171C] to-[#111113] p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="text-[11px] uppercase tracking-[0.14em] text-[#6B6B73]">
              {dayLabel}
            </div>
            <div className="mt-3 flex items-end gap-4">
              <div className="font-mono text-[56px] font-semibold leading-none tracking-tight text-[#F5F5F7]">
                {headline.value}
              </div>
              <div className="pb-1.5">
                <div className="text-sm font-medium text-[#F5F5F7]">{headline.label}</div>
                <div className="text-xs text-[#6B6B73]">{headline.sub}</div>
              </div>
            </div>
          </div>

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

        {headline.stats.length > 0 && (
          <div className="mt-6 flex flex-wrap gap-x-10 gap-y-3 border-t border-[#1F1F23] pt-4">
            {headline.stats.map((s) => (
              <div key={s.label}>
                <div className={`font-mono text-xl font-semibold ${
                  s.tone === 'warn' ? 'text-[#E5484D]'
                    : s.tone === 'good' ? 'text-[#17C5B0]' : 'text-[#F5F5F7]'
                }`}>
                  {s.value}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-[#6B6B73]">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

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
              bookings={bookings}
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

// ── per-trade headline ──────────────────────────────────────────────────

interface Stat { label: string; value: string; tone?: 'warn' | 'good' }

function computeHeadline(
  data: WorkspaceData, live: Booking[], open: number, close: number,
): { value: string; label: string; sub: string; stats: Stat[] } {
  const { pack, resources, timezone, stops, origin } = data
  const active = resources.filter((r) => r.active)
  const openMins = Math.max(1, close - open)
  const bookedMins = live.reduce((s, b) => s + mins(b), 0)
  const capacity = openMins * Math.max(1, active.length)

  switch (pack.key) {
    case 'restaurant': {
      const covers = live.reduce((s, b) => s + b.partySize, 0)
      const seats = active.reduce((s, r) => s + r.seats, 0)
      const peak = peakBucket(live, timezone, open, close)
      return {
        value: String(covers),
        label: 'covers booked',
        sub: `${live.length} bookings · ${seats} seats on the floor`,
        stats: [
          { label: 'Busiest half hour', value: peak.covers ? clock(peak.at) : '—' },
          { label: 'Covers then', value: String(peak.covers), tone: peak.covers > seats * 0.6 ? 'warn' : undefined },
          { label: 'Tables in use', value: `${new Set(live.map((b) => b.resourceId)).size}/${active.length}` },
        ],
      }
    }
    case 'mobiledetailing': {
      const legs = routeLegs(stops || [], origin)
      const tight = legs.filter((l) => l.tight).length
      const drive = legs.reduce((s, l) => s + l.minutes, 0)
      return {
        value: String((stops || []).length),
        label: 'stops on the route',
        sub: `${(bookedMins / 60).toFixed(1)} hours of work booked`,
        stats: [
          { label: 'Driving', value: drive >= 60 ? `${Math.floor(drive / 60)}h ${drive % 60}m` : `${drive}m` },
          { label: 'Tight legs', value: String(tight), tone: tight > 0 ? 'warn' : 'good' },
        ],
      }
    }
    case 'quickservice':
      return {
        value: '86',
        label: 'orders taken by phone',
        sub: 'Orders the agent took while the line was busy',
        stats: [
          { label: 'Busiest hour', value: '7pm' },
          { label: 'Missed calls', value: '0', tone: 'good' },
        ],
      }
    case 'medspa': {
      const consults = live.filter((b) => mins(b) <= 45).length
      const treatments = live.length - consults
      return {
        value: String(consults),
        label: 'consultations booked',
        sub: `${treatments} treatments alongside them`,
        stats: [
          { label: 'Rooms in use', value: `${new Set(live.map((b) => b.resourceId)).size}/${active.length}` },
          { label: 'Consult to treatment', value: consults ? `${Math.round((treatments / consults) * 100)}%` : '—' },
        ],
      }
    }
    default: {
      const pct = Math.round((bookedMins / capacity) * 100)
      const idle = Math.max(0, capacity - bookedMins)
      return {
        value: `${pct}%`,
        label: pack.homeMetric.label.toLowerCase(),
        sub: `${(bookedMins / 60).toFixed(0)}h booked of ${(capacity / 60).toFixed(0)}h open`,
        stats: [
          { label: 'Idle hours', value: `${(idle / 60).toFixed(0)}h`, tone: idle > capacity * 0.4 ? 'warn' : undefined },
          { label: `${pack.countLabel} working`, value: `${new Set(live.map((b) => b.resourceId)).size}/${active.length}` },
          { label: 'Booked', value: String(live.length) },
        ],
      }
    }
  }
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
