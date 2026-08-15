/**
 * The day grid — time down the side, one column per bookable thing.
 *
 * The list answers "who is coming next". This answers the other question a
 * host asks, which the list cannot: "where are the gaps". A restaurant
 * looking at eight columns sees instantly that Table 3 is free at 7:30 and
 * everything else is gone; a barber sees which chair is idle. Reading that
 * off a chronological list means holding eight timelines in your head.
 *
 * EVERYTHING IS POSITIONED FROM MINUTES-SINCE-MIDNIGHT IN THE MERCHANT'S OWN
 * TIMEZONE, never the browser's. An owner checking tonight from an airport
 * must see their evening, not a shifted one — the same rule the list follows,
 * and much more visible when it is wrong, because a block would land in the
 * wrong row rather than just showing a wrong label.
 *
 * Imported busy time from the merchant's other tools is drawn too, hatched
 * and unclickable. A grid that shows only our own bookings would show a shop
 * as wide open on the evening they have a private event booked in Square.
 */
import { useMemo } from 'react'
import type { Booking, BusyBlock, Resource } from '@/lib/bookings-api'

const PX_PER_MIN = 1.1
const HEADER_H = 32
/** Anything shorter still needs to be readable, so blocks have a floor. */
const MIN_BLOCK_H = 22

const STATUS_BLOCK: Record<string, string> = {
  offered: 'border-[#F5A524]/40 bg-[#F5A524]/15 text-[#F5A524]',
  confirmed: 'border-[#1A8FD6]/40 bg-[#1A8FD6]/15 text-[#8dcef2]',
  seated: 'border-[#17C5B0]/40 bg-[#17C5B0]/15 text-[#17C5B0]',
  completed: 'border-[#A1A1A8]/25 bg-[#A1A1A8]/10 text-[#A1A1A8]',
  cancelled: 'border-[#A1A1A8]/20 bg-transparent text-[#6B6B73]',
  no_show: 'border-[#E5484D]/30 bg-[#E5484D]/10 text-[#E5484D]',
}

/** Minutes since local midnight, in the MERCHANT's timezone. */
function localMinutes(iso: string, timezone: string): number {
  try {
    const parts = new Intl.DateTimeFormat('en-GB', {
      timeZone: timezone || undefined, hour12: false,
      hour: '2-digit', minute: '2-digit',
    }).formatToParts(new Date(iso))
    const get = (t: string) => Number(parts.find((p) => p.type === t)?.value ?? 0)
    // 24 is midnight at the END of a day in some locales' hour12:false output.
    return (get('hour') % 24) * 60 + get('minute')
  } catch {
    return 0
  }
}

function label(minutes: number): string {
  const h = Math.floor(minutes / 60) % 24
  const m = minutes % 60
  const ampm = h < 12 ? 'am' : 'pm'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return m === 0 ? `${h12}${ampm}` : `${h12}:${String(m).padStart(2, '0')}${ampm}`
}

