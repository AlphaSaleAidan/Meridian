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
  service_address?: string | null
  service_lat?: number | null
  service_lng?: number | null
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

/** Filled by configureForTrade(). Empty until a trade is chosen. */
const RESOURCES: any[] = []

const SERVICES: any[] = []

const HOURS: any[] = []

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

/** Long enough that a full restaurant Friday never repeats a name — a book
 *  with the same guest twice at different tables is the first thing anyone
 *  notices in a demo. */
const NAMES = [
  ['Priya Raman', '+1 604 555 0143'], ['Marcus Webb', '+1 604 555 0119'],
  ['Chen Wei', '+1 778 555 0188'], ['Sofia Duarte', '+1 604 555 0171'],
  ['Tom Ellery', '+1 236 555 0102'], ['Nadia Khoury', '+1 604 555 0166'],
  ['Ben Osei', '+1 778 555 0134'], ['Hannah Lindqvist', '+1 604 555 0155'],
  ['Diego Marquez', '+1 604 555 0127'], ['Ayesha Malik', '+1 778 555 0198'],
  ['Grace Okafor', '+1 604 555 0181'], ['Liam Doherty', '+1 778 555 0146'],
  ['Yuki Tanaka', '+1 604 555 0192'], ['Omar Haddad', '+1 236 555 0158'],
  ['Elena Rossi', '+1 604 555 0173'], ['Jamal Carter', '+1 778 555 0129'],
  ['Freya Nilsen', '+1 604 555 0104'], ['Andre Silva', '+1 604 555 0167'],
  ['Mei Lin', '+1 778 555 0115'], ['Caleb Osborne', '+1 604 555 0138'],
  ['Ines Moreau', '+1 236 555 0149'], ['Ravi Chandra', '+1 604 555 0121'],
  ['Tessa Blackwood', '+1 778 555 0175'], ['Noah Whitfield', '+1 604 555 0186'],
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
  service?: any
}): Row | null {
  const svc = input.service || serviceFor(input.party)
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
  if (trade?.travels) {
    const [addr, lat, lng] = ADDRESSES[bookings.length % ADDRESSES.length]
    row.service_address = addr
    row.service_lat = lat
    row.service_lng = lng
  }
  bookings.push(row)
  return row
}

