/**
 * Fixture backend for the Bookings preview.
 *
 * Intercepts `fetch` for /api/bookings/* and answers with the SAME wire shapes
 * the real FastAPI routes return (snake_case, UTC instants, server-rendered
 * local labels), so the page components run completely unmodified.
 *
 * The data is invented. The BEHAVIOUR is not: this store reimplements the two
 * rules that actually matter, so the preview can be clicked rather than just
 * looked at.
 *
 *   1. Overlap refusal. createBooking walks every resource that fits the party
 *      and only fails once they are all busy — and it fails with the real 409
 *      body, so the UI's `isSlotTaken` branch is the one you see. In
 *      production this refusal comes from a Postgres GiST exclusion
 *      constraint, not from code like this.
 *   2. Exclusive waitlist offers. Cancelling a booking offers the freed slot
 *      to exactly one guest, highest-ranked first, and the offer holds the
 *      slot until it expires.
 *
 * Not imported by the app. Preview harness only.
 */

const MERCHANT = 'preview-bookings'

/**
 * The preview merchant is placed in WHOEVER IS LOOKING's timezone.
 *
 * In production this is a real per-merchant setting and the two routinely
 * differ — that is the whole reason the server ships a rendered `local_label`
 * instead of letting the browser format the time. Here they are deliberately
 * aligned, because a preview whose dinner service falls outside the day the
 * viewer's browser asks for shows an empty book and proves nothing.
 */
const TZ = Intl.DateTimeFormat().resolvedOptions().timeZone || 'America/Vancouver'

type Kind = 'table' | 'staff' | 'chair' | 'bay' | 'room'

interface Row {
  id: string
  resource_id: string
  service_id: string | null
  starts_at: string
  ends_at: string
  duration_minutes: number
  party_size: number
  customer_name: string
  customer_phone: string | null
  customer_email: string | null
  notes: string | null
  status: string
  source: string
  confirmation_code: string
  provider: string | null
  waitlist_id?: string | null
}

interface WaitRow {
  id: string
  customer_name: string
  customer_phone: string
  party_size: number
  window_start: string
  window_end: string
  status: string
  notes: string | null
  offered_at: string | null
  offer_expires_at: string | null
  offer_count: number
  rank_reason: string | null
  created_at: string
}

const RESOURCES = [
  { id: 'r1', name: 'Table 1', kind: 'table' as Kind, seats: 2, sort_order: 0, active: true },
  { id: 'r2', name: 'Table 2', kind: 'table' as Kind, seats: 2, sort_order: 1, active: true },
  { id: 'r3', name: 'Table 3', kind: 'table' as Kind, seats: 4, sort_order: 2, active: true },
  { id: 'r4', name: 'Table 4', kind: 'table' as Kind, seats: 4, sort_order: 3, active: true },
  { id: 'r5', name: 'Booth 5', kind: 'table' as Kind, seats: 6, sort_order: 4, active: true },
  { id: 'r6', name: 'Patio 1', kind: 'table' as Kind, seats: 4, sort_order: 9, active: true },
]

const SERVICES = [
  {
    id: 's1', name: 'Table for 1–4', description: 'Standard turn',
    duration_minutes: 90, buffer_minutes: 15, price_cents: null,
    min_party: 1, max_party: 4, active: true,
  },
  {
    id: 's2', name: 'Table for 5–8', description: 'Longer turn for a larger party',
    duration_minutes: 120, buffer_minutes: 15, price_cents: null,
    min_party: 5, max_party: 8, active: true,
  },
]

// Tue–Sun dinner service. Monday closed, which is why the book is empty there.
const HOURS = [0, 2, 3, 4, 5, 6].map((weekday) => ({
  weekday, opens_at: '17:00:00', closes_at: '22:00:00', slot_minutes: 15,
}))

const CODES = 'ABCDEFGHJKLMNPQRTUVWXY2346789'
let seq = 0
const uid = (p: string) => `${p}-${(++seq).toString(36)}-${Math.random().toString(36).slice(2, 8)}`

