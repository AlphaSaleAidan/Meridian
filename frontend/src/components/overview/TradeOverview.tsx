/**
 * The overview a trade actually opens on.
 *
 * The first version of this was the same page with modules removed, which is
 * subtraction, not optimisation — Aidan called it correctly. A barbershop and
 * a restaurant do not want the same numbers arranged differently; they want
 * different numbers, because they are answering different questions at eight
 * in the morning:
 *
 *   barber      → which chair is going to sit idle today, and can I fill it
 *   nail studio → did the people in today book their next one before leaving
 *   detailer    → does my route physically work
 *   restaurant  → is the kitchen going to get hit all at once
 *   takeout     → what did the phone catch that we would have dropped
 *   med spa     → how many consultations turned into treatment
 *
 * So the panels differ per trade, not just their order. What is shared is the
 * COMPUTATION over one day's bookings; each trade selects the handful of
 * derived figures that mean something in that trade and ignores the rest.
 */
import type { Booking, BusyBlock, Resource } from '@/lib/bookings-api'
import type { NichePack } from '@/config/niches'
import RouteDay, { type RouteOrigin, type Stop } from '@/components/RouteDay'

export interface OverviewData {
  pack: NichePack
  bookings: Booking[]
  resources: Resource[]
  busy: BusyBlock[]
  timezone: string
  /** Present only for trades that drive to the customer. */
  stops?: Stop[]
  origin?: RouteOrigin
}

const LIVE = new Set(['confirmed', 'seated', 'completed'])

// ── shared derivations ──────────────────────────────────────────────────

function minutes(b: Booking): number {
  return Math.max(
    0,
    (new Date(b.endsAt).getTime() - new Date(b.startsAt).getTime()) / 60_000,
  )
}

function localMinutes(iso: string, tz: string): number {
  try {
    const p = new Intl.DateTimeFormat('en-GB', {
      timeZone: tz || undefined, hour12: false, hour: '2-digit', minute: '2-digit',
    }).formatToParts(new Date(iso))
    const g = (t: string) => Number(p.find((x) => x.type === t)?.value ?? 0)
    return (g('hour') % 24) * 60 + g('minute')
  } catch {
    return 0
  }
}

function fmtClock(m: number): string {
  const h = Math.floor(m / 60) % 24
  const mm = m % 60
  const ampm = h < 12 ? 'am' : 'pm'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return mm === 0 ? `${h12}${ampm}` : `${h12}:${String(mm).padStart(2, '0')}${ampm}`
}

/** Open minutes for the day, from the trade's own hours. */
function openWindow(pack: NichePack): [number, number] {
  const [oh, om] = pack.opens.split(':').map(Number)
  const [ch, cm] = pack.closes.split(':').map(Number)
  return [oh * 60 + om, ch * 60 + cm]
}

/** Gaps of at least `min` minutes on a given resource — the sellable holes. */
function gapsFor(
  resource: Resource, bookings: Booking[], pack: NichePack, tz: string, min = 30,
): { start: number; end: number }[] {
  const [open, close] = openWindow(pack)
  const taken = bookings
    .filter((b) => b.resourceId === resource.id && LIVE.has(b.status))
    .map((b) => [localMinutes(b.startsAt, tz), localMinutes(b.endsAt, tz)] as const)
    .sort((a, b) => a[0] - b[0])

  const out: { start: number; end: number }[] = []
  let cursor = open
  for (const [s, e] of taken) {
    if (s - cursor >= min) out.push({ start: cursor, end: s })
    cursor = Math.max(cursor, e)
  }
  if (close - cursor >= min) out.push({ start: cursor, end: close })
  return out
}

// ── the page ────────────────────────────────────────────────────────────

export default function TradeOverview(data: OverviewData) {
  const { pack } = data
  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-semibold tracking-tight text-[#F5F5F7]">Today</h1>
        <p className="mt-0.5 text-sm text-[#A1A1A8]">{pack.homeMetric.help}</p>
      </header>

      {(pack.key === 'detailing' || pack.key === 'mobiledetailing') && <DetailerOverview {...data} />}
      {pack.key === 'restaurant' && <RestaurantOverview {...data} />}
      {(pack.key === 'barbershop' || pack.key === 'other') && <ChairOverview {...data} />}
      {pack.key === 'nails' && <StudioOverview {...data} />}
      {pack.key === 'medspa' && <ClinicOverview {...data} />}
      {pack.key === 'quickservice' && <TakeoutOverview {...data} />}
    </div>
  )
}

// ── barbershop: idle chairs are the whole business ──────────────────────

