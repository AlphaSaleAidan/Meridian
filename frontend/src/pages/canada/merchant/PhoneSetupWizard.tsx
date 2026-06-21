import { useState, useMemo, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  PhoneForwarded, Clock, Hash, Server, ArrowRight, ArrowLeft,
  CheckCircle2, Loader2, Copy, Phone, Info, AlertCircle, Sparkles,
} from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { phoneService, type PhoneConfig } from '@/lib/phone-service'

/**
 * "Connect your phone" wizard — a segment under the Phone Calls pillar.
 *
 * Walks a merchant through the lowest-friction way to point their existing
 * business line at Meridian so incoming calls are intercepted (AI takes the
 * order or transfers to a human). Renders inside MerchantLayout, so it appears
 * on BOTH the public demo (/canada/demo) and the authenticated portal
 * (/canada/merchant) — same as every other pillar segment.
 *
 * Demo-safe: in demo mode nothing is written to the backend (local state only).
 * Authenticated: the human-transfer number persists via
 * phoneService.saveConfig({ transfer_number }) → POST /api/phone/config.
 */

// Live demo line callers can dial to hear the agent (from the deck).
const DEMO_TEST_LINE = '+1 782-358-5534'

type ConnectMode = 'forward_all' | 'overflow' | 'port' | 'sip'

interface ConnectOption {
  mode: ConnectMode
  label: string
  tagline: string
  recommended?: boolean
  icon: typeof PhoneForwarded
}

const OPTIONS: ConnectOption[] = [
  {
    mode: 'forward_all',
    label: 'Full call-forward',
    tagline: 'Keep your number. Forward ALL calls to Meridian. Zero porting, reversible instantly.',
    recommended: true,
    icon: PhoneForwarded,
  },
  {
    mode: 'overflow',
    label: 'Overflow / after-hours',
    tagline: 'Forward only when you’re busy, no-answer, or closed. Your phone still rings first.',
    icon: Clock,
  },
  {
    mode: 'port',
    label: 'Port or new Meridian number',
    tagline: 'Route natively on a Meridian number — port your existing one or get a fresh line.',
    icon: Hash,
  },
  {
    mode: 'sip',
    label: 'SIP / PBX',
    tagline: 'Add Meridian as a SIP endpoint in your phone system (RingCentral, etc.).',
    icon: Server,
  },
]

type Step = 'choose' | 'doit' | 'transfer' | 'test'

const STEPS: { key: Step; label: string }[] = [
  { key: 'choose', label: 'Connect' },
  { key: 'doit', label: 'Set it up' },
  { key: 'transfer', label: 'Transfer #' },
  { key: 'test', label: 'Test' },
]

// Carrier star-codes vary — these are the most common North-American defaults.
const STAR_CODES = [
  { label: 'Forward all calls', on: '*72', note: 'dial *72 then the Meridian number' },
  { label: 'Cancel forwarding', on: '*73', note: 'turns forwarding back off' },
  { label: 'Forward when busy', on: '*90', note: 'for the Overflow option' },
  { label: 'Forward on no-answer', on: '*92', note: 'for the Overflow option' },
]

// Loose North-American phone validation: 10–15 digits after stripping symbols.
function isValidPhone(v: string): boolean {
  const digits = v.replace(/[^\d]/g, '')
  return digits.length >= 10 && digits.length <= 15
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => { navigator.clipboard?.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500) }}
      className="p-1.5 rounded-lg bg-[#1F1F23] hover:bg-[#2A2A30] transition-colors flex-shrink-0"
      aria-label="Copy"
    >
      {copied ? <CheckCircle2 size={14} className="text-[#17C5B0]" /> : <Copy size={14} className="text-[#A1A1A8]" />}
    </button>
  )
}

