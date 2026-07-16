import { useEffect, useRef, useState } from 'react'
import { clsx } from 'clsx'
import {
  PhoneForwarded, CheckCircle2, Copy, Loader2, AlertTriangle, Info,
  ArrowLeft, ArrowRight, RefreshCw, Radio,
} from 'lucide-react'
import { phoneService, isValidE164, normalizeToE164, type ActivationStep } from '@/lib/phone-service'

/**
 * Carrier call-forwarding setup wizard with live verification.
 *
 * Step 1 — pick the carrier of the merchant's STORE line.
 * Step 2 — exact dial sequences for that carrier, BOTH modes:
 *          full/unconditional forward vs conditional (busy + no-answer).
 *          Conditional is REQUIRED when the human-transfer number is the same
 *          store line (a full forward would loop transferred calls straight
 *          back to the AI — see the transfer-loop guard in phone_dashboard /
 *          vapi_webhook).
 * Step 3 — "Verify forwarding": the backend places a short test call to the
 *          store line; if the forward works it lands on the Meridian agent
 *          and the verification flips to verified (polled here).
 *
 * Every step fires a fire-and-forget activation-funnel event so stalls are
 * visible in phone_activation_events.
 */

// ── Carrier dial-code data ──────────────────────────────────────────
// NOTE: these are the published GSM-standard / carrier codes as of 2026-07.
// RE-VERIFY WITH EACH CARRIER BEFORE PUBLISHING — carriers occasionally
// change codes or move forwarding behind their account app.
//
// GSM carriers (Rogers/Bell/Telus/Fido/Koodo/Freedom/AT&T/T-Mobile) use the
// GSM supplementary-service codes: **21*<number># (unconditional),
// **67*<number># (busy), **61*<number># (no answer); ##21# / ##67# / ##61#
// deactivate. Verizon, Videotron, and most landlines use the North-American
// vertical service codes: *72<number> / *73 (unconditional), with carrier-
// specific conditional codes.

export interface CarrierCode {
  label: string
  /** Dial string with the agent number substituted in. */
  dial: (agent: string) => string
}

export interface CarrierModeCodes {
  activate: CarrierCode[]
  deactivate: CarrierCode[]
}

export interface CarrierDef {
  id: string
  name: string
  region: 'CA' | 'US' | 'OTHER'
  unconditional: CarrierModeCodes
  conditional: CarrierModeCodes
  note?: string
  /** Per-carrier looping walkthrough video — hidden when null. */
  videoUrl: string | null
}

const gsmCodes = (): Pick<CarrierDef, 'unconditional' | 'conditional'> => ({
  unconditional: {
    activate: [{ label: 'Forward all calls', dial: a => `**21*${a}#` }],
    deactivate: [{ label: 'Cancel forwarding', dial: () => '##21#' }],
  },
  conditional: {
    activate: [
      { label: 'Forward when busy', dial: a => `**67*${a}#` },
      { label: 'Forward on no answer', dial: a => `**61*${a}#` },
    ],
    deactivate: [
      { label: 'Cancel busy forwarding', dial: () => '##67#' },
      { label: 'Cancel no-answer forwarding', dial: () => '##61#' },
    ],
  },
})

const starCodes = (): Pick<CarrierDef, 'unconditional' | 'conditional'> => ({
  unconditional: {
    activate: [{ label: 'Forward all calls', dial: a => `*72${a}` }],
    deactivate: [{ label: 'Cancel forwarding', dial: () => '*73' }],
  },
  conditional: {
    activate: [
      { label: 'Forward when busy', dial: a => `*90${a}` },
      { label: 'Forward on no answer', dial: a => `*92${a}` },
    ],
    deactivate: [
      { label: 'Cancel busy forwarding', dial: () => '*91' },
      { label: 'Cancel no-answer forwarding', dial: () => '*93' },
    ],
  },
})

