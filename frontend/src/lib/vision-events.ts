/**
 * Camera events — the things that need a person, not a chart.
 *
 * The rest of the camera pillar counts: walk-ins, occupancy, queue wait. Those
 * are planning numbers, read at the end of a week. An event is different — a
 * bottle went over by the machine eleven minutes ago and nobody has mopped it.
 * It has a time, a place, and a decision attached, and averaging it away is
 * exactly what destroys it.
 *
 * ANONYMOUS. An event records that someone at the counter was on a handset for
 * four minutes. It never records who: the row has no column for a person, and
 * the demo below invents none. That is the ceiling of the feature by design —
 * "someone at the till" is enough to walk over and look, and it is the version
 * a merchant can run without first taking advice about monitoring staff.
 */
import { getAuthHeaders } from '@/lib/supabase'
import { getActiveBusinessType } from '@/lib/demo-context'

const API_BASE = import.meta.env.VITE_API_URL || ''

export type EventKind =
  | 'spill' | 'product_loss' | 'phone_use'
  | 'unattended' | 'blocked_exit' | 'after_hours'

export type EventSeverity = 'critical' | 'warning' | 'info'
export type EventStatus = 'new' | 'acknowledged' | 'resolved' | 'dismissed'

export interface VisionEvent {
  id: string
  kind: EventKind
  severity: EventSeverity
  status: EventStatus
  zone: string | null
  detectedAt: string
  durationSec: number | null
  confidence: number | null
  detail: string | null
  /** Merchant-facing copy, shipped by the server so every channel that ever
   *  renders an event says the same thing about it. */
  title: string
  why: string
}

export interface EventSummary {
  total: number
  open: number
  criticalOpen: number
  byKind: Record<string, number>
}

/** Ordered worst-first. Used for grouping and for the filter chips. */
export const EVENT_KINDS: { key: EventKind; label: string }[] = [
  { key: 'spill', label: 'Spills' },
  { key: 'product_loss', label: 'Product loss' },
  { key: 'blocked_exit', label: 'Blocked exits' },
  { key: 'after_hours', label: 'After hours' },
  { key: 'unattended', label: 'Counter unattended' },
  { key: 'phone_use', label: 'Phone use' },
]

function mapEvent(row: any): VisionEvent {
  return {
    id: row.id,
    kind: row.kind,
    severity: row.severity || 'info',
    status: row.status || 'new',
    zone: row.zone ?? null,
    detectedAt: row.detected_at,
    durationSec: row.duration_sec ?? null,
    confidence: row.confidence ?? null,
    detail: row.detail ?? null,
    title: row.title || 'Something worth a look',
    why: row.why || '',
  }
}

export async function fetchVisionEvents(
  orgId: string, opts: { hours?: number; kind?: EventKind | null } = {},
): Promise<{ events: VisionEvent[]; summary: EventSummary }> {
  if (isDemoOrg(orgId)) return demoEvents(opts.kind ?? null)

  const params = new URLSearchParams({ hours: String(opts.hours ?? 48) })
  if (opts.kind) params.set('kind', opts.kind)

  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE}/api/vision/events/${orgId}?${params}`, {
    credentials: 'include',
    headers: { ...headers, Accept: 'application/json' },
  })
  if (!res.ok) throw new Error(`events ${res.status}`)
  const body = await res.json()
  const events = (body.events || []).map(mapEvent)
  const s = body.summary || {}
  return {
    events,
    summary: {
      total: s.total ?? events.length,
      open: s.open ?? 0,
      criticalOpen: s.critical_open ?? 0,
      byKind: s.by_kind ?? {},
    },
  }
}

export async function resolveVisionEvent(
  orgId: string, id: string, status: EventStatus, note?: string,
): Promise<void> {
  if (isDemoOrg(orgId)) {
    const row = DEMO_STATE.find((e) => e.id === id)
    if (row) row.status = status
    return
  }
  const headers = await getAuthHeaders()
  const res = await fetch(`${API_BASE}/api/vision/events/${id}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ status, note }),
  })
  if (!res.ok) throw new Error(`resolve ${res.status}`)
}

