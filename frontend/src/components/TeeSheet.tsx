/**
 * The tee sheet — drawn the way the industry tools draw it, because every
 * golf operator already runs their morning on one of them.
 *
 * The conventions this follows (ForeUP, Lightspeed Golf, GolfNow G1):
 *
 *   - A ROW PER START TIME at the course's own interval, a column per
 *     starting tee. Time runs down, not across — a starter reads a sheet
 *     top to bottom the way a host reads a book.
 *   - FOUR SEAT CELLS PER ROW. The foursome is the unit of capacity, so a
 *     party of two must read as two filled seats and two SELLABLE ones —
 *     not as an opaque chip that hides the money still sitting on the row.
 *   - Blocks (leagues, maintenance, shotguns) span their rows and say why.
 *   - 9/18 and booking source are glyphs on the party, not prose.
 *
 * Party grouping is honest to the engine: one booking owns the tee time and
 * the party is its size. The lead's name labels the party; the remaining
 * seats render as open cells because that is exactly what they are.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { Check, Phone } from 'lucide-react'
import type { Booking, BusyBlock, Resource, Service } from '@/lib/bookings-api'
import { localMinutes } from '@/components/BookingCalendar'

const SEATS = 4

/** Below this width the sheet shows one tee at a time. Matches Tailwind sm. */
const NARROW_QUERY = '(max-width: 639px)'

