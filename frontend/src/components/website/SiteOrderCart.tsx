/**
 * SiteOrderCart — online ordering cart for public merchant sites.
 *
 * Pay-first flow: "Pay & Place Order" POSTs the cart to /api/website/order,
 * which stores the order as awaiting_payment and returns a Stripe Checkout
 * URL. We redirect the customer there; the backend webhook releases the
 * ticket to the merchant's POS kitchen (marked PAID) only after Stripe
 * confirms payment. Back on the site, ?order=success|cancelled drives the
 * banner, and the success banner polls order status until the kitchen has it.
 */
import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, Minus, Plus, ShoppingBag, X, XCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface CartItem {
  name: string
  price: number
  quantity: number
  special_instructions?: string
}

/** Menu prices are freeform strings ("$14.99", "14.99 CAD"). Only items with
 * a parseable price can be ordered online. */
export function parsePrice(price?: string): number | null {
  if (!price) return null
  const m = price.replace(/,/g, '').match(/(\d+(?:\.\d{1,2})?)/)
  if (!m) return null
  const v = parseFloat(m[1])
  return Number.isFinite(v) && v > 0 ? v : null
}

interface Props {
  websiteId: string
  accent: string
  currencyHint: string
  cart: CartItem[]
  setCart: (items: CartItem[]) => void
}

