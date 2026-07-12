import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { clsx } from 'clsx'
import { ConnectReservationSystem, ORDER_TYPE_OPTIONS, hasOrderType, toggleOrderType } from '@/components/phone/ConnectReservationSystem'
import {
  PhoneForwarded, Clock, Hash, Server, ArrowRight, ArrowLeft,
  CheckCircle2, Loader2, Copy, Phone, Info, AlertCircle, Sparkles,
  Mic, Volume2, Plus, Trash2, AlertTriangle, RefreshCw, Zap,
} from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import {
  phoneService, isValidE164, saveConfigErrorMessage, type PhoneConfig,
  type ReservationConfig,
} from '@/lib/phone-service'
import { api } from '@/lib/api'
import { posSystems } from '@/data/pos-systems'
import { VoicePlayButton, VoicePreviewCard, TestCallModal } from '@/components/phone'
import {
  VOICE_OPTIONS,
  type PhoneBizConfig, type PhoneMenuItem,
} from '@/lib/phone-orders-demo-data'

/**
 * "Set up" wizard — THE phone setup flow, a segment under the Phone Calls
 * pillar. Consolidates the old embedded Phone Orders wizard
 * (components/phone/SetupWizard, now removed) with the connect-your-line
 * instructions: number provisioning + swap, connect mode, voice & greeting,
 * menu, order routing + human transfer, then activate & test.
 *
 * Renders inside MerchantLayout, so it appears on BOTH the public demo
 * (/canada/demo) and the authenticated portal (/canada/merchant) — same as
 * every other pillar segment.
 *
 * Demo-safe: in demo mode nothing is written to the backend (local state only).
 */

// Live demo line callers can dial to hear the agent (from the deck).
const DEMO_TEST_LINE = '+1 782-358-5534'

const DIRECT_API_SYSTEMS = new Set(['square', 'toast', 'clover'])

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

type Step = 'choose' | 'doit' | 'agent' | 'menu' | 'routing' | 'test'

const STEPS: { key: Step; label: string }[] = [
  { key: 'choose', label: 'Connect' },
  { key: 'doit', label: 'Set it up' },
  { key: 'agent', label: 'Voice' },
  { key: 'menu', label: 'Menu' },
  { key: 'routing', label: 'Routing' },
  { key: 'test', label: 'Test' },
]

// Carrier star-codes vary. Bell Canada uses *21/*#21 for unconditional forward
// while Rogers/Telus/Fido use the classic *72/*73 codes.
const CA_STAR_CODES = [
  { label: 'Forward all calls (Rogers · Telus · Fido)', on: '*72', note: 'dial *72 then the Meridian number' },
  { label: 'Cancel forwarding (Rogers · Telus · Fido)', on: '*73', note: 'turns forwarding back off' },
  { label: 'Forward all calls (Bell Canada)', on: '*21', note: 'Bell\'s unconditional call-forward code' },
  { label: 'Cancel forwarding (Bell Canada)', on: '#21', note: 'dial #21 to cancel Bell forwarding' },
  { label: 'Forward when busy', on: '*90', note: 'for the Overflow option' },
  { label: 'Forward on no-answer', on: '*92', note: 'for the Overflow option' },
]

// US carriers (Verizon · AT&T · T-Mobile landline/wireless) share the classic
// *72/*73 codes; AT&T wireless uses **21* for unconditional forward.
const US_STAR_CODES = [
  { label: 'Forward all calls (Verizon · AT&T · T-Mobile)', on: '*72', note: 'dial *72 then the Meridian number' },
  { label: 'Cancel forwarding (Verizon · AT&T · T-Mobile)', on: '*73', note: 'turns forwarding back off' },
  { label: 'Forward all calls (AT&T wireless)', on: '**21*', note: 'dial **21*, the Meridian number, then #' },
  { label: 'Cancel forwarding (AT&T wireless)', on: '##21#', note: 'dial ##21# to cancel forwarding' },
  { label: 'Forward when busy', on: '*90', note: 'for the Overflow option' },
  { label: 'Forward on no-answer', on: '*92', note: 'for the Overflow option' },
]

