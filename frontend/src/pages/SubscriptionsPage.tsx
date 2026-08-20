/**
 * Subscriptions — the recurring half of a repeat-purchase trade.
 *
 * A peptide store's best customers are on a monthly reorder; a mobile
 * detailer's are on a monthly wash plan. Both businesses live or die on the
 * same three numbers: how many are subscribed, what that is worth a month,
 * and who is about to churn (past-due card, paused plan, renewal this week).
 *
 * DEMO SURFACE, shaped for the Tagada connector: TagadaPay's subscriptions
 * API returns exactly this — plan, cadence, status, next rebill — so when
 * the connector lands (docs/TAGADA_CONNECTOR.md) these rows become the
 * merchant's real book and the screen does not change. Pause/resume/cancel
 * exist there too (POST /subscriptions/{id}/...), which is why the demo
 * shows the controls rather than a read-only table.
 */
import { useMemo, useState } from 'react'
import {
  AlertTriangle, CalendarClock, DollarSign, Pause, Play, RefreshCcw, X,
} from 'lucide-react'
import StatCard from '@/components/StatCard'
import { getProducts } from '@/lib/business-config'
import { getActiveBusinessType, getCurrencyMultiplier } from '@/lib/demo-context'
import { NAMES } from '@/lib/demo-bookings'
import { formatCents, formatCentsCompact } from '@/lib/format'

type SubStatus = 'active' | 'past_due' | 'paused'

interface Sub {
  id: string
  customer: string
  plan: string
  cadence: string
  cents: number
  /** Days until the next rebill (negative = overdue). */
  nextInDays: number
  status: SubStatus
  monthsIn: number
}

/** Same deterministic construction as demo-orders: the book is stable across
 *  reloads, because a subscriber list that reshuffles reads as fake. */
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

function demoSubscriptions(): Sub[] {
  const bt = getActiveBusinessType()
  const rand = seeded(`subs:${bt}`)
  const fx = getCurrencyMultiplier()
  // The trade's own catalogue, most popular first — a subscription is just a
  // product on a clock, and the popular products are the subscribed ones.
  const products = [...getProducts(bt)].sort((a, b) => b.popularity - a.popularity).slice(0, 6)
  if (!products.length) return []
  const n = 14 + Math.floor(rand() * 5)
  const subs: Sub[] = []
  for (let i = 0; i < n; i++) {
    const p = products[Math.floor(rand() * products.length)]
    const roll = rand()
    const status: SubStatus = roll < 0.78 ? 'active' : roll < 0.9 ? 'past_due' : 'paused'
    subs.push({
      id: `sub_${(1000 + Math.floor(rand() * 9000)).toString(16)}${i}`,
      customer: NAMES[(i * 7 + Math.floor(rand() * 3)) % NAMES.length][0],
      plan: p.name,
      cadence: rand() < 0.8 ? 'Monthly' : 'Every 4 weeks',
      cents: Math.round(p.price * fx),
      nextInDays: status === 'past_due' ? -(1 + Math.floor(rand() * 6)) : Math.floor(rand() * 28),
      status,
      monthsIn: 1 + Math.floor(rand() * 14),
    })
  }
  // Soonest rebill first — the top of the list is the money that moves next.
  return subs.sort((a, b) => a.nextInDays - b.nextInDays)
}

const STATUS_STYLE: Record<SubStatus, string> = {
  active: 'text-[#17C5B0] border-[#17C5B0]/30 bg-[#17C5B0]/5',
  past_due: 'text-[#E5484D] border-[#E5484D]/30 bg-[#E5484D]/5',
  paused: 'text-[#F5A524] border-[#F5A524]/30 bg-[#F5A524]/5',
}
const STATUS_LABEL: Record<SubStatus, string> = {
  active: 'Active', past_due: 'Past due', paused: 'Paused',
}