export default function SiteOrderCart({ websiteId, accent, currencyHint, cart, setCart }: Props) {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [orderType, setOrderType] = useState<'pickup' | 'delivery'>('pickup')

  const count = cart.reduce((n, i) => n + i.quantity, 0)
  const subtotal = cart.reduce((s, i) => s + i.price * i.quantity, 0)

  const setQty = (idx: number, qty: number) => {
    if (qty <= 0) setCart(cart.filter((_, i) => i !== idx))
    else setCart(cart.map((it, i) => (i === idx ? { ...it, quantity: qty } : it)))
  }
  const setNote = (idx: number, note: string) =>
    setCart(cart.map((it, i) => (i === idx ? { ...it, special_instructions: note } : it)))

  const placeOrder = async () => {
    setError('')
    if (!name.trim()) { setError('Please enter your name.'); return }
    if (!phone.trim()) { setError('Please enter your phone number.'); return }
    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/website/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          website_id: websiteId,
          customer_name: name.trim(),
          customer_phone: phone.trim(),
          customer_email: email.trim() || null,
          order_type: orderType,
          items: cart.map(i => ({
            name: i.name,
            price: i.price,
            quantity: i.quantity,
            special_instructions: i.special_instructions || '',
          })),
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (!res.ok || !body.checkout_url) {
        setError(body.detail || 'Online payment is temporarily unavailable — please call to order.')
        setSubmitting(false)
        return
      }
      // Hand off to Stripe Checkout — the kitchen only gets the ticket after payment.
      window.location.href = body.checkout_url
    } catch {
      setError('Could not reach the ordering service — please try again or call.')
      setSubmitting(false)
    }
  }

  if (count === 0 && !open) return null

  return (
    <>
      {/* Floating cart button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-5 py-3.5 rounded-full text-sm font-bold shadow-2xl transition-transform hover:scale-105"
          style={{ background: accent, color: '#000', boxShadow: `0 8px 32px ${accent}50` }}
        >
          <ShoppingBag className="w-4 h-4" />
          {count} · ${subtotal.toFixed(2)}
        </button>
      )}

      {/* Drawer */}
      {open && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative w-full max-w-md h-full bg-[#101318] border-l border-white/10 flex flex-col text-white">
            <div className="flex items-center justify-between px-6 py-5 border-b border-white/10">
              <h3 className="text-base font-semibold flex items-center gap-2">
                <ShoppingBag className="w-4 h-4" style={{ color: accent }} />
                Your Order
              </h3>
              <button onClick={() => setOpen(false)} className="p-1.5 rounded-full hover:bg-white/10">
                <X className="w-4 h-4 text-white/60" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
              {cart.map((item, idx) => (
                <div key={idx} className="rounded-xl bg-white/[0.05] border border-white/10 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium">{item.name}</span>
                    <span className="text-sm font-bold" style={{ color: accent }}>
                      ${(item.price * item.quantity).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 mt-3">
                    <button onClick={() => setQty(idx, item.quantity - 1)}
                      className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center">
                      <Minus className="w-3.5 h-3.5" />
                    </button>
                    <span className="text-sm font-semibold w-5 text-center">{item.quantity}</span>
                    <button onClick={() => setQty(idx, item.quantity + 1)}
                      className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center">
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>
                  <input
                    value={item.special_instructions || ''}
                    onChange={e => setNote(idx, e.target.value)}
                    placeholder="Special instructions (e.g. no onions)"
                    maxLength={200}
                    className="mt-3 w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2 text-xs placeholder:text-white/25 focus:outline-none focus:border-white/30"
                  />
                </div>
              ))}
              {cart.length === 0 && (
                <p className="text-sm text-white/40 text-center py-10">Your cart is empty.</p>
              )}

              {cart.length > 0 && (
                <div className="space-y-3 pt-2">
                  <div className="flex rounded-full bg-white/[0.06] border border-white/10 p-1 text-xs font-semibold">
                    {(['pickup', 'delivery'] as const).map(t => (
                      <button key={t} onClick={() => setOrderType(t)}
                        className="flex-1 py-2 rounded-full capitalize transition-colors"
                        style={orderType === t ? { background: accent, color: '#000' } : { color: 'rgba(255,255,255,.55)' }}>
                        {t}
                      </button>
                    ))}
                  </div>
                  <input value={name} onChange={e => setName(e.target.value)} placeholder="Your name *"
                    className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2.5 text-sm placeholder:text-white/25 focus:outline-none focus:border-white/30" />
                  <input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Phone number * (for order updates)" type="tel"
                    className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2.5 text-sm placeholder:text-white/25 focus:outline-none focus:border-white/30" />
                  <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email (optional, for receipt)" type="email"
                    className="w-full rounded-lg bg-black/30 border border-white/10 px-3 py-2.5 text-sm placeholder:text-white/25 focus:outline-none focus:border-white/30" />
                </div>
              )}
            </div>

            {cart.length > 0 && (
              <div className="px-6 py-5 border-t border-white/10 space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-white/60">Subtotal</span>
                  <span className="font-bold">${subtotal.toFixed(2)} {currencyHint}</span>
                </div>
                <p className="text-[11px] text-white/35">
                  Service fee added at checkout. Payment is secure via Stripe.
                </p>
                {error && <p className="text-xs text-red-400">{error}</p>}
                <button
                  onClick={placeOrder}
                  disabled={submitting}
                  className="w-full py-3.5 rounded-full text-sm font-bold transition-all disabled:opacity-60"
                  style={{ background: accent, color: '#000', boxShadow: `0 4px 20px ${accent}40` }}
                >
                  {submitting ? 'Opening secure checkout…' : 'Pay & Place Order'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  )
}

/** Post-checkout banner: ?order=success → confirm payment and poll until the
 * kitchen has the ticket; ?order=cancelled → nothing was placed. */
export function OrderReturnBanner({ accent }: { accent: string }) {
  const [state] = useState(() => {
    const q = new URLSearchParams(window.location.search)
    return { kind: q.get('order'), oid: q.get('oid') }
  })
  const [kitchen, setKitchen] = useState<'pending' | 'sent' | 'failed'>('pending')
  const [dismissed, setDismissed] = useState(false)
  const polls = useRef(0)

  useEffect(() => {
    if (state.kind !== 'success' || !state.oid) return
    const t = setInterval(async () => {
      polls.current += 1
      if (polls.current > 15) { clearInterval(t); return }
      try {
        const res = await fetch(`${API_BASE}/api/website/order/${state.oid}/status`)
        if (!res.ok) return
        const body = await res.json()
        if (body.pos_status === 'sent') { setKitchen('sent'); clearInterval(t) }
        if (body.pos_status === 'failed' || body.pos_status === 'skipped') {
          setKitchen('failed'); clearInterval(t)
        }
      } catch { /* transient — keep polling */ }
    }, 3000)
    return () => clearInterval(t)
  }, [state])

  if (dismissed || !state.kind || (state.kind !== 'success' && state.kind !== 'cancelled')) return null

  const success = state.kind === 'success'
  return (
    <div className="fixed top-4 left-1/2 -translate-x-1/2 z-[60] w-[calc(100%-2rem)] max-w-lg">
      <div
        className="rounded-2xl border px-5 py-4 backdrop-blur-md shadow-2xl flex items-start gap-3"
        style={success
          ? { background: 'rgba(10,30,20,.92)', borderColor: `${accent}50` }
          : { background: 'rgba(35,20,10,.92)', borderColor: 'rgba(247,185,85,.4)' }}
      >
        {success
          ? <CheckCircle2 className="w-5 h-5 mt-0.5 shrink-0" style={{ color: accent }} />
          : <XCircle className="w-5 h-5 mt-0.5 shrink-0 text-amber-400" />}
        <div className="flex-1 text-sm text-white">
          {success ? (
            <>
              <p className="font-semibold">Payment received — thank you!</p>
              <p className="text-white/60 text-xs mt-1">
                {kitchen === 'sent' && 'The kitchen has your order and is getting started. ✓'}
                {kitchen === 'pending' && 'Sending your order to the kitchen…'}
                {kitchen === 'failed' && 'Your paid order is confirmed — the restaurant is being notified.'}
              </p>
            </>
          ) : (
            <>
              <p className="font-semibold">Payment cancelled</p>
              <p className="text-white/60 text-xs mt-1">Your order was not placed and you were not charged.</p>
            </>
          )}
        </div>
        <button onClick={() => setDismissed(true)} className="p-1 rounded-full hover:bg-white/10">
          <X className="w-4 h-4 text-white/50" />
        </button>
      </div>
    </div>
  )
}
