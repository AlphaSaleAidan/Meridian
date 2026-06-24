import { useState, useEffect, useCallback } from 'react'
import { Loader2, CheckCircle2, CreditCard, ArrowRight, ExternalLink } from 'lucide-react'
import { getAuthHeaders } from '@/lib/supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

/**
 * Onboarding wizard step: set up unified payments (Stripe Connect).
 *
 * Creates the merchant's Stripe connected account and opens Stripe's hosted
 * onboarding, then polls status until Stripe reports the account can take
 * charges. Once enabled, customer payments for this merchant run through Stripe
 * regardless of which POS they use. Skippable — they can finish onboarding and
 * connect payments later from settings.
 */
interface ConnectStatus { connected: boolean; charges_enabled: boolean; details_submitted?: boolean }

export default function StripeConnectStep({ orgId, onDone }: { orgId?: string; onDone: () => void }) {
  const [status, setStatus] = useState<ConnectStatus | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [polling, setPolling] = useState(false)

  const refresh = useCallback(async (): Promise<ConnectStatus | null> => {
    if (!orgId) return null
    try {
      const res = await fetch(`${API_BASE}/api/stripe/connect/status/${orgId}`, { headers: await getAuthHeaders() })
      if (!res.ok) return null
      const s = (await res.json()) as ConnectStatus
      setStatus(s)
      return s
    } catch { return null }
  }, [orgId])

  useEffect(() => { refresh() }, [refresh])

  // While onboarding is open in the other tab, poll until charges are enabled.
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
    setBusy(true); setError(null)
    try {
      const res = await fetch(`${API_BASE}/api/stripe/connect/onboard/${orgId}`, {
        method: 'POST', headers: await getAuthHeaders(),
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
      setError(e instanceof Error ? e.message : 'Payment setup failed')
    } finally {
      setBusy(false)
    }
  }

  const ready = !!status?.charges_enabled

  return (
    <div className="space-y-5">
      <div className="text-center">
        <h1 className="text-xl font-bold text-[#F5F5F7]">Set Up Payments</h1>
        <p className="text-[13px] text-[#A1A1A8] mt-1">
          One payment system that works with your POS — customers pay by card, money goes to your account.
        </p>
      </div>

      <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-[#635bff]/15 border border-[#635bff]/30 flex items-center justify-center shrink-0">
            <CreditCard size={18} className="text-[#9d97ff]" />
          </div>
          <div>
            <p className="text-[13px] font-semibold text-[#F5F5F7]">Powered by Stripe</p>
            <p className="text-[12px] text-[#A1A1A8] mt-0.5">
              A quick, secure setup (about 5 minutes). Funds are deposited straight to your bank.
            </p>
          </div>
        </div>

        {ready ? (
          <div className="flex items-center gap-2 text-[13px] text-[#5BC8A0]">
            <CheckCircle2 size={16} /> Payments are connected and ready.
          </div>
        ) : (
          <button onClick={startOnboarding} disabled={busy || !orgId}
            className="w-full py-2.5 rounded-lg bg-[#635bff] text-white text-[13px] font-medium hover:bg-[#635bff]/90 disabled:opacity-50 flex items-center justify-center gap-2 transition-colors">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <ExternalLink size={14} />}
            {status?.connected ? 'Continue payment setup' : 'Set up payments'}
          </button>
        )}

        {polling && !ready && (
          <p className="text-[12px] text-[#A1A1A8] flex items-center gap-2">
            <Loader2 size={12} className="animate-spin" /> Waiting for Stripe to confirm… complete it in the new tab.
          </p>
        )}
        {error && <p className="text-[12px] text-[#E06B5E]">{error}</p>}
      </div>

      <div className="flex justify-end">
        <button onClick={onDone}
          className="flex items-center gap-2 px-6 py-2.5 text-[13px] font-medium text-[#0a0f0d] bg-[#00d4aa] rounded-lg hover:bg-[#00d4aa]/90 transition-colors">
          {ready ? 'Finish' : 'Skip for now'} <ArrowRight size={14} />
        </button>
      </div>
    </div>
  )
}