function useIsNarrow(): boolean {
  const [narrow, setNarrow] = useState(
    () => typeof window !== 'undefined' && window.matchMedia(NARROW_QUERY).matches,
  )
  useEffect(() => {
    const mq = window.matchMedia(NARROW_QUERY)
    const onChange = () => setNarrow(mq.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])
  return narrow
}

/** Same palette as the day grid, so a status reads the same on both. */
const PARTY_BLOCK: Record<string, string> = {
  offered: 'border-[#F5A524]/40 bg-[#F5A524]/10 text-[#F5A524]',
  confirmed: 'border-[#1A8FD6]/40 bg-[#1A8FD6]/12 text-[#8dcef2]',
  seated: 'border-[#17C5B0]/40 bg-[#17C5B0]/12 text-[#17C5B0]',
  completed: 'border-[#A1A1A8]/25 bg-[#A1A1A8]/8 text-[#A1A1A8]',
  cancelled: 'border-[#A1A1A8]/20 bg-transparent text-[#6B6B73]',
  no_show: 'border-[#E5484D]/30 bg-[#E5484D]/8 text-[#E5484D]',
}

/** What a status means ON A COURSE — "seated" is the engine's word, not the
 *  starter's. Display only; the record keeps its own vocabulary. */
const STATUS_WORD: Record<string, string> = {
  offered: 'held', confirmed: 'booked', seated: 'on course',
  completed: 'finished', cancelled: 'cancelled', no_show: 'no-show',
}

/** Checked in: the group has reached the counter. */
const checkedIn = (b: Booking) => b.status === 'seated' || b.status === 'completed'

/** Paid, by the two routes money actually arrives: online bookings prepay,
 *  everyone else pays when they check in. A phone booking that has not
 *  reached the counter is the one true "unpaid" on the sheet — exactly the
 *  group the starter wants to spot before they walk to the 1st. */
const isPaid = (b: Booking) => b.source !== 'phone' ? b.status !== 'offered' : checkedIn(b)

function timeLabel(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24
  const m = minutes % 60
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${h12}:${String(m).padStart(2, '0')}`
}

interface Placed {
  booking: Booking
  row: number
  span: number
  /** Round bookings hold seats; a lesson holds the whole tee for its length. */
  seatTracked: boolean
  holes?: 9 | 18
}

export default function TeeSheet({
  bookings, resources, busy, timezone, openMinutes, services, day, onSelect,
}: {
  bookings: Booking[]
  resources: Resource[]
  busy: BusyBlock[]
  timezone: string
  openMinutes: [number, number]
  services: Service[]
  /** The sheet's date (YYYY-MM-DD, merchant-local). Drives the now line. */
  day?: string
  onSelect?: (booking: Booking) => void
}) {
  const tees = useMemo(
    () => resources.filter((r) => r.active)
      .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name)),
    [resources],
  )

  // On a phone the sheet shows ONE tee at a time — two columns in 350px
  // crushed every name to a single letter, and a sheet you cannot read names
  // off is not a sheet. The glance line still counts the whole course; only
  // the view narrows. Rows also grow to a real touch target.
  const isNarrow = useIsNarrow()
  const [teeIdx, setTeeIdx] = useState(0)
  // A chip that looks tappable must DO something when tapped. When the host
  // wires no onSelect, the sheet answers with its own detail card — the same
  // question a starter asks at the window: who is this, how many, paid yet?
  // The chip's rect is captured at click time so the desktop card can open
  // AT the chip rather than at the bottom of the screen.
  const [detail, setDetail] = useState<{
    p: Placed
    rect: { top: number; bottom: number; left: number }
  } | null>(null)

  // Escape closes, like every popover the operator already uses.
  useEffect(() => {
    if (!detail) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDetail(null) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [detail])
  const rowH = isNarrow ? 44 : 34
  const displayTees = isNarrow && tees.length > 1
    ? [tees[Math.min(teeIdx, tees.length - 1)]]
    : tees

  /** The start interval is what the course actually sells its rounds at —
   *  the shortest party-banded service — never a hardcoded fifteen. */
  const interval = useMemo(() => {
    const banded = services.filter((s) => s.active && s.maxParty > 1)
    const mins = banded.map((s) => s.durationMinutes).filter((d) => d > 0)
    return mins.length ? Math.min(...mins) : 15
  }, [services])

  const [open, close] = openMinutes
  const rows = Math.max(1, Math.ceil((close - open) / interval))

  const serviceById = useMemo(
    () => new Map(services.map((s) => [s.id, s])), [services],
  )

  const placed = useMemo(() => {
    const byTee = new Map<string, Placed[]>()
    for (const t of tees) byTee.set(t.id, [])
    for (const b of bookings) {
      if (b.status === 'cancelled') continue
      const col = byTee.get(b.resourceId)
      if (!col) continue
      const start = localMinutes(b.startsAt, timezone)
      let end = localMinutes(b.endsAt, timezone)
      if (end <= start) end = close
      const row = Math.floor((start - open) / interval)
      if (row < 0 || row >= rows) continue
      const span = Math.max(1, Math.min(rows - row, Math.ceil((end - start) / interval)))
      const svc = b.serviceId ? serviceById.get(b.serviceId) : undefined
      const seatTracked = (svc?.maxParty ?? SEATS) > 1 && span === 1
      const holes = svc ? (/\b9\b/.test(svc.name) ? 9 as const : /18/.test(svc.name) ? 18 as const : undefined) : undefined
      col.push({ booking: b, row, span, seatTracked, holes })
    }
    for (const col of byTee.values()) col.sort((a, b) => a.row - b.row)
    return byTee
  }, [bookings, tees, timezone, open, close, interval, rows, serviceById])

  const blocks = useMemo(() => busy.map((x) => {
    const start = localMinutes(x.startsAt, timezone)
    let end = localMinutes(x.endsAt, timezone)
    if (end <= start) end = close
    const row = Math.max(0, Math.floor((start - open) / interval))
    const span = Math.max(1, Math.min(rows - row, Math.ceil((end - start) / interval)))
    return { block: x, row, span }
  }), [busy, timezone, open, close, interval, rows])

  // The numbers an operator glances at before anything else: how full is the
  // sheet, and how many single seats are still sellable inside partial groups.
  // A HELD time is counted apart — it is not players on the sheet yet, and
  // the band above this sheet does not count it either. Two figures on one
  // screen that disagree teach the operator to trust neither.
  const { starts, players, openSeats, held } = useMemo(() => {
    let filled = 0; let heads = 0; let seatGaps = 0; let pending = 0
    for (const col of placed.values()) {
      for (const p of col) {
        if (p.booking.status === 'offered') { pending += 1; continue }
        filled += 1
        heads += p.booking.partySize
        if (p.seatTracked) seatGaps += Math.max(0, SEATS - p.booking.partySize)
      }
    }
    return { starts: filled, players: heads, openSeats: seatGaps, held: pending }
  }, [placed])

  const totalStarts = rows * Math.max(1, tees.length)
  const agentBooked = useMemo(
    () => bookings.filter((b) =>
      b.status !== 'cancelled' && b.status !== 'offered' && b.source === 'phone').length,
    [bookings],
  )

  // The now line, only when the sheet is showing today. "Now" is computed in
  // the MERCHANT's timezone, the same clock every row is placed on.
  const nowMin = useMemo(() => {
    if (!day) return null
    try {
      const todayLocal = new Intl.DateTimeFormat('en-CA', {
        timeZone: timezone || undefined, year: 'numeric', month: '2-digit', day: '2-digit',
      }).format(new Date())
      if (todayLocal !== day) return null
      const m = localMinutes(new Date().toISOString(), timezone)
      return m >= open && m <= close ? m : null
    } catch {
      return null
    }
  }, [day, timezone, open, close])
  const nowTop = nowMin == null ? null : ((nowMin - open) / interval) * rowH

  // Universal convention in every tool surveyed: the sheet opens centred on
  // now, not on 7am — the operator's question is always "who is up next".
  const scrollRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (nowTop != null && scrollRef.current) {
      scrollRef.current.scrollTop = Math.max(0, nowTop - 180)
    }
  }, [nowTop])

  return (
    <div>
      {/* The glance line. "Open seats" is the golf-only number: seats still
          sellable inside groups already on the sheet. And the agent count is
          the Meridian number — the sheet the phone filled by itself. */}
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#A1A1A8]">
        <span>
          <span className="font-mono text-[#F5F5F7]">{starts}</span>
          <span className="text-[#6B6B73]"> / {totalStarts}</span> starts filled
        </span>
        <span><span className="font-mono text-[#F5F5F7]">{players}</span> players</span>
        <span className={openSeats > 0 ? 'text-[#17C5B0]' : ''}>
          <span className="font-mono">{openSeats}</span> open seats in booked groups
        </span>
        {agentBooked > 0 && (
          <span className="text-[#1A8FD6]">
            <span className="font-mono">{agentBooked}</span> booked by the phone agent
          </span>
        )}
        {held > 0 && (
          <span className="text-[#F5A524]" title="A held time is mid-checkout online or offered to the waitlist — locked so it cannot be double-sold.">
            <span className="font-mono">{held}</span> held
          </span>
        )}
      </div>

      {/* One tee at a time on a phone: the starter picks which tee they are
          standing on. Segmented, not a dropdown — it is a two-way choice. */}
      {isNarrow && tees.length > 1 && (
        <div className="mb-2 flex rounded-lg border border-[#1F1F23] bg-[#0E0E11] p-0.5">
          {tees.map((t, i) => (
            <button
              key={t.id}
              onClick={() => setTeeIdx(i)}
              className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
                i === Math.min(teeIdx, tees.length - 1)
                  ? 'bg-[#1A8FD6]/15 text-[#8dcef2]'
                  : 'text-[#A1A1A8]'
              }`}
            >
              {t.name}
            </button>
          ))}
        </div>
      )}

      <div ref={scrollRef} className="max-h-[600px] overflow-y-auto rounded-lg border border-[#1F1F23]">
        <div
          className="grid"
          style={{ gridTemplateColumns: `56px repeat(${displayTees.length}, minmax(0, 1fr))` }}
        >
          {/* Sticky tee header */}
          <div className="sticky top-0 z-20 border-b border-[#1F1F23] bg-[#0A0A0B]" />
          {displayTees.map((t) => (
            <div
              key={t.id}
              className="sticky top-0 z-20 border-b border-l border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-xs font-semibold text-[#F5F5F7]"
            >
              {t.name}
            </div>
          ))}

          {/* Time rail */}
          <div
            className="relative grid"
            style={{ gridTemplateRows: `repeat(${rows}, ${rowH}px)` }}
          >
            {nowTop != null && (
              <div
                className="pointer-events-none absolute right-0 z-20 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-[#E5484D]"
                style={{ top: nowTop }}
                aria-hidden="true"
              />
            )}
            {Array.from({ length: rows }, (_, i) => {
              const m = open + i * interval
              const onHour = m % 60 === 0
              return (
                <div
                  key={i}
                  className={`flex items-center justify-end pr-2 font-mono text-[10px] ${
                    onHour ? 'border-t border-[#1F1F23] text-[#A1A1A8]' : 'border-t border-[#1F1F23]/40 text-[#4A4A50]'
                  } ${i === 0 ? '!border-t-0' : ''}`}
                >
                  {timeLabel(m)}
                </div>
              )
            })}
          </div>

          {/* One column per starting tee */}
          {displayTees.map((t) => {
            const col = placed.get(t.id) ?? []
            const colBlocks = blocks
            const covered = new Set<number>()
            for (const p of col) for (let r = p.row; r < p.row + p.span; r++) covered.add(r)
            for (const x of colBlocks) for (let r = x.row; r < x.row + x.span; r++) covered.add(r)

            return (
              <div
                key={t.id}
                className="relative grid border-l border-[#1F1F23]"
                // One explicit column, and every child pins to it — without
                // that, a block and a party sharing a row auto-flow into
                // implicit side-by-side columns and halve the sheet's width.
                style={{
                  gridTemplateRows: `repeat(${rows}, ${rowH}px)`,
                  gridTemplateColumns: 'minmax(0, 1fr)',
                }}
              >
                {/* The now line — the operator's place on the page. */}
                {nowTop != null && (
                  <div
                    className="pointer-events-none absolute inset-x-0 z-20 h-px bg-[#E5484D]/60"
                    style={{ top: nowTop }}
                    aria-hidden="true"
                  />
                )}
                {/* Row ruling + open rows */}
                {Array.from({ length: rows }, (_, i) => {
                  const m = open + i * interval
                  const onHour = m % 60 === 0
                  return (
                    <div
                      key={i}
                      style={{ gridRow: `${i + 1}`, gridColumn: 1 }}
                      className={`group flex items-center px-1.5 ${
                        onHour ? 'border-t border-[#1F1F23]' : 'border-t border-[#1F1F23]/40'
                      } ${i === 0 ? '!border-t-0' : ''}`}
                    >
                      {!covered.has(i) && (
                        <span
                          className="w-full rounded border border-dashed border-transparent px-2 py-1 text-[10px] text-[#3A3A40] transition-colors group-hover:border-[#17C5B0]/30 group-hover:text-[#17C5B0]/70"
                          title={`Open tee time — ${timeLabel(m)} off ${t.name}`}
                        >
                          Open
                        </span>
                      )}
                    </div>
                  )
                })}

                {/* Imported blocks: leagues, maintenance. Hatched, labelled. */}
                {colBlocks.map(({ block, row, span }) => (
                  <div
                    key={block.id}
                    style={{ gridRow: `${row + 1} / span ${span}`, gridColumn: 1 }}
                    className="relative z-[5] m-0.5 flex items-start overflow-hidden rounded border border-[#A1A1A8]/20 px-2 py-1 text-[10px] text-[#A1A1A8]"
                    title={`${block.summary} — from your own calendar`}
                  >
                    <span
                      className="absolute inset-0 opacity-[0.06]"
                      style={{
                        backgroundImage:
                          'repeating-linear-gradient(-45deg, #A1A1A8 0 1px, transparent 1px 7px)',
                      }}
                    />
                    <span className="relative truncate">{block.summary}</span>
                  </div>
                ))}

                {/* Parties */}
                {col.map((p) => {
                  const b = p.booking
                  const cls = PARTY_BLOCK[b.status] || PARTY_BLOCK.confirmed
                  const word = STATUS_WORD[b.status] || b.status
                  const openHere = p.seatTracked ? SEATS - b.partySize : 0
                  return (
                    <div
                      key={b.id}
                      style={{ gridRow: `${p.row + 1} / span ${p.span}`, gridColumn: 1 }}
                      className="z-10 flex min-w-0 items-stretch gap-0.5 p-0.5"
                    >
                      <button
                        onClick={(e) => {
                          if (onSelect) return onSelect(b)
                          const r = e.currentTarget.getBoundingClientRect()
                          setDetail({ p, rect: { top: r.top, bottom: r.bottom, left: r.left } })
                        }}
                        title={`${b.customerName} — party of ${b.partySize}, ${word}`}
                        className={`flex min-w-0 items-center gap-1.5 overflow-hidden rounded border px-2 text-left text-[11px] transition-colors hover:brightness-125 ${cls}`}
                        style={p.seatTracked
                          ? { flexGrow: b.partySize, flexBasis: 0 }
                          : { flexGrow: 1, flexBasis: 0 }}
                      >
                        {b.source === 'phone' && (
                          <Phone className="h-2.5 w-2.5 shrink-0 opacity-70" aria-label="Booked by the phone agent" />
                        )}
                        <span className="truncate font-medium">{b.customerName}</span>
                        {b.partySize > 1 && (
                          <span className="shrink-0 opacity-70">×{b.partySize}</span>
                        )}
                        {/* The counter glyphs, straight from the tools every
                            operator already reads: ✓ checked in, $ green when
                            paid and amber while the money is still walking
                            up the path. */}
                        {checkedIn(b) && (
                          <Check className="h-2.5 w-2.5 shrink-0 text-[#17C5B0]" aria-label="Checked in" />
                        )}
                        <span
                          className={`shrink-0 font-mono text-[10px] ${
                            isPaid(b) ? 'text-[#17C5B0]' : 'text-[#F5A524]'
                          }`}
                          title={isPaid(b) ? 'Paid' : 'Pays at check-in'}
                        >
                          $
                        </span>
                        {p.holes && (
                          <span className="ml-auto shrink-0 rounded-sm border border-current/30 px-1 font-mono text-[9px] leading-4 opacity-80">
                            {p.holes}
                          </span>
                        )}
                      </button>
                      {/* The seats still for sale in this group — each its own
                          cell, exactly as wide as the player who isn't in it. */}
                      {Array.from({ length: openHere }, (_, i) => (
                        <span
                          key={i}
                          style={{ flexGrow: 1, flexBasis: 0 }}
                          className="rounded border border-dashed border-[#17C5B0]/25 bg-[#17C5B0]/[0.03] transition-colors hover:border-[#17C5B0]/50"
                          title={`Seat open in ${b.customerName}'s group — sellable`}
                        />
                      ))}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>

      {/* The key, kept to what is not obvious at first glance. */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-[#6B6B73]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-4 rounded-sm border border-dashed border-[#17C5B0]/40 bg-[#17C5B0]/[0.05]" />
          open seat in a booked group
        </span>
        <span className="flex items-center gap-1.5">
          <Phone className="h-2.5 w-2.5" /> booked by the phone agent
        </span>
        <span className="flex items-center gap-1">
          <span className="font-mono text-[#17C5B0]">$</span> paid
        </span>
        <span className="flex items-center gap-1">
          <span className="font-mono text-[#F5A524]">$</span> pays at check-in
        </span>
        <span className="flex items-center gap-1">
          <Check className="h-2.5 w-2.5 text-[#17C5B0]" /> checked in
        </span>
      </div>

      {/* The party card — what the starter needs at the window, one tap in,
          one tap out. On DESKTOP it opens AT the chip as an anchored popover
          with no dim: a glance card that darkened the whole dashboard and
          answered at the bottom of the screen was the funky part. On a phone
          it is a bottom sheet, because a thumb lives at the bottom. The
          phone number is a tel: link because "call the 9:15 who has not
          shown" is the single most common action on a sheet. */}
      {detail && (() => {
        const b = detail.p.booking
        const teeName = tees.find((t) => t.id === b.resourceId)?.name ?? ''
        const start = timeLabel(localMinutes(b.startsAt, timezone))
        const word = STATUS_WORD[b.status] || b.status
        const openHere = detail.p.seatTracked ? SEATS - b.partySize : 0

        const card = (
          <>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-[#F5F5F7]">{b.customerName}</div>
                <div className="mt-0.5 text-xs text-[#A1A1A8]">
                  {start} off {teeName} · party of {b.partySize}
                  {detail.p.holes ? ` · ${detail.p.holes} holes` : ''}
                </div>
              </div>
              <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[10px] ${
                PARTY_BLOCK[b.status] || PARTY_BLOCK.confirmed
              }`}>
                {word}
              </span>
            </div>
            <div className="mt-3 space-y-1.5 text-xs text-[#D4D4D8]">
              <div className="flex items-center gap-2">
                <span className={`font-mono ${isPaid(b) ? 'text-[#17C5B0]' : 'text-[#F5A524]'}`}>$</span>
                {isPaid(b) ? 'Paid' : 'Pays at check-in'}
              </div>
              <div className="flex items-center gap-2">
                <Phone className="h-3 w-3 text-[#1A8FD6]" />
                {b.source === 'phone' ? 'Booked by the phone agent' : 'Booked online'}
              </div>
              {openHere > 0 && (
                <div className="text-[#17C5B0]">
                  {openHere} seat{openHere > 1 ? 's' : ''} still open in this group
                </div>
              )}
              {b.notes && <div className="text-[#A1A1A8]">“{b.notes}”</div>}
            </div>
            <div className="mt-4 flex gap-2">
              {b.customerPhone && (
                <a
                  href={`tel:${b.customerPhone}`}
                  className="flex-1 rounded-lg border border-[#1A8FD6]/40 bg-[#1A8FD6]/10 px-3 py-2 text-center text-xs font-medium text-[#8dcef2] transition-colors hover:bg-[#1A8FD6]/20"
                >
                  Call {b.customerPhone}
                </a>
              )}
              <button
                onClick={() => setDetail(null)}
                className="rounded-lg border border-[#1F1F23] px-4 py-2 text-xs text-[#A1A1A8] transition-colors hover:text-[#F5F5F7]"
              >
                Close
              </button>
            </div>
          </>
        )

        if (isNarrow) {
          return (
            <>
              <button
                aria-label="Close details"
                onClick={() => setDetail(null)}
                className="animate-backdrop-in fixed inset-0 z-40 bg-black/40"
              />
              <div
                className="animate-sheet-up fixed inset-x-3 z-50 mx-auto max-w-md rounded-xl border border-[#1F1F23] bg-[#0E0E11]/98 p-4 backdrop-blur-lg"
                // Clears the mobile tab bar — a Call button behind the nav is
                // a button that does not exist.
                style={{ bottom: 'calc(var(--bottom-nav-h, 0px) + 16px)' }}
              >
                {card}
              </div>
            </>
          )
        }

        // Anchored popover: below the chip when there is room, above when
        // there is not, clamped inside the viewport. The click-away layer is
        // TRANSPARENT — dimming a whole dashboard for a glance card makes a
        // popover feel like a modal.
        const CARD_W = 340
        const CARD_H = 240
        const below = detail.rect.bottom + CARD_H + 12 < window.innerHeight
        const top = below
          ? detail.rect.bottom + 6
          : Math.max(8, detail.rect.top - CARD_H - 6)
        const left = Math.max(8, Math.min(detail.rect.left, window.innerWidth - CARD_W - 16))
        return (
          <>
            <button
              aria-label="Close details"
              onClick={() => setDetail(null)}
              className="fixed inset-0 z-40 cursor-default"
            />
            <div
              className="animate-pop-in fixed z-50 rounded-xl border border-[#1F1F23] bg-[#0E0E11]/98 p-4 shadow-xl shadow-black/40 backdrop-blur-lg"
              style={{ top, left, width: CARD_W, transformOrigin: below ? 'top left' : 'bottom left' }}
            >
              {card}
            </div>
          </>
        )
      })()}
    </div>
  )
}