function seedDay(dayKey: string) {
  if (seededDays.has(dayKey)) return
  seededDays.add(dayKey)
  if (!trade || !trade.booksAtAll || RESOURCES.length === 0) return

  const rand = seeded(dayKey)
  const [, , d] = dayKey.split('-').map(Number)
  const weekday = atLocal(dayKey, 12, 0).getUTCDay()
  // Closed days come from the trade's own hours, so a barbershop's Monday is
  // empty and a restaurant's is too, for their own reasons.
  if (!trade.days.includes(weekday)) return

  // Start times walk the trade's opening hours at its own rhythm: a barber
  // fills 30-minute slots all day, a restaurant clusters around a dinner
  // service, a detailer fits two or three long jobs in.
  const [openH, openM] = trade.opens.split(':').map(Number)
  const [closeH] = trade.closes.split(':').map(Number)
  const lengths = trade.services.map((x: any) => x.duration + x.buffer)
  const shortest = Math.min(...lengths)
  // Snapped to the quarter hour. Nobody books a car in at 9:46.
  const step = Math.max(30, Math.round(shortest / 2 / 15) * 15)
  const slots: number[] = []
  for (let m = openH * 60 + openM; m + shortest <= closeH * 60; m += step) slots.push(m)

  // Roughly two thirds full — busy enough to look like a real day, empty
  // enough that the gaps the calendar exists to show are actually visible.
  const target = Math.max(2, Math.round(slots.length * RESOURCES.length * 0.5))
  let made = 0
  for (const minute of slots) {
    for (let n = 0; n < RESOURCES.length && made < target; n++) {
      // Long jobs collide constantly on a two-bay day, so most attempts fail
      // and a low acceptance rate leaves the shop looking shut. Try often and
      // let the exclusion logic decide what actually fits.
      if (rand() > 0.82) continue
      const [name, phone] = NAMES[(made + d) % NAMES.length]
      const party = trade.partyBanded ? 2 + Math.floor(rand() * 4) : 1
      const r = rand()
      const status = r > 0.88 ? 'completed' : r > 0.8 ? 'seated' : 'confirmed'
      // Weighted to the shorter services: every shop sells more haircuts than
      // ceramic coatings, and a day made of only the flagship job is a day
      // nobody recognises.
      const pick = SERVICES[Math.min(
        SERVICES.length - 1,
        Math.floor(rand() * rand() * SERVICES.length),
      )]
      const row = makeBooking({
        startsAt: atLocal(dayKey, Math.floor(minute / 60), minute % 60),
        party,
        service: trade.partyBanded ? undefined : pick,
        name,
        phone,
        source: rand() > 0.45 ? 'phone' : 'portal',
        notes: rand() > 0.85 ? (NOTE_EXAMPLE[trade.key] || null) : null,
        status,
        rand,
      })
      if (row) made++
    }
  }
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

const waitlist: WaitRow[] = []

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
const linkState = { url: '', inherited: false, sent: 0, opened: 0, failed: 0 }

// Two blocks imported from the merchant's Square calendar: a private event
// and a staff meeting. Neither is our booking, and both have to show up or
// the book is only half the evening.
const busyBlocks: any[] = []

// ── Trade configuration ─────────────────────────────────────────────────
/**
 * Rebuild the whole fixture merchant as a shop of this trade.
 *
 * This is what makes the per-trade demos real rather than a relabelled
 * restaurant: the chairs are chairs, the services are the ones that trade
 * sells, the hours are its hours, and the day fills at its own rhythm. The
 * PACK is the source — the same config the product ships — so a demo cannot
 * drift from what a merchant of that trade would actually get.
 */
export function configureForTrade(pack: any) {
  trade = pack

  bookings.length = 0
  seededDays.clear()
  waitlist.length = 0
  busyBlocks.length = 0
  RESOURCES.length = 0
  SERVICES.length = 0
  HOURS.length = 0

  linkState.url = ''
  linkState.inherited = false
  linkState.sent = 0
  linkState.opened = 0
  linkState.failed = 0

  if (!pack.booksAtAll) return

  const base = RESOURCE_NAME[pack.resourceKind] || 'Station'
  for (let i = 0; i < pack.defaultCount; i++) {
    RESOURCES.push({
      id: uid('r'),
      // Staff are people, not numbered stations — a nail studio with
      // "Staff 1" through "Staff 4" reads as a spreadsheet, not a shop.
      name: pack.travels
        ? VAN_NAMES[i % VAN_NAMES.length]
        : pack.resourceKind === 'staff'
          ? STAFF_NAMES[i % STAFF_NAMES.length]
          : `${base} ${i + 1}`,
      kind: pack.resourceKind,
      seats: pack.resourceKind === 'table' ? (i < 2 ? 2 : i > 4 ? 6 : 4) : 1,
      sort_order: i,
      active: true,
    })
  }

  for (const svc of pack.services) {
    SERVICES.push({
      id: uid('s'), name: svc.name, description: null,
      duration_minutes: svc.duration, buffer_minutes: svc.buffer,
      price_cents: null, min_party: svc.min, max_party: svc.max, active: true,
    })
  }

  for (const weekday of pack.days) {
    HOURS.push({
      weekday,
      opens_at: `${pack.opens}:00`.slice(0, 8),
      closes_at: `${pack.closes}:00`.slice(0, 8),
      slot_minutes: 15,
    })
  }

  // A waiting list only exists where people actually wait for a slot.
  const [wStartH] = pack.opens.split(':').map(Number)
  const [wEndH] = pack.closes.split(':').map(Number)
  const mid = Math.floor((wStartH + wEndH) / 2)
  WAITING.forEach(([name, phone, reason], i) => {
    waitlist.push({
      id: uid('wl'), customer_name: name, customer_phone: phone,
      party_size: pack.partyBanded ? 2 + i : 1,
      window_start: atLocal(todayKey, Math.max(wStartH, mid - 1), 0).toISOString(),
      window_end: atLocal(todayKey, Math.min(wEndH, mid + 3), 0).toISOString(),
      status: 'waiting', notes: null,
      offered_at: null, offer_expires_at: null, offer_count: 0,
      rank_reason: reason,
      created_at: new Date(Date.now() - (i + 1) * 3600_000).toISOString(),
    })
  })

  // Two commitments imported from the shop's own calendar, so the book is
  // visibly one book rather than only what we took.
  for (const [label, startH, endH] of (BUSY[pack.key] || [])) {
    busyBlocks.push({
      id: uid('busy'),
      starts_at: atLocal(todayKey, startH, 0).toISOString(),
      ends_at: atLocal(todayKey, endH, 0).toISOString(),
      summary: label, provider: 'square_appointments',
    })
  }
}

const RESOURCE_NAME: Record<string, string> = {
  table: 'Table', chair: 'Chair', bay: 'Bay', room: 'Room', staff: 'Staff',
}

/** A van is not a person, so it does not get a person's name. */
const VAN_NAMES = ['Van 1', 'Van 2', 'Van 3']

const STAFF_NAMES = ['Mia', 'Jordan', 'Alexis', 'Sam', 'Rae', 'Kit']

/** Demo colour, deliberately kept OUT of the shipped pack config — a note a
 *  guest leaves is a property of this fixture, not of the trade. */
const NOTE_EXAMPLE: Record<string, string> = {
  restaurant: 'Window seat if possible',
  barbershop: 'Same barber as last time',
  nails: 'Allergic to acetone',
  detailing: 'Black SUV, pet hair',
  mobiledetailing: 'Driveway — gate code 4402',
  medspa: 'First visit — consult first',
  other: 'Called ahead',
}

/** Time already committed in the shop's own calendar. */
const BUSY: Record<string, [string, number, number][]> = {
  restaurant: [['Staff briefing', 16, 17], ['Private event — Booth 5', 21, 23]],
  mobiledetailing: [['Van service', 13, 14]],
  barbershop: [['Barber training', 12, 13]],
  nails: [['Supplier visit', 13, 14]],
  detailing: [['Equipment service', 12, 13]],
  medspa: [['Clinical meeting', 12, 13]],
  other: [],
}

const WAITING: [string, string, string][] = [
  ['Rebecca Tan', '+1 604 555 0164', '4 previous visits, no no-shows, average spend $88'],
  ['Julian Ferreira', '+1 778 555 0110', 'No history — ranked by arrival order'],
  ['Greg Mullen', '+1 604 555 0177', '2 no-shows on record — ranked last despite $140 average spend'],
]

let trade: any = null

/**
 * Where a mobile trade's customers are. Scattered across one metro so the
 * route has a real shape — a couple of clusters and one outlier, which is what
 * makes the "can I actually make it" question interesting rather than academic.
 */
const ADDRESSES: [string, number, number][] = [
  ['418 Maple Ridge Dr', 49.2827, -123.1207],
  ['77 Harbourview Ln', 49.2965, -123.1340],
  ['1220 Kingsway', 49.2480, -123.0710],
  ['3405 Oak Meadow Cres', 49.2380, -123.1450],
  ['92 Alder Court', 49.3120, -123.0820],
  ['615 Fraser St', 49.2600, -123.0900],
  ['2210 Westbrook Way', 49.2690, -123.2100],
  ['58 Quarry Rd', 49.3300, -123.0300],
  ['1701 Commercial Dr', 49.2700, -123.0700],
  ['840 Seymour Hts', 49.3450, -123.0100],
]

/** The van starts and ends here. */
export const BASE_LOCATION = { label: 'Shop — 12 Foundry Rd', lat: 49.2750, lng: -123.1000 }

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
    // Seed EVERY local day the window touches, not just its two ends. The
    // window starts at midnight-minus-12h, so its endpoints fall on the days
    // either side and the day actually being asked for was never seeded —
    // it only ever appeared because the concurrent availability call happened
    // to seed it first, which is a race the book lost as soon as the fixture
    // timings shifted.
    for (let t = new Date(start).getTime(); t <= new Date(end).getTime(); t += 6 * 3600_000) {
      seedDay(dayKeyOf(new Date(t).toISOString()))
    }
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

  // — the wizard's commit —
  if (path === '/setup' && method === 'POST') {
    if (body.mode === 'external_link' && !String(body.link_url || '').trim()) {
      return json({ detail: 'a booking link is required for that mode' }, 400)
    }
    const have = new Set(RESOURCES.map((r) => r.name.toLowerCase()))
    for (const r of body.resources || []) {
      if (have.has(String(r.name).toLowerCase())) continue
      RESOURCES.push({
        id: uid('r'), name: r.name, kind: r.kind,
        seats: r.seats ?? 1, sort_order: r.sort_order ?? 0, active: true,
      } as any)
    }
    const haveSvc = new Set(SERVICES.map((s) => s.name.toLowerCase()))
    for (const s of body.services || []) {
      if (haveSvc.has(String(s.name).toLowerCase())) continue
      SERVICES.push({
        id: uid('s'), name: s.name, description: null,
        duration_minutes: s.duration_minutes, buffer_minutes: s.buffer_minutes ?? 0,
        price_cents: null, min_party: s.min_party ?? 1, max_party: s.max_party ?? 1,
        active: true,
      } as any)
    }
    if ((body.hours || []).length) {
      HOURS.length = 0
      for (const h of body.hours) {
        HOURS.push({
          weekday: h.weekday,
          opens_at: `${h.opens_at}:00`.slice(0, 8),
          closes_at: `${h.closes_at}:00`.slice(0, 8),
          slot_minutes: h.slot_minutes ?? 15,
        })
      }
    }
    if (body.mode === 'external_link') {
      linkState.url = String(body.link_url).startsWith('http')
        ? body.link_url : `https://${body.link_url}`
      linkState.inherited = false
    }
    return json({ ok: true, mode: body.mode })
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

/**
 * Empty the fixture merchant so the screens behave like a shop that signed up
 * ninety seconds ago. Used by the preview's "First run" tab and by ?wizard.
 */
export function resetToNewMerchant() {
  RESOURCES.length = 0
  SERVICES.length = 0
  HOURS.length = 0
  bookings.length = 0
  seededDays.clear()
  linkState.url = ''
  linkState.inherited = false
  linkState.sent = 0
  linkState.opened = 0
  linkState.failed = 0
}

export function installFixtureApi() {
  if (typeof window !== 'undefined' && window.location.search.includes('wizard')) {
    resetToNewMerchant()
  }

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