function renewLabel(days: number): string {
  if (days < 0) return `${-days}d overdue`
  if (days === 0) return 'today'
  if (days === 1) return 'tomorrow'
  return `in ${days}d`
}

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<Sub[]>(demoSubscriptions)
  // Dunning, the demo take: a past-due card is money leaking on a schedule,
  // and the recovery move is a fresh payment link in a text — or the agent
  // calling, which is the rail this product already owns. Real send rides
  // the phone agent's send_payment_text tool (live on the ResearchChem
  // line); consent captured at signup, same rule as the Reorder Radar.
  const [recovery, setRecovery] = useState<Record<string, 'link' | 'call'>>({})

  const stats = useMemo(() => {
    const active = subs.filter((s) => s.status === 'active')
    const pastDue = subs.filter((s) => s.status === 'past_due')
    const mrr = subs.filter((s) => s.status !== 'paused').reduce((t, s) => t + s.cents, 0)
    const week = subs.filter((s) => s.status === 'active' && s.nextInDays >= 0 && s.nextInDays <= 7)
    return { active: active.length, pastDue: pastDue.length, mrr, week: week.length }
  }, [subs])

  const setStatus = (id: string, status: SubStatus) =>
    setSubs((ss) => ss.map((s) => (s.id === id ? { ...s, status } : s)))
  const cancel = (id: string) => setSubs((ss) => ss.filter((s) => s.id !== id))

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F5F7]">Subscriptions</h1>
        <p className="mt-1 text-sm text-[#A1A1A8]">
          The customers who pay you every month without being asked — and the ones about to stop.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Active subscriptions" value={String(stats.active)}
                  subtitle="billing on schedule" icon={RefreshCcw} iconColor="text-[#17C5B0]" />
        <StatCard label="Monthly recurring" value={formatCentsCompact(stats.mrr)}
                  subtitle="before churn" icon={DollarSign} iconColor="text-[#1A8FD6]" />
        <StatCard label="Renewing this week" value={String(stats.week)}
                  subtitle="money that moves next" icon={CalendarClock} iconColor="text-[#1A8FD6]" />
        <StatCard label="Past due" value={String(stats.pastDue)}
                  subtitle="card failed — retrying" icon={AlertTriangle}
                  iconColor={stats.pastDue > 0 ? 'text-[#E5484D]' : 'text-[#17C5B0]'} />
      </div>

      <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
        <h2 className="mb-3 text-sm font-semibold text-[#F5F5F7]">The book</h2>
        <div className="-mx-2 divide-y divide-[#1F1F23]">
          {subs.map((s) => (
            <div key={s.id} className="flex items-center gap-3 px-2 py-2.5">
              <div className="min-w-0 flex-1">
                <div className="flex items-baseline gap-2">
                  <span className="truncate text-sm font-medium text-[#F5F5F7]">{s.customer}</span>
                  <span className="shrink-0 text-[11px] text-[#6B6B73]">{s.monthsIn} mo</span>
                </div>
                <div className="truncate text-xs text-[#A1A1A8]">
                  {s.plan} · {s.cadence.toLowerCase()}
                </div>
              </div>
              <span className={`hidden shrink-0 font-mono text-[11px] sm:inline ${
                s.nextInDays < 0 ? 'text-[#E5484D]' : 'text-[#6B6B73]'
              }`}>
                {renewLabel(s.nextInDays)}
              </span>
              <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium ${STATUS_STYLE[s.status]}`}>
                {STATUS_LABEL[s.status]}
              </span>
              <span className="w-20 shrink-0 text-right font-mono text-sm text-[#F5F5F7]">
                {formatCents(s.cents)}
                <span className="text-[10px] text-[#6B6B73]">/mo</span>
              </span>
              {s.status === 'past_due' && (
                recovery[s.id] ? (
                  <span className={`shrink-0 rounded border px-2 py-1 text-[10px] font-medium ${
                    recovery[s.id] === 'link'
                      ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5 text-[#17C5B0]'
                      : 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6]'
                  }`}>
                    {recovery[s.id] === 'link' ? 'New payment link sent' : 'Queued for the agent'}
                  </span>
                ) : (
                  <div className="flex shrink-0 items-center gap-1.5">
                    <button onClick={() => setRecovery((r) => ({ ...r, [s.id]: 'link' }))}
                            className="rounded-lg border border-[#1F1F23] px-2 py-1 text-[10px] text-[#D4D4D8] transition-colors hover:border-[#17C5B0]/50 hover:text-[#17C5B0]">
                      Text new link
                    </button>
                    <button onClick={() => setRecovery((r) => ({ ...r, [s.id]: 'call' }))}
                            className="rounded-lg border border-[#1F1F23] px-2 py-1 text-[10px] text-[#D4D4D8] transition-colors hover:border-[#1A8FD6]/50 hover:text-[#1A8FD6]">
                      Agent call
                    </button>
                  </div>
                )
              )}
              <div className="flex shrink-0 items-center gap-1">
                {s.status === 'paused' ? (
                  <button aria-label="Resume" title="Resume" onClick={() => setStatus(s.id, 'active')}
                          className="p-1.5 text-[#6B6B73] transition-colors hover:text-[#17C5B0]">
                    <Play className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <button aria-label="Pause" title="Pause" onClick={() => setStatus(s.id, 'paused')}
                          className="p-1.5 text-[#6B6B73] transition-colors hover:text-[#F5A524]">
                    <Pause className="h-3.5 w-3.5" />
                  </button>
                )}
                <button aria-label="Cancel" title="Cancel" onClick={() => cancel(s.id)}
                        className="p-1.5 text-[#6B6B73] transition-colors hover:text-[#E5484D]">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
