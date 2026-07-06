import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { ConnectReservationSystem, ORDER_TYPE_OPTIONS, hasOrderType, toggleOrderType } from './ConnectReservationSystem'
import {
  Settings, Volume2, Link2, Phone, ListOrdered, Route,
  CheckCircle2, CreditCard, SendHorizontal, MessageSquare, AlertCircle,
} from 'lucide-react'
import { VoicePlayButton, VoicePreviewCard } from './VoicePreview'
import PersonalityPanel from './PersonalityPanel'
import {
  VOICE_OPTIONS, DEFAULT_PERSONALITY,
  type PhoneBizConfig, type VoicePersonality,
} from '@/lib/phone-orders-demo-data'
import { phoneService, saveConfigErrorMessage, type PhoneConfig , type ReservationConfig } from '@/lib/phone-service'
import { posSystems } from '@/data/pos-systems'
import MenuBuildStatus from '@/components/menu/MenuBuildStatus'
import MenuPhotoScanner from '@/components/menu/MenuPhotoScanner'

const DIRECT_API_SYSTEMS = new Set(['square', 'toast', 'clover'])

// Placeholders the merchant can drop into the Text-to-Pay SMS template.
// Rendered server-side by sms_checkout._format_checkout_sms via safe replace.
const SMS_TEMPLATE_CHIPS = ['{name}', '{business}', '{total}', '{link}'] as const

interface Props {
  biz: PhoneBizConfig
  /** Persisted config row (real accounts) — hydrates fields biz doesn't carry. */
  phoneConfig?: PhoneConfig | null
  /** Deep-link to the pillar Set up segment. Omitted where the pillar doesn't exist. */
  onReconfigure?: () => void
  connectedPos: string | null
  onConnect: () => void
  orgId: string
}

