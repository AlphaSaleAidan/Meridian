/**
 * "Send payment link" — one booking, one tap, one text.
 *
 * THE MOMENT THIS SERVES is the job ending: the hatch closes, the chair
 * spins round, and the alternative is "I'll Venmo you?" said across a
 * driveway or a counter. One tap texts the customer a real checkout for the
 * booked price, on the same mediated rail phone orders settle through —
 * Stripe destination charge to the merchant's connected account, Meridian's
 * fee taken in transit.
 *
 * When the text cannot go (no number on file, carrier rejection — every US
 * merchant until 10DLC clears) the link still exists, so the fallback is a
 * copy button rather than a dead end: the operator pastes it into whatever
 * channel the customer actually answers.
 *
 * Self-contained on purpose: two screens render it (the route view and the
 * day list) and neither should carry per-booking send state of its own.
 */
import { useState } from 'react'
import { Copy, CreditCard } from 'lucide-react'
import { bookingsApi } from '@/lib/bookings-api'

export default function SendPaymentLink({ bookingId }: { bookingId: string }) {
  const [state, setState] = useState<{ label: string; url?: string; ok?: boolean } | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)

  const send = async () => {
    setBusy(true)
    try {
      const res = await bookingsApi.sendPaymentLink(bookingId)
      setState(res.sent
        ? { label: 'Payment link texted', ok: true }
        : res.url
          ? { label: res.reason === 'no_phone'
                ? 'No number on file — copy the link instead'
                : 'Could not text — copy the link instead',
              url: res.url }
          : { label: res.reason === 'no_price'
                ? 'No price on this service'
                : 'Could not create a link' })
    } catch {
      setState({ label: 'Could not create a link' })
    } finally {
      setBusy(false)
    }
  }

  const copy = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* clipboard denied — the outcome text stays visible */ }
  }

  if (state) {
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs ${
        state.ok ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'
      }`}>
        {state.label}
        {state.url && (
          <button
            onClick={() => copy(state.url!)}
            className="inline-flex items-center gap-1 rounded-md border border-[#1A8FD6]/40 bg-[#1A8FD6]/10 px-2 py-1 text-xs font-medium text-[#1A8FD6] transition-colors hover:bg-[#1A8FD6]/20"
          >
            <Copy className="h-3 w-3" />
            {copied ? 'Copied' : 'Copy link'}
          </button>
        )}
      </span>
    )
  }

  return (
    <button
      disabled={busy}
      onClick={send}
      className="inline-flex items-center gap-1.5 rounded-md border border-[#1F1F23] px-2 py-1 text-xs text-[#A1A1A8] transition-colors hover:border-[#17C5B0]/40 hover:text-[#17C5B0] disabled:opacity-50"
    >
      <CreditCard className="h-3.5 w-3.5" />
      {busy ? 'Creating link…' : 'Send payment link'}
    </button>
  )
}