/** Region detection — this wizard mounts under /canada/* and /us/* + /demo. */
function isCanadaMount(): boolean {
  return typeof window !== 'undefined' && window.location.pathname.startsWith('/canada')
}

/** Region-aware star codes — the Canada mounts keep their existing list. */
function starCodesForPath(): typeof CA_STAR_CODES {
  return isCanadaMount() ? CA_STAR_CODES : US_STAR_CODES
}

const PROVISION_TIMEOUT_MS = 30_000

/** Normalise a raw North-American number to +1XXXXXXXXXX E.164 format. */
function normalizeToE164(raw: string): string {
  const digits = raw.replace(/[^\d]/g, '')
  if (digits.length === 10) return `+1${digits}`
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`
  return raw.trim() // already E.164 or unknown format — pass through as-is
}

/** E.164 validation: accepts raw input that can be normalised to +1XXXXXXXXXX. */
function isValidPhone(v: string): boolean {
  return isValidE164(normalizeToE164(v))
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

const inputCls = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50'

export default function PhoneSetupWizard() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()

  const connectedPos = org?.pos_provider || null
  const posInfo = connectedPos ? posSystems.find(p => p.key === connectedPos) : null
  const hasDirectApi = connectedPos ? DIRECT_API_SYSTEMS.has(connectedPos) : false

  const [step, setStep] = useState<Step>('choose')
  const [mode, setMode] = useState<ConnectMode>('forward_all')
  const [phoneConfig, setPhoneConfig] = useState<PhoneConfig | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showTestCall, setShowTestCall] = useState(false)

  // ── Agent configuration (ported from the old embedded SetupWizard) ──
  const [businessName, setBusinessName] = useState(org?.business_name || 'My Business')
  const [greeting, setGreeting] = useState('')
  const [voice, setVoice] = useState('af_bella')
  const [orderTypes, setOrderTypes] = useState<string[]>(['pickup', 'delivery'])
  const [reservationConfig, setReservationConfig] = useState<ReservationConfig | null>(null)
  const [routing, setRouting] = useState<'pos' | 'webhook' | 'sms' | 'email'>(connectedPos ? 'pos' : 'sms')
  const [transferNumber, setTransferNumber] = useState('')
  const [menu, setMenu] = useState<PhoneMenuItem[]>([])
  const [newItem, setNewItem] = useState({ name: '', price: '', category: '' })
  const [addItemError, setAddItemError] = useState<string | null>(null)

  // Load existing config (authed only) and hydrate everything the wizard edits.
  // Demo never hits the backend.
  useEffect(() => {
    if (!orgId || isDemo) return
    phoneService.getConfig(orgId).then(cfg => {
      setPhoneConfig(cfg)
      if (cfg.business_name) setBusinessName(cfg.business_name)
      if (cfg.greeting) setGreeting(cfg.greeting)
      if (cfg.voice) setVoice(cfg.voice)
      if (cfg.order_types?.length) setOrderTypes(cfg.order_types)
      if (cfg.reservation_config) setReservationConfig(cfg.reservation_config)
      if (cfg.order_routing) setRouting(cfg.order_routing)
      if (cfg.transfer_number) setTransferNumber(cfg.transfer_number)
      if (cfg.menu_items?.length) {
        setMenu(cfg.menu_items.map((m: any, i: number) => ({
          id: m.id || `item-${i}`,
          name: m.name || '',
          price: typeof m.price === 'number' ? m.price : parseFloat(m.price) || 0,
          category: m.category || 'General',
        })))
      }
    })
  }, [orgId, isDemo])

  // ── Number provisioning: fresh accounts get a real Meridian number here. ──
  // The backend endpoint is idempotent (never double-buys); the ref guards
  // React's double-mount. We wait for the config fetch so an existing number
  // is displayed rather than re-requested.
  const [provisioning, setProvisioning] = useState(false)
  const [provisionError, setProvisionError] = useState<string | null>(null)
  const provisionStarted = useRef(false)

  const doProvision = useCallback((force = false) => {
    if (!orgId || isDemo) return
    provisionStarted.current = true
    setProvisioning(true)
    setProvisionError(null)
    // Soft timeout: telco purchase + webhook wiring can stall. Surface a
    // friendly retry instead of an indefinite spinner; the underlying request
    // may still resolve and fill the number in afterwards.
    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      setProvisioning(false)
      setProvisionError('This is taking longer than expected. Please try again.')
    }, PROVISION_TIMEOUT_MS)
    phoneService
      .provisionNumber({ merchant_id: orgId, country: 'CA', business_name: businessName, force })
      .then(res => {
        settled = true
        setPhoneConfig(p => ({ ...(p ?? { exists: true, merchant_id: orgId }), exists: true, phone_number: res.phone_number }))
        setProvisionError(null)
      })
      .catch((e: unknown) => {
        settled = true
        setProvisionError(e instanceof Error ? e.message : 'Could not provision a number')
      })
      .finally(() => { settled = true; clearTimeout(timer); setProvisioning(false) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orgId, isDemo, businessName])

  useEffect(() => {
    if (isDemo || !orgId) return
    if (phoneConfig === null) return // config still loading
    if (provisionStarted.current) return
    if (phoneConfig.phone_number && phoneConfig.phone_number.trim()) return
    doProvision()
  }, [isDemo, orgId, phoneConfig, doProvision])

  const handleSwapNumber = useCallback(() => {
    if (isDemo || provisioning) return
    const current = phoneConfig?.phone_number || ''
    const okToSwap = window.confirm(
      `Replace ${current || 'your current Meridian number'} with a new one?\n\n` +
      'The old number is released immediately — callers and forwarding rules pointing at it will stop working.',
    )
    if (!okToSwap) return
    doProvision(true)
  }, [isDemo, provisioning, phoneConfig?.phone_number, doProvision])

  // The merchant's provisioned Meridian number (forward target). Placeholder in
  // demo / while provisioning.
  const meridianNumber = useMemo(() => {
    if (!isDemo && phoneConfig?.phone_number) return phoneConfig.phone_number
    if (isDemo) return DEMO_TEST_LINE
    return ''
  }, [isDemo, phoneConfig])

  const sipEndpoint = useMemo(() => {
    const id = !isDemo && orgId ? orgId : 'your-org-id'
    return `sip:${id}@sip.meridian.tips`
  }, [isDemo, orgId])

  const selected = OPTIONS.find(o => o.mode === mode)!

  // ── Menu helpers (ported) ──
  const addMenuItem = () => {
    const name = newItem.name.trim()
    const price = parseFloat(newItem.price)
    // Surface why a row was rejected instead of silently dropping it.
    if (!name) { setAddItemError('Item name is required.'); return }
    if (newItem.price.trim() === '' || Number.isNaN(price)) { setAddItemError('Enter a price (e.g. 9.99).'); return }
    if (price < 0) { setAddItemError('Price cannot be negative.'); return }
    setMenu(prev => [
      ...prev,
      { id: `m-${Date.now()}`, name, price, category: newItem.category.trim() || 'General' },
    ])
    setNewItem({ name: '', price: '', category: '' })
    setAddItemError(null)
  }

  // Items the agent would read back with no price — flagged before activation.
  const zeroPricedItems = menu.filter(m => !(m.price > 0))

  const transferTrimmed = transferNumber.trim()
  const transferValid = transferTrimmed === '' || isValidPhone(transferTrimmed)

  // ── Credit-balance check (ported): the live agent refuses calls when the
  // balance can't cover a minute, so warn before activation silently fails. ──
  const [balance, setBalance] = useState<{ balance: number; low_balance_threshold: number; is_low: boolean } | null>(null)
  const [balanceChecked, setBalanceChecked] = useState(false)

  useEffect(() => {
    if (step !== 'routing' || balanceChecked || !orgId || isDemo) return
    setBalanceChecked(true)
    api.creditBalance(orgId)
      .then(b => setBalance({ balance: b.balance, low_balance_threshold: b.low_balance_threshold, is_low: b.is_low }))
      .catch(() => setBalance(null))
  }, [step, balanceChecked, orgId, isDemo])

  const balanceEmpty = balance != null && balance.balance <= 0
  const balanceLow = balance != null && !balanceEmpty && balance.is_low

  // ── Activation: persist the full agent config + go live. ──
  const handleActivate = useCallback(async () => {
    setError(null)
    if (transferTrimmed && !isValidPhone(transferTrimmed)) {
      setError('Enter a valid transfer number (include the area code).')
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
    const res = await phoneService.saveConfig({
      merchant_id: orgId,
      business_name: businessName,
      phone_number: phoneConfig?.phone_number || undefined,
      greeting: greeting || undefined,
      voice,
      order_types: orderTypes,
      reservation_config: reservationConfig ?? undefined,
      menu_items: menu.map(m => ({ name: m.name, price: m.price, category: m.category })),
      transfer_number: transferTrimmed ? normalizeToE164(transferTrimmed) : undefined,
      order_routing: routing,
      active: true,
    })
    setSaving(false)
    if (!res.ok) {
      // Item 2: show the SPECIFIC failure reason, not a generic message.
      setError(saveConfigErrorMessage(res))
      return
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
    setStep('test')
  }, [isDemo, orgId, businessName, phoneConfig?.phone_number, greeting, voice, orderTypes, menu, transferTrimmed, routing])

  const currentStepIdx = STEPS.findIndex(s => s.key === step)

  const bizForTest: PhoneBizConfig = useMemo(() => ({
    id: orgId || 'demo',
    name: businessName,
    vertical: 'restaurant',
    country: isCanadaMount() ? 'CA' : 'US',
    currency: isCanadaMount() ? 'CA$' : '$',
    taxRate: isCanadaMount() ? 0.13 : 0.08,
    phone: meridianNumber,
    greeting,
    voice,
    orderTypes: orderTypes as PhoneBizConfig['orderTypes'],
    menu,
  }), [orgId, businessName, meridianNumber, greeting, voice, orderTypes, menu])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-[#F5F5F7]">Set up your phone agent</h1>
        <p className="text-sm text-[#A1A1A8] mt-1">
          Point your business line at Meridian, pick a voice, load your menu, and go live —
          incoming calls are answered by your AI agent or transferred to a person on request.
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
          <AlertCircle size={14} className="flex-shrink-0" /> {error}
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

      {/* ═══ Step 2 — Do it (option-specific instructions + your number) ═══ */}
      {step === 'doit' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <selected.icon size={16} className="text-[#1A8FD6]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">{selected.label}</h3>
            </div>

            {/* Your Meridian number — auto-provisioned for fresh accounts. */}
            <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
              <p className="text-[10px] text-[#A1A1A8] mb-1">
                {mode === 'sip' ? 'Your Meridian number' : mode === 'port' ? 'Assigned Meridian number' : 'Your Meridian forwarding number'}
              </p>
              <div className="flex items-center gap-2">
                {provisioning ? (
                  <p className="text-base font-medium text-[#A1A1A8] flex-1 flex items-center gap-2">
                    <Loader2 size={14} className="text-[#1A8FD6] animate-spin" /> Provisioning your number…
                  </p>
                ) : (
                  <p className="text-base font-bold font-mono text-[#F5F5F7] flex-1 break-all">
                    {meridianNumber || 'No number yet'}
                  </p>
                )}
                {meridianNumber.startsWith('+') && !provisioning && <CopyButton text={meridianNumber.replace(/[^+\d]/g, '')} />}
                {!isDemo && meridianNumber.startsWith('+') && !provisioning && (
                  <button
                    type="button"
                    onClick={handleSwapNumber}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[#1F1F23] text-[10px] font-medium text-[#A1A1A8] hover:border-[#1A8FD6]/30 hover:text-[#1A8FD6] transition-colors flex-shrink-0"
                    title="Release this number and get a new one"
                  >
                    <RefreshCw size={11} /> Swap number
                  </button>
                )}
              </div>
              {provisionError && (
                <div className="mt-2 space-y-1.5">
                  <p className="text-[10px] text-red-400/80">{provisionError}</p>
                  <button
                    type="button"
                    onClick={() => doProvision()}
                    disabled={provisioning}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6] text-[10px] font-medium hover:bg-[#1A8FD6]/10 disabled:opacity-40 transition-colors">
                    <RefreshCw size={11} /> Try again
                  </button>
                </div>
              )}
              {!provisionError && !provisioning && !isDemo && meridianNumber.startsWith('+') && (
                <p className="text-[9px] text-[#A1A1A8]/50 mt-1.5">Dedicated number assigned to your business</p>
              )}
            </div>

            {/* Forward instructions — shown for forwarding-based options */}
            {(mode === 'forward_all' || mode === 'overflow') && (
              <>
                <div className="space-y-2">
                  <p className="text-[11px] text-[#A1A1A8] font-medium">
                    From your business phone, dial the star-code, then the Meridian number above:
                  </p>
                  {starCodesForPath()
                    .filter(sc => mode === 'forward_all'
                      ? (sc.on !== '*90' && sc.on !== '*92')
                      : true)
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
            <button onClick={() => setStep('agent')} className="flex items-center gap-2 px-5 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
              Continue <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 3 — Voice & greeting ═══ */}
      {step === 'agent' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <div className="flex items-center gap-2">
              <Mic size={16} className="text-[#1A8FD6]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Voice & Greeting</h3>
            </div>
            <div>
              <label className="text-xs text-[#A1A1A8] block mb-1">Business Name</label>
              <input className={inputCls} value={businessName} onChange={e => setBusinessName(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-[#A1A1A8] block mb-1">Greeting Message</label>
              <textarea
                className={inputCls + ' resize-none h-16'}
                placeholder={`Thanks for calling ${businessName}! What can I get started for you?`}
                value={greeting}
                onChange={e => setGreeting(e.target.value)}
              />
            </div>
            <div>
              <label className="text-xs text-[#A1A1A8] block mb-2">Agent Voice</label>
              <div className="grid grid-cols-2 gap-2">
                {VOICE_OPTIONS.map(v => (
                  <div key={v.id} onClick={() => setVoice(v.id)}
                    role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setVoice(v.id) }}
                    className={clsx('px-3 py-2 rounded-lg border text-left transition-all cursor-pointer',
                      voice === v.id ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                    <div className="flex items-center gap-1.5">
                      <Volume2 size={12} className={voice === v.id ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'} />
                      <p className={clsx('text-xs font-medium flex-1', voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                      <VoicePlayButton voiceId={v.id} isSelected={voice === v.id} />
                    </div>
                    <p className="text-[9px] text-[#A1A1A8]/60 mt-0.5">{v.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Voice preview with waveform — plays the real studio sample */}
            <VoicePreviewCard voiceId={voice} />

            <div>
              <label className="text-xs text-[#A1A1A8] block mb-2">Order Types</label>
              <div className="flex gap-2">
                {ORDER_TYPE_OPTIONS.map(({ value, label }) => (
                  <button key={value} onClick={() => {
                    setOrderTypes(p => toggleOrderType(p, value))
                  }} className={clsx('px-3 py-1.5 rounded-lg border text-xs font-medium transition-all',
                    hasOrderType(orderTypes, value) ? 'border-[#17C5B0]/20 bg-[#17C5B0]/5 text-[#17C5B0]' : 'border-[#1F1F23] text-[#A1A1A8]')}>
                    {label}
                  </button>
                ))}
              </div>
              {hasOrderType(orderTypes, 'reservation') && (
                <ConnectReservationSystem
                  merchantId={orgId}
                  config={reservationConfig}
                  onSaved={setReservationConfig}
                />
              )}
            </div>
          </div>

          <div className="flex justify-between items-center">
            <button onClick={() => setStep('doit')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('menu')} className="flex items-center gap-2 px-5 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
              Continue <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 4 — Menu ═══ */}
      {step === 'menu' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Menu Items</h3>
            <p className="text-xs text-[#A1A1A8]">
              {posInfo ? `Menu synced from ${posInfo.name}. Edit or add items below — this is what your agent reads to callers.`
                : 'Add the items your agent should take orders for. Callers can order anything on this list.'}
            </p>
            <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
              {menu.length === 0 && (
                <p className="text-[10px] text-[#A1A1A8]/60 py-3 text-center">No items yet — add your first below.</p>
              )}
              {menu.map((item, idx) => {
                const noPrice = !(item.price > 0)
                return (
                  <div key={item.id} className={clsx('flex items-center gap-2 px-3 py-2 rounded-lg',
                    noPrice ? 'bg-[#111113] ring-1 ring-amber-500/30' : 'bg-[#111113]')}>
                    <input
                      className="flex-1 min-w-0 bg-transparent text-xs text-[#F5F5F7] focus:outline-none"
                      value={item.name}
                      aria-label="Item name"
                      onChange={e => setMenu(prev => prev.map((m, i) => i === idx ? { ...m, name: e.target.value } : m))}
                    />
                    <div className={clsx('flex items-center text-xs font-mono', noPrice ? 'text-amber-400' : 'text-[#17C5B0]')}>
                      <span>{isCanadaMount() ? 'CA$' : '$'}</span>
                      <input
                        className="w-14 bg-transparent text-right focus:outline-none"
                        type="number"
                        step="0.01"
                        min="0"
                        value={item.price}
                        aria-label="Item price"
                        onChange={e => setMenu(prev => prev.map((m, i) => i === idx ? { ...m, price: parseFloat(e.target.value) || 0 } : m))}
                      />
                    </div>
                    <button
                      onClick={() => setMenu(prev => prev.filter((_, i) => i !== idx))}
                      aria-label={`Remove ${item.name}`}
                      className="text-[#A1A1A8]/50 hover:text-red-400 transition-colors flex-shrink-0">
                      <Trash2 size={12} />
                    </button>
                  </div>
                )
              })}
            </div>
            {zeroPricedItems.length > 0 && (
              <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <AlertTriangle size={12} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <p className="text-[10px] text-amber-200/80 leading-relaxed">
                  {zeroPricedItems.length} item{zeroPricedItems.length > 1 ? 's have' : ' has'} no price — callers won't hear a price for {zeroPricedItems.length > 1 ? 'them' : 'it'}.
                </p>
              </div>
            )}
            <div>
              <div className="flex items-center gap-2 pt-1">
                <input
                  className={inputCls + ' flex-1'}
                  placeholder="Item name"
                  value={newItem.name}
                  onChange={e => { setNewItem(p => ({ ...p, name: e.target.value })); if (addItemError) setAddItemError(null) }}
                  onKeyDown={e => { if (e.key === 'Enter') addMenuItem() }}
                />
                <input
                  className={inputCls + ' w-20'}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                  min="0"
                  value={newItem.price}
                  onChange={e => { setNewItem(p => ({ ...p, price: e.target.value })); if (addItemError) setAddItemError(null) }}
                  onKeyDown={e => { if (e.key === 'Enter') addMenuItem() }}
                />
                <button
                  onClick={addMenuItem}
                  aria-label="Add menu item"
                  className="flex-shrink-0 p-2 rounded-lg bg-[#1A8FD6]/10 text-[#1A8FD6] hover:bg-[#1A8FD6]/20 disabled:opacity-30 transition-colors">
                  <Plus size={14} />
                </button>
              </div>
              {addItemError && (
                <p className="text-[9px] text-red-400/80 mt-1.5">{addItemError}</p>
              )}
            </div>
            <p className="text-[10px] text-[#A1A1A8]/60">
              Tip: you can also scan a paper menu or import a CSV from Phone Orders → Settings.
            </p>
          </div>

          <div className="flex justify-between items-center">
            <button onClick={() => setStep('agent')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button onClick={() => setStep('routing')} className="flex items-center gap-2 px-5 py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
              Continue <ArrowRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 5 — Order routing + human transfer + activate ═══ */}
      {step === 'routing' && (
        <div className="space-y-4">
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Order Routing</h3>
            <p className="text-xs text-[#A1A1A8]">Where should confirmed orders be sent?</p>
            <div className="space-y-2">
              {posInfo && (
                <button onClick={() => setRouting(hasDirectApi ? 'pos' : 'webhook')}
                  className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                    (routing === 'pos' || routing === 'webhook') ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                  <div className="flex items-center gap-2">
                    <p className={clsx('text-sm font-medium', (routing === 'pos' || routing === 'webhook') ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>
                      {posInfo.name}
                    </p>
                    {hasDirectApi && <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#17C5B0]/10 text-[#17C5B0] font-medium">Direct API</span>}
                    {!hasDirectApi && <span className="text-[9px] px-1.5 py-0.5 rounded bg-[#1A8FD6]/10 text-[#1A8FD6] font-medium">Webhook</span>}
                  </div>
                  <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">
                    {hasDirectApi ? `Orders sent directly to ${posInfo.name} via API` : `Orders sent via webhook to ${posInfo.name}`}
                  </p>
                </button>
              )}
              {!posInfo && (
                <button onClick={() => setRouting('pos')}
                  className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                    routing === 'pos' ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                  <p className={clsx('text-sm font-medium', routing === 'pos' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>POS System</p>
                  <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">Connect your POS in Settings to enable direct order routing</p>
                </button>
              )}
              <button onClick={() => setRouting('sms')}
                className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                  routing === 'sms' ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                <p className={clsx('text-sm font-medium', routing === 'sms' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>SMS Alert</p>
                <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">Text order details to your phone for manual POS entry</p>
              </button>
              <button onClick={() => setRouting('email')}
                className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                  routing === 'email' ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                <p className={clsx('text-sm font-medium', routing === 'email' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>Email</p>
                <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">Send formatted order confirmation via email</p>
              </button>
            </div>

            {/* Human warm-transfer fallback */}
            <div className="pt-2">
              <label className="text-xs text-[#A1A1A8] flex items-center gap-1.5 mb-1">
                <PhoneForwarded size={12} className="text-[#A1A1A8]" /> Transfer to a human at
                <span className="text-[#A1A1A8]/50">(optional)</span>
              </label>
              <input
                className={clsx(inputCls, transferValid ? '' : 'border-red-400/50 focus:border-red-400/50')}
                placeholder="+1 (555) 123-4567"
                inputMode="tel"
                autoComplete="off"
                value={transferNumber}
                onChange={e => { setTransferNumber(e.target.value); setError(null) }}
              />
              {transferValid ? (
                <p className="text-[9px] text-[#A1A1A8]/50 mt-1">
                  Callers who ask for a person are warm-transferred here. Leave blank to keep every call with the AI agent.
                </p>
              ) : (
                <p className="text-[9px] text-red-400/80 mt-1">
                  That doesn’t look like a complete phone number yet — e.g. +14165551234.
                </p>
              )}
            </div>

            {/* Credit balance warnings — calls are gated when the balance can't
                cover a minute, so flag an empty/low balance before activation. */}
            {balanceEmpty && (
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/5 border border-red-500/20">
                <AlertTriangle size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
                <div className="space-y-0.5">
                  <p className="text-[11px] text-red-200 font-medium">Your call credit balance is empty.</p>
                  <p className="text-[10px] text-red-200/70 leading-relaxed">
                    You can activate, but callers will hear "this account is temporarily paused" until you add credits. Top up from the Billing section to go live.
                  </p>
                </div>
              </div>
            )}
            {balanceLow && (
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20">
                <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="space-y-0.5">
                  <p className="text-[11px] text-amber-200 font-medium">Low call credit balance ({balance!.balance.toLocaleString()} credits).</p>
                  <p className="text-[10px] text-amber-200/70 leading-relaxed">
                    That's only a few minutes of calls. Consider topping up from the Billing section so your line stays live.
                  </p>
                </div>
              </div>
            )}

            {isDemo && (
              <p className="text-[10px] text-[#A1A1A8]/70 italic">
                Demo mode — nothing is saved. In your live portal this activates your phone agent.
              </p>
            )}
          </div>

          <div className="flex justify-between items-center">
            <button onClick={() => setStep('menu')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
            <button
              onClick={handleActivate}
              disabled={saving || !transferValid}
              className="flex items-center gap-2 px-5 py-2.5 bg-[#17C5B0] text-white text-sm font-medium rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-colors"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : saved ? <CheckCircle2 size={14} /> : <Zap size={14} />}
              {saving ? 'Activating…' : saved ? 'Activated' : 'Activate agent'}
              {!saving && !saved && <ArrowRight size={14} />}
            </button>
          </div>
        </div>
      )}

      {/* ═══ Step 6 — Test it ═══ */}
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
              <p className="text-[10px] text-[#A1A1A8] mb-1">
                {!isDemo && meridianNumber.startsWith('+') ? 'Call your Meridian number now' : 'Call your live demo line now'}
              </p>
              {(() => {
                const testLine = !isDemo && meridianNumber.startsWith('+') ? meridianNumber : DEMO_TEST_LINE
                return (
                  <div className="flex items-center gap-2">
                    <p className="text-xl font-bold font-mono text-[#F5F5F7] flex-1">{testLine}</p>
                    <CopyButton text={testLine.replace(/[^+\d]/g, '')} />
                    <a
                      href={`tel:${testLine.replace(/[^+\d]/g, '')}`}
                      className="flex items-center gap-1.5 px-3 py-2 bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold rounded-lg hover:bg-[#17C5B0]/90 transition-colors flex-shrink-0"
                    >
                      <Phone size={14} /> Call now
                    </a>
                  </div>
                )
              })()}
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

            {/* In-browser test call (mic + speaker), ported from the old wizard. */}
            <button onClick={() => setShowTestCall(true)}
              className="w-full flex items-center justify-center gap-2 py-2.5 border border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6] text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/10 transition-colors">
              <Phone size={12} /> Test in browser instead
            </button>

            <div className="bg-[#1A8FD6]/5 border border-[#1A8FD6]/15 rounded-lg p-3 flex items-start gap-2">
              <Info size={12} className="text-[#1A8FD6] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                Once your forwarding is live, callers to <span className="text-[#F5F5F7]">your own business number</span> reach
                the same agent.
              </p>
            </div>
          </div>

          <div className="flex justify-start">
            <button onClick={() => setStep('routing')} className="flex items-center gap-2 px-4 py-2.5 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
          </div>
        </div>
      )}

      {showTestCall && (
        <TestCallModal
          biz={bizForTest}
          orgId={orgId}
          personality={phoneConfig?.personality}
          onClose={() => setShowTestCall(false)}
        />
      )}
    </div>
  )
}
