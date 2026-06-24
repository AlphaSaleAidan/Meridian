import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Settings, Volume2, Link2, Phone, ListOrdered, Route,
  CheckCircle2, CreditCard, SendHorizontal, MessageSquare,
} from 'lucide-react'
import { VoicePlayButton, VoicePreviewCard } from './VoicePreview'
import PersonalityPanel from './PersonalityPanel'
import {
  VOICE_OPTIONS, DEFAULT_VOICE_SETTINGS, DEFAULT_PERSONALITY,
  type PhoneBizConfig, type VoiceSettings, type VoicePersonality,
} from '@/lib/phone-orders-demo-data'
import { phoneService } from '@/lib/phone-service'
import { posSystems } from '@/data/pos-systems'
import MenuBuildStatus from '@/components/menu/MenuBuildStatus'
import MenuPhotoScanner from '@/components/menu/MenuPhotoScanner'

const DIRECT_API_SYSTEMS = new Set(['square', 'toast', 'clover'])

interface Props {
  biz: PhoneBizConfig
  onReconfigure: () => void
  connectedPos: string | null
  onConnect: () => void
  orgId: string
}

export default function SettingsTab({ biz, onReconfigure, connectedPos, onConnect, orgId }: Props) {
  const posInfo = connectedPos ? posSystems.find(p => p.key === connectedPos) : null
  const hasDirectApi = connectedPos ? DIRECT_API_SYSTEMS.has(connectedPos) : false
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>({ ...DEFAULT_VOICE_SETTINGS })
  const [personality, setPersonality] = useState<VoicePersonality>({ ...DEFAULT_PERSONALITY })
  const [cfg, setCfg] = useState({
    active: true,
    greeting: biz.greeting,
    voice: biz.voice,
    businessName: biz.name,
    orderTypes: [...biz.orderTypes] as string[],
    smsCheckout: true,
  })

  async function handleSave() {
    if (!orgId) return
    setSaving(true)
    await phoneService.saveConfig({
      merchant_id: orgId,
      business_name: cfg.businessName,
      greeting: cfg.greeting,
      voice: cfg.voice,
      order_types: cfg.orderTypes,
      active: cfg.active,
    })
    setSaving(false)
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

        {/* Voice Preview with waveform + sliders */}
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
            {['pickup', 'delivery', 'dine_in'].map(type => (
              <button key={type} onClick={() => {
                setCfg(p => ({ ...p, orderTypes: p.orderTypes.includes(type) ? p.orderTypes.filter(t => t !== type) : [...p.orderTypes, type] }))
              }} className={clsx('px-3 py-1.5 rounded-lg border text-xs font-medium transition-all capitalize',
                cfg.orderTypes.includes(type) ? 'border-[#17C5B0]/20 bg-[#17C5B0]/5 text-[#17C5B0]' : 'border-[#1F1F23] text-[#A1A1A8]')}>
                {type.replace('_', ' ')}
              </button>
            ))}
          </div>
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
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
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
      </div>

      {/* Text-to-Pay */}
      <div className="card p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <CreditCard size={14} className="text-[#17C5B0]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Text-to-Pay Checkout</h3>
          </div>
          <button onClick={() => setCfg(p => ({ ...p, smsCheckout: !p.smsCheckout }))}
            className={clsx('relative w-10 h-5 rounded-full transition-colors', cfg.smsCheckout ? 'bg-[#17C5B0]' : 'bg-[#2A2A30]')}>
            <span className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform', cfg.smsCheckout ? 'left-5' : 'left-0.5')} />
          </button>
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

      {/* Supplementary builder — scan a paper menu / specials board into the menu. */}
      <MenuPhotoScanner />

      {/* Save + Reconfigure */}
      <button onClick={handleSave} disabled={saving}
        className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
        {saving ? 'Saving...' : saved ? <><CheckCircle2 size={14} /> Saved</> : 'Save Changes'}
      </button>
      <button onClick={onReconfigure}
        className="w-full py-2 border border-[#1F1F23] rounded-lg text-xs text-[#A1A1A8] hover:border-[#1A8FD6]/30 hover:text-[#1A8FD6] transition-colors">
        Re-run Setup Wizard
      </button>
    </div>
  )
}
