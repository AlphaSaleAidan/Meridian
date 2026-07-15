import { useCallback, useEffect, useState } from 'react'
import { CheckCircle2, CreditCard, ExternalLink, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { getAuthHeaders } from '@/lib/supabase'
import { useOrgId } from '@/hooks/useOrg'

const API_BASE = import.meta.env.VITE_API_URL || ''

/**
 * Persistent "get paid" surface on the merchant dashboard.
 *
 * The onboarding wizard's Stripe Connect step is skippable, which used to
 * leave skippers with NO way to connect a bank account later — and without
 * it, mobile-order and phone-order payments fall back to platform-direct
 * charges (money lands in Meridian's account, manual settlement). This card
 * closes that gap: it shows live Connect status and drives Stripe's hosted
 * onboarding, polling until charges are enabled.
 *
 * States: not connected (prominent CTA) → incomplete (finish setup) →
 * connected (slim confirmation line).
 */
interface ConnectStatus {
  connected: boolean
  charges_enabled: boolean
  details_submitted?: boolean
  payouts_enabled?: boolean
}

export default function PaymentsSetupCard() {
  const orgId = useOrgId()
  const [status, setStatus] = useState<ConnectStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [polling, setPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async (): Promise<ConnectStatus | null> => {
    if (!orgId) return null
    try {
      const res = await fetch(`${API_BASE}/api/stripe/connect/status/${orgId}`, {
        headers: await getAuthHeaders(),
      })
      if (!res.ok) return null
      const s = (await res.json()) as ConnectStatus
      setStatus(s)
      return s
    } catch {
      return null
    }
  }, [orgId])

  useEffect(() => { refresh() }, [refresh])

  // While Stripe onboarding is open in the other tab, poll until enabled.
  useEffect(() => {
    if (!polling) return
    const id = setInterval(async () => {
      const s = await refresh()
      if (s?.charges_enabled) { setPolling(false); clearInterval(id) }
    }, 4000)
    return () => clearInterval(id)
  }, [polling, refresh])

  async function startOnboarding() {
    if (!orgId) return
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/stripe/connect/onboard/${orgId}`, {
        method: 'POST',
        headers: await getAuthHeaders(),
      })
      if (!res.ok) {
        let detail = `Could not start payment setup (${res.status})`
        try { detail = (await res.json()).detail || detail } catch { /* noop */ }
        throw new Error(detail)
      }
      const { onboarding_url } = await res.json()
      window.open(onboarding_url, '_blank', 'noopener')
      setPolling(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start payment setup')
    } finally {
      setBusy(false)
    }
  }

  // Status unknown (loading/API error): render nothing rather than nag.
  if (!status) return null

  // Fully enabled → slim confirmation, no CTA noise.
  if (status.charges_enabled) {
    return (
      <div className="flex items-center gap-2.5 rounded-2xl bg-pm-teal/5 border border-pm-teal/20 px-4 py-3">
        <CheckCircle2 size={16} className="text-pm-teal flex-shrink-0" />
        <p className="text-sm text-pm-text">
          <span className="font-semibold">Payments connected</span>
          <span className="text-pm-muted"> — customer payments deposit to your bank daily.</span>
        </p>
      </div>
    )
  }

  const incomplete = status.connected // account exists, onboarding unfinished
  return (
    <div className={clsx(
      'rounded-2xl bg-pm-surface border p-5 sm:p-6',
      incomplete ? 'border-pm-amber-orange/30' : 'border-pm-border',
    )}>
      <div className="flex flex-col sm:flex-row sm:items-center gap-4">
        <div className={clsx(
          'w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0',
          incomplete ? 'bg-pm-amber-orange/10' : 'bg-pm-teal/10',
        )}>
          <CreditCard size={20} className={incomplete ? 'text-pm-amber-orange' : 'text-pm-teal'} />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-pm-text">
            {incomplete ? 'Finish connecting your bank account' : 'Connect a bank account to get paid'}
          </h3>
          <p className="text-sm text-pm-muted mt-0.5">
            {incomplete
              ? 'Stripe needs a few more details before customer payments can deposit to your account.'
              : 'Online and phone orders are paid by card. Connect once and money from every order deposits to your bank daily.'}
          </p>
          {error && <p className="text-xs text-pm-amber-orange mt-1.5">{error}</p>}
        </div>
        <button
          onClick={startOnboarding}
          disabled={busy}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-pm-teal text-black text-sm font-semibold hover:opacity-90 transition-opacity disabled:opacity-60 flex-shrink-0"
        >
          {busy || polling ? <Loader2 size={15} className="animate-spin" /> : <ExternalLink size={15} />}
          {polling ? 'Waiting for Stripe…' : incomplete ? 'Finish setup' : 'Connect bank account'}
        </button>
      </div>
    </div>
  )
}