export default function BookingCalendar({
  bookings, resources, busy, timezone, onSelect, openMinutes,
}: {
  bookings: Booking[]
  resources: Resource[]
  busy: BusyBlock[]
  timezone: string
  onSelect?: (booking: Booking) => void
  /** The merchant's trading window, when the caller knows it. Without this the
   *  grid spans only what is booked, so a shop open from nine with nothing
   *  before noon appears to open at eleven — and the gaps listed elsewhere
   *  refer to hours the grid does not draw. */
  openMinutes?: [number, number]
}) {
  const columns = useMemo(
    () => resources.filter((r) => r.active)
      .sort((a, b) => a.sortOrder - b.sortOrder || a.name.localeCompare(b.name)),
    [resources],
  )

  /**
   * The window is derived from what is actually on the day, not from a fixed
   * 00:00–24:00. A shop open 5pm–10pm should not have to scroll past a blank
   * morning to find its service, and a booking that runs past closing still
   * has to be visible.
   */
  const [dayStart, dayEnd] = useMemo(() => {
    const starts: number[] = []
    const ends: number[] = []
    for (const b of bookings) {
      starts.push(localMinutes(b.startsAt, timezone))
      const end = localMinutes(b.endsAt, timezone)
      // A booking that crosses midnight comes back as a smaller number; clamp
      // it to the end of the day rather than drawing it upwards.
      ends.push(end <= starts[starts.length - 1] ? 24 * 60 : end)
    }
    for (const x of busy) {
      starts.push(localMinutes(x.startsAt, timezone))
      const end = localMinutes(x.endsAt, timezone)
      ends.push(end <= starts[starts.length - 1] ? 24 * 60 : end)
    }
    if (openMinutes) {
      starts.push(openMinutes[0])
      ends.push(openMinutes[1])
    }
    if (!starts.length) return [9 * 60, 22 * 60]
    const lo = Math.max(0, Math.floor((Math.min(...starts) - 60) / 60) * 60)
    const hi = Math.min(24 * 60, Math.ceil((Math.max(...ends) + 60) / 60) * 60)
    return [lo, Math.max(hi, lo + 240)]
  }, [bookings, busy, timezone, openMinutes])

  const height = (dayEnd - dayStart) * PX_PER_MIN
  const hourMarks = useMemo(() => {
    const out: number[] = []
    for (let m = dayStart; m <= dayEnd; m += 60) out.push(m)
    return out
  }, [dayStart, dayEnd])

  const place = (startIso: string, endIso: string) => {
    const s = localMinutes(startIso, timezone)
    let e = localMinutes(endIso, timezone)
    if (e <= s) e = 24 * 60
    return {
      top: (s - dayStart) * PX_PER_MIN,
      height: Math.max(MIN_BLOCK_H, (e - s) * PX_PER_MIN),
    }
  }

  // Imported time with no resource of its own belongs to the whole shop — a
  // private event, a staff meeting — so it is drawn as a band behind every
  // column rather than being dropped for want of somewhere to put it.
  const shopWideBusy = busy

  if (columns.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[#1F1F23] px-4 py-10 text-center text-sm text-[#6B6B73]">
        Add a table, chair or bay and the day grid appears here.
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1F1F23] bg-[#0E0E11]">
      <div className="flex min-w-max">
        {/* Time gutter */}
        <div className="sticky left-0 z-20 w-14 shrink-0 border-r border-[#1F1F23] bg-[#0E0E11]">
          <div style={{ height: HEADER_H }} className="border-b border-[#1F1F23]" />
          <div className="relative" style={{ height }}>
            {hourMarks.map((m) => (
              <div
                key={m}
                className="absolute right-2 -translate-y-1/2 text-[10px] tabular-nums text-[#6B6B73]"
                style={{ top: (m - dayStart) * PX_PER_MIN }}
              >
                {label(m)}
              </div>
            ))}
          </div>
        </div>

        {columns.map((r) => (
          <div key={r.id} className="w-36 shrink-0 border-r border-[#1F1F23] last:border-r-0">
            <div
              style={{ height: HEADER_H }}
              className="flex items-center justify-between gap-1 border-b border-[#1F1F23] px-2"
            >
              <span className="truncate text-xs font-medium text-[#F5F5F7]">{r.name}</span>
              {r.kind === 'table' && (
                <span className="shrink-0 text-[10px] text-[#6B6B73]">{r.seats}</span>
              )}
            </div>

            <div className="relative" style={{ height }}>
              {hourMarks.map((m) => (
                <div
                  key={m}
                  className="absolute inset-x-0 border-t border-[#1F1F23]/60"
                  style={{ top: (m - dayStart) * PX_PER_MIN }}
                />
              ))}

              {shopWideBusy.map((x) => {
                const pos = place(x.startsAt, x.endsAt)
                return (
                  <div
                    key={`${r.id}-${x.id}`}
                    title={`${x.summary || 'Busy'} — from your own calendar`}
                    className="absolute inset-x-0 border-y border-dashed border-[#2A2A30] bg-[repeating-linear-gradient(45deg,transparent,transparent_5px,rgba(255,255,255,0.035)_5px,rgba(255,255,255,0.035)_10px)]"
                    style={{ top: pos.top, height: pos.height }}
                  />
                )
              })}

              {bookings
                .filter((b) => b.resourceId === r.id)
                .map((b) => {
                  const pos = place(b.startsAt, b.endsAt)
                  const tone = STATUS_BLOCK[b.status] || STATUS_BLOCK.confirmed
                  return (
                    <button
                      key={b.id}
                      onClick={() => onSelect?.(b)}
                      title={`${b.customerName} · ${b.partySize} · ${b.confirmationCode}`}
                      className={`absolute inset-x-1 overflow-hidden rounded-md border px-1.5 py-1 text-left transition-colors hover:brightness-125 ${tone}`}
                      style={{ top: pos.top, height: pos.height }}
                    >
                      <span className="block truncate text-[11px] font-medium leading-tight">
                        {b.customerName}
                      </span>
                      {pos.height > 34 && (
                        <span className="block truncate text-[10px] opacity-70">
                          {label(localMinutes(b.startsAt, timezone))} · {b.partySize}
                        </span>
                      )}
                    </button>
                  )
                })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
