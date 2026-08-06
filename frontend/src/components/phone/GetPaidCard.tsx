import { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { clsx } from 'clsx'
import { AlertCircle, Banknote, CheckCircle2, Loader2 } from 'lucide-react'
import { ConnectAccountOnboarding, ConnectComponentsProvider } from '@stripe/react-connect-js'
import type { AppearanceVariables, StripeConnectInstance } from '@stripe/connect-js'
import { getAuthHeaders } from '@/lib/supabase'
import { ensureAnimStyles } from './phone-anim-styles'

/**
 * Self-serve "Get Paid" card — Stripe Connect EMBEDDED onboarding.
 *
 * The merchant connects a bank account and starts receiving payouts for phone
 * orders WITHOUT leaving meridian.tips and without ever signing into Stripe:
 * the backend mints a connected account plus an AccountSession, and Stripe's
 * onboarding form renders inline inside this card. (Contrast with the hosted
 * AccountLink flow, which bounces the merchant to connect.stripe.com.)
 *
 * States: not connected → onboarding (embedded form) → pending (Stripe is
 * verifying; auto-polls /status) → connected.
 */
const API_BASE = (import.meta.env.VITE_API_URL || '') as string

const POLL_MS = 4000
// ~1 minute of "verifying" before we stop the background poll and hand the
// merchant an explicit retry — Stripe verification can take far longer than a
// page visit, and a forever-spinning tab is neither honest nor free.
const MAX_POLLS = 15

/** Response shape of GET /api/stripe/connect/status/{merchant_id}. */
interface ConnectStatus {
  connected: boolean
  charges_enabled: boolean
  details_submitted?: boolean
  payouts_enabled?: boolean
}

interface AccountSession {
  account_id: string
  client_secret: string
  publishable_key: string
}

type CardState = 'loading' | 'not_connected' | 'onboarding' | 'pending' | 'connected'

/** Re-theme Stripe's embedded form to the portal's dark card palette so it
 *  doesn't read as a third-party widget dropped into the page. */
const APPEARANCE: AppearanceVariables = {
  fontFamily: 'Geist Sans, Inter, system-ui, -apple-system, sans-serif',
  borderRadius: '10px',
  colorPrimary: '#1A8FD6',
  colorBackground: '#111113',
  colorText: '#F5F5F7',
  colorSecondaryText: '#A1A1A8',
  colorBorder: '#1F1F23',
  colorDanger: '#f87171',
  offsetBackgroundColor: '#0A0A0B',
  formHighlightColorBorder: '#1A8FD6',
  formAccentColor: '#17C5B0',
  buttonPrimaryColorBackground: '#1A8FD6',
  buttonPrimaryColorBorder: '#1A8FD6',
  buttonPrimaryColorText: '#FFFFFF',
  buttonSecondaryColorBackground: '#1A1A1D',
  buttonSecondaryColorBorder: '#1F1F23',
  buttonSecondaryColorText: '#F5F5F7',
}

export default function GetPaidCard({ orgId, isDemo = false, footnote }: {
  orgId: string
  isDemo?: boolean
  /** Rendered below the card body in every state except connected — lets the
   *  host page keep its own fee/billing disclosure next to the CTA. */
  footnote?: ReactNode
}) {
  const [state, setState] = useState<CardState>('loading')
  const [resumable, setResumable] = useState(false)
  const [busy, setBusy] = useState(false)
  const [stalled, setStalled] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [connectInstance, setConnectInstance] = useState<StripeConnectInstance | null>(null)
  // The client_secret from the session we created to get the publishable key.
  // Connect.js calls fetchClientSecret immediately on init; handing back the
  // one we already hold avoids minting a second AccountSession per click.
  const pendingSecret = useRef<string | null>(null)

  useEffect(() => { ensureAnimStyles() }, [])

  const fetchStatus = useCallback(async (): Promise<ConnectStatus | null> => {
    if (!orgId) return null
    try {
      const res = await fetch(`${API_BASE}/api/stripe/connect/status/${orgId}`, {
        headers: await getAuthHeaders(),
      })
      if (!res.ok) return null
      return (await res.json()) as ConnectStatus
    } catch {
      return null
    }
  }, [orgId])

  // Initial status. An account that exists but hasn't finished onboarding
  // resolves to "verifying" once details were submitted, and to a resumable
  // CTA before that — reloading mid-flow must not look like a fresh start.
  useEffect(() => {
    let alive = true
    if (isDemo || !orgId) { setState('not_connected'); return }
    void (async () => {
      const s = await fetchStatus()
      if (!alive) return
      if (s?.charges_enabled) { setState('connected'); return }
      setResumable(Boolean(s?.connected))
      setState(s?.connected && s.details_submitted ? 'pending' : 'not_connected')
    })()
    return () => { alive = false }
  }, [orgId, isDemo, fetchStatus])

  // While Stripe verifies, poll until charges are enabled.
  useEffect(() => {
    if (state !== 'pending' || isDemo) return
    let alive = true
    let tries = 0
    const id = setInterval(() => {
      void (async () => {
        tries += 1
        const s = await fetchStatus()
        if (!alive) return
        if (s?.charges_enabled) { setState('connected'); clearInterval(id) }
        else if (tries >= MAX_POLLS) { setStalled(true); clearInterval(id) }
      })()
    }, POLL_MS)
    return () => { alive = false; clearInterval(id) }
  }, [state, isDemo, fetchStatus])

  const createSession = useCallback(async (): Promise<AccountSession> => {
    const res = await fetch(`${API_BASE}/api/stripe/connect/account-session/${orgId}`, {
      method: 'POST',
      headers: { ...(await getAuthHeaders()), 'Content-Type': 'application/json' },
    })
    if (!res.ok) {
      let detail = `Could not start payment setup (${res.status})`
      try { detail = (await res.json()).detail || detail } catch { /* noop */ }
      throw new Error(detail)
    }
    return (await res.json()) as AccountSession
  }, [orgId])

  async function startOnboarding() {
    if (isDemo || busy || !orgId) return
    setBusy(true)
    setError(null)
    setStalled(false)
    try {
      const session = await createSession()
      pendingSecret.current = session.client_secret
      // Imported on demand: this module injects Stripe's Connect.js script as
      // an import side effect, and merchants who never open this card
      // shouldn't pay to load it.
      const { loadConnectAndInitialize } = await import('@stripe/connect-js')
      const instance = loadConnectAndInitialize({
        publishableKey: session.publishable_key,
        fetchClientSecret: async () => {
          const cached = pendingSecret.current
          if (cached) { pendingSecret.current = null; return cached }
          return (await createSession()).client_secret
        },
        appearance: { variables: APPEARANCE },
      })
      setConnectInstance(instance)
      setState('onboarding')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not start payment setup')
    } finally {
      setBusy(false)
    }
  }

  // Stripe's embedded form is done with the merchant (submitted, or backed
  // out). Charges are rarely live the same instant, so confirm once and fall
  // through to the polling "verifying" state.
  const handleExit = useCallback(() => {
    setConnectInstance(null)
    setStalled(false)
    setState('pending')
    void (async () => {
      const s = await fetchStatus()
      if (s?.charges_enabled) setState('connected')
    })()
  }, [fetchStatus])

  async function recheck() {
    setStalled(false)
    setBusy(true)
    const s = await fetchStatus()
    setBusy(false)
    if (s?.charges_enabled) setState('connected')
    else setStalled(true)
  }

  /* ── Connected ── */
  if (state === 'connected') {
    return (
      <div className="card p-5 border-[#17C5B0]/20">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
            <CheckCircle2 size={20} className="text-[#17C5B0]" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-base font-bold text-[#F5F5F7]">You&apos;re all set. Payouts go to your bank daily.</h2>
            <p className="text-xs text-[#A1A1A8] mt-1.5 leading-relaxed">
              Customers pay the full order; your daily payout is the order total minus Meridian&apos;s
              per-order fee — nothing to invoice, nothing to pay us.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const onboarding = state === 'onboarding' && connectInstance !== null
  const verifying = state === 'pending'

  return (
    <div className={clsx('card p-5', onboarding ? 'border-[#1A8FD6]/25' : 'border-[#1A8FD6]/15')}>
      <div className="flex items-start gap-4">
        <div className="w-11 h-11 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
          {verifying
            ? <Loader2 size={20} className="text-[#1A8FD6] animate-spin" />
            : <Banknote size={20} className="text-[#1A8FD6]" />}
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-base font-bold text-[#F5F5F7]">
            {verifying
              ? 'Almost there — we’re verifying your details'
              : onboarding
                ? 'Connect your bank'
                : 'Get paid for phone orders'}
          </h2>
          <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
            {verifying
              ? 'Stripe is reviewing what you submitted. This usually takes a minute — you can leave this page, payouts switch on automatically.'
              : onboarding
                ? 'Your details go straight to Stripe, our payments processor. Meridian never sees your bank credentials.'
                : 'Connect your bank to receive payouts — no Stripe account needed.'}
          </p>
        </div>
        {state === 'not_connected' && (
          <button
            onClick={startOnboarding}
            disabled={busy || isDemo || !orgId}
            className={clsx(
              'flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              isDemo
                ? 'bg-[#1A8FD6]/30 text-[#1A8FD6]/60 cursor-not-allowed'
                : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-60',
            )}
          >
            {busy && <Loader2 size={14} className="animate-spin" />}
            {busy ? 'Starting…' : resumable ? 'Finish connecting' : 'Connect payments'}
          </button>
        )}
        {state === 'loading' && (
          <span className="flex-shrink-0 w-3.5 h-3.5 mt-2 border-2 border-[#1F1F23] border-t-[#1A8FD6] rounded-full animate-spin" />
        )}
      </div>

      {onboarding && (
        <div className="embed-reveal mt-4 pt-4 border-t border-[#1F1F23]">
          <ConnectComponentsProvider connectInstance={connectInstance}>
            <ConnectAccountOnboarding
              onExit={handleExit}
              onLoadError={({ error: e }) => setError(e.message || 'Stripe could not load the onboarding form.')}
            />
          </ConnectComponentsProvider>
        </div>
      )}

      {stalled && (
        <div className="mt-4 bg-[#111113] border border-[#1F1F23] rounded-lg px-4 py-3 flex items-center gap-3">
          <p className="text-[11px] text-[#A1A1A8] leading-relaxed flex-1">
            Stripe is still reviewing. You&apos;ll be able to take payments as soon as it clears.
          </p>
          <button
            onClick={recheck}
            disabled={busy}
            className="flex-shrink-0 px-3 py-1.5 rounded-lg text-[11px] font-medium text-[#F5F5F7] bg-[#1A1A1D] border border-[#1F1F23] hover:border-[#1A8FD6]/30 transition-colors disabled:opacity-60"
          >
            {busy ? 'Checking…' : 'Check again'}
          </button>
        </div>
      )}

      {error && (
        <div className="mt-4 bg-red-400/5 border border-red-400/20 rounded-lg px-4 py-3 flex items-start gap-2">
          <AlertCircle size={12} className="text-red-400 mt-0.5 flex-shrink-0" />
          <p className="text-[11px] text-red-400 leading-relaxed">{error}</p>
        </div>
      )}

      {footnote}
    </div>
  )
}
