import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Phone, PhoneCall, PhoneOff, Settings, Mic, Volume2,
  CheckCircle2, TrendingUp, MessageSquare,
} from 'lucide-react'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'

type Tab = 'overview' | 'calls' | 'settings'

interface CallLog {
  id: string
  callerPhone: string
  customerName: string
  status: 'order_placed' | 'no_order' | 'transferred' | 'in_progress'
  duration: string
  itemCount: number
  total: number
  createdAt: string
}

interface PhoneConfig {
  active: boolean
  phoneNumber: string
  greeting: string
  voice: string
  businessName: string
  orderTypes: string[]
}

const DEMO_CALLS: CallLog[] = [
  { id: '1', callerPhone: '+1 (416) 555-0147', customerName: 'Sarah Chen', status: 'order_placed', duration: '2:34', itemCount: 3, total: 24.97, createdAt: '2 min ago' },
  { id: '2', callerPhone: '+1 (905) 555-0233', customerName: 'Mike Johnson', status: 'order_placed', duration: '1:48', itemCount: 2, total: 18.49, createdAt: '14 min ago' },
  { id: '3', callerPhone: '+1 (647) 555-0089', customerName: '', status: 'no_order', duration: '0:32', itemCount: 0, total: 0, createdAt: '28 min ago' },
  { id: '4', callerPhone: '+1 (416) 555-0312', customerName: 'David Park', status: 'transferred', duration: '1:15', itemCount: 0, total: 0, createdAt: '1 hr ago' },
  { id: '5', callerPhone: '+1 (905) 555-0178', customerName: 'Lisa Wang', status: 'order_placed', duration: '3:02', itemCount: 5, total: 41.95, createdAt: '1.5 hr ago' },
]

const DEMO_CONFIG: PhoneConfig = {
  active: true,
  phoneNumber: '+1 (416) 555-0100',
  greeting: 'Thank you for calling! How can I help you today?',
  voice: 'af_bella',
  businessName: 'Demo Restaurant',
  orderTypes: ['pickup', 'delivery', 'dine_in'],
}

const VOICE_OPTIONS = [
  { id: 'af_bella', label: 'Bella', desc: 'Warm, professional (female)' },
  { id: 'af_sarah', label: 'Sarah', desc: 'Friendly, casual (female)' },
  { id: 'am_adam', label: 'Adam', desc: 'Authoritative (male)' },
  { id: 'am_michael', label: 'Michael', desc: 'Conversational (male)' },
]

