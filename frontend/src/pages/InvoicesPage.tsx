/**
 * Send a custom invoice — the bill for work the till never sees.
 *
 * An online store's checkout handles the catalogue; what it cannot handle is
 * the custom order: the bulk purchase quoted on the phone, the wholesale
 * account, the special request. Today that money is collected by PayPal link
 * or e-transfer and never lands beside the rest of the revenue. This page is
 * that bill: line items, a memo, a due date, and a payable link in the
 * customer's inbox.
 *
 * DEMO SURFACE. Sending shows the flow and seeds the ledger locally; the
 * real send rides Stripe (Connect is already live for payments) when this
 * graduates. Everything here is deliberately shaped like a Stripe invoice —
 * line items in cents, days-until-due — so graduation is wiring, not rework.
 */
import { useMemo, useState } from 'react'
import { Plus, Send, Trash2 } from 'lucide-react'
import { getProducts } from '@/lib/business-config'
import { getActiveBusinessType, getCurrencyMultiplier } from '@/lib/demo-context'
import { NAMES } from '@/lib/demo-bookings'
import { currencyPrefix, formatCents, formatDate } from '@/lib/format'

interface Line {
  description: string
  qty: number
  /** Unit price in display-market cents, already converted. */
  unitCents: number
}

const DUE_CHOICES = [
  { days: 0, label: 'On receipt' },
  { days: 7, label: '7 days' },
  { days: 14, label: '14 days' },
  { days: 30, label: '30 days' },
]

/** The demo ledger: what "recent invoices" looks like once this is real.
 *  Deterministic, derived from the trade's own catalogue. */
function recentInvoices() {
  const products = getProducts(getActiveBusinessType())
  const fx = getCurrencyMultiplier()
  const now = Date.now()
  const rows = [
    { n: 1042, name: NAMES[3][0], mult: 6, daysAgo: 1, status: 'sent' as const },
    { n: 1041, name: NAMES[11][0], mult: 12, daysAgo: 3, status: 'paid' as const },
    { n: 1040, name: NAMES[7][0], mult: 4, daysAgo: 6, status: 'paid' as const },
    { n: 1039, name: NAMES[16][0], mult: 9, daysAgo: 12, status: 'overdue' as const },
    { n: 1038, name: NAMES[20][0], mult: 5, daysAgo: 15, status: 'paid' as const },
  ]
  return rows.map((r, i) => ({
    id: `INV-${r.n}`,
    customer: r.name,
    cents: Math.round((products[i % products.length]?.price ?? 5000) * r.mult * fx),
    date: new Date(now - r.daysAgo * 86400_000).toISOString(),
    status: r.status,
  }))
}

const STATUS_STYLE = {
  paid: 'text-[#17C5B0] border-[#17C5B0]/30 bg-[#17C5B0]/5',
  sent: 'text-[#1A8FD6] border-[#1A8FD6]/30 bg-[#1A8FD6]/5',
  overdue: 'text-[#E5484D] border-[#E5484D]/30 bg-[#E5484D]/5',
}

const inputCls =
  'w-full rounded-lg border border-[#1F1F23] bg-[#0E0E11] px-3 py-2 text-sm text-[#F5F5F7] ' +
  'placeholder:text-[#6B6B73] focus:border-[#1A8FD6]/60 focus:outline-none'