// ── Demo ────────────────────────────────────────────────────────────────
//
// Per trade, because the whole point is that a merchant recognises their own
// shop. A barbershop does not have a walk-in freezer and a restaurant does not
// leave a display case open.

function isDemoOrg(orgId: string): boolean {
  return orgId === 'demo' || !orgId
}

interface DemoSeed {
  kind: EventKind
  severity: EventSeverity
  zone: string
  minutesAgo: number
  detail: string
  durationSec?: number
  status?: EventStatus
}

const BY_TRADE: Record<string, DemoSeed[]> = {
  restaurant: [
    { kind: 'spill', severity: 'critical', zone: 'Dining room', minutesAgo: 14,
      detail: 'Liquid on the floor between tables 6 and 7, still there after 12 minutes.' },
    { kind: 'unattended', severity: 'warning', zone: 'Host stand', minutesAgo: 52,
      durationSec: 240, detail: 'Four minutes with nobody on the host stand and two parties waiting.' },
    { kind: 'phone_use', severity: 'info', zone: 'Bar', minutesAgo: 96,
      durationSec: 310, detail: 'Prolonged handset use behind the bar during service.' },
    { kind: 'blocked_exit', severity: 'critical', zone: 'Rear corridor', minutesAgo: 190,
      detail: 'Delivery crates left in front of the fire exit.', status: 'resolved' },
  ],
  quickservice: [
    { kind: 'spill', severity: 'critical', zone: 'Counter', minutesAgo: 22,
      detail: 'Drink went over in front of the till.' },
    { kind: 'unattended', severity: 'warning', zone: 'Front counter', minutesAgo: 65,
      durationSec: 180, detail: 'Three minutes unattended with five people in the queue.' },
    { kind: 'phone_use', severity: 'info', zone: 'Prep line', minutesAgo: 120,
      durationSec: 420, detail: 'Seven minutes on a handset at the prep line.' },
  ],
  coffeeshop: [
    { kind: 'spill', severity: 'critical', zone: 'Milk station', minutesAgo: 8,
      detail: 'Milk on the floor at the jug station.' },
    { kind: 'product_loss', severity: 'warning', zone: 'Pastry case', minutesAgo: 74,
      detail: 'Item left the pastry case with no matching sale within two minutes.' },
    { kind: 'phone_use', severity: 'info', zone: 'Espresso bar', minutesAgo: 133,
      durationSec: 265, detail: 'Handset use at the bar during the morning rush.' },
  ],
  smokeshop: [
    { kind: 'product_loss', severity: 'critical', zone: 'Display wall', minutesAgo: 31,
      detail: 'Case opened and an item removed with no sale in the following four minutes.' },
    { kind: 'after_hours', severity: 'critical', zone: 'Back room', minutesAgo: 620,
      detail: 'Movement at 02:14 with the shop closed.', status: 'dismissed' },
    { kind: 'phone_use', severity: 'info', zone: 'Checkout', minutesAgo: 150,
      durationSec: 380, detail: 'Prolonged handset use at the till.' },
  ],
  autoshop: [
    { kind: 'spill', severity: 'critical', zone: 'Bay 2', minutesAgo: 26,
      detail: 'Fluid on the bay floor, not yet absorbed.' },
    { kind: 'blocked_exit', severity: 'critical', zone: 'Side door', minutesAgo: 88,
      detail: 'Tyre stack in front of the side exit.' },
    { kind: 'product_loss', severity: 'warning', zone: 'Parts shelf', minutesAgo: 200,
      detail: 'Part taken from the shelf with no job number attached.', status: 'acknowledged' },
  ],
  barbershop: [
    { kind: 'spill', severity: 'critical', zone: 'Wash basin', minutesAgo: 19,
      detail: 'Water pooled by the basin.' },
    { kind: 'product_loss', severity: 'warning', zone: 'Retail shelf', minutesAgo: 105,
      detail: 'Product left the retail shelf with no sale on the till.' },
    { kind: 'phone_use', severity: 'info', zone: 'Chair 2', minutesAgo: 160,
      durationSec: 290, detail: 'Handset use at the chair between cuts.' },
  ],
  nails: [
    { kind: 'spill', severity: 'critical', zone: 'Pedicure row', minutesAgo: 12,
      detail: 'Water on the floor beside the pedicure chairs.' },
    { kind: 'product_loss', severity: 'warning', zone: 'Polish wall', minutesAgo: 140,
      detail: 'Bottle removed from the wall with no matching sale.' },
    { kind: 'unattended', severity: 'warning', zone: 'Front desk', minutesAgo: 58,
      durationSec: 200, detail: 'Front desk empty while a client waited to pay.' },
  ],
  medspa: [
    { kind: 'product_loss', severity: 'critical', zone: 'Treatment room 2', minutesAgo: 44,
      detail: 'Stock removed from the cabinet with no treatment logged against it.' },
    { kind: 'blocked_exit', severity: 'critical', zone: 'Rear corridor', minutesAgo: 175,
      detail: 'Linen trolley left across the corridor exit.', status: 'resolved' },
    { kind: 'unattended', severity: 'warning', zone: 'Reception', minutesAgo: 70,
      durationSec: 260, detail: 'Reception unattended with a client waiting.' },
  ],
}

