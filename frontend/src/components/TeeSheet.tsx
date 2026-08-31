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
import { useMemo } from 'react'
import { Phone } from 'lucide-react'
import type { Booking, BusyBlock, Resource, Service } from '@/lib/bookings-api'
import { localMinutes } from '@/components/BookingCalendar'

const ROW_H = 34
const SEATS = 4

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
  bookings, resources, busy, timezone, openMinutes, services, onSelect,
}: {
  bookings: Booking[]
  resources: Resource[]
  busy: BusyBlock[]
  timezone: string
  openMinutes: [number, number]
  services: Service[]
  onSelect?: (booking: Booking) => void
}) {
  const tees = useMemo(
    () => resources.filter((r) => r.active)
      .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name)),
    [resources],
  )

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
  const { starts, players, openSeats } = useMemo(() => {
    let filled = 0; let heads = 0; let seatGaps = 0
    for (const col of placed.values()) {
      for (const p of col) {
        filled += 1
        heads += p.booking.partySize
        if (p.seatTracked) seatGaps += Math.max(0, SEATS - p.booking.partySize)
      }
    }
    return { starts: filled, players: heads, openSeats: seatGaps }
  }, [placed])

  const totalStarts = rows * Math.max(1, tees.length)

  return (
    <div>
      {/* The glance line. "Open seats" is the golf-only number: seats still
          sellable inside groups already on the sheet. */}
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-[#A1A1A8]">
        <span>
          <span className="font-mono text-[#F5F5F7]">{starts}</span>
          <span className="text-[#6B6B73]"> / {totalStarts}</span> starts filled
        </span>
        <span><span className="font-mono text-[#F5F5F7]">{players}</span> players</span>
        <span className={openSeats > 0 ? 'text-[#17C5B0]' : ''}>
          <span className="font-mono">{openSeats}</span> open seats in booked groups
        </span>
      </div>

      <div className="max-h-[600px] overflow-y-auto rounded-lg border border-[#1F1F23]">
        <div
          className="grid"
          style={{ gridTemplateColumns: `56px repeat(${tees.length}, minmax(0, 1fr))` }}
        >
          {/* Sticky tee header */}
          <div className="sticky top-0 z-20 border-b border-[#1F1F23] bg-[#0A0A0B]" />
          {tees.map((t) => (
            <div
              key={t.id}
              className="sticky top-0 z-20 border-b border-l border-[#1F1F23] bg-[#0A0A0B] px-3 py-2 text-xs font-semibold text-[#F5F5F7]"
            >
              {t.name}
            </div>
          ))}

          {/* Time rail */}
          <div
            className="grid"
            style={{ gridTemplateRows: `repeat(${rows}, ${ROW_H}px)` }}
          >
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
          {tees.map((t) => {
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
                  gridTemplateRows: `repeat(${rows}, ${ROW_H}px)`,
                  gridTemplateColumns: 'minmax(0, 1fr)',
                }}
              >
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
                        onClick={() => onSelect?.(b)}
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

      {/* The key, kept to the two things that are not obvious. */}
      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-[#6B6B73]">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-4 rounded-sm border border-dashed border-[#17C5B0]/40 bg-[#17C5B0]/[0.05]" />
          open seat in a booked group
        </span>
        <span className="flex items-center gap-1.5">
          <Phone className="h-2.5 w-2.5" /> booked by the phone agent
        </span>
      </div>
    </div>
  )
}
