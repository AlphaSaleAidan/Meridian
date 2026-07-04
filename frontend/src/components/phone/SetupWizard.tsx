import { useState, useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import {
  Store, Mic, ListOrdered, Route, Zap, Volume2,
  CheckCircle2, ArrowRight, ArrowLeft, Phone, Loader2, Plus, Trash2,
  AlertTriangle, RefreshCw, PhoneForwarded,
} from 'lucide-react'
import { VoicePlayButton, VoicePreviewCard } from './VoicePreview'
import TestCallModal from './TestCallModal'
import {
  VOICE_OPTIONS, DEFAULT_VOICE_SETTINGS,
  type PhoneBizConfig, type VoiceSettings, type PhoneMenuItem,
} from '@/lib/phone-orders-demo-data'
import { phoneService, isValidE164, type PhoneConfig } from '@/lib/phone-service'
import { api } from '@/lib/api'
import { posSystems } from '@/data/pos-systems'

const WIZARD_STEPS = [
  { icon: Store, label: 'Setup' },
  { icon: Mic, label: 'Voice' },
  { icon: ListOrdered, label: 'Menu' },
  { icon: Route, label: 'Routing' },
  { icon: Zap, label: 'Activate' },
]

const DIRECT_API_SYSTEMS = new Set(['square', 'toast', 'clover'])

// Countries we can self-provision a local voice+SMS number in from the wizard.
// Canada-first per product doctrine; US is opt-in.
type ProvisionCountry = 'CA' | 'US'
const COUNTRY_OPTIONS: { code: ProvisionCountry; label: string }[] = [
  { code: 'CA', label: 'Canada' },
  { code: 'US', label: 'United States' },
]

const PROVISION_TIMEOUT_MS = 30_000

interface Props {
  biz: PhoneBizConfig
  onDone: () => void
  connectedPos: string | null
  orgId: string
  // Persisted config for this merchant, when editing an existing setup. Used to
  // hydrate the routing / transfer-number / business-hours fields the wizard
  // collects but PhoneBizConfig doesn't carry.
  existingConfig?: PhoneConfig
}

export default function SetupWizard({ biz, onDone, connectedPos, orgId, existingConfig }: Props) {
  const [step, setStep] = useState(0)
  const [showTestCall, setShowTestCall] = useState(false)
  const posInfo = connectedPos ? posSystems.find(p => p.key === connectedPos) : null
  const hasDirectApi = connectedPos ? DIRECT_API_SYSTEMS.has(connectedPos) : false
  const hasMenuSync = posInfo?.dataAvailable?.menuItems ?? false

  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>({ ...DEFAULT_VOICE_SETTINGS })
  const [cfg, setCfg] = useState({
    businessName: biz.name,
    phone: biz.phone,
    greeting: biz.greeting,
    voice: biz.voice,
    orderTypes: [...biz.orderTypes] as string[],
    // Hydrate the saved routing choice when re-opening an existing setup, else
    // default by whether a POS is connected.
    routing: (existingConfig?.order_routing ?? (connectedPos ? 'pos' : 'sms')) as 'pos' | 'webhook' | 'sms' | 'email',
    // Human warm-transfer fallback number. Optional; persisted as transfer_number
    // so the live agent can offer "let me put you through to someone". Hydrated
    // from the saved value so editing an existing setup shows the real number.
    transferNumber: existingConfig?.transfer_number ?? '',
    // Business-hours / after-hours messaging. The wizard has no editor for these
    // yet, but they are carried through so an edit-and-reactivate round-trips
    // (rather than wipes) whatever the merchant configured. Read by the live
    // agent's after-hours gate (phone.py).
    businessHours: existingConfig?.business_hours ?? undefined as Record<string, string> | undefined,
    afterHoursMessage: existingConfig?.after_hours_message ?? undefined as string | undefined,
  })

  // Editable menu the agent will read back to callers. Seeded from the POS sync
  // / demo data, but the merchant can add, edit, and remove items here so a
  // self-service number takes orders against their real menu.
  const [menu, setMenu] = useState<PhoneMenuItem[]>(() => biz.menu.map(m => ({ ...m })))
  const [newItem, setNewItem] = useState({ name: '', price: '', category: '' })
  const [addItemError, setAddItemError] = useState<string | null>(null)

  // Reservations: scrape the merchant's site for their EXISTING booking link
  // (OpenTable/Resy/…). The agent then texts callers that link — it never books.
  const [websiteUrl, setWebsiteUrl] = useState('')
  const [scrapeReservations, setScrapeReservations] = useState(false)
  const [rezScraping, setRezScraping] = useState(false)
  const [rezResult, setRezResult] = useState<{ url: string; platform: string } | null>(null)
  const [rezError, setRezError] = useState<string | null>(null)

  const runReservationScrape = async () => {
    if (!websiteUrl.trim()) { setRezError('Enter your website URL first'); return }
    setRezScraping(true); setRezError(null)
    const res = await phoneService.scrapeReservationLink(orgId, websiteUrl.trim())
    setRezScraping(false)
    if (!res) { setRezError('Could not reach your website — check the URL'); return }
    if (!res.found) { setRezError('No reservation link found — you can paste one in Settings later'); return }
    setRezResult({ url: res.reservation_url, platform: res.reservation_platform })
  }

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

  // Items the agent would read back with no price ("a coffee" instead of
  // "a coffee, three fifty"). Flagged before Activate so nothing ships silently
  // priced at zero.
  const zeroPricedItems = menu.filter(m => !(m.price > 0))
  const transferTrimmed = cfg.transferNumber.trim()
  const transferValid = transferTrimmed === '' || isValidE164(transferTrimmed)

  // Auto-provision a dedicated number on first mount when the merchant has none
  // yet. Backend is idempotent; the ref guards React's double-mount.
  const [country, setCountry] = useState<ProvisionCountry>('CA')
  const [provisioning, setProvisioning] = useState(false)
  const [provisionError, setProvisionError] = useState<string | null>(null)
  const provisionStarted = useRef(false)

  const doProvision = (selected: ProvisionCountry) => {
    provisionStarted.current = true
    setProvisioning(true)
    setProvisionError(null)
    // Soft timeout: telco purchase + webhook wiring can stall (slow carrier,
    // missing regulatory bundle). Surface a friendly retry instead of an
    // indefinite spinner. The underlying request may still resolve and fill
    // the number in afterwards.
    let settled = false
    const timer = setTimeout(() => {
      if (settled) return
      setProvisioning(false)
      setProvisionError('This is taking longer than expected. Please try again.')
    }, PROVISION_TIMEOUT_MS)
    phoneService
      .provisionNumber({ merchant_id: orgId, country: selected, business_name: cfg.businessName })
      .then(res => { settled = true; setCfg(p => ({ ...p, phone: res.phone_number })); setProvisionError(null) })
      .catch((e: unknown) => { settled = true; setProvisionError(e instanceof Error ? e.message : 'Could not provision a number') })
      .finally(() => { settled = true; clearTimeout(timer); setProvisioning(false) })
  }

  useEffect(() => {
    if (provisionStarted.current) return
    if (cfg.phone && cfg.phone.trim()) return
    doProvision(country)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Credit-balance check, fetched the first time the merchant reaches Activate.
  // The live agent refuses calls when the balance can't cover a minute
  // (phone.py credit gate), so a zero-balance "activation" silently fails for
  // the first real caller. We warn here before that happens.
  const [balance, setBalance] = useState<{ balance: number; low_balance_threshold: number; is_low: boolean } | null>(null)
  const [balanceChecked, setBalanceChecked] = useState(false)

  useEffect(() => {
    if (step !== 4 || balanceChecked || !orgId) return
    setBalanceChecked(true)
    api.creditBalance(orgId)
      .then(b => setBalance({ balance: b.balance, low_balance_threshold: b.low_balance_threshold, is_low: b.is_low }))
      .catch(() => setBalance(null))
  }, [step, balanceChecked, orgId])

  const balanceEmpty = balance != null && balance.balance <= 0
  const balanceLow = balance != null && !balanceEmpty && balance.is_low

  const inputCls = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50'

  const hasNumber = Boolean(cfg.phone && cfg.phone.trim()) && !provisioning

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-bold text-[#F5F5F7]">Phone Agent Setup</h2>
        <p className="text-xs text-[#A1A1A8] mt-1">Configure your AI phone agent in {WIZARD_STEPS.length} steps</p>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-1">
        {WIZARD_STEPS.map((s, i) => {
          const Icon = s.icon
          const done = i < step
          const active = i === step
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-1">
              <div className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center border transition-all',
                done ? 'bg-[#17C5B0] border-[#17C5B0] text-white' :
                active ? 'border-[#1A8FD6] bg-[#1A8FD6]/10 text-[#1A8FD6]' :
                'border-[#1F1F23] text-[#A1A1A8]',
              )}>
                {done ? <CheckCircle2 size={14} /> : <Icon size={14} />}
              </div>
              <span className={clsx('text-[9px] font-medium', active ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{s.label}</span>
            </div>
          )
        })}
      </div>

      <div className="card p-5 space-y-4">
        {/* Step 0: Business Details */}
        {step === 0 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Business Details</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[#A1A1A8] block mb-1">Business Name</label>
                <input className={inputCls} value={cfg.businessName} onChange={e => setCfg(p => ({ ...p, businessName: e.target.value }))} />
              </div>

              {/* Country picker — only relevant while we don't yet have a number.
                  Once a number is bought it's fixed, so we hide the picker. */}
              {!hasNumber && (
                <div>
                  <label className="text-xs text-[#A1A1A8] block mb-1">Number Country</label>
                  <div className="flex gap-2">
                    {COUNTRY_OPTIONS.map(c => (
                      <button
                        key={c.code}
                        type="button"
                        onClick={() => setCountry(c.code)}
                        disabled={provisioning}
                        className={clsx('px-3 py-1.5 rounded-lg border text-xs font-medium transition-all disabled:opacity-40',
                          country === c.code ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#F5F5F7]' : 'border-[#1F1F23] text-[#A1A1A8]')}>
                        {c.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <label className="text-xs text-[#A1A1A8] block mb-1">Phone Number</label>
                <div className="relative">
                  <input
                    className={inputCls}
                    value={provisioning ? 'Provisioning your number…' : cfg.phone}
                    readOnly
                  />
                  {provisioning && (
                    <Loader2 size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#1A8FD6] animate-spin" />
                  )}
                </div>
                {provisionError ? (
                  <div className="mt-1.5 space-y-1.5">
                    <p className="text-[9px] text-red-400/80">{provisionError}</p>
                    <button
                      type="button"
                      onClick={() => doProvision(country)}
                      disabled={provisioning}
                      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6] text-[10px] font-medium hover:bg-[#1A8FD6]/10 disabled:opacity-40 transition-colors">
                      <RefreshCw size={11} /> Try again
                    </button>
                  </div>
                ) : (
                  <p className="text-[9px] text-[#A1A1A8]/50 mt-1">
                    {hasNumber ? 'Dedicated number assigned to your business' : 'Auto-provisioned for your business'}
                  </p>
                )}
              </div>
              <div>
                <label className="text-xs text-[#A1A1A8] block mb-1">Website (optional)</label>
                <input
                  className={inputCls}
                  placeholder="https://yourrestaurant.com"
                  value={websiteUrl}
                  onChange={e => { setWebsiteUrl(e.target.value); setRezResult(null); setRezError(null) }}
                />
              </div>
              {/* Reservation link scrape toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <div
                  className={clsx('w-9 h-5 rounded-full transition-colors relative', scrapeReservations ? 'bg-[#17C5B0]' : 'bg-[#1F1F23]')}
                  onClick={() => { setScrapeReservations(v => !v); setRezError(null) }}
                >
                  <div className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform', scrapeReservations ? 'translate-x-4' : 'translate-x-0.5')} />
                </div>
                <span className="text-xs text-[#F5F5F7]">Find my reservation link — the agent texts callers your existing booking page (OpenTable, Resy, …)</span>
              </label>
              {scrapeReservations && (
                <div className="space-y-2">
                  {rezResult ? (
                    <div className="px-3 py-2 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/25 text-xs text-[#17C5B0]">
                      Found ({rezResult.platform}): <span className="text-[#F5F5F7] break-all">{rezResult.url}</span>
                    </div>
                  ) : (
                    <button
                      onClick={runReservationScrape}
                      disabled={rezScraping}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 text-[#1A8FD6] hover:bg-[#1A8FD6]/25 disabled:opacity-50 flex items-center gap-2"
                    >
                      {rezScraping && <Loader2 size={12} className="animate-spin" />}
                      {rezScraping ? 'Scanning your website…' : 'Scan my website'}
                    </button>
                  )}
                  {rezError && <p className="text-[10px] text-amber-400/90">{rezError}</p>}
                </div>
              )}
            </div>
          </>
        )}

        {/* Step 1: Voice & Greeting */}
        {step === 1 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Voice & Greeting</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-[#A1A1A8] block mb-1">Greeting Message</label>
                <textarea className={inputCls + ' resize-none h-16'} value={cfg.greeting} onChange={e => setCfg(p => ({ ...p, greeting: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-[#A1A1A8] block mb-2">Agent Voice</label>
                <div className="grid grid-cols-2 gap-2">
                  {VOICE_OPTIONS.map(v => (
                    <div key={v.id} onClick={() => setCfg(p => ({ ...p, voice: v.id }))}
                      role="button" tabIndex={0} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setCfg(p => ({ ...p, voice: v.id })) }}
                      className={clsx('px-3 py-2 rounded-lg border text-left transition-all cursor-pointer',
                        cfg.voice === v.id ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                      <div className="flex items-center gap-1.5">
                        <Volume2 size={12} className={cfg.voice === v.id ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'} />
                        <p className={clsx('text-xs font-medium flex-1', cfg.voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                        <VoicePlayButton voiceId={v.id} isSelected={cfg.voice === v.id} />
                      </div>
                      <p className="text-[9px] text-[#A1A1A8]/60 mt-0.5">{v.desc}</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Voice preview with waveform */}
              <VoicePreviewCard
                voiceId={cfg.voice}
                businessName={cfg.businessName}
                greeting={cfg.greeting}
                settings={voiceSettings}
                onSettingsChange={setVoiceSettings}
              />

              <div>
                <label className="text-xs text-[#A1A1A8] block mb-2">Order Types</label>
                <div className="flex gap-2">
                  {['pickup', 'delivery', 'dine_in'].map(t => (
                    <button key={t} onClick={() => {
                      setCfg(p => ({ ...p, orderTypes: p.orderTypes.includes(t) ? p.orderTypes.filter(x => x !== t) : [...p.orderTypes, t] }))
                    }} className={clsx('px-3 py-1.5 rounded-lg border text-xs font-medium capitalize transition-all',
                      cfg.orderTypes.includes(t) ? 'border-[#17C5B0]/20 bg-[#17C5B0]/5 text-[#17C5B0]' : 'border-[#1F1F23] text-[#A1A1A8]')}>
                      {t.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* Step 2: Menu */}
        {step === 2 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Menu Items</h3>
            <p className="text-xs text-[#A1A1A8]">
              {posInfo && hasMenuSync ? `Menu synced from ${posInfo.name}. Edit or add items below — this is what your agent reads to callers.`
                : posInfo ? `${posInfo.name} doesn't support menu sync. Add the items your agent should take orders for.`
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
                      <span>{biz.currency}</span>
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
          </>
        )}

        {/* Step 3: Routing */}
        {step === 3 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Order Routing</h3>
            <p className="text-xs text-[#A1A1A8]">Where should confirmed orders be sent?</p>
            <div className="space-y-2">
              {posInfo && (
                <button onClick={() => setCfg(p => ({ ...p, routing: hasDirectApi ? 'pos' : 'webhook' }))}
                  className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                    (cfg.routing === 'pos' || cfg.routing === 'webhook') ? 'border-[#17C5B0]/30 bg-[#17C5B0]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                  <div className="flex items-center gap-2">
                    <p className={clsx('text-sm font-medium', (cfg.routing === 'pos' || cfg.routing === 'webhook') ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>
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
                <button onClick={() => setCfg(p => ({ ...p, routing: 'pos' }))}
                  className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                    cfg.routing === 'pos' ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                  <p className={clsx('text-sm font-medium', cfg.routing === 'pos' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>POS System</p>
                  <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">Connect your POS in Settings to enable direct order routing</p>
                </button>
              )}
              <button onClick={() => setCfg(p => ({ ...p, routing: 'sms' }))}
                className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                  cfg.routing === 'sms' ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                <p className={clsx('text-sm font-medium', cfg.routing === 'sms' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>SMS Alert</p>
                <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">Text order details to your phone for manual POS entry</p>
              </button>
              <button onClick={() => setCfg(p => ({ ...p, routing: 'email' }))}
                className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                  cfg.routing === 'email' ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                <p className={clsx('text-sm font-medium', cfg.routing === 'email' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>Email</p>
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
                placeholder="+1 555 123 4567"
                inputMode="tel"
                value={cfg.transferNumber}
                onChange={e => setCfg(p => ({ ...p, transferNumber: e.target.value }))}
              />
              {transferValid ? (
                <p className="text-[9px] text-[#A1A1A8]/50 mt-1">
                  Callers who need a person are warm-transferred here. Leave blank to disable.
                </p>
              ) : (
                <p className="text-[9px] text-red-400/80 mt-1">
                  Use international format, e.g. +14165551234.
                </p>
              )}
            </div>
          </>
        )}

        {/* Step 4: Activate */}
        {step === 4 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Ready to Activate</h3>
            <div className="space-y-2 text-xs">
              {[
                ['Business', cfg.businessName],
                ['Phone', cfg.phone],
                ['Voice', VOICE_OPTIONS.find(v => v.id === cfg.voice)?.label || ''],
                ['Menu Items', String(menu.length)],
                ['Order Routing', cfg.routing === 'pos' && posInfo ? `${posInfo.name} (Direct API)` : cfg.routing === 'webhook' && posInfo ? `${posInfo.name} (Webhook)` : cfg.routing === 'pos' ? 'POS System' : cfg.routing === 'sms' ? 'SMS Alert' : 'Email'],
                ['Order Types', cfg.orderTypes.map(t => t.replace('_', ' ')).join(', ')],
                ['Human Transfer', transferTrimmed || 'Not set'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-2 border-b border-[#1F1F23] last:border-0">
                  <span className="text-[#A1A1A8]">{label}</span>
                  <span className="text-[#F5F5F7] font-medium capitalize">{value}</span>
                </div>
              ))}
            </div>

            {/* Credit balance warning — calls are gated when the balance can't
                cover a minute, so flag an empty/low balance before activation. */}
            {balanceEmpty && (
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/5 border border-red-500/20 mt-3">
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
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 mt-3">
                <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <div className="space-y-0.5">
                  <p className="text-[11px] text-amber-200 font-medium">Low call credit balance ({balance!.balance.toLocaleString()} credits).</p>
                  <p className="text-[10px] text-amber-200/70 leading-relaxed">
                    That's only a few minutes of calls. Consider topping up from the Billing section so your line stays live.
                  </p>
                </div>
              </div>
            )}
            {zeroPricedItems.length > 0 && (
              <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-500/5 border border-amber-500/20 mt-3">
                <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
                <p className="text-[10px] text-amber-200/80 leading-relaxed">
                  {zeroPricedItems.length} menu item{zeroPricedItems.length > 1 ? 's have' : ' has'} no price set — callers won't hear a price. You can fix this in the Menu step.
                </p>
              </div>
            )}

            <div className="card p-3 border-[#17C5B0]/10 mt-3">
              <div className="flex items-start gap-2">
                <Mic size={14} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
                <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                  <span className="text-[#F5F5F7] font-medium">Powered by Meridian AI.</span>{' '}
                  Enterprise-grade voice agent included with your plan. No per-call fees.
                </p>
              </div>
            </div>
            <button onClick={() => setShowTestCall(true)}
              className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 border border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6] text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/10 transition-colors">
              <Phone size={12} /> Test Call
            </button>
          </>
        )}
      </div>

      {showTestCall && (
        <TestCallModal
          biz={{ ...biz, name: cfg.businessName, greeting: cfg.greeting, voice: cfg.voice, orderTypes: cfg.orderTypes as PhoneBizConfig['orderTypes'], menu }}
          orgId={orgId}
          onClose={() => setShowTestCall(false)}
        />
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button onClick={() => step > 0 && setStep(step - 1)} disabled={step === 0}
          className="flex items-center gap-1.5 px-4 py-2 text-sm text-[#A1A1A8] hover:text-[#F5F5F7] disabled:opacity-30 transition-colors">
          <ArrowLeft size={14} /> Back
        </button>
        {step < 4 ? (
          <button
            onClick={() => setStep(step + 1)}
            disabled={step === 3 && !transferValid}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-40 transition-colors">
            Next <ArrowRight size={14} />
          </button>
        ) : (
          <button onClick={async () => {
            if (orgId) {
              await phoneService.saveConfig({
                merchant_id: orgId,
                business_name: cfg.businessName,
                phone_number: cfg.phone,
                greeting: cfg.greeting,
                voice: cfg.voice,
                order_types: cfg.orderTypes,
                menu_items: menu.map(m => ({ name: m.name, price: m.price, category: m.category })),
                transfer_number: transferTrimmed || undefined,
                order_routing: cfg.routing,
                // Round-trip business-hours / after-hours config so reactivating
                // an existing setup preserves it. Omitted when unset (the backend
                // only writes provided fields, so nothing is wiped).
                business_hours: cfg.businessHours,
                after_hours_message: cfg.afterHoursMessage,
                active: true,
                ...(websiteUrl.trim() ? { website_url: websiteUrl.trim() } : {}),
                reservations_enabled: scrapeReservations && !!rezResult,
              })
            }
            onDone()
          }}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#17C5B0] text-white text-sm font-medium rounded-lg hover:bg-[#17C5B0]/90 transition-colors">
            <Zap size={14} /> Activate Agent
          </button>
        )}
      </div>
    </div>
  )
}
