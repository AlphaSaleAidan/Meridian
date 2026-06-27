import { useState, useMemo, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  Phone, PhoneCall, PhoneOff, PhoneIncoming, Settings, Mic, Volume2,
  CheckCircle2, TrendingUp, MessageSquare, X, Search, ChevronRight,
  Clock, DollarSign, Link2, Copy, Info,
  CreditCard, SendHorizontal, AlertCircle, PhoneForwarded, Zap,
  Banknote, ExternalLink, ArrowRight,
} from 'lucide-react'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { useModuleFlags } from '@/config/moduleFlags'
import {
  getPhoneDemoData, getPhoneStats, VOICE_OPTIONS,
  type PhoneCallEntry, type PhoneBizConfig, type CallStatus, type PaymentStatus,
} from '@/lib/phone-orders-demo-data'
import { phoneService, type PhoneConfig } from '@/lib/phone-service'
import { getAuthHeaders } from '@/lib/supabase'
import {
  LiveCallsBanner, RecordingPlayback, SetupWizard, SettingsTab,
} from '@/components/phone'

/* ---------- Config maps ---------- */
const STATUS_CFG: Record<CallStatus, { label: string; color: string; bg: string; icon: typeof Phone }> = {
  order_placed: { label: 'Order Placed', color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', icon: CheckCircle2 },
  no_order: { label: 'No Order', color: 'text-[#A1A1A8]', bg: 'bg-[#A1A1A8]/10', icon: PhoneOff },
  transferred: { label: 'Transferred', color: 'text-amber-400', bg: 'bg-amber-400/10', icon: Phone },
  in_progress: { label: 'In Progress', color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', icon: PhoneCall },
}
const PAYMENT_CFG: Record<PaymentStatus, { label: string; color: string; bg: string; icon: typeof Phone }> = {
  paid: { label: 'Paid', color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10', icon: CheckCircle2 },
  pending: { label: 'Pending', color: 'text-amber-400', bg: 'bg-amber-400/10', icon: CreditCard },
  expired: { label: 'Expired', color: 'text-red-400', bg: 'bg-red-400/10', icon: AlertCircle },
  none: { label: '', color: '', bg: '', icon: Phone },
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

function fmtMoney(n: number, cur: string) { return `${cur}${n.toFixed(2)}` }

/* ---------- Revenue Sparkline ---------- */
function RevenueSparkline({ calls, currency }: { calls: PhoneCallEntry[]; currency: string }) {
  const points = useMemo(() => {
    const now = new Date()
    return Array.from({ length: 7 }, (_, idx) => {
      const d = 6 - idx
      const dayStart = new Date(now); dayStart.setDate(dayStart.getDate() - d); dayStart.setHours(0, 0, 0, 0)
      const dayEnd = new Date(dayStart); dayEnd.setDate(dayEnd.getDate() + 1)
      return Math.round(calls.filter(c => c.status === 'order_placed' && new Date(c.createdAt) >= dayStart && new Date(c.createdAt) < dayEnd).reduce((s, c) => s + c.total, 0) * 100) / 100
    })
  }, [calls])
  const max = Math.max(...points, 1), w = 120, h = 32, pad = 2
  const coords = points.map((v, i) => `${pad + (i / 6) * (w - pad * 2)},${h - pad - (v / max) * (h - pad * 2)}`).join(' ')
  return (
    <div className="flex items-center gap-3">
      <svg width={w} height={h} className="flex-shrink-0">
        <polyline points={coords} fill="none" stroke="#17C5B0" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((v, i) => <circle key={i} cx={pad + (i / 6) * (w - pad * 2)} cy={h - pad - (v / max) * (h - pad * 2)} r="2" fill="#17C5B0" opacity={i === 6 ? 1 : 0.5} />)}
      </svg>
      <div>
        <p className="text-[10px] text-[#A1A1A8]">7-day trend</p>
        <p className="text-xs font-mono font-medium text-[#17C5B0]">{currency}{points.reduce((a, b) => a + b, 0).toFixed(2)}</p>
      </div>
    </div>
  )
}

/* ---------- Conversion Funnel ---------- */
function ConversionFunnel({ calls }: { calls: PhoneCallEntry[] }) {
  const { total, orders, paid } = useMemo(() => ({
    total: calls.length,
    orders: calls.filter(c => c.status === 'order_placed').length,
    paid: calls.filter(c => c.paymentStatus === 'paid').length,
  }), [calls])
  if (total === 0) return null
  const orderPct = Math.round((orders / total) * 100)
  const paidPct = orders > 0 ? Math.round((paid / orders) * 100) : 0
  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3"><TrendingUp size={14} className="text-[#7C5CFF]" /><h3 className="text-sm font-semibold text-[#F5F5F7]">Conversion Funnel</h3></div>
      <div className="space-y-2.5">
        {[{ label: 'Total Calls', n: total, pct: 100, color: 'bg-[#1A8FD6]' }, { label: 'Orders Placed', n: orders, pct: orderPct, color: 'bg-[#17C5B0]' }, { label: 'Paid', n: paid, pct: Math.round((paid / Math.max(total, 1)) * 100), color: 'bg-amber-400' }].map((row, i) => (
          <div key={row.label}>
            {i > 0 && <div className="flex items-center justify-center gap-1 text-[9px] text-[#A1A1A8] mb-2"><span>{i === 1 ? `${orderPct}% converted` : `${paidPct}% paid`}</span></div>}
            <div className="flex items-center justify-between mb-1"><span className="text-[10px] text-[#A1A1A8]">{row.label}</span><span className="text-[10px] font-mono text-[#F5F5F7]">{row.n}</span></div>
            <div className="h-3 rounded-full bg-[#1F1F23] overflow-hidden"><div className={`h-full rounded-full ${row.color}`} style={{ width: `${Math.max(row.pct, 2)}%` }} /></div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ---------- Transcript Modal ---------- */
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
        <RecordingPlayback transcript={call.transcript} voiceId={biz.voice} />
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
            <div className="border-t border-[#1F1F23] mt-2 pt-2 flex justify-between text-xs font-semibold">
              <span className="text-[#F5F5F7]">Total</span>
              <span className="text-[#17C5B0] font-mono">{biz.currency}{call.total.toFixed(2)}</span>
            </div>
            {call.paymentStatus !== 'none' && (
              <div className="border-t border-[#1F1F23] mt-3 pt-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {call.smsSent && <span className="inline-flex items-center gap-1 text-[10px] text-[#1A8FD6]"><SendHorizontal size={10} /> SMS sent</span>}
                  {(() => { const pc = PAYMENT_CFG[call.paymentStatus]; return <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', pc.bg, pc.color)}><pc.icon size={10} /> {pc.label}</span> })()}
                </div>
                {call.paymentLink && call.paymentStatus === 'pending' && (
                  <button onClick={() => navigator.clipboard.writeText(call.paymentLink)} className="flex items-center gap-1 text-[10px] text-[#1A8FD6] hover:text-[#1A8FD6]/80 transition-colors"><Copy size={10} /> Copy link</button>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

/* ---------- Connect Phone Modal ---------- */
function ConnectPhoneModal({ biz, onClose }: { biz: PhoneBizConfig; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-md bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-2"><Link2 size={16} className="text-[#1A8FD6]" /><h3 className="text-sm font-semibold text-[#F5F5F7]">Connect Your Store Phone</h3></div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-[#1F1F23] transition-colors"><X size={16} className="text-[#A1A1A8]" /></button>
        </div>
        <div className="px-5 py-5 space-y-5">
          <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
            <p className="text-[10px] text-[#A1A1A8] mb-1">Your AI Agent Phone Number</p>
            <div className="flex items-center gap-2">
              <p className="text-lg font-bold font-mono text-[#F5F5F7]">{biz.phone}</p>
              <button onClick={() => { navigator.clipboard.writeText(biz.phone.replace(/[^+\d]/g, '')); setCopied(true); setTimeout(() => setCopied(false), 2000) }} className="p-1.5 rounded-lg hover:bg-[#1F1F23] transition-colors">
                {copied ? <CheckCircle2 size={14} className="text-[#17C5B0]" /> : <Copy size={14} className="text-[#A1A1A8]" />}
              </button>
            </div>
          </div>
          <div className="bg-[#17C5B0]/5 border border-[#17C5B0]/15 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info size={12} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                <span className="text-[#17C5B0] font-medium">No hardware needed.</span>{' '}Forward your store line to this number, or publish it as your dedicated order line.
              </p>
            </div>
          </div>
          <button onClick={onClose} className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">Got It</button>
        </div>
      </div>
    </div>
  )
}

/* ---------- Overview Tab ---------- */
function OverviewTab({ calls, biz, period, setPeriod, onViewCall, onConnect }: {
  calls: PhoneCallEntry[]; biz: PhoneBizConfig; period: string; setPeriod: (p: 'today' | '7d' | '30d' | '90d') => void; onViewCall: (c: PhoneCallEntry) => void; onConnect: () => void
}) {
  const stats = useMemo(() => getPhoneStats(calls, period as any), [calls, period])
  const liveCalls = calls.filter(c => c.status === 'in_progress')
  const recentCalls = calls.slice(0, 8)
  return (
    <div className="space-y-5">
      <LiveCallsBanner biz={biz} />
      <div className="flex items-center gap-2">
        {(['today', '7d', '30d', '90d'] as const).map(p => (
          <button key={p} onClick={() => setPeriod(p)} className={clsx('px-3 py-1 rounded-lg text-xs font-medium transition-colors', period === p ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>{p === 'today' ? 'Today' : p}</button>
        ))}
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-walkthrough="phone-stats">
        {[{ label: 'Total Calls', value: stats.totalCalls, icon: PhoneCall, color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10' }, { label: 'Orders Placed', value: stats.orders, icon: CheckCircle2, color: 'text-[#17C5B0]', bg: 'bg-[#17C5B0]/10' }, { label: 'Conversion', value: `${stats.conversion}%`, icon: TrendingUp, color: 'text-[#7C5CFF]', bg: 'bg-[#7C5CFF]/10' }, { label: 'Revenue', value: fmtMoney(stats.revenue, biz.currency), icon: DollarSign, color: 'text-amber-400', bg: 'bg-amber-400/10' }].map(card => (
          <DashboardTiltCard key={card.label} className="card p-4">
            <div className="flex items-center gap-2">
              <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center', card.bg)}><card.icon size={16} className={card.color} /></div>
              <div>
                <p className="stat-label">{card.label}</p>
                <p className={clsx('text-lg font-bold font-mono', card.label === 'Revenue' ? 'text-amber-400' : 'text-[#F5F5F7]')}>{card.value}</p>
                {card.label === 'Revenue' && <div className="mt-1.5"><RevenueSparkline calls={calls} currency={biz.currency} /></div>}
              </div>
            </div>
          </DashboardTiltCard>
        ))}
      </div>
      {stats.orders > 0 && (
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-center gap-2 mb-3"><CreditCard size={14} className="text-[#17C5B0]" /><h3 className="text-sm font-semibold text-[#F5F5F7]">Text-to-Pay Checkout</h3></div>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-[#111113] rounded-lg px-3 py-2"><p className="text-[10px] text-[#A1A1A8]">Collected</p><p className="text-sm font-bold text-[#17C5B0] font-mono">{fmtMoney(stats.paidRevenue, biz.currency)}</p></div>
            <div className="bg-[#111113] rounded-lg px-3 py-2"><p className="text-[10px] text-[#A1A1A8]">Pending</p><p className="text-sm font-bold text-amber-400 font-mono">{stats.pending}</p></div>
            <div className="bg-[#111113] rounded-lg px-3 py-2"><p className="text-[10px] text-[#A1A1A8]">Collection Rate</p><p className="text-sm font-bold text-[#F5F5F7] font-mono">{stats.orders > 0 ? Math.round(stats.paid / stats.orders * 100) : 0}%</p></div>
          </div>
        </div>
      )}
      <ConversionFunnel calls={calls} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="card p-4 border-[#1A8FD6]/10"><div className="flex items-start gap-2"><div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0"><Mic size={16} className="text-[#1A8FD6]" /></div><div><h3 className="text-sm font-semibold text-[#F5F5F7]">AI Voice Agent</h3><p className="text-[10px] text-[#A1A1A8] mt-1 leading-relaxed">Answers calls 24/7, takes orders conversationally. Included with your plan.</p></div></div></div>
        <div className="card p-4"><div className="flex items-center gap-2 mb-2"><Clock size={12} className="text-[#A1A1A8]" /><span className="text-[10px] text-[#A1A1A8] font-medium">AVG CALL DURATION</span></div><p className="text-xl font-bold text-[#F5F5F7] font-mono">{Math.floor(stats.avgDurationSec / 60)}:{String(stats.avgDurationSec % 60).padStart(2, '0')}</p></div>
        <div className="card p-4"><div className="flex items-center gap-2 mb-2"><DollarSign size={12} className="text-amber-400" /><span className="text-[10px] text-[#A1A1A8] font-medium">AVG ORDER VALUE</span></div><p className="text-xl font-bold text-amber-400 font-mono">{fmtMoney(stats.avgOrder, biz.currency)}</p></div>
      </div>
      {/* Recent Calls */}
      <div className="card overflow-hidden">
        <div className="px-4 py-3 border-b border-[#1F1F23] flex items-center gap-2"><MessageSquare size={14} className="text-[#17C5B0]" /><h3 className="text-sm font-semibold text-[#F5F5F7]">Recent Calls</h3></div>
        <div className="divide-y divide-[#1F1F23]">
          {recentCalls.map(call => {
            const sc = STATUS_CFG[call.status]; const Icon = sc.icon
            return (
              <button key={call.id} onClick={() => onViewCall(call)} className="w-full px-4 py-3 flex items-center gap-3 hover:bg-[#111113] transition-colors text-left">
                <div className={clsx('w-7 h-7 rounded-full flex items-center justify-center', sc.bg)}><Icon size={12} className={sc.color} /></div>
                <div className="flex-1 min-w-0"><p className="text-xs font-medium text-[#F5F5F7] truncate">{call.name || 'Unknown'}</p><p className="text-[10px] text-[#A1A1A8] font-mono">{call.phone}</p></div>
                <div className="text-right flex-shrink-0">{call.total > 0 && <p className="text-xs font-mono text-amber-400">{fmtMoney(call.total, biz.currency)}</p>}<p className="text-[10px] text-[#A1A1A8]">{timeAgo(call.createdAt)}</p></div>
                <ChevronRight size={14} className="text-[#A1A1A8]" />
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}

/* ---------- Call Log Tab ---------- */
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
          <input type="text" value={search} onChange={e => setSearch(e.target.value)} className="w-full pl-9 pr-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/50 focus:outline-none focus:border-[#1A8FD6]/50" placeholder="Search calls..." />
        </div>
        <div className="flex gap-1 flex-shrink-0">
          <button onClick={() => setFilter('all')} className={clsx('px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors', filter === 'all' ? 'bg-[#1F1F23] text-[#F5F5F7]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>All</button>
          {(Object.keys(STATUS_CFG) as CallStatus[]).map(s => (
            <button key={s} onClick={() => setFilter(s)} className={clsx('px-3 py-1.5 rounded-lg text-[10px] font-medium transition-colors', filter === s ? STATUS_CFG[s].bg + ' ' + STATUS_CFG[s].color : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>{STATUS_CFG[s].label}</button>
          ))}
        </div>
      </div>
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="pm-table min-w-[750px]">
            <thead><tr><th className="text-left">Caller</th><th className="text-left">Status</th><th className="text-left">Payment</th><th className="text-left">Type</th><th className="text-right">Duration</th><th className="text-right">Total</th><th className="text-right">Time</th></tr></thead>
            <tbody>
              {filtered.slice(0, 50).map(call => {
                const sc = STATUS_CFG[call.status]; const Icon = sc.icon
                const pc = call.paymentStatus !== 'none' ? PAYMENT_CFG[call.paymentStatus] : null
                return (
                  <tr key={call.id} onClick={() => onViewCall(call)} className="cursor-pointer hover:bg-[#111113]">
                    <td><p className="text-[#F5F5F7] font-medium">{call.name || 'Unknown'}</p><p className="text-[10px] text-[#A1A1A8] font-mono">{call.phone}</p></td>
                    <td><span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', sc.bg, sc.color)}><Icon size={10} /> {sc.label}</span></td>
                    <td>{pc ? <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', pc.bg, pc.color)}><pc.icon size={10} /> {pc.label}</span> : <span className="text-[10px] text-[#A1A1A8]/40">&mdash;</span>}</td>
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
        {filtered.length === 0 && <div className="py-12 text-center text-sm text-[#A1A1A8]">{search || filter !== 'all' ? 'No calls match your filters.' : 'No calls yet.'}</div>}
        {filtered.length > 50 && <div className="px-4 py-3 border-t border-[#1F1F23] text-center text-[10px] text-[#A1A1A8]">Showing 50 of {filtered.length} calls</div>}
      </div>
    </div>
  )
}

/* ---------- Text Ordering Tab ---------- */
function TextOrderingTab({ biz, isDemo }: { biz: PhoneBizConfig; isDemo: boolean }) {
  const [enabled, setEnabled] = useState(true)
  const smsNumber = biz.phone || '+1 (212) 555-2024'
  const DEMO_SMS = [
    { from: 'customer', text: "Hi, I'd like to place an order" },
    { from: 'business', text: `Welcome to ${biz.name}! Text 'menu' to see our full menu.` },
    { from: 'customer', text: 'menu' },
    { from: 'business', text: `${biz.menu.slice(0, 4).map(m => `  ${m.name} -- ${biz.currency}${m.price.toFixed(2)}`).join('\n')}\n\nText what you'd like to order!` },
    { from: 'customer', text: `I'll have the ${biz.menu[0]?.name || 'special'}` },
    { from: 'business', text: `Got it! 1x ${biz.menu[0]?.name} (${biz.currency}${biz.menu[0]?.price.toFixed(2)}). Anything else?` },
    { from: 'customer', text: "That's it" },
    { from: 'business', text: `Order confirmed! Total: ${biz.currency}${((biz.menu[0]?.price || 0) * (1 + biz.taxRate)).toFixed(2)} with tax.\n\nPay here: pay.meridian.ai/checkout/demo` },
  ]
  return (
    <div className="space-y-5">
      <div className="card p-5 border-[#7C5CFF]/15">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-[#7C5CFF]/10 flex items-center justify-center flex-shrink-0"><MessageSquare size={20} className="text-[#7C5CFF]" /></div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-[#F5F5F7]">Text-to-Order</h2>
            <p className="text-xs text-[#A1A1A8] mt-1">Let customers text your number to place an order and pay.</p>
          </div>
          <button onClick={() => setEnabled(!enabled)} className={clsx('relative w-11 h-6 rounded-full transition-colors flex-shrink-0 mt-1', enabled ? 'bg-[#7C5CFF]' : 'bg-[#2A2A2E]')}>
            <span className={clsx('absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform', enabled ? 'left-[22px]' : 'left-0.5')} />
          </button>
        </div>
      </div>
      {enabled && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <div className="card p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2"><Settings size={14} className="text-[#A1A1A8]" /> Configuration</h3>
            <div>
              <label className="text-[10px] text-[#A1A1A8] uppercase tracking-wider">SMS Number</label>
              <div className="mt-1 flex items-center gap-2">
                <input type="text" value={smsNumber} readOnly className="flex-1 px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] font-mono" />
                <button onClick={() => navigator.clipboard?.writeText(smsNumber.replace(/[^+\d]/g, ''))} className="p-2 bg-[#1F1F23] rounded-lg hover:bg-[#2A2A2E] transition-colors"><Copy size={14} className="text-[#A1A1A8]" /></button>
              </div>
            </div>
          </div>
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2 mb-4"><MessageSquare size={14} className="text-[#7C5CFF]" /> Live Preview</h3>
            <div className="bg-[#0A0A0B] rounded-xl p-3 max-h-[420px] overflow-y-auto space-y-2">
              <div className="text-center pb-2 border-b border-[#1F1F23] mb-2"><p className="text-xs font-medium text-[#F5F5F7]">{biz.name}</p></div>
              {DEMO_SMS.map((msg, i) => (
                <div key={i} className={clsx('flex', msg.from === 'customer' ? 'justify-end' : 'justify-start')}>
                  <div className={clsx('max-w-[80%] px-3 py-2 rounded-2xl text-xs whitespace-pre-line', msg.from === 'customer' ? 'bg-[#7C5CFF] text-white rounded-br-md' : 'bg-[#1F1F23] text-[#F5F5F7] rounded-bl-md')}>{msg.text}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* ---------- Money-flow fee constants ---------- */
const MERIDIAN_FEE = 2.50          // flat per order
const STRIPE_PCT   = 0.029         // 2.9 %
const STRIPE_FIXED = 0.30          // + $0.30 per transaction

function calcSplit(total: number): { meridianFee: number; stripeFee: number; net: number } {
  const stripeFee = Math.round((total * STRIPE_PCT + STRIPE_FIXED) * 100) / 100
  const net       = Math.round((total - MERIDIAN_FEE - stripeFee) * 100) / 100
  return { meridianFee: MERIDIAN_FEE, stripeFee, net }
}

/* ---------- Get Paid Tab ---------- */
function GetPaidTab({ calls, biz, orgId, isDemo }: {
  calls: PhoneCallEntry[]
  biz: PhoneBizConfig
  orgId: string
  isDemo: boolean
}) {
  const apiBase = (import.meta.env.VITE_API_URL || '') as string
  const [connectStatus, setConnectStatus] = useState<'loading' | 'connected' | 'not_connected' | 'error'>('loading')
  const [connectLoading, setConnectLoading] = useState(false)

  const orderCalls = calls.filter(c => c.status === 'order_placed' && c.total > 0)

  useEffect(() => {
    if (isDemo) { setConnectStatus('not_connected'); return }
    if (!orgId) { setConnectStatus('not_connected'); return }
    fetch(`${apiBase}/api/stripe/connect/status/${orgId}`, {})
      .then(r => r.ok ? (r.json() as Promise<{ connected: boolean }>) : null)
      .then(data => { setConnectStatus(data?.connected ? 'connected' : 'not_connected') })
      .catch(() => setConnectStatus('not_connected'))
  }, [orgId, isDemo, apiBase])

  async function handleConnect() {
    if (isDemo || connectLoading) return
    setConnectLoading(true)
    try {
      const headers = await getAuthHeaders()
      const res = await fetch(`${apiBase}/api/stripe/connect/onboard/${orgId}`, {
        method: 'POST',
        headers: { ...headers, 'Content-Type': 'application/json' },
      })
      if (res.ok) {
        const data = (await res.json()) as { onboarding_url?: string }
        if (data.onboarding_url) { window.location.href = data.onboarding_url }
      }
    } catch { /* noop — leave status as-is */ }
    finally { setConnectLoading(false) }
  }

  const totals = useMemo(() => orderCalls.reduce(
    (acc, c) => {
      const { meridianFee, stripeFee, net } = calcSplit(c.total)
      return {
        gross:        acc.gross + c.total,
        meridianFees: acc.meridianFees + meridianFee,
        stripeFees:   acc.stripeFees + stripeFee,
        net:          acc.net + net,
        paid:         acc.paid + (c.paymentStatus === 'paid' ? 1 : 0),
        total:        acc.total + 1,
      }
    },
    { gross: 0, meridianFees: 0, stripeFees: 0, net: 0, paid: 0, total: 0 },
  ), [orderCalls])

  return (
    <div className="space-y-5">

      {/* ── Connect Stripe card ── */}
      <div className={clsx('card p-5', connectStatus === 'connected' ? 'border-[#17C5B0]/20' : 'border-[#1A8FD6]/15')}>
        <div className="flex items-start gap-4">
          <div className={clsx('w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0', connectStatus === 'connected' ? 'bg-[#17C5B0]/10' : 'bg-[#1A8FD6]/10')}>
            <Banknote size={20} className={connectStatus === 'connected' ? 'text-[#17C5B0]' : 'text-[#1A8FD6]'} />
          </div>
          <div className="flex-1 min-w-0">
            {connectStatus === 'connected' ? (
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-[#F5F5F7]">Payouts connected</h2>
                  <CheckCircle2 size={14} className="text-[#17C5B0]" />
                </div>
                <p className="text-xs text-[#A1A1A8] mt-1">Your Stripe account is linked — earnings are deposited daily.</p>
              </div>
            ) : (
              <div>
                <h2 className="text-base font-bold text-[#F5F5F7]">Connect to get paid</h2>
                <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                  Link your bank account via Stripe Connect (uses Plaid) to receive daily payouts of your net revenue.
                  Your earnings are deposited automatically after each completed order.
                </p>
              </div>
            )}
          </div>
          {connectStatus !== 'connected' && (
            <button
              onClick={isDemo ? undefined : handleConnect}
              disabled={connectLoading || isDemo}
              className={clsx(
                'flex-shrink-0 flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                isDemo
                  ? 'bg-[#1A8FD6]/30 text-[#1A8FD6]/60 cursor-not-allowed'
                  : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90',
              )}
            >
              {connectLoading
                ? <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                : <ExternalLink size={14} />
              }
              {connectLoading ? 'Redirecting…' : 'Connect payouts'}
            </button>
          )}
        </div>
        {connectStatus !== 'connected' && (
          <div className="mt-4 bg-[#111113] border border-[#1F1F23] rounded-lg px-4 py-3 flex items-start gap-2">
            <Info size={12} className="text-[#A1A1A8] mt-0.5 flex-shrink-0" />
            <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
              Long AI calls (&gt;3 min) add <strong className="text-[#F5F5F7]">$0.45/min</strong> billed separately.
              Stripe processing is ~2.9% + $0.30 per transaction. Meridian charges a flat $2.50 service fee per order.
            </p>
          </div>
        )}
      </div>

      {/* ── Totals summary ── */}
      {totals.total > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[
            { label: 'Gross Collected',    value: fmtMoney(totals.gross, biz.currency),        color: 'text-amber-400' },
            { label: 'Meridian Fees',      value: `−${fmtMoney(totals.meridianFees, biz.currency)}`, color: 'text-red-400' },
            { label: 'Stripe Fees (est.)', value: `−${fmtMoney(totals.stripeFees, biz.currency)}`,   color: 'text-red-400' },
            { label: 'You Receive',        value: fmtMoney(Math.max(totals.net, 0), biz.currency),   color: 'text-[#17C5B0]' },
          ].map(card => (
            <div key={card.label} className="card px-4 py-3">
              <p className="text-[10px] text-[#A1A1A8]">{card.label}</p>
              <p className={clsx('text-lg font-bold font-mono mt-0.5', card.color)}>{card.value}</p>
            </div>
          ))}
        </div>
      )}
      {totals.total > 0 && (
        <p className="text-[10px] text-[#A1A1A8]">
          {totals.paid} of {totals.total} order{totals.total !== 1 ? 's' : ''} paid &middot;
          Stripe fees are estimated (2.9% + $0.30). Long AI calls (&gt;3 min) add $0.45/min billed separately.
        </p>
      )}

      {/* ── Per-order table ── */}
      {orderCalls.length === 0 ? (
        <div className="card py-14 text-center">
          <DollarSign size={28} className="text-[#1F1F23] mx-auto mb-3" />
          <p className="text-sm font-medium text-[#A1A1A8]">No completed orders yet</p>
          <p className="text-[10px] text-[#A1A1A8]/60 mt-1">Revenue from phone orders will appear here once customers place and pay.</p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="px-4 py-3 border-b border-[#1F1F23] flex items-center gap-2">
            <DollarSign size={14} className="text-amber-400" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Order Money Flow</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="pm-table min-w-[700px]">
              <thead>
                <tr>
                  <th className="text-left">Order</th>
                  <th className="text-right">Customer Pays</th>
                  <th className="text-right">−Meridian Fee</th>
                  <th className="text-right">−Stripe Fee</th>
                  <th className="text-right">You Receive</th>
                  <th className="text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {orderCalls.slice(0, 50).map(call => {
                  const { meridianFee, stripeFee, net } = calcSplit(call.total)
                  const pc = call.paymentStatus !== 'none' ? PAYMENT_CFG[call.paymentStatus] : null
                  return (
                    <tr key={call.id}>
                      <td>
                        <p className="text-[#F5F5F7] font-medium">{call.name || 'Unknown'}</p>
                        <p className="text-[10px] text-[#A1A1A8] font-mono">{timeAgo(call.createdAt)}</p>
                      </td>
                      <td className="text-right font-mono text-amber-400">{fmtMoney(call.total, biz.currency)}</td>
                      <td className="text-right font-mono text-red-400">−{fmtMoney(meridianFee, biz.currency)}</td>
                      <td className="text-right font-mono text-red-400">−{fmtMoney(stripeFee, biz.currency)}</td>
                      <td className="text-right font-mono text-[#17C5B0] font-semibold">{net > 0 ? fmtMoney(net, biz.currency) : '—'}</td>
                      <td>
                        {pc
                          ? <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', pc.bg, pc.color)}><pc.icon size={10} /> {pc.label}</span>
                          : <span className="text-[10px] text-[#A1A1A8]/40">—</span>
                        }
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {orderCalls.length > 50 && (
            <div className="px-4 py-3 border-t border-[#1F1F23] text-center text-[10px] text-[#A1A1A8]">
              Showing 50 of {orderCalls.length} orders
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-[10px] text-[#A1A1A8]">
        <span className="flex items-center gap-1"><ArrowRight size={10} className="text-amber-400" /> Customer pays full order total</span>
        <span className="flex items-center gap-1"><ArrowRight size={10} className="text-red-400" /> Meridian flat fee: $2.50/order</span>
        <span className="flex items-center gap-1"><ArrowRight size={10} className="text-red-400" /> Stripe processing: ~2.9% + $0.30</span>
        <span className="flex items-center gap-1"><ArrowRight size={10} className="text-[#17C5B0]" /> Net deposited to your account</span>
      </div>
    </div>
  )
}

/* ========== Main Page ========== */
type Tab = 'overview' | 'calls' | 'text_orders' | 'get_paid' | 'settings'

export default function PhoneOrdersPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const flags = useModuleFlags()
  const [tab, setTab] = useState<Tab>('overview')
  const [period, setPeriod] = useState<'today' | '7d' | '30d' | '90d'>('30d')
  const [selectedCall, setSelectedCall] = useState<PhoneCallEntry | null>(null)
  const [showWizard, setShowWizard] = useState(false)
  const [showConnect, setShowConnect] = useState(false)
  const [realCalls, setRealCalls] = useState<PhoneCallEntry[] | null>(null)
  const [phoneConfig, setPhoneConfig] = useState<PhoneConfig | null>(null)

  const connectedPos = org?.pos_provider || null
  const setupKey = 'meridian_phone_setup'
  const [setupDone, setSetupDone] = useState(() => isDemo || localStorage.getItem(setupKey) === '1')

  const demoData = useMemo(() => getPhoneDemoData('midtown-kitchen'), [])

  useEffect(() => {
    if (!orgId || isDemo) return
    phoneService.getConfig(orgId).then(cfg => { setPhoneConfig(cfg); if (cfg.exists && cfg.active) setSetupDone(true) })
    phoneService.getCalls(orgId).then(c => setRealCalls(c))
  }, [orgId, isDemo])

  const business: PhoneBizConfig = useMemo(() => {
    const cad = typeof window !== 'undefined' && window.location.pathname.startsWith('/canada')
    const currency = cad ? 'CA$' : '$'
    if (!isDemo && phoneConfig?.exists) return { id: phoneConfig.merchant_id, name: phoneConfig.business_name || org?.business_name || 'My Business', vertical: phoneConfig.business_type || 'restaurant', country: 'US' as const, currency, taxRate: 0.08, phone: phoneConfig.phone_number || '', greeting: phoneConfig.greeting || '', voice: phoneConfig.voice || 'af_bella', orderTypes: (phoneConfig.order_types || ['pickup', 'delivery']) as any, menu: (phoneConfig.menu_items || []).map((m: any, i: number) => ({ id: m.id || `item-${i}`, name: m.name || '', price: m.price || 0, category: m.category || 'General' })) }
    if (!isDemo) return { id: orgId || '', name: org?.business_name || 'My Business', vertical: 'restaurant', country: 'US' as const, currency, taxRate: 0.08, phone: '', greeting: '', voice: 'af_bella', orderTypes: ['pickup', 'delivery'] as any, menu: [] }
    return demoData.business
  }, [phoneConfig, demoData.business, org?.business_name, isDemo, orgId])

  const calls = isDemo ? demoData.calls : (realCalls ?? [])

  const handleWizardDone = useCallback(async () => {
    localStorage.setItem(setupKey, '1')
    setSetupDone(true)
    setShowWizard(false)
    if (orgId && !isDemo) phoneService.getConfig(orgId).then(setPhoneConfig)
  }, [orgId, isDemo])

  if (!setupDone || showWizard) {
    return (
      <div className="space-y-6">
        {!showWizard && (
          <div className="card p-5 border-[#17C5B0]/10">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0"><Phone size={20} className="text-[#17C5B0]" /></div>
              <div><h2 className="text-sm font-semibold text-[#F5F5F7]">Welcome to Phone Orders</h2><p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">Set up your AI phone agent in under 2 minutes.</p></div>
            </div>
          </div>
        )}
        <SetupWizard biz={business} onDone={handleWizardDone} connectedPos={connectedPos} orgId={orgId} existingConfig={phoneConfig?.exists ? phoneConfig : undefined} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div><h1 className="text-2xl font-bold text-[#F5F5F7]">Phone Orders</h1><p className="text-sm text-[#A1A1A8] mt-1">AI-powered phone ordering for your business</p></div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowConnect(true)} className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors"><Phone size={14} /> Connect Phone</button>
          <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-[#17C5B0]/10 text-[#17C5B0]"><span className="w-1.5 h-1.5 rounded-full bg-[#17C5B0] animate-pulse" />Active</span>
        </div>
      </div>
      <div className="period-toggle">
        {([
          { key: 'overview' as const, label: 'Overview' },
          { key: 'calls' as const, label: 'Call Log' },
          ...(flags.textToOrder ? [{ key: 'text_orders' as const, label: 'Text Orders' }] : []),
          { key: 'get_paid' as const, label: 'Get Paid' },
          { key: 'settings' as const, label: 'Settings' },
        ]).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} className={tab === t.key ? 'period-btn-active' : 'period-btn-inactive'}>{t.label}</button>
        ))}
      </div>
      {tab === 'overview' && <OverviewTab calls={calls} biz={business} period={period} setPeriod={setPeriod} onViewCall={setSelectedCall} onConnect={() => setShowConnect(true)} />}
      {tab === 'calls' && <CallLogTab calls={calls} biz={business} onViewCall={setSelectedCall} />}
      {tab === 'text_orders' && flags.textToOrder && <TextOrderingTab biz={business} isDemo={isDemo} />}
      {tab === 'get_paid' && <GetPaidTab calls={calls} biz={business} orgId={orgId} isDemo={isDemo} />}
      {tab === 'settings' && <SettingsTab biz={business} onReconfigure={() => setShowWizard(true)} connectedPos={connectedPos} onConnect={() => setShowConnect(true)} orgId={orgId} />}
      {selectedCall && <TranscriptModal call={selectedCall} biz={business} onClose={() => setSelectedCall(null)} />}
      {showConnect && <ConnectPhoneModal biz={business} onClose={() => setShowConnect(false)} />}
    </div>
  )
}