function code(rand: () => number): string {
  return Array.from({ length: 5 }, () => CODES[Math.floor(rand() * CODES.length)]).join('')
}

/** Deterministic per-day PRNG so navigating back to a day shows the same book. */
function seeded(key: string): () => number {
  let h = 2166136261
  for (let i = 0; i < key.length; i++) {
    h ^= key.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return () => {
    h += 0x6d2b79f5
    let t = h
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

function localLabel(iso: string): string {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, hour: 'numeric', minute: '2-digit', hour12: true,
  }).format(new Date(iso))
}

/** Build a UTC instant for a wall-clock time on `dayKey` in the merchant's tz. */
function atLocal(dayKey: string, hour: number, minute: number): Date {
  const [y, m, d] = dayKey.split('-').map(Number)
  // Start from the UTC guess, then correct by the zone's offset at that moment.
  const guess = Date.UTC(y, m - 1, d, hour, minute)
  const off = zoneOffsetMs(new Date(guess))
  return new Date(guess + off)
}

function zoneOffsetMs(at: Date): number {
  const dtf = new Intl.DateTimeFormat('en-US', {
    timeZone: TZ, hour12: false,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
  const p: Record<string, string> = {}
  for (const part of dtf.formatToParts(at)) if (part.type !== 'literal') p[part.type] = part.value
  const asUtc = Date.UTC(
    +p.year, +p.month - 1, +p.day, +p.hour % 24, +p.minute, +p.second,
  )
  return at.getTime() - asUtc
}

const NAMES = [
  ['Priya Raman', '+1 604 555 0143'], ['Marcus Webb', '+1 604 555 0119'],
  ['Chen Wei', '+1 778 555 0188'], ['Sofia Duarte', '+1 604 555 0171'],
  ['Tom Ellery', '+1 236 555 0102'], ['Nadia Khoury', '+1 604 555 0166'],
  ['Ben Osei', '+1 778 555 0134'], ['Hannah Lindqvist', '+1 604 555 0155'],
  ['Diego Marquez', '+1 604 555 0127'], ['Ayesha Malik', '+1 778 555 0198'],
]

const bookings: Row[] = []
const seededDays = new Set<string>()

function serviceFor(party: number) {
  return SERVICES.find((s) => party >= s.min_party && party <= s.max_party) || SERVICES[0]
}

function overlaps(a: Row, startMs: number, endMs: number): boolean {
  // Half-open [start, end) — back-to-back bookings do not collide, exactly as
  // tstzrange behaves in the real constraint.
  return new Date(a.starts_at).getTime() < endMs && startMs < new Date(a.ends_at).getTime()
}

const HOLDING = new Set(['confirmed', 'seated', 'offered'])

function freeResource(startMs: number, endMs: number, party: number): string | null {
  const fits = RESOURCES
    .filter((r) => r.active && r.seats >= party)
    .sort((a, b) => a.seats - b.seats || a.sort_order - b.sort_order)
  for (const r of fits) {
    const clash = bookings.some(
      (b) => b.resource_id === r.id && HOLDING.has(b.status) && overlaps(b, startMs, endMs),
    )
    if (!clash) return r.id
  }
  return null
}

function makeBooking(input: {
  startsAt: Date; party: number; name: string; phone: string | null
  source: string; notes?: string | null; status?: string; rand?: () => number
}): Row | null {
  const svc = serviceFor(input.party)
  const startMs = input.startsAt.getTime()
  const endMs = startMs + (svc.duration_minutes + svc.buffer_minutes) * 60_000
  const resourceId = freeResource(startMs, endMs, input.party)
  if (!resourceId) return null
  const row: Row = {
    id: uid('bk'),
    resource_id: resourceId,
    service_id: svc.id,
    starts_at: new Date(startMs).toISOString(),
    ends_at: new Date(endMs).toISOString(),
    duration_minutes: svc.duration_minutes,
    party_size: input.party,
    customer_name: input.name,
    customer_phone: input.phone,
    customer_email: null,
    notes: input.notes ?? null,
    status: input.status ?? 'confirmed',
    source: input.source,
    confirmation_code: code(input.rand ?? Math.random),
    provider: null,
  }
  bookings.push(row)
  return row
}

function seedDay(dayKey: string) {
  if (seededDays.has(dayKey)) return
  seededDays.add(dayKey)
  const rand = seeded(dayKey)
  const [, , d] = dayKey.split('-').map(Number)
  const weekday = atLocal(dayKey, 12, 0).getUTCDay()
  if (weekday === 1) return // Monday: closed, and the empty state is worth seeing

  const times = [17, 17.5, 18, 18.25, 18.75, 19, 19.25, 19.5, 20, 20.5]
  const count = 6 + Math.floor(rand() * 4)
  const chosen = times.slice(0, count)
  chosen.forEach((t, i) => {
    const hour = Math.floor(t)
    const minute = Math.round((t - hour) * 60)
    const [name, phone] = NAMES[(i + d) % NAMES.length]
    const party = 2 + Math.floor(rand() * 4)
    const r = rand()
    const status = r > 0.86 ? 'completed' : r > 0.78 ? 'seated' : 'confirmed'
    makeBooking({
      startsAt: atLocal(dayKey, hour, minute),
      party,
      name,
      phone,
      source: rand() > 0.45 ? 'phone' : 'portal',
      notes: rand() > 0.82 ? 'Window seat if possible' : null,
      status,
      rand,
    })
  })
}

// ── Waitlist ────────────────────────────────────────────────────────────
const todayKey = (() => {
  const now = new Date()
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(now)
  const g = (t: string) => p.find((x) => x.type === t)!.value
  return `${g('year')}-${g('month')}-${g('day')}`
})()

const waitlist: WaitRow[] = [
  {
    id: uid('wl'), customer_name: 'Rebecca Tan', customer_phone: '+1 604 555 0164',
    party_size: 2, window_start: atLocal(todayKey, 18, 0).toISOString(),
    window_end: atLocal(todayKey, 20, 30).toISOString(),
    status: 'waiting', notes: 'Anniversary',
    offered_at: null, offer_expires_at: null, offer_count: 0,
    rank_reason: '4 previous visits, no no-shows, average spend $88',
    created_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
  },
  {
    id: uid('wl'), customer_name: 'Julian Ferreira', customer_phone: '+1 778 555 0110',
    party_size: 4, window_start: atLocal(todayKey, 19, 0).toISOString(),
    window_end: atLocal(todayKey, 21, 0).toISOString(),
    status: 'waiting', notes: null,
    offered_at: null, offer_expires_at: null, offer_count: 0,
    rank_reason: 'No history — ranked by arrival order',
    created_at: new Date(Date.now() - 2 * 3600_000).toISOString(),
  },
  {
    id: uid('wl'), customer_name: 'Greg Mullen', customer_phone: '+1 604 555 0177',
    party_size: 2, window_start: atLocal(todayKey, 18, 30).toISOString(),
    window_end: atLocal(todayKey, 21, 30).toISOString(),
    status: 'waiting', notes: null,
    offered_at: null, offer_expires_at: null, offer_count: 1,
    rank_reason: '2 no-shows on record — ranked last despite $140 average spend',
    created_at: new Date(Date.now() - 90 * 60_000).toISOString(),
  },
]

function rankScore(w: WaitRow): number {
  const r = w.rank_reason || ''
  let score = 0
  const noShows = /(\d+) no-shows?/.exec(r)
  if (noShows) score -= 40 * Number(noShows[1])
  const visits = /(\d+) previous visits/.exec(r)
  if (visits) score += Math.min(Number(visits[1]) * 6, 10)
  const spend = /\$(\d+)/.exec(r)
  if (spend) score += Math.min(Number(spend[1]) / 5, 20)
  score += w.party_size * 1.5
  return score
}

/** Offer a freed slot to exactly one guest — the hold is a real booking row. */
function offerFreedSlot(freed: Row): { offered: boolean; reason: string; candidates: number } {
  const startMs = new Date(freed.starts_at).getTime()
  const endMs = new Date(freed.ends_at).getTime()
  const eligible = waitlist
    .filter((w) => w.status === 'waiting')
    .filter((w) => w.party_size <= (RESOURCES.find((r) => r.id === freed.resource_id)?.seats ?? 0))
    .filter((w) => new Date(w.window_start).getTime() <= startMs
      && startMs < new Date(w.window_end).getTime())
    .sort((a, b) => rankScore(b) - rankScore(a))

  if (!eligible.length) {
    return { offered: false, reason: 'Nobody on the waitlist matches that slot', candidates: 0 }
  }
  const winner = eligible[0]
  const hold = makeBooking({
    startsAt: new Date(startMs),
    party: winner.party_size,
    name: winner.customer_name,
    phone: winner.customer_phone,
    source: 'sms',
    status: 'offered',
    notes: 'Held for waitlist offer',
  })
  if (!hold) {
    return { offered: false, reason: 'The slot was taken before the offer went out', candidates: eligible.length }
  }
  hold.waitlist_id = winner.id
  winner.status = 'offered'
  winner.offered_at = new Date().toISOString()
  winner.offer_expires_at = new Date(Date.now() + 15 * 60_000).toISOString()
  winner.offer_count += 1
  return {
    offered: true,
    reason: `Offered to ${winner.customer_name} — ${winner.rank_reason}`,
    candidates: eligible.length,
  }
}

// ── Integrations fixtures (mirrors registry.py verbatim) ────────────────
const UNAVAILABLE = [
  ['resy', 'Resy', 'Resy (American Express) publishes no third-party booking API.', "Connect the shop's Google Calendar instead, or let us take bookings directly and keep Resy for walk-up traffic."],
  ['tock', 'Tock', 'Tock (Squarespace) has no public developer surface.', 'Same as Resy — use the calendar path.'],
  ['booksy', 'Booksy', "No public developer portal. Booksy exposes booking to Google's Reserve programme, not to other platforms.", 'Connect Google Calendar if Booksy syncs to it, otherwise let us hold the calendar and keep Booksy for online self-booking.'],
  ['vagaro', 'Vagaro', 'No public developer portal. (Schedulicity is now part of Vagaro — schedulicity.com redirects there.)', 'Use the Google Calendar path.'],
  ['fresha', 'Fresha', 'No public developer portal.', 'Use the Google Calendar path.'],
  ['squire', 'Squire', 'Barbershop platform with no public developer portal.', 'Use the Google Calendar path.'],
  ['opentable', 'OpenTable', 'Write access exists but only under a signed partner agreement; there is no self-serve developer portal.', 'We can read the shop’s calendar today. Ask us about OpenTable if it matters — the partnership takes lead time, not engineering.'],
  ['sevenrooms', 'SevenRooms', 'Partner-gated. The hold-then-confirm flow is documented but credentials require a commercial agreement.', 'Same as OpenTable.'],
  ['urable', 'Urable / Mobile Tech RX (detailing)', 'Auto-detailing software runs no developer programme at all.', 'Detailers should run bookings here directly, with Google Calendar connected so the owner sees them where they already look.'],
].map(([key, label, reason, workaround]) => ({ key, label, reason, workaround }))

const connections: any[] = [
  {
    id: uid('conn'), provider: 'square_appointments', status: 'connected',
    direction: 'both', last_sync_at: new Date(Date.now() - 11 * 60_000).toISOString(),
    last_error: null,
  },
]

const squareOptions = {
  access_level: 'buyer',
  booking_enabled: true,
  location_id: 'L7PREVIEW9',
  services: [
    { service_variation_id: 'sv_dinner', service_variation_version: 1737400001, name: 'Dinner reservation', duration_minutes: 90 },
    { service_variation_id: 'sv_bar', service_variation_version: 1737400002, name: 'Bar seating', duration_minutes: 60 },
    { service_variation_id: 'sv_private', service_variation_version: 1737400003, name: 'Private room', duration_minutes: 150 },
  ],
  team_members: [
    { team_member_id: 'tm_host', display_name: 'Front of house', is_bookable: true },
    { team_member_id: 'tm_owner', display_name: 'Elena (owner)', is_bookable: true },
  ],
  default_service: {
    service_variation_id: 'sv_dinner',
    service_variation_version: 1737400001,
    team_member_id: 'tm_host',
  },
}

let feedToken: string | null = null

// The merchant in this fixture already answered the onboarding questionnaire,
// so the card opens showing an inherited URL waiting to be confirmed — which
// is the state most real merchants will meet it in.
const linkState = {
  url: 'https://mapletandoor.ca/reservations',
  inherited: true,
  sent: 31,
  opened: 22,
  failed: 2,
}

// Two blocks imported from the merchant's Square calendar: a private event
// and a staff meeting. Neither is our booking, and both have to show up or
// the book is only half the evening.
const busyBlocks = [
  {
    id: uid('busy'), starts_at: atLocal(todayKey, 16, 0).toISOString(),
    ends_at: atLocal(todayKey, 17, 0).toISOString(),
    summary: 'Staff briefing', provider: 'square_appointments',
  },
  {
    id: uid('busy'), starts_at: atLocal(todayKey, 21, 0).toISOString(),
    ends_at: atLocal(todayKey, 23, 0).toISOString(),
    summary: 'Private event — Booth 5', provider: 'square_appointments',
  },
]

// ── Router ──────────────────────────────────────────────────────────────
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), {
    status, headers: { 'Content-Type': 'application/json' },
  })

function dayKeyOf(iso: string): string {
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date(iso))
  const g = (t: string) => p.find((x) => x.type === t)!.value
  return `${g('year')}-${g('month')}-${g('day')}`
}