export const CARRIERS: CarrierDef[] = [
  // Canada first
  { id: 'rogers', name: 'Rogers', region: 'CA', ...gsmCodes(), videoUrl: null },
  { id: 'bell', name: 'Bell', region: 'CA', ...gsmCodes(), videoUrl: null },
  { id: 'telus', name: 'Telus', region: 'CA', ...gsmCodes(), videoUrl: null },
  { id: 'freedom', name: 'Freedom', region: 'CA', ...gsmCodes(), videoUrl: null },
  { id: 'fido', name: 'Fido', region: 'CA', ...gsmCodes(), videoUrl: null },
  { id: 'koodo', name: 'Koodo', region: 'CA', ...gsmCodes(), videoUrl: null },
  {
    id: 'videotron', name: 'Vidéotron', region: 'CA', ...starCodes(), videoUrl: null,
    note: 'Vidéotron uses the *72/*73 star codes rather than the GSM ** codes.',
  },
  // US
  { id: 'att', name: 'AT&T', region: 'US', ...gsmCodes(), videoUrl: null },
  {
    id: 'verizon', name: 'Verizon', region: 'US',
    unconditional: {
      activate: [{ label: 'Forward all calls', dial: a => `*72${a}` }],
      deactivate: [{ label: 'Cancel forwarding', dial: () => '*73' }],
    },
    conditional: {
      activate: [{ label: 'Forward when busy or unanswered', dial: a => `*71${a}` }],
      deactivate: [{ label: 'Cancel conditional forwarding', dial: () => '*73' }],
    },
    note: 'On Verizon, *71 covers both busy and no-answer in one code.',
    videoUrl: null,
  },
  { id: 'tmobile', name: 'T-Mobile', region: 'US', ...gsmCodes(), videoUrl: null },
  // Fallback
  {
    id: 'other', name: 'Other / landline', region: 'OTHER', ...starCodes(), videoUrl: null,
    note: 'Most landlines and smaller carriers use *72/*73. If these don\'t work, search "call forwarding" in your carrier\'s help — some only support it via their app.',
  },
]

type WizStep = 1 | 2 | 3
type VerifyState = 'idle' | 'starting' | 'pending' | 'verified' | 'failed'

interface Props {
  /** The Meridian agent DID calls get forwarded TO. */
  agentNumber: string
  merchantId: string
  isDemo?: boolean
  /** Preselect the forwarding mode tab ('conditional' for overflow setups). */
  defaultMode?: 'unconditional' | 'conditional'
  className?: string
}

const VERIFY_TIMEOUT_MS = 60_000
const POLL_INTERVAL_MS = 3_000