export default function PhoneSetupWizard() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()

  const [step, setStep] = useState<Step>('choose')
  const [mode, setMode] = useState<ConnectMode>('forward_all')
  const [phoneConfig, setPhoneConfig] = useState<PhoneConfig | null>(null)
  const [transferNumber, setTransferNumber] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load existing config (authed only). Demo never hits the backend.
  useEffect(() => {
    if (!orgId || isDemo) return
    phoneService.getConfig(orgId).then(cfg => {
      setPhoneConfig(cfg)
      if (cfg.transfer_number) setTransferNumber(cfg.transfer_number)
    })
  }, [orgId, isDemo])

  // The merchant's provisioned Meridian number (forward target). Placeholder in
  // demo / before provisioning — onboarding assigns the real number.
  const meridianNumber = useMemo(() => {
    if (!isDemo && phoneConfig?.phone_number) return phoneConfig.phone_number
    return 'your Meridian number from onboarding'
  }, [isDemo, phoneConfig])

  const sipEndpoint = useMemo(() => {
    const id = !isDemo && orgId ? orgId : 'your-org-id'
    return `sip:${id}@sip.meridian.tips`
  }, [isDemo, orgId])

  const selected = OPTIONS.find(o => o.mode === mode)!

  const handleSaveTransfer = useCallback(async () => {
    setError(null)
    if (transferNumber.trim() && !isValidPhone(transferNumber)) {
      setError('Enter a valid phone number (include the area code).')
      return
    }
    if (isDemo) {
      // Demo: keep local state only, no real write.
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      setStep('test')
      return
    }
    if (!orgId) { setError('Your account is still being set up — please refresh and try again.'); return }
    setSaving(true)
    try {
      const ok = await phoneService.saveConfig({
        merchant_id: orgId,
        transfer_number: transferNumber.trim(),
      })
      if (!ok) { setError('Could not save the transfer number — please try again.'); return }
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
      setStep('test')
    } catch {
      setError('Could not reach the server — please try again.')
    } finally {
      setSaving(false)
    }
  }, [transferNumber, isDemo, orgId])

  const currentStepIdx = STEPS.findIndex(s => s.key === step)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[#F5F5F7]">Connect your phone</h1>
        <p className="text-sm text-[#A1A1A8] mt-1">
          Point your business line at Meridian so incoming calls are answered by your AI agent —
          or transferred to a person when the caller asks.
        </p>
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-1">
        {STEPS.map((s, i) => {
          const isActive = i === currentStepIdx
          const isDone = i < currentStepIdx
          return (
            <div key={s.key} className="flex-1 flex flex-col gap-1.5">
              <div className={clsx('h-1 rounded-full transition-all duration-500', isDone || isActive ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]')} />
              <span className={clsx('text-[9px] font-medium text-center', isActive ? 'text-[#F5F5F7]' : isDone ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/40')}>
                {s.label}
              </span>
            </div>
          )
        })}
      </div>

      {error && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* ═══ Step 1 — Choose how to connect ═══ */}
      {step === 'choose' && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {OPTIONS.map(opt => {
              const active = opt.mode === mode
              const Icon = opt.icon
              return (
                <button
                  key={opt.mode}
                  onClick={() => setMode(opt.mode)}
                  className={clsx(
                    'card p-4 text-left transition-colors flex flex-col gap-2',
                    active ? 'border-[#17C5B0]/50 bg-[#17C5B0]/[0.04]' : 'hover:border-[#1A8FD6]/30',
                  )}
                >
                  <div className="flex items-center gap-2">
                    <div className={clsx('w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0', active ? 'bg-[#17C5B0]/15' : 'bg-[#1F1F23]')}>
                      <Icon size={18} className={active ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'} />
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-[#F5F5F7]">{opt.label}</span>
                      {opt.recommended && (
                        <span className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full bg-[#17C5B0]/15 text-[#17C5B0]">Recommended</span>
                      )}
                    </div>
                    {active && <CheckCircle2 size={16} className="text-[#17C5B0] ml-auto flex-shrink-0" />}
                  </div>
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">{opt.tagline}</p>
                </button>
              )
            })}
          </div>
          <div className="flex justify-end">
            <button onClick={() => setStep('doit')} className="flex items-center gap-2 px-5 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
              Continue <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 2 — Do it (option-specific instructions) ═══ */}
      {step === 'doit' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <selected.icon size={16} className="text-[#1A8FD6]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">{selected.label}</h3>
            </div>

            {/* Forward target — shown for forwarding-based options */}
            {(mode === 'forward_all' || mode === 'overflow') && (
              <>
                <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
                  <p className="text-[10px] text-[#A1A1A8] mb-1">Your Meridian forwarding number</p>
                  <div className="flex items-center gap-2">
                    <p className="text-base font-bold font-mono text-[#F5F5F7] flex-1 break-all">{meridianNumber}</p>
                    {meridianNumber.startsWith('+') && <CopyButton text={meridianNumber.replace(/[^+\d]/g, '')} />}
                  </div>
                </div>

                <div className="space-y-2">
                  <p className="text-[11px] text-[#A1A1A8] font-medium">
                    From your business phone, dial the star-code, then the Meridian number above:
                  </p>
                  {STAR_CODES
                    .filter(sc => mode === 'forward_all' ? sc.on === '*72' || sc.on === '*73' : true)
                    .map(sc => (
                      <div key={sc.on} className="flex items-center gap-3 bg-[#111113] border border-[#1F1F23] rounded-lg px-3 py-2">
                        <code className="text-sm font-mono font-semibold text-[#17C5B0] flex-shrink-0">{sc.on}</code>
                        <div className="flex-1 min-w-0">
                          <p className="text-xs text-[#F5F5F7]">{sc.label}</p>
                          <p className="text-[10px] text-[#A1A1A8]">{sc.note}</p>
                        </div>
                        <CopyButton text={sc.on} />
                      </div>
                    ))}
                </div>

                <div className="bg-amber-400/5 border border-amber-400/15 rounded-lg p-3 flex items-start gap-2">
                  <Info size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
                  <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                    Star-codes vary by carrier. If <code className="text-[#F5F5F7]">*72</code> doesn’t work, search
                    “{`call forwarding`}” in your carrier’s help (Bell, Rogers, Telus, etc.) — they all support it,
                    sometimes via the carrier app instead of a star-code.
                  </p>
                </div>
              </>
            )}

            {/* Port / new number */}
            {mode === 'port' && (
              <div className="space-y-3">
                <p className="text-xs text-[#A1A1A8] leading-relaxed">
                  We’ll route calls natively on a Meridian number — no forwarding needed.
                </p>
                <ol className="space-y-2">
                  {[
                    'Get a new Meridian number instantly, or start a port of your existing number.',
                    'Porting keeps your number but takes a few business days — we run it in the background.',
                    'Update your listings (Google, signage) to the Meridian number when the port completes.',
                  ].map((line, i) => (
                    <li key={i} className="flex items-start gap-3">
                      <span className="w-5 h-5 rounded-full bg-[#1A8FD6]/15 text-[#1A8FD6] text-[11px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5">{i + 1}</span>
                      <span className="text-xs text-[#F5F5F7] leading-relaxed">{line}</span>
                    </li>
                  ))}
                </ol>
                <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
                  <p className="text-[10px] text-[#A1A1A8] mb-1">Assigned Meridian number</p>
                  <p className="text-base font-bold font-mono text-[#F5F5F7] break-all">{meridianNumber}</p>
                </div>
              </div>
            )}

            {/* SIP / PBX */}
            {mode === 'sip' && (
              <div className="space-y-3">
                <p className="text-xs text-[#A1A1A8] leading-relaxed">
                  Add Meridian as a SIP endpoint / trunk in your phone system (RingCentral, 3CX, etc.),
                  then route your inbound DID to it.
                </p>
                <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
                  <p className="text-[10px] text-[#A1A1A8] mb-1">SIP endpoint</p>
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-bold font-mono text-[#F5F5F7] flex-1 break-all">{sipEndpoint}</p>
                    <CopyButton text={sipEndpoint} />
                  </div>
                </div>
                <div className="bg-[#1A8FD6]/5 border border-[#1A8FD6]/15 rounded-lg p-3 flex items-start gap-2">
                  <Info size={12} className="text-[#1A8FD6] mt-0.5 flex-shrink-0" />
                  <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                    SIP credentials and codec settings are provisioned per account. Share this endpoint with
                    your PBX admin — we’ll send the auth details to set up the trunk.
                  </p>
                </div>
              </div>
            )}
          </div>

          <div className="flex justify-between items-center">
            <button onClick={() => setStep('choose')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('transfer')} className="flex items-center gap-2 px-5 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
              Continue <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 3 — Human transfer number ═══ */}
      {step === 'transfer' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Phone size={16} className="text-[#7C5CFF]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Ring a person on request</h3>
            </div>
            <p className="text-xs text-[#A1A1A8] leading-relaxed">
              When a caller asks to speak with someone, Meridian transfers the call to this number —
              your cell or landline. Leave it blank to keep every call with the AI agent.
            </p>
            <div>
              <label className="text-xs text-[#A1A1A8] block mb-1.5">Human transfer number</label>
              <input
                type="tel"
                value={transferNumber}
                onChange={e => { setTransferNumber(e.target.value); setError(null) }}
                placeholder="+1 (555) 123-4567"
                autoComplete="off"
                className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] font-mono placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50"
              />
              {transferNumber && !isValidPhone(transferNumber) && (
                <p className="text-[10px] text-amber-400 mt-1.5">That doesn’t look like a complete phone number yet.</p>
              )}
            </div>
            {isDemo && (
              <p className="text-[10px] text-[#A1A1A8]/70 italic">
                Demo mode — nothing is saved. In your live portal this writes to your phone config.
              </p>
            )}
          </div>

          <div className="flex justify-between items-center">
            <button onClick={() => setStep('doit')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button
              onClick={handleSaveTransfer}
              disabled={saving}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : saved ? <CheckCircle2 size={14} /> : null}
              {saving ? 'Saving…' : saved ? 'Saved' : 'Save & continue'}
              {!saving && !saved && <ArrowRight size={14} />}
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 4 — Test it ═══ */}
      {step === 'test' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-5 border-[#17C5B0]/15">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
                <Sparkles size={20} className="text-[#17C5B0]" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#F5F5F7]">Place a test call</h3>
                <p className="text-xs text-[#A1A1A8] mt-0.5">Hear the agent live, then watch the order land in Phone Orders.</p>
              </div>
            </div>

            <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
              <p className="text-[10px] text-[#A1A1A8] mb-1">Call your live demo line now</p>
              <div className="flex items-center gap-2">
                <p className="text-xl font-bold font-mono text-[#F5F5F7] flex-1">{DEMO_TEST_LINE}</p>
                <CopyButton text={DEMO_TEST_LINE.replace(/[^+\d]/g, '')} />
                <a
                  href={`tel:${DEMO_TEST_LINE.replace(/[^+\d]/g, '')}`}
                  className="flex items-center gap-1.5 px-3 py-2 bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-colors flex-shrink-0"
                >
                  <Phone size={14} /> Call now
                </a>
              </div>
            </div>

            <div className="space-y-2.5">
              {[
                'You’ll hear the AI greeting when the call connects.',
                'Place a quick test order out loud — the agent takes it conversationally.',
                'Ask for “a person” to confirm the transfer rings your number.',
                'Hang up and open Phone Orders — your test call appears in the log.',
              ].map((line, i) => (
                <div key={i} className="flex items-start gap-3">
                  <CheckCircle2 size={16} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
                  <span className="text-xs text-[#F5F5F7] leading-relaxed">{line}</span>
                </div>
              ))}
            </div>

            <div className="bg-[#1A8FD6]/5 border border-[#1A8FD6]/15 rounded-lg p-3 flex items-start gap-2">
              <Info size={12} className="text-[#1A8FD6] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                Once your forwarding is live, callers to <span className="text-[#F5F5F7]">your own business number</span> reach
                the same agent — the demo line is just for a quick first listen.
              </p>
            </div>
          </div>

          <div className="flex justify-start">
            <button onClick={() => setStep('transfer')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