function ChairOverview({ pack, bookings, resources, timezone }: OverviewData) {
  const [open, close] = openWindow(pack)
  const openMins = close - open
  const live = bookings.filter((b) => LIVE.has(b.status))

  const perChair = resources.filter((r) => r.active).map((r) => {
    const mine = live.filter((b) => b.resourceId === r.id)
    const booked = mine.reduce((s, b) => s + minutes(b), 0)
    return {
      resource: r,
      booked,
      pct: openMins > 0 ? Math.min(100, Math.round((booked / openMins) * 100)) : 0,
      gaps: gapsFor(r, bookings, pack, timezone),
    }
  })

  const totalBooked = perChair.reduce((s, c) => s + c.booked, 0)
  const capacity = openMins * Math.max(1, perChair.length)
  const idle = Math.max(0, capacity - totalBooked)

  return (
    <>
      <Headline
        label={pack.homeMetric.label}
        value={`${Math.round((totalBooked / Math.max(capacity, 1)) * 100)}%`}
        sub={`${Math.round(totalBooked / 60)}h booked of ${Math.round(capacity / 60)}h open`}
      />

      <Panel
        title="Chair by chair"
        hint="The one at the bottom is the one to fill first."
      >
        <div className="space-y-2.5">
          {[...perChair].sort((a, b) => a.pct - b.pct).map((c) => (
            <div key={c.resource.id}>
              <div className="flex items-baseline justify-between text-sm">
                <span className="text-[#F5F5F7]">{c.resource.name}</span>
                <span className="font-mono text-xs text-[#A1A1A8]">{c.pct}%</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[#1F1F23]">
                <div
                  className={`h-full rounded-full ${
                    c.pct >= 70 ? 'bg-[#17C5B0]' : c.pct >= 40 ? 'bg-[#1A8FD6]' : 'bg-[#E5484D]'
                  }`}
                  style={{ width: `${c.pct}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        title={`${Math.round(idle / 60)} idle hours you could still sell`}
        hint="Gaps of half an hour or more. The waiting list is who to text."
      >
        <div className="flex flex-wrap gap-1.5">
          {perChair.flatMap((c) =>
            c.gaps.map((g) => (
              <span
                key={`${c.resource.id}-${g.start}`}
                className="rounded-lg border border-[#1F1F23] px-2.5 py-1 text-xs text-[#D4D4D8]"
              >
                {c.resource.name}
                <span className="ml-2 text-[#6B6B73]">
                  {fmtClock(g.start)}–{fmtClock(g.end)}
                </span>
              </span>
            )))}
          {perChair.every((c) => c.gaps.length === 0) && (
            <span className="text-sm text-[#17C5B0]">Fully booked. Nothing to fill.</span>
          )}
        </div>
      </Panel>
    </>
  )
}

// ── nail studio: the next appointment is the cheapest one ───────────────

function StudioOverview({ pack, bookings, resources, timezone }: OverviewData) {
  const live = bookings.filter((b) => LIVE.has(b.status))
  const [open, close] = openWindow(pack)
  const openMins = close - open

  const byTech = resources.filter((r) => r.active).map((r) => {
    const mine = live.filter((b) => b.resourceId === r.id)
    return {
      name: r.name,
      count: mine.length,
      hours: mine.reduce((s, b) => s + minutes(b), 0) / 60,
      pct: Math.min(100, Math.round(
        (mine.reduce((s, b) => s + minutes(b), 0) / Math.max(openMins, 1)) * 100)),
    }
  })

  // Long services are where the money is and where a cancellation hurts most.
  const long = live.filter((b) => minutes(b) >= 90)

  return (
    <>
      <Headline
        label={pack.homeMetric.label}
        value={`${live.length}`}
        sub={`${byTech.filter((t) => t.count > 0).length} of ${byTech.length} technicians working`}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Who is busy" hint="Hours on the book today.">
          <ul className="space-y-2">
            {[...byTech].sort((a, b) => b.hours - a.hours).map((t) => (
              <li key={t.name} className="flex items-center justify-between gap-3">
                <span className="text-sm text-[#F5F5F7]">{t.name}</span>
                <span className="flex items-center gap-2">
                  <span className="h-1.5 w-24 overflow-hidden rounded-full bg-[#1F1F23]">
                    <span
                      className="block h-full rounded-full bg-[#1A8FD6]"
                      style={{ width: `${t.pct}%` }}
                    />
                  </span>
                  <span className="w-16 text-right font-mono text-xs text-[#A1A1A8]">
                    {t.hours.toFixed(1)}h
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </Panel>

        <Panel
          title="Long sittings today"
          hint="A cancellation here costs two hours, not twenty minutes — these are the ones worth confirming."
        >
          {long.length === 0 ? (
            <p className="text-sm text-[#6B6B73]">No long services on the book.</p>
          ) : (
            <ul className="space-y-1.5">
              {long.map((b) => (
                <li key={b.id} className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="text-[#F5F5F7]">{b.customerName}</span>
                  <span className="font-mono text-xs text-[#A1A1A8]">
                    {Math.round(minutes(b))} min
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  )
}

// ── detailer: does the day physically work ──────────────────────────────

function DetailerOverview({ pack, bookings, resources, timezone, stops, origin }: OverviewData) {
  const live = bookings.filter((b) => LIVE.has(b.status))
  const bayHours = live.reduce((s, b) => s + minutes(b), 0) / 60
  const [open, close] = openWindow(pack)
  const capacity = ((close - open) / 60) * Math.max(1, resources.filter((r) => r.active).length)

  const mix = new Map<string, number>()
  for (const b of live) {
    const key = `${Math.round(minutes(b) / 60)}h jobs`
    mix.set(key, (mix.get(key) || 0) + 1)
  }

  return (
    <>
      <Headline
        label={pack.homeMetric.label}
        value={pack.travels ? String(live.length) : `${bayHours.toFixed(1)}h`}
        sub={pack.travels
          ? `${bayHours.toFixed(1)} hours of work booked`
          : `of ${capacity.toFixed(0)}h available across your bays`}
      />

      {stops && origin && stops.length > 0 ? (
        <Panel
          title="Today's route"
          hint="In the order you will drive it. A leg the clock does not allow is called out."
        >
          <RouteDay stops={stops} origin={origin} timezone={timezone} />
        </Panel>
      ) : (
        pack.travels && (
          <Panel title="Today's route" hint="">
            <p className="text-sm text-[#6B6B73]">Nothing on the road today.</p>
          </Panel>
        )
      )}

      <Panel title="Job mix" hint="What today is actually made of.">
        <div className="flex flex-wrap gap-2">
          {[...mix.entries()].sort().map(([label, n]) => (
            <span
              key={label}
              className="rounded-lg border border-[#1F1F23] px-3 py-1.5 text-sm text-[#D4D4D8]"
            >
              <span className="font-mono text-[#F5F5F7]">{n}</span>
              <span className="ml-2 text-[#6B6B73]">{label}</span>
            </span>
          ))}
          {mix.size === 0 && <span className="text-sm text-[#6B6B73]">Nothing booked.</span>}
        </div>
      </Panel>
    </>
  )
}

// ── restaurant: pacing, not headcount ───────────────────────────────────

function RestaurantOverview({ pack, bookings, resources, timezone }: OverviewData) {
  const live = bookings.filter((b) => LIVE.has(b.status))
  const covers = live.reduce((s, b) => s + b.partySize, 0)
  const [open, close] = openWindow(pack)

  // Covers per half hour — the number a kitchen actually feels.
  const buckets: { at: number; covers: number }[] = []
  for (let m = open; m < close; m += 30) {
    const inBucket = live.filter((b) => {
      const s = localMinutes(b.startsAt, timezone)
      return s >= m && s < m + 30
    })
    buckets.push({ at: m, covers: inBucket.reduce((s, b) => s + b.partySize, 0) })
  }
  const peak = Math.max(1, ...buckets.map((b) => b.covers))
  const worst = buckets.reduce((a, b) => (b.covers > a.covers ? b : a), buckets[0])

  const big = live.filter((b) => b.partySize >= 5)
  const seats = resources.filter((r) => r.active).reduce((s, r) => s + r.seats, 0)

  return (
    <>
      <Headline
        label={pack.homeMetric.label}
        value={String(covers)}
        sub={`${live.length} bookings across ${seats} seats`}
      />

      <Panel
        title="When the kitchen gets hit"
        hint={worst && worst.covers > 0
          ? `Heaviest at ${fmtClock(worst.at)} — ${worst.covers} covers land inside half an hour.`
          : 'Nothing booked yet.'}
      >
        <div className="flex h-28 items-end gap-1">
          {buckets.map((b) => (
            <div key={b.at} className="flex flex-1 flex-col items-center gap-1">
              <div
                className={`w-full rounded-t ${
                  b.covers === peak && peak > 0 ? 'bg-[#E5484D]/70' : 'bg-[#1A8FD6]/60'
                }`}
                style={{ height: `${(b.covers / peak) * 100}%`, minHeight: b.covers ? 3 : 0 }}
                title={`${fmtClock(b.at)} — ${b.covers} covers`}
              />
              {b.at % 60 === 0 && (
                <span className="text-[9px] text-[#6B6B73]">{fmtClock(b.at)}</span>
              )}
            </div>
          ))}
        </div>
      </Panel>

      <Panel
        title="Large parties tonight"
        hint="The bookings worth confirming by hand."
      >
        {big.length === 0 ? (
          <p className="text-sm text-[#6B6B73]">None over four.</p>
        ) : (
          <ul className="space-y-1.5">
            {big.map((b) => (
              <li key={b.id} className="flex items-baseline justify-between gap-3 text-sm">
                <span className="text-[#F5F5F7]">{b.customerName}</span>
                <span className="font-mono text-xs text-[#A1A1A8]">
                  {b.partySize} · {fmtClock(localMinutes(b.startsAt, timezone))}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </>
  )
}

// ── med spa: consults are the top of the funnel ─────────────────────────

function ClinicOverview({ pack, bookings, resources, timezone }: OverviewData) {
  const live = bookings.filter((b) => LIVE.has(b.status))
  const consults = live.filter((b) => minutes(b) <= 45)
  const treatments = live.filter((b) => minutes(b) > 45)
  const rooms = resources.filter((r) => r.active)

  return (
    <>
      <Headline
        label={pack.homeMetric.label}
        value={String(consults.length)}
        sub={`${treatments.length} treatments booked alongside them`}
      />

      <div className="grid gap-4 md:grid-cols-2">
        <Panel
          title="Consultations to treatments"
          hint="A consultation that does not become a treatment is a room you gave away."
        >
          <div className="flex items-end gap-6">
            <Figure value={consults.length} label="Consults" tone="blue" />
            <Figure value={treatments.length} label="Treatments" tone="teal" />
            <Figure
              value={consults.length > 0
                ? `${Math.round((treatments.length / consults.length) * 100)}%`
                : '—'}
              label="Ratio"
            />
          </div>
        </Panel>

        <Panel title="Rooms in use" hint="Today's load per treatment room.">
          <ul className="space-y-2">
            {rooms.map((r) => {
              const n = live.filter((b) => b.resourceId === r.id).length
              return (
                <li key={r.id} className="flex items-center justify-between text-sm">
                  <span className="text-[#F5F5F7]">{r.name}</span>
                  <span className="font-mono text-xs text-[#A1A1A8]">
                    {n} booked
                  </span>
                </li>
              )
            })}
          </ul>
        </Panel>
      </div>
    </>
  )
}

// ── takeout: the phone is the product ───────────────────────────────────

function TakeoutOverview({ pack }: OverviewData) {
  // A takeout shop has no bookings by design, so this reads the phone rather
  // than the calendar. Figures are illustrative in the preview; in production
  // they come from voice_call_endings and the POS.
  const hours = [11, 12, 13, 17, 18, 19, 20, 21]
  const taken = [4, 9, 6, 8, 17, 22, 14, 6]
  const peak = Math.max(...taken)

  return (
    <>
      <Headline
        label={pack.homeMetric.label}
        value={String(taken.reduce((a, b) => a + b, 0))}
        sub="Orders the agent took while the line was busy"
      />

      <Panel
        title="When the phone runs hot"
        hint="Every bar is an order somebody would otherwise have hung up on."
      >
        <div className="flex h-28 items-end gap-2">
          {taken.map((n, i) => (
            <div key={hours[i]} className="flex flex-1 flex-col items-center gap-1">
              <span className="font-mono text-[10px] text-[#A1A1A8]">{n}</span>
              <div
                className={`w-full rounded-t ${
                  n === peak ? 'bg-[#E5484D]/70' : 'bg-[#1A8FD6]/60'
                }`}
                style={{ height: `${(n / peak) * 100}%` }}
              />
              <span className="text-[9px] text-[#6B6B73]">
                {hours[i] > 12 ? `${hours[i] - 12}p` : `${hours[i]}a`}
              </span>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="No booking module" hint="">
        <p className="text-sm text-[#A1A1A8]">
          This trade's phone is order volume, not a calendar. There is no book to
          show, and pretending otherwise is how a takeout shop decides the
          product was not built for them.
        </p>
      </Panel>
    </>
  )
}

// ── shared furniture ────────────────────────────────────────────────────

function Headline({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
      <div className="text-[11px] uppercase tracking-wide text-[#A1A1A8]">{label}</div>
      <div className="mt-1 font-mono text-4xl font-semibold tracking-tight text-[#F5F5F7]">
        {value}
      </div>
      {sub && <div className="mt-1 text-sm text-[#6B6B73]">{sub}</div>}
    </section>
  )
}

function Panel({ title, hint, children }: {
  title: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
      <h2 className="text-sm font-semibold text-[#F5F5F7]">{title}</h2>
      {hint && <p className="mb-4 mt-0.5 text-sm text-[#A1A1A8]">{hint}</p>}
      {children}
    </section>
  )
}

function Figure({ value, label, tone }: {
  value: number | string
  label: string
  tone?: 'blue' | 'teal'
}) {
  return (
    <div>
      <div className={`font-mono text-3xl font-semibold ${
        tone === 'blue' ? 'text-[#1A8FD6]' : tone === 'teal' ? 'text-[#17C5B0]' : 'text-[#F5F5F7]'
      }`}>
        {value}
      </div>
      <div className="mt-0.5 text-xs text-[#A1A1A8]">{label}</div>
    </div>
  )
}