async function route(url: URL, init: RequestInit): Promise<Response> {
  const method = (init.method || 'GET').toUpperCase()
  const path = url.pathname.replace('/api/bookings', '')
  const body = init.body ? JSON.parse(String(init.body)) : {}
  const seg = path.split('/').filter(Boolean)

  // — resources —
  if (path === `/resources/${MERCHANT}`) return json({ resources: RESOURCES })
  if (path === '/resources' && method === 'POST') {
    const r = {
      id: uid('r'), name: body.name, kind: body.kind, seats: body.seats,
      sort_order: body.sort_order ?? 0, active: true,
    }
    RESOURCES.push(r as any)
    return json({ resource: r })
  }
  if (seg[0] === 'resources' && method === 'PATCH') {
    const r: any = RESOURCES.find((x) => x.id === seg[1])
    if (!r) return json({ detail: 'not found' }, 404)
    for (const [k, v] of Object.entries(body)) if (v !== undefined) r[k] = v
    return json({ resource: r })
  }

  // — services —
  if (path === `/services/${MERCHANT}`) return json({ services: SERVICES })
  if (path === '/services' && method === 'POST') {
    const s = {
      id: uid('s'), name: body.name, description: null,
      duration_minutes: body.duration_minutes, buffer_minutes: body.buffer_minutes ?? 0,
      price_cents: body.price_cents ?? null, min_party: body.min_party ?? 1,
      max_party: body.max_party ?? 1, active: true,
    }
    SERVICES.push(s as any)
    return json({ service: s })
  }

  // — hours —
  if (path === `/hours/${MERCHANT}`) return json({ hours: HOURS })
  if (path === '/hours' && method === 'PUT') {
    HOURS.length = 0
    for (const r of body.rows || []) {
      HOURS.push({
        weekday: r.weekday,
        opens_at: `${r.opens_at}:00`.slice(0, 8),
        closes_at: `${r.closes_at}:00`.slice(0, 8),
        slot_minutes: r.slot_minutes ?? 15,
      })
    }
    return json({ hours: HOURS })
  }

  // — the book —
  if (seg[0] === 'list') {
    const start = url.searchParams.get('start')!
    const end = url.searchParams.get('end')!
    const includeCancelled = url.searchParams.get('include_cancelled') === 'true'
    seedDay(dayKeyOf(start))
    seedDay(dayKeyOf(end))
    const s = new Date(start).getTime()
    const e = new Date(end).getTime()
    const rows = bookings
      .filter((b) => {
        const t = new Date(b.starts_at).getTime()
        return t >= s && t <= e
      })
      .filter((b) => includeCancelled || !['cancelled', 'no_show'].includes(b.status))
      .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
    return json({ bookings: rows })
  }

  // — availability —
  if (seg[0] === 'availability') {
    const day = url.searchParams.get('day') || todayKey
    const party = Number(url.searchParams.get('party_size') || 1)
    seedDay(day)
    const weekday = atLocal(day, 12, 0).getUTCDay()
    const row = HOURS.find((h) => h.weekday === weekday)
    if (!row) return json({ timezone: TZ, slots: [] })
    const svc = serviceFor(party)
    const [oh, om] = row.opens_at.split(':').map(Number)
    const [ch, cm] = row.closes_at.split(':').map(Number)
    const open = atLocal(day, oh, om).getTime()
    const close = atLocal(day, ch, cm).getTime()
    const slots: any[] = []
    for (let t = open; t < close; t += row.slot_minutes * 60_000) {
      const endMs = t + (svc.duration_minutes + svc.buffer_minutes) * 60_000
      if (t < Date.now()) continue
      const rid = freeResource(t, endMs, party)
      if (!rid) continue
      slots.push({
        starts_at: new Date(t).toISOString(),
        ends_at: new Date(endMs).toISOString(),
        local_label: localLabel(new Date(t).toISOString()),
        resource_id: rid,
        resource_name: RESOURCES.find((r) => r.id === rid)!.name,
        duration_minutes: svc.duration_minutes,
      })
    }
    return json({ timezone: TZ, slots })
  }

  // — create —
  if (path === '/create' && method === 'POST') {
    const row = makeBooking({
      startsAt: new Date(body.starts_at),
      party: body.party_size ?? 1,
      name: body.customer_name,
      phone: body.customer_phone ?? null,
      notes: body.notes ?? null,
      source: body.source || 'portal',
    })
    if (!row) {
      // The real 409 body, so the UI's isSlotTaken branch is what you see.
      return json(
        { detail: 'That time was just taken. (23P01 bookings_no_double_book)' },
        409,
      )
    }
    return json({ booking: row })
  }

  // — waitlist —
  if (seg[0] === 'waitlist' && method === 'GET') {
    const status = url.searchParams.get('status') || 'waiting'
    const rows = status === 'all'
      ? waitlist
      : waitlist.filter((w) => w.status === status)
    return json({ waitlist: rows })
  }
  if (path === '/waitlist' && method === 'POST') {
    const w: WaitRow = {
      id: uid('wl'), customer_name: body.customer_name,
      customer_phone: body.customer_phone, party_size: body.party_size ?? 1,
      window_start: body.window_start, window_end: body.window_end,
      status: 'waiting', notes: body.notes ?? null,
      offered_at: null, offer_expires_at: null, offer_count: 0,
      rank_reason: 'No history — ranked by arrival order',
      created_at: new Date().toISOString(),
    }
    waitlist.push(w)
    return json({ entry: w })
  }
  if (seg[0] === 'waitlist' && method === 'DELETE') {
    const i = waitlist.findIndex((w) => w.id === seg[1])
    if (i >= 0) waitlist.splice(i, 1)
    return json({ ok: true })
  }
  if (seg[0] === 'waitlist' && seg[2] === 'recover' && method === 'POST') {
    const b = bookings.find((x) => x.id === seg[3])
    if (!b) return json({ detail: 'not found' }, 404)
    return json(offerFreedSlot(b))
  }

  // — integrations —
  if (seg[0] === 'integrations' && method === 'GET') {
    return json({
      connections,
      available: [
        {
          key: 'square_appointments', label: 'Square Appointments',
          summary: 'Book directly into the merchant’s Square calendar. Works on every Square plan.',
          read_busy: true, write_booking: true, webhooks: true,
        },
        {
          key: 'ics_feed', label: 'Calendar feed (.ics)',
          summary: 'Read busy time from any calendar that publishes a subscribe link, and publish ours back.',
          read_busy: true, write_booking: false, webhooks: false,
        },
      ],
      unavailable: UNAVAILABLE,
    })
  }
  if (path === '/integrations/ics' && method === 'POST') {
    const c = {
      id: uid('conn'), provider: 'ics_feed', status: 'connected',
      direction: 'read', last_sync_at: new Date().toISOString(), last_error: null,
    }
    connections.push(c)
    return json({ connection: c, sync: { imported: 12, removed: 0 } })
  }

  // — the texted booking link —
  if (seg[0] === 'link' && method === 'GET') {
    return json({
      url: linkState.url,
      inherited: linkState.inherited,
      mode: linkState.url ? 'external_link' : 'off',
      sent: linkState.sent,
      opened: linkState.opened,
      failed: linkState.failed,
      recent: [],
    })
  }
  if (seg[0] === 'link' && method === 'POST') {
    const raw = String(body.url || '').trim()
    if (raw && !/^(https?:\/\/)?[\w.-]+\.[a-z]{2,}(\/\S*)?$/i.test(raw)) {
      return json({ detail: 'that does not look like a web address' }, 400)
    }
    linkState.url = raw
      ? (raw.startsWith('http') ? raw : `https://${raw}`)
      : ''
    linkState.inherited = false
    return json({ url: linkState.url, mode: linkState.url ? 'external_link' : 'off' })
  }

  // — time taken in the merchant's other tools —
  if (seg[0] === 'busy' && method === 'GET') {
    const start = url.searchParams.get('start')!
    const end = url.searchParams.get('end')!
    seedDay(dayKeyOf(start))
    const s = new Date(start).getTime()
    const e = new Date(end).getTime()
    return json({
      busy: busyBlocks.filter((b) => {
        const t = new Date(b.starts_at).getTime()
        return t >= s && t <= e
      }),
    })
  }

  // — square —
  if (path === '/square/authorize') {
    return json({
      authorize_url: 'https://connect.squareup.com/oauth2/authorize?preview=1',
    })
  }
  if (seg[0] === 'square' && seg[1] === 'options' && method === 'GET') {
    return json(squareOptions)
  }
  if (seg[0] === 'square' && seg[1] === 'options' && method === 'POST') {
    squareOptions.default_service = {
      service_variation_id: body.default_service.service_variation_id,
      service_variation_version: body.default_service.service_variation_version,
      team_member_id: body.default_service.team_member_id,
    }
    return json({ ok: true })
  }
  if (seg[0] === 'square' && seg[1] === 'refresh' && method === 'POST') {
    return json({ ok: true, services: squareOptions.services.length })
  }

  // — outbound feed —
  if (seg[0] === 'feed' && seg[2] === 'enable' && method === 'POST') {
    feedToken = feedToken || uid('tok').replace(/-/g, '')
    return json({ feed_url: `${url.origin}/api/bookings/feed/${feedToken}.ics` })
  }

  // — status changes —
  if (seg.length === 1 && method === 'PATCH') {
    const b = bookings.find((x) => x.id === seg[0])
    if (!b) return json({ detail: 'not found' }, 404)
    const wasHolding = HOLDING.has(b.status)
    for (const [k, v] of Object.entries(body)) {
      if (v === undefined || v === null) continue
      ;(b as any)[k] = v
    }
    // Freeing a slot is what triggers the recovery offer.
    if (wasHolding && !HOLDING.has(b.status)) offerFreedSlot(b)
    return json({ booking: b })
  }

  return json({ detail: `preview: no fixture for ${method} ${path}` }, 404)
}

export function installFixtureApi() {
  const real = window.fetch.bind(window)
  window.fetch = async (input: any, init: any = {}) => {
    const raw = typeof input === 'string' ? input : input.url
    const url = new URL(raw, window.location.origin)
    if (!url.pathname.startsWith('/api/bookings')) return real(input, init)
    // A beat of latency so loading states are visible rather than skipped.
    await new Promise((r) => setTimeout(r, 90 + Math.random() * 120))
    try {
      return await route(url, init)
    } catch (e) {
      return json({ detail: `preview fixture error: ${String(e)}` }, 500)
    }
  }
}