const FALLBACK: DemoSeed[] = BY_TRADE.restaurant

/**
 * Mutable so the demo's Resolve and Dismiss buttons do something.
 *
 * Rebuilt whenever the trade changes — a barbershop's events must not survive
 * a switch to a restaurant, which is what a module-level constant would do.
 */
let DEMO_STATE: VisionEvent[] = []
let DEMO_TRADE = ''

function buildDemo(): VisionEvent[] {
  const trade = getActiveBusinessType()
  const key = trade === 'fast_food' ? 'quickservice'
    : trade === 'coffee_shop' ? 'coffeeshop'
    : trade === 'auto_shop' ? 'autoshop'
    : trade === 'smoke_shop' ? 'smokeshop'
    : trade === 'mobile_detailing' ? 'autoshop'
    : trade === 'detailing' ? 'autoshop'
    : trade
  const seeds = BY_TRADE[key] || FALLBACK
  const now = Date.now()

  return seeds.map((seed, i) => {
    const meta = COPY[seed.kind]
    return {
      id: `demo-ev-${key}-${i}`,
      kind: seed.kind,
      severity: seed.severity,
      status: seed.status || 'new',
      zone: seed.zone,
      detectedAt: new Date(now - seed.minutesAgo * 60_000).toISOString(),
      durationSec: seed.durationSec ?? null,
      // A demo that shows 100% confidence is a demo that oversells the
      // detector. These are the numbers a real model returns.
      confidence: 0.72 + ((i * 7) % 20) / 100,
      detail: seed.detail,
      title: meta.title,
      why: meta.why,
    }
  })
}

/** The same copy the server ships, so the demo and the product read alike. */
const COPY: Record<EventKind, { title: string; why: string }> = {
  spill: { title: 'Spill on the floor',
           why: 'A wet floor is a slip claim until somebody mops it.' },
  product_loss: { title: 'Product left without a sale',
                  why: 'Stock moved off the shelf with no matching transaction.' },
  phone_use: { title: 'Prolonged phone use in a work zone',
               why: 'Time on a handset in a work zone is time a customer is waiting.' },
  unattended: { title: 'Counter unattended',
                why: 'Customers were waiting with nobody serving.' },
  blocked_exit: { title: 'Exit or aisle blocked',
                  why: 'A blocked fire exit is the one that fails an inspection.' },
  after_hours: { title: 'Movement after hours',
                 why: 'Something moved while the shop should have been empty.' },
}

function demoEvents(kind: EventKind | null): { events: VisionEvent[]; summary: EventSummary } {
  const trade = getActiveBusinessType()
  if (trade !== DEMO_TRADE) {
    DEMO_TRADE = trade
    DEMO_STATE = buildDemo()
  }
  const all = DEMO_STATE
  const events = kind ? all.filter((e) => e.kind === kind) : all
  const open = all.filter((e) => e.status === 'new')
  const byKind: Record<string, number> = {}
  for (const e of all) byKind[e.kind] = (byKind[e.kind] || 0) + 1
  return {
    events,
    summary: {
      total: all.length,
      open: open.length,
      criticalOpen: open.filter((e) => e.severity === 'critical').length,
      byKind,
    },
  }
}
