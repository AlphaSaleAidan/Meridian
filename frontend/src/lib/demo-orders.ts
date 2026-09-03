/**
 * The day's orders for a counter trade — the feed the storefront connector
 * will one day replace.
 *
 * A trade with no book still has a day, and until now the workspace could
 * only show it as four tiles and a phone chart. This generates the thing an
 * owner actually scans: who ordered, what, through which channel, and where
 * it is now. Deterministic per day and per trade, the same way demo-bookings
 * seeds the book, so paging back to yesterday shows yesterday's orders and
 * not a reshuffle.
 *
 * DEMO ONLY, and deliberately shaped for what comes next: when web orders
 * ingest from the merchant's real storefront (Shopify/Woo — the missing
 * capability logged on the peptides pack), it lands as this same
 * WorkspaceOrder shape and the screen does not change.
 */
import type { NichePack } from '@/config/niches'
import { getProducts, type ProductDef } from './business-config'
import { getActiveBusinessType, getCurrencyMultiplier } from './demo-context'
import { NAMES } from './demo-bookings'

export interface WorkspaceOrder {
  id: string
  /** Display label, e.g. "7:42 PM". Newest orders sort first. */
  timeLabel: string
  customer: string
  /** "BPC-157 5mg ×2 · Bacteriostatic Water 30ml" */
  items: string
  totalCents: number
  channel: 'web' | 'phone' | 'counter'
  /** Shipping trades run paid → packed → shipped; over-the-counter trades
   *  are completed the moment the bag crosses the till. */
  status: 'paid' | 'packed' | 'shipped' | 'completed' | 'refunded'
}

/** Same FNV/mulberry construction demo-bookings uses; a different stream so
 *  the orders do not mirror the book. */
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

function timeLabel(minutes: number): string {
  const h24 = Math.floor(minutes / 60) % 24
  const m = minutes % 60
  const h12 = h24 % 12 === 0 ? 12 : h24 % 12
  return `${h12}:${String(m).padStart(2, '0')} ${h24 < 12 ? 'AM' : 'PM'}`
}

function pickItems(products: ProductDef[], rand: () => number): { text: string; cents: number } {
  const count = rand() < 0.45 ? 1 : rand() < 0.8 ? 2 : 3
  const chosen: { p: ProductDef; qty: number }[] = []
  const pool = [...products]
  for (let i = 0; i < count && pool.length; i++) {
    // Popularity-weighted without building a distribution: walk until a
    // product survives its own popularity roll.
    let idx = Math.floor(rand() * pool.length)
    for (let tries = 0; tries < 4; tries++) {
      if (rand() < pool[idx].popularity) break
      idx = Math.floor(rand() * pool.length)
    }
    const p = pool.splice(idx, 1)[0]
    chosen.push({ p, qty: i === 0 && rand() < 0.3 ? 2 : 1 })
  }
  return {
    text: chosen.map(({ p, qty }) => (qty > 1 ? `${p.name} ×${qty}` : p.name)).join(' · '),
    cents: chosen.reduce((s, { p, qty }) => s + p.price * qty, 0),
  }
}

export function demoOrdersFor(pack: NichePack, day: string): WorkspaceOrder[] {
  const rand = seeded(`orders:${pack.key}:${day}`)
  const products = getProducts(getActiveBusinessType())
  if (!products.length) return []
  const channels = pack.orderChannels ?? ['counter', 'phone']
  const fx = getCurrencyMultiplier()

  // A web channel takes orders while the shop sleeps; a counter cannot.
  const [openH] = pack.opens ? pack.opens.split(':').map(Number) : [9]
  const [closeH] = pack.closes ? pack.closes.split(':').map(Number) : [17]
  const dayStart = channels.includes('web') ? 6 * 60 + 30 : openH * 60
  const dayEnd = channels.includes('web') ? 22 * 60 : closeH * 60

  const n = 11 + Math.floor(rand() * 4)
  const rows: { minutes: number; order: WorkspaceOrder }[] = []
  for (let i = 0; i < n; i++) {
    const minutes = dayStart + Math.floor(rand() * (dayEnd - dayStart))
    const { text, cents } = pickItems(products, rand)
    // The first-listed channel is the trade's main one and takes ~70%.
    const channel = rand() < 0.7 ? channels[0] : channels[Math.floor(rand() * channels.length)]
    let status: WorkspaceOrder['status']
    if (rand() < 0.05) {
      status = 'refunded'
    } else if (!pack.ships) {
      status = 'completed'
    } else {
      // Fulfilment follows the clock: the morning's orders have left, the
      // afternoon's are on the bench, the evening's are still just paid.
      const age = (dayEnd - minutes) / (dayEnd - dayStart)
      status = age > 0.6 ? 'shipped' : age > 0.25 ? 'packed' : 'paid'
    }
    rows.push({
      minutes,
      order: {
        id: `#${4100 + Math.floor(rand() * 800)}`,
        timeLabel: timeLabel(minutes),
        customer: NAMES[Math.floor(rand() * NAMES.length)][0],
        items: text,
        totalCents: Math.round(cents * fx),
        channel,
        status,
      },
    })
  }
  // Newest first, like every order feed.
  return rows.sort((a, b) => b.minutes - a.minutes).map((r) => r.order)
}