export default function SettingsTab({ biz, phoneConfig, onReconfigure, connectedPos, onConnect, orgId }: Props) {
  const posInfo = connectedPos ? posSystems.find(p => p.key === connectedPos) : null
  const hasDirectApi = connectedPos ? DIRECT_API_SYSTEMS.has(connectedPos) : false
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [personality, setPersonality] = useState<VoicePersonality>({ ...DEFAULT_PERSONALITY })
  const [smsPayTemplate, setSmsPayTemplate] = useState('')
  const [cfg, setCfg] = useState({
    active: true,
    greeting: biz.greeting,
    voice: biz.voice,
    businessName: biz.name,
    orderTypes: [...biz.orderTypes] as string[],
  })

  // Hydrate the saved SMS template once the persisted config arrives.
  useEffect(() => {
    if (phoneConfig?.sms_pay_template) setSmsPayTemplate(phoneConfig.sms_pay_template)
  }, [phoneConfig?.sms_pay_template])

  // Hydrate the saved personality (defaults fill any missing fields so older
  // rows saved before a field existed still render a complete panel).
  useEffect(() => {
    if (phoneConfig?.personality) setPersonality({ ...DEFAULT_PERSONALITY, ...phoneConfig.personality })
  }, [phoneConfig?.personality])

  const [reservationConfig, setReservationConfig] = useState<ReservationConfig | null>(phoneConfig?.reservation_config ?? null)
  useEffect(() => {
    if (phoneConfig?.reservation_config) setReservationConfig(phoneConfig.reservation_config)
  }, [phoneConfig?.reservation_config])

  async function handleSave() {
    if (!orgId) return
    setSaving(true)
    setSaveError(null)
    const res = await phoneService.saveConfig({
      merchant_id: orgId,
      business_name: cfg.businessName,
      greeting: cfg.greeting,
      voice: cfg.voice,
      order_types: cfg.orderTypes,
      active: cfg.active,
      sms_pay_template: smsPayTemplate.trim() || undefined,
      personality,
    })
    setSaving(false)
    if (!res.ok) {
      setSaveError(saveConfigErrorMessage(res))
      return
    }
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-4">
      {/* Main settings card */}
      <div className="card p-4 sm:p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Settings size={14} className="text-[#7C5CFF]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Phone Agent Settings</h3>
          </div>
          <button onClick={() => setCfg(p => ({ ...p, active: !p.active }))}
            className={clsx('relative w-10 h-5 rounded-full transition-colors', cfg.active ? 'bg-[#17C5B0]' : 'bg-[#2A2A30]')}>
            <span className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform', cfg.active ? 'left-5' : 'left-0.5')} />
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="text-xs text-[#A1A1A8] block mb-1">Phone Number</label>
            <input type="text" value={biz.phone} readOnly className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] font-mono" />
          </div>
          <div>
            <label className="text-xs text-[#A1A1A8] block mb-1">Business Name</label>
            <input type="text" value={cfg.businessName} onChange={e => setCfg(p => ({ ...p, businessName: e.target.value }))}
              className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50" />
          </div>
        </div>
        <div>
          <label className="text-xs text-[#A1A1A8] block mb-1">Greeting</label>
          <textarea value={cfg.greeting} onChange={e => setCfg(p => ({ ...p, greeting: e.target.value }))} rows={2}
            className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50 resize-none" />
        </div>
        <div>
          <label className="text-xs text-[#A1A1A8] block mb-2">Agent Voice</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
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

        {/* Voice Preview with waveform — plays the real studio sample */}
        <VoicePreviewCard voiceId={cfg.voice} />

        <div>
          <label className="text-xs text-[#A1A1A8] block mb-2">Order Types</label>
          <div className="flex gap-2">
            {ORDER_TYPE_OPTIONS.map(({ value, label }) => (
              <button key={value} onClick={() => {
                setCfg(p => ({ ...p, orderTypes: toggleOrderType(p.orderTypes, value) }))
              }} className={clsx('px-3 py-1.5 rounded-lg border text-xs font-medium transition-all',
                hasOrderType(cfg.orderTypes, value) ? 'border-[#17C5B0]/20 bg-[#17C5B0]/5 text-[#17C5B0]' : 'border-[#1F1F23] text-[#A1A1A8]')}>
                {label}
              </button>
            ))}
          </div>
          {hasOrderType(cfg.orderTypes, 'reservation') && (
            <ConnectReservationSystem
              merchantId={orgId}
              config={reservationConfig}
              onSaved={setReservationConfig}
            />
          )}
        </div>
      </div>

      {/* Personality panel (NEW) */}
      <PersonalityPanel personality={personality} onChange={setPersonality} />

      {/* Phone Connection */}
      <div className="card p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-3">
          <Link2 size={14} className="text-[#1A8FD6]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Phone Connection</h3>
        </div>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-3 mb-3">
          <p className="text-[10px] text-[#A1A1A8] mb-0.5">AI Agent Number</p>
          <p className="text-sm font-mono font-medium text-[#F5F5F7]">{biz.phone}</p>
        </div>
        <button onClick={onConnect}
          className="w-full flex items-center justify-center gap-1.5 py-2 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
          <Phone size={12} /> Full Setup Instructions
        </button>
      </div>

      {/* Menu */}
      <div className="card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <ListOrdered size={14} className="text-[#1A8FD6]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Menu ({biz.menu.length} items)</h3>
        </div>
        <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
          {biz.menu.map(item => (
            <div key={item.id} className="flex items-center justify-between px-3 py-1.5 bg-[#111113] rounded-lg">
              <div>
                <p className="text-xs text-[#F5F5F7]">{item.name}</p>
                <p className="text-[9px] text-[#A1A1A8]">{item.category}</p>
              </div>
              <span className="text-xs font-mono text-[#17C5B0]">{biz.currency}{item.price.toFixed(2)}</span>
            </div>
          ))}
        </div>
        {/* Supplementary builders — scan a paper menu or import a CSV. */}
        <MenuPhotoScanner />
      </div>

      {/* Text-to-Pay — always on; merchants customize the SMS body below. */}
      <div className="card p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <CreditCard size={14} className="text-[#17C5B0]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Text-to-Pay Checkout</h3>
          </div>
          <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-[#17C5B0]/10 text-[#17C5B0]">Included</span>
        </div>
        <div className="space-y-2">
          <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
            After each phone order, the customer receives an SMS with their order confirmation and a secure payment link.
          </p>
          <div className="bg-[#111113] rounded-lg p-3 space-y-2">
            <p className="text-[10px] text-[#A1A1A8] font-medium">How it works:</p>
            <div className="flex items-start gap-2">
              <SendHorizontal size={10} className="text-[#1A8FD6] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8]">Customer calls and places an order with the AI agent</p>
            </div>
            <div className="flex items-start gap-2">
              <MessageSquare size={10} className="text-[#1A8FD6] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8]">They receive an SMS with order details and a payment link</p>
            </div>
            <div className="flex items-start gap-2">
              <CreditCard size={10} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8]">
                {posInfo ? `Payment processed through ${posInfo.name}` : 'Payment processed through your connected POS'}
              </p>
            </div>
          </div>

          {/* SMS message template */}
          <div className="pt-2">
            <label className="text-xs text-[#A1A1A8] block mb-1">SMS message</label>
            <textarea
              value={smsPayTemplate}
              onChange={e => setSmsPayTemplate(e.target.value)}
              rows={3}
              placeholder={'Hi {name}! Your order from {business} is confirmed — {total}.\nPay here: {link}'}
              className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 resize-none"
            />
            <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
              <span className="text-[9px] text-[#A1A1A8]/60">Insert:</span>
              {SMS_TEMPLATE_CHIPS.map(chip => (
                <button
                  key={chip}
                  type="button"
                  onClick={() => setSmsPayTemplate(t => (t ? `${t}${t.endsWith(' ') || t.endsWith('\n') ? '' : ' '}${chip}` : chip))}
                  className="px-1.5 py-0.5 rounded bg-[#1F1F23] text-[10px] font-mono text-[#1A8FD6] hover:bg-[#2A2A30] transition-colors"
                >
                  {chip}
                </button>
              ))}
            </div>
            <p className="text-[9px] text-[#A1A1A8]/50 mt-1">
              Leave blank to use the default message. The payment {'{link}'} is always appended if your message omits it.
            </p>
          </div>
        </div>
      </div>

      {/* Order Routing */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Route size={14} className="text-[#17C5B0]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Order Routing</h3>
        </div>
        {posInfo ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between px-3 py-2 bg-[#111113] rounded-lg">
              <div>
                <p className="text-xs text-[#F5F5F7] font-medium">{posInfo.name}</p>
                <p className="text-[9px] text-[#A1A1A8]">
                  {hasDirectApi ? 'Direct API -- orders appear in POS instantly' : 'Webhook -- orders sent within seconds'}
                </p>
              </div>
              <span className={clsx('text-[9px] px-1.5 py-0.5 rounded font-medium',
                hasDirectApi ? 'bg-[#17C5B0]/10 text-[#17C5B0]' : 'bg-[#1A8FD6]/10 text-[#1A8FD6]')}>
                {hasDirectApi ? 'Direct' : 'Webhook'}
              </span>
            </div>
          </div>
        ) : (
          <div className="px-3 py-3 bg-[#111113] rounded-lg">
            <p className="text-xs text-[#A1A1A8]">No POS connected. Orders sent via SMS/email notification.</p>
          </div>
        )}
      </div>

      {/* Auto menu-builder progress — populates from the connected POS catalog. */}
      <MenuBuildStatus />

      {/* Save + Reconfigure */}
      {saveError && (
        <div className="px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-center gap-2">
          <AlertCircle size={14} className="flex-shrink-0" /> {saveError}
        </div>
      )}
      <button onClick={handleSave} disabled={saving}
        className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
        {saving ? 'Saving...' : saved ? <><CheckCircle2 size={14} /> Saved</> : 'Save Changes'}
      </button>
      {onReconfigure && (
        <button onClick={onReconfigure}
          className="w-full py-2 border border-[#1F1F23] rounded-lg text-xs text-[#A1A1A8] hover:border-[#1A8FD6]/30 hover:text-[#1A8FD6] transition-colors">
          Re-run Setup Wizard
        </button>
      )}
    </div>
  )
}