const statusConfig = {
  order_placed: { label: 'Order Placed', color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', icon: CheckCircle2 },
  no_order: { label: 'No Order', color: 'text-[#A1A1A8]', bg: 'bg-[#A1A1A8]/10', icon: PhoneOff },
  transferred: { label: 'Transferred', color: 'text-amber-400', bg: 'bg-amber-400/10', icon: Phone },
  in_progress: { label: 'In Progress', color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', icon: PhoneCall },
}

export default function PhoneOrdersPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const [tab, setTab] = useState<Tab>('overview')
  const [config, setConfig] = useState<PhoneConfig>(DEMO_CONFIG)
  const [calls] = useState<CallLog[]>(DEMO_CALLS)

  const orderCalls = calls.filter(c => c.status === 'order_placed')
  const totalRevenue = orderCalls.reduce((s, c) => s + c.total, 0)
  const conversionRate = calls.length > 0 ? Math.round((orderCalls.length / calls.length) * 100) : 0

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Phone Orders</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              AI phone agent — 100% open source, self-hosted
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium',
              config.active ? 'bg-[#17C5B0]/10 text-[#17C5B0]' : 'bg-[#A1A1A8]/10 text-[#A1A1A8]'
            )}>
              <span className={clsx('w-1.5 h-1.5 rounded-full', config.active ? 'bg-[#17C5B0] animate-pulse' : 'bg-[#A1A1A8]')} />
              {config.active ? 'Active' : 'Inactive'}
            </span>
          </div>
        </div>
      </ScrollReveal>

      {/* Tabs */}
      <div className="period-toggle">
        {([
          { key: 'overview' as const, label: 'Overview' },
          { key: 'calls' as const, label: 'Call Log' },
          { key: 'settings' as const, label: 'Settings' },
        ]).map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={tab === t.key ? 'period-btn-active' : 'period-btn-inactive'}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && (
        <>
          <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
            <StaggerItem>
              <DashboardTiltCard className="card p-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                    <PhoneCall size={16} className="text-[#1A8FD6]" />
                  </div>
                  <div>
                    <p className="stat-label">Total Calls</p>
                    <p className="text-lg font-bold text-[#F5F5F7] font-mono">{calls.length}</p>
                  </div>
                </div>
              </DashboardTiltCard>
            </StaggerItem>
            <StaggerItem>
              <DashboardTiltCard className="card p-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                    <CheckCircle2 size={16} className="text-[#17C5B0]" />
                  </div>
                  <div>
                    <p className="stat-label">Orders</p>
                    <p className="text-lg font-bold text-[#17C5B0] font-mono">{orderCalls.length}</p>
                  </div>
                </div>
              </DashboardTiltCard>
            </StaggerItem>
            <StaggerItem>
              <DashboardTiltCard className="card p-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                    <TrendingUp size={16} className="text-[#7C5CFF]" />
                  </div>
                  <div>
                    <p className="stat-label">Conversion</p>
                    <p className="text-lg font-bold text-[#F5F5F7] font-mono">{conversionRate}%</p>
                  </div>
                </div>
              </DashboardTiltCard>
            </StaggerItem>
            <StaggerItem>
              <DashboardTiltCard className="card p-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                    <Phone size={16} className="text-amber-400" />
                  </div>
                  <div>
                    <p className="stat-label">Revenue</p>
                    <p className="text-lg font-bold text-amber-400 font-mono">${totalRevenue.toFixed(2)}</p>
                  </div>
                </div>
              </DashboardTiltCard>
            </StaggerItem>
          </StaggerContainer>

          {/* How it works */}
          <ScrollReveal variant="fadeUp" delay={0.1}>
            <div className="card p-4 border-[#1A8FD6]/10">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
                  <Mic size={16} className="text-[#1A8FD6]" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#F5F5F7]">100% Open Source Stack</h3>
                  <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                    <span className="text-[#F5F5F7] font-medium">Fonoster</span> (SIP) →
                    <span className="text-[#F5F5F7] font-medium"> WhisperLiveKit</span> (STT) →
                    <span className="text-[#F5F5F7] font-medium"> Llama 3.3</span> (LLM) →
                    <span className="text-[#F5F5F7] font-medium"> Kokoro</span> (TTS).
                    No paid APIs. Self-hosted on your infrastructure. Only cost: SIP trunk at ~$0.004/min.
                  </p>
                </div>
              </div>
            </div>
          </ScrollReveal>

          {/* Recent calls */}
          <ScrollReveal variant="fadeUp" delay={0.15}>
            <div className="card overflow-hidden">
              <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare size={14} className="text-[#17C5B0]" />
                  <h3 className="text-sm font-semibold text-[#F5F5F7]">Recent Calls</h3>
                </div>
                <button onClick={() => setTab('calls')} className="text-[10px] text-[#1A8FD6] hover:underline">View all</button>
              </div>
              <CallLogTable calls={calls.slice(0, 3)} />
            </div>
          </ScrollReveal>
        </>
      )}

      {tab === 'calls' && (
        <ScrollReveal variant="fadeUp">
          <div className="card overflow-hidden">
            <div className="px-4 sm:px-5 py-4 border-b border-[#1F1F23]">
              <div className="flex items-center gap-2">
                <PhoneCall size={14} className="text-[#1A8FD6]" />
                <h3 className="text-sm font-semibold text-[#F5F5F7]">Call Log</h3>
              </div>
              <p className="text-[10px] text-[#A1A1A8] mt-0.5">All incoming calls handled by the AI phone agent</p>
            </div>
            <CallLogTable calls={calls} />
          </div>
        </ScrollReveal>
      )}

      {tab === 'settings' && (
        <PhoneSettingsPanel config={config} onUpdate={setConfig} isDemo={isDemo} />
      )}
    </div>
  )
}

function CallLogTable({ calls }: { calls: CallLog[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="pm-table min-w-[600px]">
        <thead>
          <tr>
            <th className="text-left">Caller</th>
            <th className="text-left">Status</th>
            <th className="text-right">Duration</th>
            <th className="text-right">Items</th>
            <th className="text-right">Total</th>
            <th className="text-right">Time</th>
          </tr>
        </thead>
        <tbody>
          {calls.map(call => {
            const sc = statusConfig[call.status]
            const Icon = sc.icon
            return (
              <tr key={call.id}>
                <td>
                  <p className="text-[#F5F5F7] font-medium">{call.customerName || 'Unknown'}</p>
                  <p className="text-[10px] text-[#A1A1A8] font-mono">{call.callerPhone}</p>
                </td>
                <td>
                  <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', sc.bg, sc.color)}>
                    <Icon size={10} />
                    {sc.label}
                  </span>
                </td>
                <td className="text-right font-mono text-[#A1A1A8]">{call.duration}</td>
                <td className="text-right font-mono text-[#F5F5F7]">{call.itemCount || '—'}</td>
                <td className="text-right font-mono text-[#F5F5F7]">{call.total > 0 ? `$${call.total.toFixed(2)}` : '—'}</td>
                <td className="text-right text-[10px] text-[#A1A1A8]">{call.createdAt}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function PhoneSettingsPanel({ config, onUpdate, isDemo }: { config: PhoneConfig; onUpdate: (c: PhoneConfig) => void; isDemo: boolean }) {
  return (
    <div className="space-y-4">
      <ScrollReveal variant="fadeUp">
        <div className="card p-4 sm:p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Settings size={14} className="text-[#7C5CFF]" />
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Phone Agent Settings</h3>
            </div>
            <button
              onClick={() => onUpdate({ ...config, active: !config.active })}
              className={clsx(
                'relative w-10 h-5 rounded-full transition-colors',
                config.active ? 'bg-[#17C5B0]' : 'bg-[#2A2A30]'
              )}
            >
              <span className={clsx(
                'absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
                config.active ? 'left-5' : 'left-0.5'
              )} />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-[#A1A1A8] block mb-1">Phone Number</label>
              <input
                type="text"
                value={config.phoneNumber}
                readOnly
                className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] font-mono"
              />
              <p className="text-[9px] text-[#A1A1A8]/40 mt-1">Provisioned via Fonoster SIP trunk</p>
            </div>
            <div>
              <label className="text-xs text-[#A1A1A8] block mb-1">Business Name</label>
              <input
                type="text"
                value={config.businessName}
                onChange={e => onUpdate({ ...config, businessName: e.target.value })}
                className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50"
              />
            </div>
          </div>

          <div>
            <label className="text-xs text-[#A1A1A8] block mb-1">Greeting Message</label>
            <textarea
              value={config.greeting}
              onChange={e => onUpdate({ ...config, greeting: e.target.value })}
              rows={2}
              className="w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] focus:outline-none focus:border-[#1A8FD6]/50 resize-none"
            />
          </div>

          <div>
            <label className="text-xs text-[#A1A1A8] block mb-2">Agent Voice</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {VOICE_OPTIONS.map(v => (
                <button
                  key={v.id}
                  onClick={() => onUpdate({ ...config, voice: v.id })}
                  className={clsx(
                    'px-3 py-2 rounded-lg border text-left transition-all',
                    config.voice === v.id
                      ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5'
                      : 'border-[#1F1F23] hover:border-[#2A2A30]'
                  )}
                >
                  <div className="flex items-center gap-1.5">
                    <Volume2 size={12} className={config.voice === v.id ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]'} />
                    <p className={clsx('text-xs font-medium', config.voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                  </div>
                  <p className="text-[9px] text-[#A1A1A8]/60 mt-0.5">{v.desc}</p>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-[#A1A1A8] block mb-2">Order Types</label>
            <div className="flex flex-wrap gap-2">
              {['pickup', 'delivery', 'dine_in'].map(type => (
                <button
                  key={type}
                  onClick={() => {
                    const types = config.orderTypes.includes(type)
                      ? config.orderTypes.filter(t => t !== type)
                      : [...config.orderTypes, type]
                    onUpdate({ ...config, orderTypes: types })
                  }}
                  className={clsx(
                    'px-3 py-1.5 rounded-lg border text-xs font-medium transition-all capitalize',
                    config.orderTypes.includes(type)
                      ? 'border-[#17C5B0]/20 bg-[#17C5B0]/5 text-[#17C5B0]'
                      : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#2A2A30]'
                  )}
                >
                  {type.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
              <Phone size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Self-Hosted Phone System</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Your phone number is powered by Meridian's self-hosted infrastructure.
                No third-party voice APIs — all processing happens on your servers.
                The only external cost is the SIP trunk carrier (~$0.004/min).
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