export default function ForwardingWizard({ agentNumber, merchantId, isDemo = false, defaultMode = 'unconditional', className }: Props) {
  const [step, setStep] = useState<WizStep>(1)
  const [carrierId, setCarrierId] = useState<string | null>(null)
  const [modeTab, setModeTab] = useState<'unconditional' | 'conditional'>(defaultMode)
  const [businessLine, setBusinessLine] = useState('')
  const [verifyState, setVerifyState] = useState<VerifyState>('idle')
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const timeoutTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const carrier = CARRIERS.find(c => c.id === carrierId) || null
  const agentDigits = agentNumber.replace(/[^+\d]/g, '')

  const fire = (s: ActivationStep, meta?: Record<string, unknown>) => {
    if (!isDemo) phoneService.activationEvent(merchantId, s, meta)
  }

  // codes_viewed once per carrier when step 2 renders.
  const codesViewedFor = useRef<string | null>(null)
  useEffect(() => {
    if (step === 2 && carrier && codesViewedFor.current !== carrier.id) {
      codesViewedFor.current = carrier.id
      fire('codes_viewed', { carrier: carrier.id })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, carrier?.id])

  const stopPolling = () => {
    if (pollTimer.current) { clearInterval(pollTimer.current); pollTimer.current = null }
    if (timeoutTimer.current) { clearTimeout(timeoutTimer.current); timeoutTimer.current = null }
  }
  useEffect(() => stopPolling, [])

  const startVerify = async () => {
    setVerifyError(null)
    const line = businessLine.trim()
    if (!isValidE164(normalizeToE164(line))) {
      setVerifyError('Enter your store\'s full phone number, e.g. +1 416 555 0123.')
      return
    }
    fire('verify_started', { carrier: carrierId })
    if (isDemo) {
      // Demo: simulate a successful verification, no backend writes.
      setVerifyState('pending')
      timeoutTimer.current = setTimeout(() => setVerifyState('verified'), 2500)
      return
    }
    setVerifyState('starting')
    try {
      await phoneService.verifyForwardingStart(merchantId, normalizeToE164(line))
    } catch (e) {
      setVerifyState('failed')
      setVerifyError(e instanceof Error ? e.message : 'Could not start verification')
      fire('verify_failed', { carrier: carrierId, phase: 'start' })
      return
    }
    setVerifyState('pending')
    const startedAt = Date.now()
    pollTimer.current = setInterval(async () => {
      try {
        const s = await phoneService.verifyForwardingStatus(merchantId)
        if (s.status === 'verified') {
          stopPolling()
          setVerifyState('verified')
          fire('verified', { carrier: carrierId })
        } else if (s.status === 'failed' || Date.now() - startedAt > VERIFY_TIMEOUT_MS) {
          stopPolling()
          setVerifyState('failed')
          fire('verify_failed', { carrier: carrierId, phase: 'timeout' })
        }
      } catch { /* keep polling until timeout */ }
    }, POLL_INTERVAL_MS)
    timeoutTimer.current = setTimeout(() => {
      if (pollTimer.current) {
        stopPolling()
        setVerifyState('failed')
        fire('verify_failed', { carrier: carrierId, phase: 'timeout' })
      }
    }, VERIFY_TIMEOUT_MS + POLL_INTERVAL_MS)
  }

  const CodeRow = ({ code }: { code: CarrierCode }) => {
    const [copied, setCopied] = useState(false)
    const dial = code.dial(agentDigits || '<your Meridian number>')
    return (
      <div className="flex items-center gap-3 bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2">
        <code className="text-sm font-mono font-semibold text-[#17C5B0] flex-shrink-0 break-all">{dial}</code>
        <p className="text-[10px] text-[#A1A1A8] flex-1 text-right">{code.label}</p>
        <button
          onClick={() => { navigator.clipboard?.writeText(dial); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
          className="p-1.5 rounded-lg bg-[#1F1F23] hover:bg-[#2A2A30] transition-colors flex-shrink-0"
          aria-label={`Copy ${code.label} code`}
        >
          {copied ? <CheckCircle2 size={13} className="text-[#17C5B0]" /> : <Copy size={13} className="text-[#A1A1A8]" />}
        </button>
      </div>
    )
  }

  return (
    <div className={clsx('space-y-4', className)}>
      {/* Mini stepper */}
      <div className="flex items-center gap-1">
        {(['Carrier', 'Dial codes', 'Verify'] as const).map((label, i) => {
          const idx = (i + 1) as WizStep
          const active = idx === step
          const done = idx < step || (idx === 3 && verifyState === 'verified')
          return (
            <div key={label} className="flex-1 flex flex-col gap-1">
              <div className={clsx('h-0.5 rounded-full transition-all', done || active ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]')} />
              <span className={clsx('text-[9px] font-medium text-center', active ? 'text-[#F5F5F7]' : done ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/40')}>{label}</span>
            </div>
          )
        })}
      </div>

      {/* ── Step 1: carrier select ── */}
      {step === 1 && (
        <div className="space-y-3">
          <p className="text-[11px] text-[#A1A1A8]">Who provides your <span className="text-[#F5F5F7] font-medium">store line</span> (the number customers already call)?</p>
          {(['CA', 'US', 'OTHER'] as const).map(region => (
            <div key={region}>
              <p className="text-[9px] font-semibold uppercase tracking-wider text-[#A1A1A8]/60 mb-1.5">
                {region === 'CA' ? 'Canada' : region === 'US' ? 'United States' : 'Everything else'}
              </p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {CARRIERS.filter(c => c.region === region).map(c => (
                  <button
                    key={c.id}
                    onClick={() => { setCarrierId(c.id); fire('carrier_selected', { carrier: c.id }) }}
                    className={clsx('px-3 py-2 rounded-lg border text-xs font-medium text-left transition-all',
                      carrierId === c.id ? 'border-[#17C5B0]/40 bg-[#17C5B0]/5 text-[#F5F5F7]' : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#2A2A30]')}
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            </div>
          ))}
          <div className="flex justify-end">
            <button
              onClick={() => setStep(2)}
              disabled={!carrier}
              className="flex items-center gap-1.5 px-4 py-2 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-40 transition-colors"
            >
              Show my dial codes <ArrowRight size={12} />
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: dial codes, both modes ── */}
      {step === 2 && carrier && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <PhoneForwarded size={14} className="text-[#1A8FD6]" />
            <p className="text-xs font-semibold text-[#F5F5F7]">{carrier.name} — dial these from your store phone</p>
          </div>

          {/* Mode tabs */}
          <div className="flex gap-2">
            {([
              { id: 'unconditional' as const, label: 'Forward everything' },
              { id: 'conditional' as const, label: 'Busy / no answer only' },
            ]).map(t => (
              <button key={t.id} onClick={() => setModeTab(t.id)}
                className={clsx('px-3 py-1.5 rounded-lg border text-[11px] font-medium transition-all',
                  modeTab === t.id ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5 text-[#17C5B0]' : 'border-[#1F1F23] text-[#A1A1A8]')}>
                {t.label}
              </button>
            ))}
          </div>

          <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
            {modeTab === 'unconditional'
              ? 'Every call to your store line goes straight to the AI agent. Your store phone won\'t ring.'
              : 'Your store phone rings first; the AI agent only picks up when the line is busy or nobody answers.'}
          </p>

          <div className="space-y-1.5">
            {carrier[modeTab].activate.map(code => <CodeRow key={code.label} code={code} />)}
          </div>
          <p className="text-[9px] font-semibold uppercase tracking-wider text-[#A1A1A8]/60 pt-1">To turn it back off</p>
          <div className="space-y-1.5">
            {carrier[modeTab].deactivate.map(code => <CodeRow key={code.label} code={code} />)}
          </div>

          {/* Loop-safety callout — ties to the transfer-number validation. */}
          <div className="bg-amber-400/5 border border-amber-400/15 rounded-lg p-3 flex items-start gap-2">
            <AlertTriangle size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
            <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
              <span className="text-amber-400 font-medium">If your "transfer to a human" number is this same store line, you MUST use busy / no-answer forwarding.</span>{' '}
              With "forward everything" on, a transferred call would be forwarded straight back to the AI in a loop and never reach a person.
            </p>
          </div>

          {carrier.note && (
            <div className="bg-[#1A8FD6]/5 border border-[#1A8FD6]/15 rounded-lg p-3 flex items-start gap-2">
              <Info size={12} className="text-[#1A8FD6] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8] leading-relaxed">{carrier.note}</p>
            </div>
          )}

          {/* Per-carrier walkthrough video slot — hidden until a videoUrl ships. */}
          {carrier.videoUrl && (
            <video src={carrier.videoUrl} className="w-full rounded-lg border border-[#1F1F23]" autoPlay loop muted playsInline />
          )}

          <div className="flex justify-between items-center pt-1">
            <button onClick={() => setStep(1)} className="flex items-center gap-1.5 px-3 py-2 text-xs text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={12} /> Back
            </button>
            <button onClick={() => setStep(3)} className="flex items-center gap-1.5 px-4 py-2 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
              I dialed it — verify <ArrowRight size={12} />
            </button>
          </div>
        </div>
      )}

      {/* ── Step 3: live verification ── */}
      {step === 3 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Radio size={14} className="text-[#17C5B0]" />
            <p className="text-xs font-semibold text-[#F5F5F7]">Verify your forwarding is live</p>
          </div>
          <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
            We place a short test call to your store line. If forwarding is set up, it reaches your
            AI agent and we confirm automatically — nothing to answer on your end.
          </p>

          <div>
            <label className="text-xs text-[#A1A1A8] block mb-1">Your store line (the number you forwarded)</label>
            <input
              className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50"
              placeholder="+1 (416) 555-0123"
              inputMode="tel"
              autoComplete="off"
              value={businessLine}
              onChange={e => { setBusinessLine(e.target.value); setVerifyError(null) }}
              disabled={verifyState === 'pending' || verifyState === 'starting'}
            />
          </div>

          {verifyState === 'verified' ? (
            <div className="flex items-start gap-2 px-3 py-3 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/20">
              <CheckCircle2 size={16} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-xs font-semibold text-[#17C5B0]">Forwarding verified — you're all set.</p>
                <p className="text-[10px] text-[#A1A1A8] mt-0.5">Calls to your store line now reach your AI agent.</p>
              </div>
            </div>
          ) : verifyState === 'pending' || verifyState === 'starting' ? (
            <div className="flex items-center gap-2 px-3 py-3 rounded-lg bg-[#1A8FD6]/5 border border-[#1A8FD6]/15">
              <Loader2 size={14} className="text-[#1A8FD6] animate-spin flex-shrink-0" />
              <p className="text-[11px] text-[#A1A1A8]">Calling your store line and listening for the forward… up to 60 seconds.</p>
            </div>
          ) : (
            <>
              {verifyState === 'failed' && (
                <div className="flex items-start gap-2 px-3 py-3 rounded-lg bg-red-500/5 border border-red-500/20">
                  <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                  <div className="space-y-0.5">
                    <p className="text-[11px] text-red-200 font-medium">We couldn't confirm the forward yet.</p>
                    <p className="text-[10px] text-red-200/70 leading-relaxed">
                      {verifyError || 'The test call didn\'t reach your AI agent. Double-check you dialed the code from the store phone itself, wait a minute for the carrier to apply it, then retry. Busy/no-answer forwarding only kicks in if the line is busy or unanswered — let it ring.'}
                    </p>
                  </div>
                </div>
              )}
              {verifyError && verifyState !== 'failed' && (
                <p className="text-[10px] text-red-400/80">{verifyError}</p>
              )}
              <button
                onClick={startVerify}
                className="w-full flex items-center justify-center gap-1.5 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-colors"
              >
                {verifyState === 'failed' ? <><RefreshCw size={12} /> Retry verification</> : <><Radio size={12} /> Verify forwarding</>}
              </button>
            </>
          )}

          <div className="flex justify-start">
            <button onClick={() => { stopPolling(); setVerifyState('idle'); setStep(2) }} className="flex items-center gap-1.5 px-3 py-2 text-xs text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={12} /> Back to dial codes
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