export default function InvoicesPage() {
  const products = getProducts(getActiveBusinessType())
  const fx = getCurrencyMultiplier()

  const [customer, setCustomer] = useState('')
  const [email, setEmail] = useState('')
  const [memo, setMemo] = useState('')
  const [dueDays, setDueDays] = useState(7)
  const [lines, setLines] = useState<Line[]>([
    // Start from the trade's own best seller: an invoice builder that opens
    // on an empty row makes the owner type what the product already knows.
    {
      description: products[0]?.name ?? '',
      qty: 1,
      unitCents: Math.round((products[0]?.price ?? 0) * fx),
    },
  ])
  const [sentTo, setSentTo] = useState<{ email: string; id: string; cents: number } | null>(null)

  const totalCents = useMemo(
    () => lines.reduce((s, l) => s + l.qty * l.unitCents, 0), [lines])
  const ledger = useMemo(recentInvoices, [])

  const setLine = (i: number, patch: Partial<Line>) =>
    setLines((ls) => ls.map((l, j) => (j === i ? { ...l, ...patch } : l)))

  const canSend = customer.trim() && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
    && lines.some((l) => l.description.trim() && l.qty > 0 && l.unitCents > 0)

  const send = () => {
    if (!canSend) return
    setSentTo({ email, id: `INV-${1043 + Math.floor(totalCents % 7)}`, cents: totalCents })
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-[#F5F5F7]">Send an invoice</h1>
        <p className="mt-1 text-sm text-[#A1A1A8]">
          A custom bill for the order your checkout never saw — the customer pays it online,
          and it lands beside the rest of the day's revenue.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        {/* ── The bill ─────────────────────────────────────────────── */}
        <section className="space-y-4 rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-[11px] uppercase tracking-wide text-[#6B6B73]">Bill to</label>
              <input className={inputCls} placeholder="Customer name"
                     value={customer} onChange={(e) => setCustomer(e.target.value)} />
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] uppercase tracking-wide text-[#6B6B73]">Email</label>
              <input className={inputCls} placeholder="name@example.com" type="email"
                     value={email} onChange={(e) => setEmail(e.target.value)} />
            </div>
          </div>

          <div>
            <label className="mb-1.5 block text-[11px] uppercase tracking-wide text-[#6B6B73]">Items</label>
            <div className="space-y-2">
              {lines.map((l, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input className={inputCls} placeholder="Description" list="invoice-catalog"
                         value={l.description}
                         onChange={(e) => {
                           const hit = products.find((p) => p.name === e.target.value)
                           setLine(i, hit
                             ? { description: hit.name, unitCents: Math.round(hit.price * fx) }
                             : { description: e.target.value })
                         }} />
                  <input className={`${inputCls} w-16 text-center font-mono`} type="number" min={1}
                         aria-label="Quantity" value={l.qty}
                         onChange={(e) => setLine(i, { qty: Math.max(1, Number(e.target.value) || 1) })} />
                  <div className="relative">
                    <input className={`${inputCls} w-32 pl-7 text-right font-mono`} type="number"
                           min={0} step="0.01" aria-label="Unit price"
                           value={(l.unitCents / 100).toFixed(2)}
                           onChange={(e) => setLine(i, { unitCents: Math.round((Number(e.target.value) || 0) * 100) })} />
                    <span className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-xs text-[#6B6B73]">{currencyPrefix()}</span>
                  </div>
                  <button aria-label="Remove line" disabled={lines.length === 1}
                          onClick={() => setLines((ls) => ls.filter((_, j) => j !== i))}
                          className="p-1.5 text-[#6B6B73] transition-colors hover:text-[#E5484D] disabled:opacity-30">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
            {/* The catalogue rides a datalist: type freely, or pick a product
                and its price fills itself in. */}
            <datalist id="invoice-catalog">
              {products.map((p) => <option key={p.sku} value={p.name} />)}
            </datalist>
            <button onClick={() => setLines((ls) => [...ls, { description: '', qty: 1, unitCents: 0 }])}
                    className="mt-2 inline-flex items-center gap-1.5 text-xs text-[#1A8FD6] transition-colors hover:text-[#F5F5F7]">
              <Plus className="h-3.5 w-3.5" /> Add line
            </button>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-[11px] uppercase tracking-wide text-[#6B6B73]">Due</label>
              <div className="flex gap-1.5">
                {DUE_CHOICES.map((d) => (
                  <button key={d.days} onClick={() => setDueDays(d.days)}
                          className={`rounded-lg border px-2.5 py-1.5 text-xs transition-colors ${
                            dueDays === d.days
                              ? 'border-[#1A8FD6]/60 bg-[#1A8FD6]/10 text-[#F5F5F7]'
                              : 'border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7]'
                          }`}>
                    {d.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-[11px] uppercase tracking-wide text-[#6B6B73]">Memo <span className="normal-case text-[#6B6B73]">(optional)</span></label>
              <input className={inputCls} placeholder="Shows on the invoice"
                     value={memo} onChange={(e) => setMemo(e.target.value)} />
            </div>
          </div>
        </section>

        {/* ── Total, send, and the ledger ──────────────────────────── */}
        <aside className="space-y-4">
          <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
            <div className="flex items-baseline justify-between">
              <span className="text-[11px] uppercase tracking-wide text-[#6B6B73]">Total</span>
              <span className="font-mono text-2xl font-semibold text-[#F5F5F7]">{formatCents(totalCents)}</span>
            </div>
            <p className="mt-1 text-right text-[11px] text-[#6B6B73]">
              {dueDays === 0 ? 'due on receipt' : `due in ${dueDays} days`}
            </p>
            <button onClick={send} disabled={!canSend}
                    className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#17C5B0] px-4 py-2.5 text-sm font-medium text-[#0B0B0D] transition-opacity hover:opacity-90 disabled:opacity-40">
              <Send className="h-4 w-4" /> Send invoice
            </button>
            {sentTo && (
              <div className="mt-3 rounded-lg border border-[#17C5B0]/25 bg-[#17C5B0]/5 p-3 text-xs text-[#D4D4D8]">
                <span className="font-medium text-[#17C5B0]">{sentTo.id} sent</span> to {sentTo.email} —
                payable online for {formatCents(sentTo.cents)}. You'll see it in the ledger the moment it's paid.
              </div>
            )}
          </section>

          <section className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
            <h2 className="mb-3 text-sm font-semibold text-[#F5F5F7]">Recent invoices</h2>
            <div className="-mx-2 divide-y divide-[#1F1F23]">
              {ledger.map((inv) => (
                <div key={inv.id} className="flex items-center gap-3 px-2 py-2.5">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline gap-2">
                      <span className="truncate text-sm text-[#F5F5F7]">{inv.customer}</span>
                      <span className="shrink-0 font-mono text-[10px] text-[#6B6B73]">{inv.id}</span>
                    </div>
                    <div className="text-[11px] text-[#6B6B73]">{formatDate(inv.date)}</div>
                  </div>
                  <span className={`shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium capitalize ${STATUS_STYLE[inv.status]}`}>
                    {inv.status}
                  </span>
                  <span className="w-20 shrink-0 text-right font-mono text-sm text-[#F5F5F7]">
                    {formatCents(inv.cents)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
