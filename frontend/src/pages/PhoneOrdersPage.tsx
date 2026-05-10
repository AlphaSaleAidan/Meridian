import { useState, useMemo, useEffect } from 'react'
import { clsx } from 'clsx'
import {
  Phone, PhoneCall, PhoneOff, PhoneIncoming, Settings, Mic, Volume2,
  CheckCircle2, TrendingUp, MessageSquare, X, Search, ChevronRight,
  ArrowRight, ArrowLeft, Store, ListOrdered, Route, Zap, FileText,
  Clock, DollarSign, Filter,
} from 'lucide-react'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useIsDemo } from '@/hooks/useOrg'
import {
  getPhoneDemoData, getPhoneStats, VOICE_OPTIONS,
  type PhoneCallEntry, type PhoneBizConfig, type CallStatus,
} from '@/lib/phone-orders-demo-data'

const STATUS_CFG: Record<CallStatus, { label: string; color: string; bg: string; icon: typeof Phone }> = {
  order_placed: { label: 'Order Placed', color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', icon: CheckCircle2 },
  no_order: { label: 'No Order', color: 'text-[#A1A1A8]', bg: 'bg-[#A1A1A8]/10', icon: PhoneOff },
  transferred: { label: 'Transferred', color: 'text-amber-400', bg: 'bg-amber-400/10', icon: Phone },
  in_progress: { label: 'In Progress', color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', icon: PhoneCall },
}

const WIZARD_STEPS = [
  { icon: Store, label: 'Setup' },
  { icon: Mic, label: 'Voice' },
  { icon: ListOrdered, label: 'Menu' },
  { icon: Route, label: 'Routing' },
  { icon: Zap, label: 'Activate' },
]

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function fmtMoney(n: number, cur: string): string {
  return `${cur}${n.toFixed(2)}`
}

function SetupWizard({ biz, onDone }: { biz: PhoneBizConfig; onDone: () => void }) {
  const [step, setStep] = useState(0)
  const [cfg, setCfg] = useState({
    businessName: biz.name,
    phone: biz.phone,
    greeting: biz.greeting,
    voice: biz.voice,
    orderTypes: [...biz.orderTypes] as string[],
    menuPasted: false,
    routing: 'pos' as 'pos' | 'sms' | 'email',
  })

  const inputCls = 'w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50'

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-bold text-[#F5F5F7]">Phone Agent Setup</h2>
        <p className="text-xs text-[#A1A1A8] mt-1">Configure your AI phone agent in {WIZARD_STEPS.length} steps</p>
      </div>

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
                'border-[#1F1F23] text-[#A1A1A8]'
              )}>
                {done ? <CheckCircle2 size={14} /> : <Icon size={14} />}
              </div>
              <span className={clsx('text-[9px] font-medium', active ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{s.label}</span>
            </div>
          )
        })}
      </div>

      <div className="card p-5 space-y-4">
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
                <input className={inputCls} value={cfg.phone} readOnly />
                <p className="text-[9px] text-[#A1A1A8]/50 mt-1">Provisioned via Fonoster SIP trunk</p>
              </div>
            </div>
          </>
        )}

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
                    <button key={v.id} onClick={() => setCfg(p => ({ ...p, voice: v.id }))}
                      className={clsx('px-3 py-2 rounded-lg border text-left transition-all',
                        cfg.voice === v.id ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                      <div className="flex items-center gap-1.5">
                        <Volume2 size={12} className={cfg.voice === v.id ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'} />
                        <p className={clsx('text-xs font-medium', cfg.voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                      </div>
                      <p className="text-[9px] text-[#A1A1A8]/60 mt-0.5">{v.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
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

        {step === 2 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Menu Items</h3>
            <p className="text-xs text-[#A1A1A8]">Your menu has been loaded from your POS. Review below:</p>
            <div className="max-h-48 overflow-y-auto space-y-1 pr-1">
              {biz.menu.map(item => (
                <div key={item.id} className="flex items-center justify-between px-3 py-2 bg-[#111113] rounded-lg">
                  <div>
                    <p className="text-xs text-[#F5F5F7]">{item.name}</p>
                    <p className="text-[9px] text-[#A1A1A8]">{item.category}</p>
                  </div>
                  <span className="text-xs font-mono text-[#17C5B0]">{biz.currency}{item.price.toFixed(2)}</span>
                </div>
              ))}
            </div>
            {!cfg.menuPasted && (
              <button onClick={() => setCfg(p => ({ ...p, menuPasted: true }))}
                className="w-full py-2 border border-dashed border-[#1F1F23] rounded-lg text-xs text-[#A1A1A8] hover:border-[#1A8FD6]/30 hover:text-[#1A8FD6] transition-colors">
                + Paste additional items
              </button>
            )}
          </>
        )}

        {step === 3 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Order Routing</h3>
            <p className="text-xs text-[#A1A1A8]">Where should confirmed orders be sent?</p>
            <div className="space-y-2">
              {[
                { key: 'pos' as const, label: 'POS System', desc: 'Send directly to Square, Toast, or Clover' },
                { key: 'sms' as const, label: 'SMS Alert', desc: 'Text order details to your phone' },
                { key: 'email' as const, label: 'Email', desc: 'Send order confirmation via email' },
              ].map(opt => (
                <button key={opt.key} onClick={() => setCfg(p => ({ ...p, routing: opt.key }))}
                  className={clsx('w-full px-4 py-3 rounded-lg border text-left transition-all',
                    cfg.routing === opt.key ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                  <p className={clsx('text-sm font-medium', cfg.routing === opt.key ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{opt.label}</p>
                  <p className="text-[10px] text-[#A1A1A8]/60 mt-0.5">{opt.desc}</p>
                </button>
              ))}
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Ready to Activate</h3>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Business</span>
                <span className="text-[#F5F5F7] font-medium">{cfg.businessName}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Phone</span>
                <span className="text-[#F5F5F7] font-mono">{cfg.phone}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Voice</span>
                <span className="text-[#F5F5F7]">{VOICE_OPTIONS.find(v => v.id === cfg.voice)?.label}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Menu Items</span>
                <span className="text-[#F5F5F7]">{biz.menu.length}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-[#1F1F23]">
                <span className="text-[#A1A1A8]">Order Routing</span>
                <span className="text-[#F5F5F7] capitalize">{cfg.routing === 'pos' ? 'POS System' : cfg.routing}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-[#A1A1A8]">Order Types</span>
                <span className="text-[#F5F5F7] capitalize">{cfg.orderTypes.map(t => t.replace('_', ' ')).join(', ')}</span>
              </div>
            </div>
            <div className="card p-3 border-[#17C5B0]/10 mt-3">
              <div className="flex items-start gap-2">
                <Mic size={14} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
                <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                  <span className="text-[#F5F5F7] font-medium">100% self-hosted.</span>{' '}
                  Fonoster SIP + WhisperLiveKit STT + Llama 3.3 + Kokoro TTS. Only external cost: SIP trunk ~$0.004/min.
                </p>
              </div>
            </div>
          </>
        )}
      </div>

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
          <button onClick={onDone}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#17C5B0] text-white text-sm font-medium rounded-lg hover:bg-[#17C5B0]/90 transition-colors">
            <Zap size={14} /> Activate Agent
          </button>
        )}
      </div>
    </div>
  )
}

function TranscriptModal({ call, biz, onClose }: { call: PhoneCallEntry; biz: PhoneBizConfig; onClose: () => void }) {
  const sc = STATUS_CFG[call.status]
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-lg bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl max-h-[80vh] flex flex-col" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div>
            <p className="text-sm font-semibold text-[#F5F5F7]">{call.name || 'Unknown Caller'}</p>
            <p className="text-[10px] text-[#A1A1A8] font-mono">{call.phone} &middot; {call.duration} &middot; {timeAgo(call.createdAt)}</p>
          </div>
          <div className="flex items-center gap-2">
            <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full', sc.bg, sc.color)}>{sc.label}</span>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-[#1F1F23] transition-colors"><X size={16} className="text-[#A1A1A8]" /></button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
          {call.transcript.map((line, i) => (
            <div key={i} className={clsx('flex', line.speaker === 'agent' ? 'justify-start' : 'justify-end')}>
              <div className={clsx('max-w-[80%] px-3 py-2 rounded-xl', line.speaker === 'agent' ? 'bg-[#1F1F23] text-[#F5F5F7]' : 'bg-[#1A8FD6]/15 text-[#F5F5F7]')}>
                <p className="text-xs leading-relaxed">{line.text}</p>
                <p className={clsx('text-[9px] mt-1', line.speaker === 'agent' ? 'text-[#A1A1A8]/50' : 'text-[#1A8FD6]/50')}>{line.time}</p>
              </div>
            </div>
          ))}
        </div>
        {call.items.length > 0 && (
          <div className="px-5 py-3 border-t border-[#1F1F23]">
            <p className="text-[10px] text-[#A1A1A8] mb-2 font-medium">ORDER SUMMARY</p>
            {call.items.map((item, i) => (
              <div key={i} className="flex justify-between text-xs py-0.5">
                <span className="text-[#F5F5F7]">{item.qty}x {item.name}</span>
                <span className="text-[#A1A1A8] font-mono">{biz.currency}{(item.price * item.qty).toFixed(2)}</span>
              </div>
            ))}
            <div className="border-t border-[#1F1F23] mt-2 pt-2 flex justify-between text-xs">
              <span className="text-[#A1A1A8]">Subtotal</span>
              <span className="text-[#F5F5F7] font-mono">{biz.currency}{call.subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs mt-0.5">
              <span className="text-[#A1A1A8]">Tax</span>
              <span className="text-[#F5F5F7] font-mono">{biz.currency}{call.tax.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-xs mt-1 font-semibold">
              <span className="text-[#F5F5F7]">Total</span>
              <span className="text-[#17C5B0] font-mono">{biz.currency}{call.total.toFixed(2)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function OverviewTab({ calls, biz, period, setPeriod, onViewCall }: {
  calls: PhoneCallEntry[]; biz: PhoneBizConfig; period: string; setPeriod: (p: 'today' | '7d' | '30d' | '90d') => void; onViewCall: (c: PhoneCallEntry) => void
}) {
  const stats = useMemo(() => getPhoneStats(calls, period as any), [calls, period])
  const liveCalls = calls.filter(c => c.status === 'in_progress')
  const recentCalls = calls.slice(0, 8)

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        {(['today', '7d', '30d', '90d'] as const).map(p => (
          <button key={p} onClick={() => setPeriod(p)}
            className={clsx('px-3 py-1 rounded-lg text-xs font-medium transition-colors',
              period === p ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>
            {p === 'today' ? 'Today' : p}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Total Calls', value: stats.totalCalls, icon: PhoneCall, color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10' },
          { label: 'Orders Placed', value: stats.orders, icon: CheckCircle2, color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10' },
          { label: 'Conversion', value: `${stats.conversion}%`, icon: TrendingUp, color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10' },
          { label: 'Revenue', value: fmtMoney(stats.revenue, biz.currency), icon: DollarSign, color: 'text-amber-400', bg: 'bg-amber-400/10' },
        ].map(card => (
          <DashboardTiltCard key={card.label} className="card p-4">
            <div className="flex items-center gap-2">
              <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', card.bg)}>
                <card.icon size={16} className={card.color} />
              </div>
              <div>
                <p className="stat-label">{card.label}</p>
                <p className={clsx('text-lg font-bold font-mono', card.label === 'Revenue' ? 'text-amber-400' : 'text-[#F5F5F7]')}>{card.value}</p>
              </div>
            </div>
          </DashboardTiltCard>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="card p-4 border-[#1A8FD6]/10">
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
              <Mic size={16} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Open Source Stack</h3>
              <p className="text-[10px] text-[#A1A1A8] mt-1 leading-relaxed">
                Fonoster SIP &rarr; WhisperLiveKit STT &rarr; Llama 3.3 LLM &rarr; Kokoro TTS. Self-hosted, ~$0.004/min.
              </p>
            </div>
          </div>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={12} className="text-[#A1A1A8]" />
            <span className="text-[10px] text-[#A1A1A8] font-medium">AVG CALL DURATION</span>
          </div>
          <p className="text-xl font-bold text-[#F5F5F7] font-mono">
            {Math.floor(stats.avgDurationSec / 60)}:{String(stats.avgDurationSec % 60).padStart(2, '0')}
          </p>
        </div>
        <div className="card p-4">
          <div className="flex items-center gap-2 mb-2">
            <DollarSign size={12} className="text-amber-400" />
            <span className="text-[10px] text-[#A1A1A8] font-medium">AVG ORDER VALUE</span>
          </div>
          <p className="text-xl font-bold text-amber-400 font-mono">{fmtMoney(stats.avgOrder, biz.currency)}</p>
        </div>
      </div>

      {liveCalls.length > 0 && (
        <div className="card overflow-hidden border-[#17C5B0]/20">
          <div className="px-4 py-3 border-b border-[#1F1F23] flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#17C5B0] animate-pulse" />
            <span className="text-xs font-semibold text-[#17C5B0]">Live Calls</span>
          </div>
          {liveCalls.map(call => (
            <div key={call.id} className="px-4 py-3 flex items-center gap-3 border-b border-[#1F1F23] last:border-0">
              <PhoneIncoming size={14} className="text-[#17C5B0] animate-pulse" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-[#F5F5F7] font-medium truncate">{call.name || 'Incoming Call'}</p>
                <p className="text-[10px] text-[#A1A1A8] font-mono">{call.phone}</p>
              </div>
              <span className="text-[10px] font-mono text-[#17C5B0]">{call.duration}</span>
            </div>
          ))}
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-[#1F1F23] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare size={14} className="text-[#17C5B0]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Recent Calls</h3>
          </div>
        </div>
        <div className="divide-y divide-[#1F1F23]">
          {recentCalls.map(call => {
            const sc = STATUS_CFG[call.status]
            const Icon = sc.icon
            return (
              <button key={call.id} onClick={() => onViewCall(call)} className="w-full px-4 py-3 flex items-center gap-3 hover:bg-[#111113] transition-colors text-left">
                <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center', sc.bg)}>
                  <Icon size={12} className={sc.color} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[#F5F5F7] truncate">{call.name || 'Unknown'}</p>
                  <p className="text-[10px] text-[#A1A1A8] font-mono">{call.phone}</p>
                </div>
                <div className="text-right flex-shrink-0">
                  {call.total > 0 && <p className="text-xs font-mono text-amber-400">{fmtMoney(call.total, biz.currency)}</p>}
                  <p className="text-[10px] text-[#A1A1A8]">{timeAgo(call.createdAt)}</p>
                </div>
                <ChevronRight size={14} className="text-[#A1A1A8]" />
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function CallLogTab({ calls, biz, onViewCall }: { calls: PhoneCallEntry[]; biz: PhoneBizConfig; onViewCall: (c: PhoneCallEntry) => void }) {
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<CallStatus | 'all'>('all')

  const filtered = calls.filter(c => {
    if (filter !== 'all' && c.status !== filter) return false
    if (!search) return true
    const s = search.toLowerCase()
    return c.name.toLowerCase().includes(s) || c.phone.includes(s)
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]" />
          <input type="text" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/50 focus:outline-none focus:border-[#1A8FD6]/50"
            placeholder="Search calls..." />
        </div>
        <div className="flex gap-1 flex-shrink-0">
          <button onClick={() => setFilter('all')} className={clsx('px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors',
            filter === 'all' ? 'bg-[#1F1F23] text-[#F5F5F7]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>All</button>
          {(Object.keys(STATUS_CFG) as CallStatus[]).map(s => (
            <button key={s} onClick={() => setFilter(s)} className={clsx('px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors',
              filter === s ? STATUS_CFG[s].bg + ' ' + STATUS_CFG[s].color : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>
              {STATUS_CFG[s].label}
            </button>
          ))}
        </div>
      </div>

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="pm-table min-w-[650px]">
            <thead>
              <tr>
                <th className="text-left">Caller</th>
                <th className="text-left">Status</th>
                <th className="text-left">Type</th>
                <th className="text-right">Duration</th>
                <th className="text-right">Total</th>
                <th className="text-right">Time</th>
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 50).map(call => {
                const sc = STATUS_CFG[call.status]
                const Icon = sc.icon
                return (
                  <tr key={call.id} onClick={() => onViewCall(call)} className="cursor-pointer hover:bg-[#111113]">
                    <td>
                      <p className="text-[#F5F5F7] font-medium">{call.name || 'Unknown'}</p>
                      <p className="text-[10px] text-[#A1A1A8] font-mono">{call.phone}</p>
                    </td>
                    <td>
                      <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', sc.bg, sc.color)}>
                        <Icon size={10} /> {sc.label}
                      </span>
                    </td>
                    <td className="text-xs text-[#A1A1A8] capitalize">{call.orderType.replace('_', ' ')}</td>
                    <td className="text-right font-mono text-[#A1A1A8]">{call.duration}</td>
                    <td className="text-right font-mono text-[#F5F5F7]">{call.total > 0 ? fmtMoney(call.total, biz.currency) : '—'}</td>
                    <td className="text-right text-[10px] text-[#A1A1A8]">{timeAgo(call.createdAt)}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <div className="py-12 text-center text-sm text-[#A1A1A8]">{search || filter !== 'all' ? 'No calls match your filters.' : 'No calls yet.'}</div>
        )}
        {filtered.length > 50 && (
          <div className="px-4 py-3 border-t border-[#1F1F23] text-center text-[10px] text-[#A1A1A8]">Showing 50 of {filtered.length} calls</div>
        )}
      </div>
    </div>
  )
}

function SettingsTab({ biz, onReconfigure }: { biz: PhoneBizConfig; onReconfigure: () => void }) {
  const [cfg, setCfg] = useState({
    active: true,
    greeting: biz.greeting,
    voice: biz.voice,
    businessName: biz.name,
    orderTypes: [...biz.orderTypes] as string[],
  })

  return (
    <div className="space-y-4">
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
              <button key={v.id} onClick={() => setCfg(p => ({ ...p, voice: v.id }))}
                className={clsx('px-3 py-2 rounded-lg border text-left transition-all',
                  cfg.voice === v.id ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5' : 'border-[#1F1F23] hover:border-[#2A2A30]')}>
                <div className="flex items-center gap-1.5">
                  <Volume2 size={12} className={cfg.voice === v.id ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'} />
                  <p className={clsx('text-xs font-medium', cfg.voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                </div>
                <p className="text-[9px] text-[#A1A1A8]/60 mt-0.5">{v.desc}</p>
              </button>
            ))}
          </div>
        </div>
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

      <div className="card p-4 border-[#17C5B0]/10">
        <div className="flex items-start gap-3">
          <Phone size={16} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Self-Hosted Phone System</h3>
            <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
              Your phone agent runs on Meridian's self-hosted infrastructure. No third-party voice APIs &mdash; only cost is SIP trunk at ~$0.004/min.
            </p>
          </div>
        </div>
      </div>

      <button onClick={onReconfigure}
        className="w-full py-2 border border-[#1F1F23] rounded-lg text-xs text-[#A1A1A8] hover:border-[#1A8FD6]/30 hover:text-[#1A8FD6] transition-colors">
        Re-run Setup Wizard
      </button>
    </div>
  )
}

type Tab = 'overview' | 'calls' | 'settings'

export default function PhoneOrdersPage() {
  const isDemo = useIsDemo()
  const [tab, setTab] = useState<Tab>('overview')
  const [period, setPeriod] = useState<'today' | '7d' | '30d' | '90d'>('30d')
  const [selectedCall, setSelectedCall] = useState<PhoneCallEntry | null>(null)
  const [showWizard, setShowWizard] = useState(false)

  const setupKey = 'meridian_phone_setup'
  const [setupDone, setSetupDone] = useState(() => localStorage.getItem(setupKey) === '1')

  const { business, calls } = useMemo(() => getPhoneDemoData('midtown-kitchen'), [])

  function handleWizardDone() {
    localStorage.setItem(setupKey, '1')
    setSetupDone(true)
    setShowWizard(false)
  }

  if (!setupDone || showWizard) {
    return (
      <div className="space-y-6">
        <SetupWizard biz={business} onDone={handleWizardDone} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Phone Orders</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">AI phone agent &mdash; 100% open source, self-hosted</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-[#17C5B0]/10 text-[#17C5B0]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#17C5B0] animate-pulse" />
            Active
          </span>
        </div>
      </div>

      <div className="period-toggle">
        {([
          { key: 'overview' as const, label: 'Overview', icon: TrendingUp },
          { key: 'calls' as const, label: 'Call Log', icon: PhoneCall },
          { key: 'settings' as const, label: 'Settings', icon: Settings },
        ]).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={tab === t.key ? 'period-btn-active' : 'period-btn-inactive'}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab calls={calls} biz={business} period={period} setPeriod={setPeriod} onViewCall={setSelectedCall} />}
      {tab === 'calls' && <CallLogTab calls={calls} biz={business} onViewCall={setSelectedCall} />}
      {tab === 'settings' && <SettingsTab biz={business} onReconfigure={() => setShowWizard(true)} />}

      {selectedCall && <TranscriptModal call={selectedCall} biz={business} onClose={() => setSelectedCall(null)} />}
    </div>
  )
}
