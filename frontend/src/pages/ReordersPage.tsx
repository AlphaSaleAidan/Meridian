/**
 * Reorder Radar — the lapsed-cycle board.
 *
 * A repeat-purchase trade's revenue is a set of clocks: Chen buys BPC-157
 * every 4 weeks, and when he is 9 days late that is not a mystery, it is a
 * phone call nobody made. This page is those clocks, sorted by how late they
 * run, with the two buttons that close the loop: text a reorder link, or
 * have the agent call.
 *
 * DEMO SURFACE. The real feed is the Tagada connector's order history
 * (docs/TAGADA_CONNECTOR.md § Reorder loop): median gap between a customer's
 * orders of the same product = their cycle; lapsed = today - last order >
 * cycle + grace. The actions ride rails that already exist and already work
 * — the phone agent's send_payment_text and create_order_link tools were
 * verified live on the ResearchChem line 2026-08-20. Outbound contact
 * REQUIRES checkout-time consent (TCPA) — the connector spec makes consent a
 * first-class column, and this page must never show a customer who has not
 * opted in.
 */
import { useMemo, useState } from 'react'
import {
  CalendarClock, CircleDollarSign, MessageSquare, PhoneCall, Radar, Users,
} from 'lucide-react'
import StatCard from '@/components/StatCard'
import { getProducts } from '@/lib/business-config'
import { getActiveBusinessType, getCurrencyMultiplier } from '@/lib/demo-context'
import { NAMES } from '@/lib/demo-bookings'
import { formatCents, formatCentsCompact } from '@/lib/format'

interface Lapse {
  id: string
  customer: string
  product: string
  cycleDays: number
  daysLate: number
  cents: number
  ordersSoFar: number
}

type Outcome = 'texted' | 'queued'

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

function demoLapses(): { lapsed: Lapse[]; onCycle: number } {
  const bt = getActiveBusinessType()
  const rand = seeded(`reorders:${bt}`)
  const fx = getCurrencyMultiplier()
  const products = [...getProducts(bt)].sort((a, b) => b.popularity - a.popularity).slice(0, 5)
  if (!products.length) return { lapsed: [], onCycle: 0 }
  const lapsed: Lapse[] = []
  const n = 7 + Math.floor(rand() * 3)
  for (let i = 0; i < n; i++) {
    const p = products[Math.floor(rand() * products.length)]
    const cycle = [21, 28, 28, 30, 35][Math.floor(rand() * 5)]
    lapsed.push({
      id: `lap_${i}`,
      customer: NAMES[(i * 5 + 2) % NAMES.length][0],
      product: p.name,
      cycleDays: cycle,
      daysLate: 2 + Math.floor(rand() * 19),
      cents: Math.round(p.price * fx),
      ordersSoFar: 2 + Math.floor(rand() * 9),
    })
  }
  // Latest first: the longer they run, the colder they get.
  lapsed.sort((a, b) => b.daysLate - a.daysLate)
  return { lapsed, onCycle: 38 + Math.floor(rand() * 20) }
}

export default function ReordersPage() {
  const { lapsed, onCycle } = useMemo(demoLapses, [])
  const [done, setDone] = useState<Record<string, Outcome>>({})

  const atRisk = lapsed.filter((l) => !done[l.id])
  const valueAtRisk = atRisk.reduce((t, l) => t + l.cents, 0)

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F5F7]">Reorder radar</h1>
        <p className="mt-1 text-sm text-[#A1A1A8]">
          Every regular runs on a cycle. These are the ones past theirs — each row is a sale
          that happens the moment somebody reaches out, and only these customers opted in to hear from you.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Lapsed right now" value={String(atRisk.length)}
                  subtitle="past their usual cycle" icon={Radar}
                  iconColor={atRisk.length ? 'text-[#F5A524]' : 'text-[#17C5B0]'} />
        <StatCard label="Value on the table" value={formatCentsCompact(valueAtRisk)}
                  subtitle="their usual order, once each" icon={CircleDollarSign} iconColor="text-[#1A8FD6]" />
        <StatCard label="On cycle" value={String(onCycle)}
                  subtitle="regulars not due yet" icon={Users} iconColor="text-[#17C5B0]" />
        <StatCard label="Median cycle" value="28 days"
                  subtitle="across your regulars" icon={CalendarClock} iconColor="text-[#1A8FD6]" />
      </div>

      <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
        <h2 className="mb-3 text-sm font-semibold text-[#F5F5F7]">Past their cycle</h2>
        <div className="-mx-2 divide-y divide-[#1F1F23]">
          {lapsed.map((l) => {
            const out = done[l.id]
            return (
              <div key={l.id} className="flex items-center gap-3 px-2 py-2.5">
                <div className={`w-14 shrink-0 text-center font-mono text-sm font-semibold ${
                  l.daysLate >= 14 ? 'text-[#E5484D]' : l.daysLate >= 7 ? 'text-[#F5A524]' : 'text-[#D4D4D8]'
                }`}>
                  {l.daysLate}d
                  <div className="text-[9px] font-normal text-[#6B6B73]">late</div>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm font-medium text-[#F5F5F7]">{l.customer}</div>
                  <div className="truncate text-xs text-[#A1A1A8]">
                    {l.product} · every {l.cycleDays}d · {l.ordersSoFar} orders so far
                  </div>
                </div>
                <span className="hidden w-16 shrink-0 text-right font-mono text-sm text-[#F5F5F7] sm:inline">
                  {formatCents(l.cents)}
                </span>
                {out ? (
                  <span className={`shrink-0 rounded border px-2 py-1 text-[10px] font-medium ${
                    out === 'texted'
                      ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5 text-[#17C5B0]'
                      : 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6]'
                  }`}>
                    {out === 'texted' ? 'Reorder link sent' : 'Queued for the agent'}
                  </span>
                ) : (
                  <div className="flex shrink-0 items-center gap-1.5">
                    <button onClick={() => setDone((d) => ({ ...d, [l.id]: 'texted' }))}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-2.5 py-1.5 text-xs text-[#D4D4D8] transition-colors hover:border-[#17C5B0]/50 hover:text-[#17C5B0]">
                      <MessageSquare className="h-3.5 w-3.5" /> Text link
                    </button>
                    <button onClick={() => setDone((d) => ({ ...d, [l.id]: 'queued' }))}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-[#1F1F23] px-2.5 py-1.5 text-xs text-[#D4D4D8] transition-colors hover:border-[#1A8FD6]/50 hover:text-[#1A8FD6]">
                      <PhoneCall className="h-3.5 w-3.5" /> Agent call
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
        <p className="mt-3 text-[11px] text-[#6B6B73]">
          Texts and calls go only to customers who opted in at checkout. The agent takes the
          reorder on the call and texts the payment link itself.
        </p>
      </section>
    </div>
  )
}
