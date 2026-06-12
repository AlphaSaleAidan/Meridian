import { useState, useEffect, useRef } from 'react'
import { clsx } from 'clsx'
import {
  Store, Mic, ListOrdered, Route, Zap, Volume2,
  CheckCircle2, ArrowRight, ArrowLeft, Phone, Loader2, Plus, Trash2,
} from 'lucide-react'
import { VoicePlayButton, VoicePreviewCard } from './VoicePreview'
import TestCallModal from './TestCallModal'
import {
  VOICE_OPTIONS, DEFAULT_VOICE_SETTINGS,
  type PhoneBizConfig, type VoiceSettings, type PhoneMenuItem,
} from '@/lib/phone-orders-demo-data'
import { phoneService } from '@/lib/phone-service'
import { posSystems } from '@/data/pos-systems'

const WIZARD_STEPS = [
  { icon: Store, label: 'Setup' },
  { icon: Mic, label: 'Voice' },
  { icon: ListOrdered, label: 'Menu' },
  { icon: Route, label: 'Routing' },
  { icon: Zap, label: 'Activate' },
]

const DIRECT_API_SYSTEMS = new Set(['square', 'toast', 'clover'])

interface Props {
  biz: PhoneBizConfig
  onDone: () => void
  connectedPos: string | null
  orgId: string
}

export default function SetupWizard({ biz, onDone, connectedPos, orgId }: Props) {
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
    routing: (connectedPos ? 'pos' : 'sms') as 'pos' | 'webhook' | 'sms' | 'email',
  })

  // Editable menu the agent will read back to callers. Seeded from the POS sync
  // / demo data, but the merchant can add, edit, and remove items here so a
  // self-service number takes orders against their real menu.
  const [menu, setMenu] = useState<PhoneMenuItem[]>(() => biz.menu.map(m => ({ ...m })))
  const [newItem, setNewItem] = useState({ name: '', price: '', category: '' })

  const addMenuItem = () => {
    const name = newItem.name.trim()
    const price = parseFloat(newItem.price)
    if (!name || Number.isNaN(price)) return
    setMenu(prev => [
      ...prev,
      { id: `m-${Date.now()}`, name, price, category: newItem.category.trim() || 'General' },
    ])
    setNewItem({ name: '', price: '', category: '' })
  }

  // Auto-provision a dedicated Twilio number on first mount when the merchant
  // has none yet. Backend is idempotent; the ref guards React's double-mount.
  const [provisioning, setProvisioning] = useState(false)
  const [provisionError, setProvisionError] = useState<string | null>(null)
  const provisionStarted = useRef(false)

  useEffect(() => {
    if (provisionStarted.current) return
    if (cfg.phone && cfg.phone.trim()) return
    provisionStarted.current = true
    setProvisioning(true)
    setProvisionError(null)
    phoneService
      .provisionNumber({ merchant_id: orgId, country: 'CA', business_name: cfg.businessName })
      .then(res => setCfg(p => ({ ...p, phone: res.phone_number })))
      .catch((e: unknown) => setProvisionError(e instanceof Error ? e.message : 'Could not provision a number'))
      .finally(() => setProvisioning(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const inputCls = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50'

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
                  <p className="text-[9px] text-red-400/80 mt-1">{provisionError}</p>
                ) : (
                  <p className="text-[9px] text-[#A1A1A8]/50 mt-1">
                    {cfg.phone && !provisioning ? 'Dedicated number assigned to your business' : 'Auto-provisioned for your business'}
                  </p>
                )}
              </div>
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
              {menu.map((item, idx) => (
                <div key={item.id} className="flex items-center gap-2 px-3 py-2 bg-[#111113] rounded-lg">
                  <input
                    className="flex-1 min-w-0 bg-transparent text-xs text-[#F5F5F7] focus:outline-none"
                    value={item.name}
                    aria-label="Item name"
                    onChange={e => setMenu(prev => prev.map((m, i) => i === idx ? { ...m, name: e.target.value } : m))}
                  />
                  <div className="flex items-center text-xs font-mono text-[#17C5B0]">
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
              ))}
            </div>
            <div className="flex items-center gap-2 pt-1">
              <input
                className={inputCls + ' flex-1'}
                placeholder="Item name"
                value={newItem.name}
                onChange={e => setNewItem(p => ({ ...p, name: e.target.value }))}
                onKeyDown={e => { if (e.key === 'Enter') addMenuItem() }}
              />
              <input
                className={inputCls + ' w-20'}
                placeholder="0.00"
                type="number"
                step="0.01"
                min="0"
                value={newItem.price}
                onChange={e => setNewItem(p => ({ ...p, price: e.target.value }))}
                onKeyDown={e => { if (e.key === 'Enter') addMenuItem() }}
              />
              <button
                onClick={addMenuItem}
                disabled={!newItem.name.trim() || Number.isNaN(parseFloat(newItem.price))}
                aria-label="Add menu item"
                className="flex-shrink-0 p-2 rounded-lg bg-[#1A8FD6]/10 text-[#1A8FD6] hover:bg-[#1A8FD6]/20 disabled:opacity-30 transition-colors">
                <Plus size={14} />
              </button>
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
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between py-2 border-b border-[#1F1F23] last:border-0">
                  <span className="text-[#A1A1A8]">{label}</span>
                  <span className="text-[#F5F5F7] font-medium capitalize">{value}</span>
                </div>
              ))}
            </div>
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
          <button onClick={() => setStep(step + 1)}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
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
                active: true,
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
