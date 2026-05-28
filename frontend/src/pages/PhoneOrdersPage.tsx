import { useState, useMemo, useEffect, useCallback, useRef } from 'react'
import { clsx } from 'clsx'
import {
  Phone, PhoneCall, PhoneOff, PhoneIncoming, Settings, Mic, Volume2,
  CheckCircle2, TrendingUp, MessageSquare, X, Search, ChevronRight,
  ArrowRight, ArrowLeft, Store, ListOrdered, Route, Zap,
  Clock, DollarSign, Link2, Copy, Info, Play, Square, Pause,
  CreditCard, SendHorizontal, AlertCircle, PhoneForwarded,
} from 'lucide-react'
import DashboardTiltCard from '@/components/DashboardTiltCard'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import { posSystems } from '@/data/pos-systems'
import {
  getPhoneDemoData, getPhoneStats, VOICE_OPTIONS,
  type PhoneCallEntry, type PhoneBizConfig, type CallStatus, type PaymentStatus,
} from '@/lib/phone-orders-demo-data'
import { phoneService, type PhoneConfig } from '@/lib/phone-service'

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

/* ---------- inline CSS for waveform + pulse animations ---------- */
const ANIM_STYLE_ID = 'phone-orders-anims'
function ensureAnimStyles() {
  if (typeof document === 'undefined') return
  if (document.getElementById(ANIM_STYLE_ID)) return
  const style = document.createElement('style')
  style.id = ANIM_STYLE_ID
  style.textContent = `
    @keyframes waveBar {
      0%, 100% { height: 4px; }
      50% { height: 16px; }
    }
    .wave-bar { animation: waveBar 1.2s ease-in-out infinite; }
    .wave-bar:nth-child(2) { animation-delay: 0.15s; }
    .wave-bar:nth-child(3) { animation-delay: 0.3s; }
    .wave-bar:nth-child(4) { animation-delay: 0.45s; }
    .wave-bar:nth-child(5) { animation-delay: 0.6s; }
    .wave-bar:nth-child(6) { animation-delay: 0.75s; }
    .wave-bar:nth-child(7) { animation-delay: 0.9s; }
    .wave-bar:nth-child(8) { animation-delay: 1.05s; }
    @keyframes livePulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(23,197,176,0.4); }
      50% { box-shadow: 0 0 0 6px rgba(23,197,176,0); }
    }
    .live-pulse-ring { animation: livePulse 2s ease-in-out infinite; }
    @keyframes testCallRing {
      0%, 100% { transform: rotate(0deg); }
      10% { transform: rotate(15deg); }
      20% { transform: rotate(-15deg); }
      30% { transform: rotate(10deg); }
      40% { transform: rotate(-10deg); }
      50% { transform: rotate(0deg); }
    }
    .test-call-ring { animation: testCallRing 1.5s ease-in-out infinite; }
  `
  document.head.appendChild(style)
}

/* ---------- Live Calls Banner ---------- */
function LiveCallsBanner() {
  const [activeCalls, setActiveCalls] = useState(() => Math.random() < 0.5 ? 1 : 0)

  useEffect(() => {
    ensureAnimStyles()
    const interval = setInterval(() => {
      setActiveCalls(Math.random() < 0.4 ? 1 : 0)
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={clsx(
      'flex items-center gap-2.5 px-4 py-2.5 rounded-lg border transition-colors',
      activeCalls > 0
        ? 'bg-[#17C5B0]/5 border-[#17C5B0]/20'
        : 'bg-[#111113] border-[#1F1F23]'
    )}>
      <div className="relative flex items-center justify-center">
        <span className={clsx(
          'w-2.5 h-2.5 rounded-full',
          activeCalls > 0 ? 'bg-[#17C5B0] live-pulse-ring' : 'bg-[#A1A1A8]/40'
        )} />
      </div>
      <span className={clsx(
        'text-xs font-medium',
        activeCalls > 0 ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'
      )}>
        {activeCalls > 0
          ? `${activeCalls} active call`
          : 'No active calls'}
      </span>
      {activeCalls > 0 && (
        <PhoneCall size={12} className="text-[#17C5B0] animate-pulse ml-auto" />
      )}
    </div>
  )
}

/* ---------- Revenue Sparkline (7-day SVG) ---------- */
function RevenueSparkline({ calls, currency }: { calls: PhoneCallEntry[]; currency: string }) {
  const points = useMemo(() => {
    const now = new Date()
    const buckets: number[] = []
    for (let d = 6; d >= 0; d--) {
      const dayStart = new Date(now)
      dayStart.setDate(dayStart.getDate() - d)
      dayStart.setHours(0, 0, 0, 0)
      const dayEnd = new Date(dayStart)
      dayEnd.setDate(dayEnd.getDate() + 1)
      const dayRev = calls
        .filter(c => c.status === 'order_placed' && new Date(c.createdAt) >= dayStart && new Date(c.createdAt) < dayEnd)
        .reduce((s, c) => s + c.total, 0)
      buckets.push(Math.round(dayRev * 100) / 100)
    }
    return buckets
  }, [calls])

  const max = Math.max(...points, 1)
  const w = 120
  const h = 32
  const pad = 2
  const coords = points.map((v, i) => {
    const x = pad + (i / 6) * (w - pad * 2)
    const y = h - pad - (v / max) * (h - pad * 2)
    return `${x},${y}`
  })
  const polyline = coords.join(' ')
  const total7d = points.reduce((a, b) => a + b, 0)

  return (
    <div className="flex items-center gap-3">
      <svg width={w} height={h} className="flex-shrink-0">
        <polyline
          points={polyline}
          fill="none"
          stroke="#17C5B0"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {points.map((v, i) => {
          const x = pad + (i / 6) * (w - pad * 2)
          const y = h - pad - (v / max) * (h - pad * 2)
          return <circle key={i} cx={x} cy={y} r="2" fill="#17C5B0" opacity={i === 6 ? 1 : 0.5} />
        })}
      </svg>
      <div>
        <p className="text-[10px] text-[#A1A1A8]">7-day trend</p>
        <p className="text-xs font-mono font-medium text-[#17C5B0]">{currency}{total7d.toFixed(2)}</p>
      </div>
    </div>
  )
}

/* ---------- Conversion Funnel ---------- */
function ConversionFunnel({ calls }: { calls: PhoneCallEntry[] }) {
  const data = useMemo(() => {
    const total = calls.length
    const orders = calls.filter(c => c.status === 'order_placed').length
    const paid = calls.filter(c => c.paymentStatus === 'paid').length
    return { total, orders, paid }
  }, [calls])

  if (data.total === 0) return null

  const orderPct = Math.round((data.orders / data.total) * 100)
  const paidPct = data.orders > 0 ? Math.round((data.paid / data.orders) * 100) : 0
  const maxWidth = 100

  return (
    <div className="card p-4">
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp size={14} className="text-[#7C5CFF]" />
        <h3 className="text-sm font-semibold text-[#F5F5F7]">Conversion Funnel</h3>
      </div>
      <div className="space-y-2.5">
        {/* Total Calls */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-[#A1A1A8]">Total Calls</span>
            <span className="text-[10px] font-mono text-[#F5F5F7]">{data.total}</span>
          </div>
          <div className="h-3 rounded-full bg-[#1F1F23] overflow-hidden">
            <div className="h-full rounded-full bg-[#1A8FD6]" style={{ width: `${maxWidth}%` }} />
          </div>
        </div>
        {/* Arrow + percentage */}
        <div className="flex items-center justify-center gap-1 text-[9px] text-[#A1A1A8]">
          <ArrowRight size={10} className="text-[#A1A1A8]/50" />
          <span>{orderPct}% converted</span>
        </div>
        {/* Orders Placed */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-[#A1A1A8]">Orders Placed</span>
            <span className="text-[10px] font-mono text-[#F5F5F7]">{data.orders}</span>
          </div>
          <div className="h-3 rounded-full bg-[#1F1F23] overflow-hidden">
            <div className="h-full rounded-full bg-[#17C5B0]" style={{ width: `${Math.max(orderPct, 2)}%` }} />
          </div>
        </div>
        {/* Arrow + percentage */}
        <div className="flex items-center justify-center gap-1 text-[9px] text-[#A1A1A8]">
          <ArrowRight size={10} className="text-[#A1A1A8]/50" />
          <span>{paidPct}% paid</span>
        </div>
        {/* Paid */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-[#A1A1A8]">Paid</span>
            <span className="text-[10px] font-mono text-[#F5F5F7]">{data.paid}</span>
          </div>
          <div className="h-3 rounded-full bg-[#1F1F23] overflow-hidden">
            <div className="h-full rounded-full bg-amber-400" style={{ width: `${Math.max((data.paid / Math.max(data.total, 1)) * 100, 2)}%` }} />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---------- Recording Playback (waveform + SpeechSynthesis) ---------- */
function RecordingPlayback({ transcript, voiceId }: { transcript: { speaker: string; text: string; time: string }[]; voiceId?: string }) {
  const [playing, setPlaying] = useState(false)

  useEffect(() => { ensureAnimStyles() }, [])

  function handleToggle() {
    if (playing) {
      window.speechSynthesis.cancel()
      setPlaying(false)
      return
    }
    const agentLine = transcript.find(l => l.speaker === 'agent')
    if (!agentLine) return
    const utter = new SpeechSynthesisUtterance(agentLine.text)
    utter.rate = 0.95
    utter.pitch = 1.05
    const voices = window.speechSynthesis.getVoices()
    const sample = voiceId ? VOICE_SAMPLES[voiceId] : undefined
    if (sample) {
      utter.pitch = sample.pitch
      utter.rate = sample.rate
    }
    const isFemale = voiceId?.startsWith('af_')
    const preferred = voices.find(v =>
      isFemale
        ? /samantha|karen|victoria|zira|female/i.test(v.name)
        : /daniel|alex|david|male|mark/i.test(v.name)
    )
    if (preferred) utter.voice = preferred
    utter.onend = () => setPlaying(false)
    utter.onerror = () => setPlaying(false)
    setPlaying(true)
    window.speechSynthesis.speak(utter)
  }

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-[#111113] border-t border-[#1F1F23]">
      <button
        onClick={handleToggle}
        className={clsx(
          'w-8 h-8 rounded-full flex items-center justify-center transition-all flex-shrink-0',
          playing ? 'bg-[#17C5B0] text-white' : 'bg-[#1A8FD6]/15 text-[#1A8FD6] hover:bg-[#1A8FD6]/25'
        )}
      >
        {playing ? <Pause size={12} /> : <Play size={12} fill="currentColor" />}
      </button>
      <div className="flex items-end gap-[3px] h-5 flex-1">
        {Array.from({ length: 8 }).map((_, i) => (
          <div
            key={i}
            className={clsx(
              'w-[3px] rounded-full transition-all',
              playing ? 'wave-bar bg-[#17C5B0]' : 'bg-[#1F1F23]'
            )}
            style={{ height: playing ? undefined : `${4 + Math.random() * 12}px` }}
          />
        ))}
      </div>
      <span className="text-[10px] text-[#A1A1A8] flex-shrink-0">
        {playing ? 'Playing...' : 'Play Recording'}
      </span>
    </div>
  )
}

/* ---------- Test Call Modal ---------- */
function TestCallModal({ biz, onClose }: { biz: PhoneBizConfig; onClose: () => void }) {
  const [elapsed, setElapsed] = useState(0)
  const [phase, setPhase] = useState<'ringing' | 'active' | 'ended'>('ringing')
  const [visibleLines, setVisibleLines] = useState<{ speaker: string; text: string }[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const speechRef = useRef(false)

  const testTranscript = useMemo(() => [
    { speaker: 'agent', text: biz.greeting },
    { speaker: 'caller', text: "Hi, I'd like to place an order for pickup." },
    { speaker: 'agent', text: 'Of course! What would you like?' },
    { speaker: 'caller', text: `I'll have the ${biz.menu[0]?.name || 'special'}, please.` },
    { speaker: 'agent', text: `Got it! ${biz.menu[0]?.name || 'That item'} coming right up. Anything else?` },
    { speaker: 'caller', text: "That's everything." },
    { speaker: 'agent', text: `Your order will be ready in about 15 minutes. Thank you for calling ${biz.name}!` },
  ], [biz])

  useEffect(() => {
    ensureAnimStyles()
    // auto-answer after 2 seconds
    const answerTimeout = setTimeout(() => {
      setPhase('active')
    }, 2000)
    return () => clearTimeout(answerTimeout)
  }, [])

  useEffect(() => {
    if (phase !== 'active') return
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [phase])

  // Reveal transcript lines one at a time
  useEffect(() => {
    if (phase !== 'active') return
    let lineIdx = 0
    const revealInterval = setInterval(() => {
      if (lineIdx >= testTranscript.length) {
        clearInterval(revealInterval)
        return
      }
      const line = testTranscript[lineIdx]
      setVisibleLines(prev => [...prev, line])

      // Speak agent lines
      if (line.speaker === 'agent' && !speechRef.current) {
        const utter = new SpeechSynthesisUtterance(line.text)
        utter.rate = 0.95
        utter.pitch = 1.05
        const sample = VOICE_SAMPLES[biz.voice]
        if (sample) { utter.pitch = sample.pitch; utter.rate = sample.rate }
        const voices = window.speechSynthesis.getVoices()
        const isFemale = biz.voice.startsWith('af_')
        const preferred = voices.find(v =>
          isFemale
            ? /samantha|karen|victoria|zira|female/i.test(v.name)
            : /daniel|alex|david|male|mark/i.test(v.name)
        )
        if (preferred) utter.voice = preferred
        window.speechSynthesis.speak(utter)
      }

      lineIdx++
    }, 3000)

    return () => {
      clearInterval(revealInterval)
      window.speechSynthesis.cancel()
    }
  }, [phase, testTranscript, biz.voice])

  function handleHangUp() {
    window.speechSynthesis.cancel()
    if (timerRef.current) clearInterval(timerRef.current)
    setPhase('ended')
    setTimeout(onClose, 600)
  }

  const fmtElapsed = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={handleHangUp}>
      <div className="w-full max-w-sm bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="px-5 py-4 text-center border-b border-[#1F1F23]">
          {phase === 'ringing' && (
            <>
              <div className="w-14 h-14 mx-auto rounded-full bg-[#17C5B0]/10 flex items-center justify-center mb-3 live-pulse-ring">
                <PhoneForwarded size={24} className="text-[#17C5B0] test-call-ring" />
              </div>
              <p className="text-sm font-semibold text-[#F5F5F7]">Incoming Test Call</p>
              <p className="text-[10px] text-[#A1A1A8] font-mono mt-1">{biz.phone}</p>
              <p className="text-xs text-[#17C5B0] mt-2 animate-pulse">Ringing...</p>
            </>
          )}
          {phase === 'active' && (
            <>
              <div className="w-14 h-14 mx-auto rounded-full bg-[#17C5B0]/10 flex items-center justify-center mb-3">
                <PhoneCall size={24} className="text-[#17C5B0]" />
              </div>
              <p className="text-sm font-semibold text-[#F5F5F7]">Test Call Active</p>
              <p className="text-lg font-mono font-bold text-[#17C5B0] mt-1">{fmtElapsed}</p>
            </>
          )}
          {phase === 'ended' && (
            <>
              <div className="w-14 h-14 mx-auto rounded-full bg-[#A1A1A8]/10 flex items-center justify-center mb-3">
                <PhoneOff size={24} className="text-[#A1A1A8]" />
              </div>
              <p className="text-sm font-semibold text-[#A1A1A8]">Call Ended</p>
              <p className="text-[10px] font-mono text-[#A1A1A8] mt-1">{fmtElapsed}</p>
            </>
          )}
        </div>

        {/* Transcript area */}
        {phase === 'active' && visibleLines.length > 0 && (
          <div className="px-4 py-3 max-h-52 overflow-y-auto space-y-2">
            {visibleLines.map((line, i) => (
              <div key={i} className={clsx('flex', line.speaker === 'agent' ? 'justify-start' : 'justify-end')}>
                <div className={clsx(
                  'max-w-[85%] px-3 py-1.5 rounded-xl text-xs',
                  line.speaker === 'agent' ? 'bg-[#1F1F23] text-[#F5F5F7]' : 'bg-[#1A8FD6]/15 text-[#F5F5F7]'
                )}>
                  {line.text}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Waveform */}
        {phase === 'active' && (
          <div className="flex items-end justify-center gap-[3px] h-6 px-4 pb-2">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="w-[3px] rounded-full bg-[#17C5B0] wave-bar" />
            ))}
          </div>
        )}

        {/* Hang Up */}
        {phase !== 'ended' && (
          <div className="px-5 py-4 border-t border-[#1F1F23] flex justify-center">
            <button
              onClick={handleHangUp}
              className="flex items-center gap-2 px-6 py-2.5 bg-red-500/90 text-white text-xs font-medium rounded-full hover:bg-red-500 transition-colors"
            >
              <PhoneOff size={14} /> Hang Up
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

const DIRECT_API_SYSTEMS = new Set(['square', 'toast', 'clover'])

const VOICE_SAMPLES: Record<string, { text: string; pitch: number; rate: number }> = {
  af_bella: { text: "Thank you for calling! I'd be happy to help you place an order today.", pitch: 1.1, rate: 0.95 },
  af_sarah: { text: "Hey there! Welcome in — what can I get started for you?", pitch: 1.2, rate: 1.05 },
  am_adam: { text: "Good evening. I'll take your order whenever you're ready.", pitch: 0.8, rate: 0.9 },
  am_michael: { text: "Hi! Thanks for calling — let me know what sounds good to you.", pitch: 0.95, rate: 1.0 },
}

function VoicePlayButton({ voiceId, isSelected }: { voiceId: string; isSelected: boolean }) {
  const [playing, setPlaying] = useState(false)

  function handlePlay(e: React.MouseEvent) {
    e.stopPropagation()
    if (playing) {
      window.speechSynthesis.cancel()
      setPlaying(false)
      return
    }
    window.speechSynthesis.cancel()
    const sample = VOICE_SAMPLES[voiceId]
    if (!sample) return
    const utter = new SpeechSynthesisUtterance(sample.text)
    utter.pitch = sample.pitch
    utter.rate = sample.rate
    const voices = window.speechSynthesis.getVoices()
    const isFemale = voiceId.startsWith('af_')
    const preferred = voices.find(v =>
      isFemale
        ? /samantha|karen|victoria|zira|female/i.test(v.name)
        : /daniel|alex|david|male|mark/i.test(v.name)
    )
    if (preferred) utter.voice = preferred
    utter.onend = () => setPlaying(false)
    utter.onerror = () => setPlaying(false)
    setPlaying(true)
    window.speechSynthesis.speak(utter)
  }

  return (
    <button onClick={handlePlay}
      className={clsx(
        'w-6 h-6 rounded-full flex items-center justify-center transition-all flex-shrink-0',
        playing
          ? 'bg-[#1A8FD6] text-white'
          : isSelected ? 'bg-[#1A8FD6]/15 text-[#1A8FD6] hover:bg-[#1A8FD6]/25' : 'bg-[#1F1F23] text-[#A1A1A8] hover:bg-[#2A2A30]'
      )}
      title={playing ? 'Stop' : 'Preview voice'}>
      {playing ? <Square size={8} fill="currentColor" /> : <Play size={10} fill="currentColor" />}
    </button>
  )
}

function SetupWizard({ biz, onDone, connectedPos, orgId }: { biz: PhoneBizConfig; onDone: () => void; connectedPos: string | null; orgId: string }) {
  const [step, setStep] = useState(0)
  const [showTestCall, setShowTestCall] = useState(false)
  const posInfo = connectedPos ? posSystems.find(p => p.key === connectedPos) : null
  const hasDirectApi = connectedPos ? DIRECT_API_SYSTEMS.has(connectedPos) : false
  const hasMenuSync = posInfo?.dataAvailable?.menuItems ?? false

  const [cfg, setCfg] = useState({
    businessName: biz.name,
    phone: biz.phone,
    greeting: biz.greeting,
    voice: biz.voice,
    orderTypes: [...biz.orderTypes] as string[],
    menuPasted: false,
    routing: (connectedPos ? 'pos' : 'sms') as 'pos' | 'webhook' | 'sms' | 'email',
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
                <p className="text-[9px] text-[#A1A1A8]/50 mt-1">Auto-provisioned for your business</p>
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
                        <p className={clsx('text-xs font-medium flex-1', cfg.voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                        <VoicePlayButton voiceId={v.id} isSelected={cfg.voice === v.id} />
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
            <p className="text-xs text-[#A1A1A8]">
              {posInfo && hasMenuSync
                ? `Menu synced from ${posInfo.name}. Review below:`
                : posInfo
                  ? `${posInfo.name} doesn't support menu sync. Add items manually or paste below:`
                  : 'No POS connected. Add your menu items below:'}
            </p>
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
                    {hasDirectApi
                      ? `Orders sent directly to ${posInfo.name} via API — appears in your POS instantly`
                      : `Orders sent via webhook to ${posInfo.name} — appears in your POS within seconds`}
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
            {posInfo && !hasDirectApi && (
              <div className="card p-3 border-[#1A8FD6]/10 mt-2">
                <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                  <span className="text-[#F5F5F7] font-medium">How it works:</span>{' '}
                  Orders are sent to {posInfo.name} via webhook. If the webhook is unavailable,
                  orders are saved to your Meridian dashboard and you're notified via SMS for manual entry.
                  All 80+ POS systems are supported.
                </p>
              </div>
            )}
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
                <span className="text-[#F5F5F7]">
                  {cfg.routing === 'pos' && posInfo ? `${posInfo.name} (Direct API)` :
                   cfg.routing === 'webhook' && posInfo ? `${posInfo.name} (Webhook)` :
                   cfg.routing === 'pos' ? 'POS System' :
                   cfg.routing === 'sms' ? 'SMS Alert' : 'Email'}
                </span>
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
                  <span className="text-[#F5F5F7] font-medium">Powered by Meridian AI.</span>{' '}
                  Enterprise-grade voice agent included with your plan. No per-call fees.
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowTestCall(true)}
              className="w-full mt-3 flex items-center justify-center gap-2 py-2.5 border border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6] text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/10 transition-colors"
            >
              <Phone size={12} /> Test Call
            </button>
          </>
        )}
      </div>

      {showTestCall && <TestCallModal biz={biz} onClose={() => setShowTestCall(false)} />}

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
            {call.paymentStatus !== 'none' && (
              <div className="border-t border-[#1F1F23] mt-3 pt-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {call.smsSent && (
                      <span className="inline-flex items-center gap-1 text-[10px] text-[#1A8FD6]">
                        <SendHorizontal size={10} /> SMS sent
                      </span>
                    )}
                    {(() => {
                      const pc = PAYMENT_CFG[call.paymentStatus]
                      return (
                        <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', pc.bg, pc.color)}>
                          <pc.icon size={10} /> {pc.label}
                        </span>
                      )
                    })()}
                  </div>
                  {call.paymentLink && call.paymentStatus === 'pending' && (
                    <button onClick={() => navigator.clipboard.writeText(call.paymentLink)}
                      className="flex items-center gap-1 text-[10px] text-[#1A8FD6] hover:text-[#1A8FD6]/80 transition-colors">
                      <Copy size={10} /> Copy link
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function OverviewTab({ calls, biz, period, setPeriod, onViewCall, onConnect }: {
  calls: PhoneCallEntry[]; biz: PhoneBizConfig; period: string; setPeriod: (p: 'today' | '7d' | '30d' | '90d') => void; onViewCall: (c: PhoneCallEntry) => void; onConnect: () => void
}) {
  const stats = useMemo(() => getPhoneStats(calls, period as any), [calls, period])
  const liveCalls = calls.filter(c => c.status === 'in_progress')
  const recentCalls = calls.slice(0, 8)

  return (
    <div className="space-y-5">
      <LiveCallsBanner />

      <div className="flex items-center gap-2">
        {(['today', '7d', '30d', '90d'] as const).map(p => (
          <button key={p} onClick={() => setPeriod(p)}
            className={clsx('px-3 py-1 rounded-lg text-xs font-medium transition-colors',
              period === p ? 'bg-[#1A8FD6]/10 text-[#1A8FD6]' : 'text-[#A1A1A8] hover:text-[#F5F5F7]')}>
            {p === 'today' ? 'Today' : p}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-walkthrough="phone-stats">
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
                {card.label === 'Revenue' && (
                  <div className="mt-1.5">
                    <RevenueSparkline calls={calls} currency={biz.currency} />
                  </div>
                )}
              </div>
            </div>
          </DashboardTiltCard>
        ))}
      </div>

      {stats.orders > 0 && (
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-center gap-2 mb-3">
            <CreditCard size={14} className="text-[#17C5B0]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Text-to-Pay Checkout</h3>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-[#111113] rounded-lg px-3 py-2">
              <p className="text-[10px] text-[#A1A1A8]">Collected</p>
              <p className="text-sm font-bold text-[#17C5B0] font-mono">{fmtMoney(stats.paidRevenue, biz.currency)}</p>
              <p className="text-[9px] text-[#A1A1A8]/60">{stats.paid} paid</p>
            </div>
            <div className="bg-[#111113] rounded-lg px-3 py-2">
              <p className="text-[10px] text-[#A1A1A8]">Pending</p>
              <p className="text-sm font-bold text-amber-400 font-mono">{stats.pending}</p>
              <p className="text-[9px] text-[#A1A1A8]/60">awaiting payment</p>
            </div>
            <div className="bg-[#111113] rounded-lg px-3 py-2">
              <p className="text-[10px] text-[#A1A1A8]">Collection Rate</p>
              <p className="text-sm font-bold text-[#F5F5F7] font-mono">{stats.orders > 0 ? Math.round(stats.paid / stats.orders * 100) : 0}%</p>
              <p className="text-[9px] text-[#A1A1A8]/60">of orders paid</p>
            </div>
          </div>
        </div>
      )}

      <ConversionFunnel calls={calls} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <div className="card p-4 border-[#1A8FD6]/10">
          <div className="flex items-start gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
              <Mic size={16} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">AI Voice Agent</h3>
              <p className="text-[10px] text-[#A1A1A8] mt-1 leading-relaxed">
                Answers calls 24/7, takes orders conversationally, and routes them to your POS. Included with your plan.
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

      <PhoneSetupCard biz={biz} onConnect={onConnect} />

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
          <table className="pm-table min-w-[750px]">
            <thead>
              <tr>
                <th className="text-left">Caller</th>
                <th className="text-left">Status</th>
                <th className="text-left">Payment</th>
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
                const pc = call.paymentStatus !== 'none' ? PAYMENT_CFG[call.paymentStatus] : null
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
                    <td>
                      {pc ? (
                        <span className={clsx('inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full', pc.bg, pc.color)}>
                          <pc.icon size={10} /> {pc.label}
                        </span>
                      ) : (
                        <span className="text-[10px] text-[#A1A1A8]/40">—</span>
                      )}
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

function SettingsTab({ biz, onReconfigure, connectedPos, onConnect, orgId }: { biz: PhoneBizConfig; onReconfigure: () => void; connectedPos: string | null; onConnect: () => void; orgId: string }) {
  const posInfo = connectedPos ? posSystems.find(p => p.key === connectedPos) : null
  const hasDirectApi = connectedPos ? DIRECT_API_SYSTEMS.has(connectedPos) : false
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
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
                  <p className={clsx('text-xs font-medium flex-1', cfg.voice === v.id ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]')}>{v.label}</p>
                  <VoicePlayButton voiceId={v.id} isSelected={cfg.voice === v.id} />
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

      <div className="card p-4 sm:p-5">
        <div className="flex items-center gap-2 mb-3">
          <Link2 size={14} className="text-[#1A8FD6]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Phone Connection</h3>
        </div>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-3 mb-3">
          <p className="text-[10px] text-[#A1A1A8] mb-0.5">AI Agent Number</p>
          <p className="text-sm font-mono font-medium text-[#F5F5F7]">{biz.phone}</p>
        </div>
        <div className="space-y-2 mb-3">
          <div className="flex items-start gap-2">
            <div className="w-4 h-4 rounded-full bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-[8px] font-bold text-[#1A8FD6]">1</span>
            </div>
            <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
              <span className="text-[#F5F5F7] font-medium">Forward your store line</span> to this number, or publish it as your dedicated order line on Google, your website, and in-store signage.
            </p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-4 h-4 rounded-full bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
              <span className="text-[8px] font-bold text-[#1A8FD6]">2</span>
            </div>
            <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
              <span className="text-[#F5F5F7] font-medium">Test it</span> &mdash; call the number from your cell phone. The AI agent will greet you and take a test order.
            </p>
          </div>
        </div>
        <button onClick={onConnect}
          className="w-full flex items-center justify-center gap-1.5 py-2 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
          <Phone size={12} /> Full Setup Instructions
        </button>
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
            After each phone order, the customer receives an SMS with their order confirmation and a secure payment link from your POS system.
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
                {posInfo
                  ? `Payment is processed through ${posInfo.name} — funds go directly to your account`
                  : 'Payment is processed through your connected POS — funds go directly to your account'}
              </p>
            </div>
          </div>
          {!posInfo && (
            <p className="text-[10px] text-amber-400/80">
              Connect a POS system to enable direct payment processing. Without a POS, customers pay via Meridian-hosted checkout.
            </p>
          )}
        </div>
      </div>

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
                  {hasDirectApi ? 'Direct API — orders appear in POS instantly' : 'Webhook — orders sent within seconds'}
                </p>
              </div>
              <span className={clsx('text-[9px] px-1.5 py-0.5 rounded font-medium',
                hasDirectApi ? 'bg-[#17C5B0]/10 text-[#17C5B0]' : 'bg-[#1A8FD6]/10 text-[#1A8FD6]')}>
                {hasDirectApi ? 'Direct' : 'Webhook'}
              </span>
            </div>
            <p className="text-[10px] text-[#A1A1A8]/60 px-1">
              Fallback: orders saved to Meridian dashboard + SMS notification if POS is unreachable
            </p>
          </div>
        ) : (
          <div className="px-3 py-3 bg-[#111113] rounded-lg">
            <p className="text-xs text-[#A1A1A8]">No POS connected. Orders will be sent via SMS/email notification.</p>
            <p className="text-[10px] text-[#1A8FD6] mt-1">Connect a POS in merchant settings for direct order routing.</p>
          </div>
        )}
      </div>

      <div className="card p-4 border-[#17C5B0]/10">
        <div className="flex items-start gap-3">
          <Phone size={16} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Meridian AI Phone Agent</h3>
            <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
              Your phone agent answers calls 24/7, takes orders, and routes them directly to your POS. Included with your Meridian plan.
            </p>
          </div>
        </div>
      </div>

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

function ConnectPhoneModal({ biz, onClose }: { biz: PhoneBizConfig; onClose: () => void }) {
  const [copied, setCopied] = useState(false)
  function copyNumber() {
    navigator.clipboard.writeText(biz.phone.replace(/[^+\d]/g, ''))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" onClick={onClose}>
      <div className="w-full max-w-md bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-2">
            <Link2 size={16} className="text-[#1A8FD6]" />
            <h3 className="text-sm font-semibold text-[#F5F5F7]">Connect Your Store Phone</h3>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-[#1F1F23] transition-colors"><X size={16} className="text-[#A1A1A8]" /></button>
        </div>
        <div className="px-5 py-5 space-y-5">
          <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
            <p className="text-[10px] text-[#A1A1A8] mb-1">Your AI Agent Phone Number</p>
            <div className="flex items-center gap-2">
              <p className="text-lg font-bold font-mono text-[#F5F5F7]">{biz.phone}</p>
              <button onClick={copyNumber} className="p-1.5 rounded-lg hover:bg-[#1F1F23] transition-colors">
                {copied ? <CheckCircle2 size={14} className="text-[#17C5B0]" /> : <Copy size={14} className="text-[#A1A1A8]" />}
              </button>
            </div>
            <p className="text-[9px] text-[#A1A1A8]/60 mt-1">Auto-provisioned for your business</p>
          </div>

          <div>
            <h4 className="text-xs font-semibold text-[#F5F5F7] mb-3">How to connect your store phone</h4>
            <div className="space-y-3">
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-[10px] font-bold text-[#1A8FD6]">1</span>
                </div>
                <div>
                  <p className="text-xs text-[#F5F5F7] font-medium">Set up call forwarding</p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5 leading-relaxed">
                    Forward your store's main phone line to the number above. Most carriers support this &mdash; dial *72 + the number, or set it in your phone system's admin panel.
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-[10px] font-bold text-[#1A8FD6]">2</span>
                </div>
                <div>
                  <p className="text-xs text-[#F5F5F7] font-medium">Or use as a dedicated order line</p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5 leading-relaxed">
                    Publish the AI number as your ordering line on Google Business, your website, and signage. Keep your main line for other calls.
                  </p>
                </div>
              </div>
              <div className="flex gap-3">
                <div className="w-6 h-6 rounded-full bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center flex-shrink-0">
                  <span className="text-[10px] font-bold text-[#1A8FD6]">3</span>
                </div>
                <div>
                  <p className="text-xs text-[#F5F5F7] font-medium">Test with a quick call</p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5 leading-relaxed">
                    Call the number from your cell phone to hear the AI agent greet you and take a test order. Orders appear in the dashboard instantly.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-[#17C5B0]/5 border border-[#17C5B0]/15 rounded-lg p-3">
            <div className="flex items-start gap-2">
              <Info size={12} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
              <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
                <span className="text-[#17C5B0] font-medium">No hardware needed.</span>{' '}
                The AI agent answers calls 24/7. It greets callers, takes orders, reads back totals, and sends orders to your POS automatically. Calls that need a human are transferred to your staff number.
              </p>
            </div>
          </div>

          <button onClick={onClose} className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
            Got It
          </button>
        </div>
      </div>
    </div>
  )
}

function PhoneSetupCard({ biz, onConnect }: { biz: PhoneBizConfig; onConnect: () => void }) {
  return (
    <div className="card p-4 border-[#1A8FD6]/15">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
          <Link2 size={16} className="text-[#1A8FD6]" />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Connect Your Store Phone</h3>
          <p className="text-[10px] text-[#A1A1A8] mt-1 leading-relaxed">
            Forward your store number to <span className="text-[#F5F5F7] font-mono font-medium">{biz.phone}</span> or publish it as your order line. The AI agent answers calls, takes orders, and routes them to your POS.
          </p>
          <button onClick={onConnect}
            className="mt-2 flex items-center gap-1.5 px-3 py-1.5 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
            <Phone size={12} /> Setup Instructions
          </button>
        </div>
      </div>
    </div>
  )
}

/* ---------- Text Ordering Tab ---------- */
const DEMO_SMS_CONVO = [
  { from: 'customer', text: "Hi, I'd like to place an order" },
  { from: 'business', text: "Welcome to The Midtown Kitchen! 🍽️ What can I get for you? Text 'menu' to see our full menu." },
  { from: 'customer', text: 'menu' },
  { from: 'business', text: "📋 The Midtown Kitchen Menu\n\nMains:\n  Grilled Salmon — $24.99\n  Chicken Parm — $19.99\n  Truffle Burger — $18.99\n\nStarters:\n  Caesar Salad — $12.99\n  Calamari — $13.99\n\nSides:\n  Truffle Fries — $8.99\n\nText what you'd like to order!" },
  { from: 'customer', text: 'I\'ll have the truffle burger and truffle fries' },
  { from: 'business', text: "Got it! 1x Truffle Burger ($18.99) and 1x Truffle Fries ($8.99). Anything else?" },
  { from: 'customer', text: "That's it" },
  { from: 'business', text: "Your total is $30.46 with tax. What's your name, and is this pickup or delivery?" },
  { from: 'customer', text: 'Sarah, pickup' },
  { from: 'business', text: "Order confirmed, Sarah! 🎉\n\n  1x Truffle Burger — $18.99\n  1x Truffle Fries — $8.99\n\nTotal: $30.46 (pickup)\n\nPay here: pay.meridian.ai/checkout/mk-0-1\n\nYour order will be ready in 15-20 min.\n\nThank you! — The Midtown Kitchen" },
]

function TextOrderingTab({ biz, isDemo }: { biz: PhoneBizConfig; isDemo: boolean }) {
  const [enabled, setEnabled] = useState(true)
  const [smsNumber, setSmsNumber] = useState(biz.phone || '+1 (212) 555-2024')
  const [showConvo, setShowConvo] = useState(true)

  return (
    <div className="space-y-5">
      {/* Text-to-Order Header */}
      <div className="card p-5 border-[#7C5CFF]/15">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-[#7C5CFF]/10 flex items-center justify-center flex-shrink-0">
            <MessageSquare size={20} className="text-[#7C5CFF]" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-[#F5F5F7]">Text-to-Order</h2>
            <p className="text-xs text-[#A1A1A8] mt-1">
              Let customers text your number to place an order and pay — no phone call needed.
              AI handles the conversation, builds the order, and sends a payment link.
            </p>
          </div>
          <button
            onClick={() => setEnabled(!enabled)}
            className={clsx(
              'relative w-11 h-6 rounded-full transition-colors flex-shrink-0 mt-1',
              enabled ? 'bg-[#7C5CFF]' : 'bg-[#2A2A2E]'
            )}
          >
            <span className={clsx(
              'absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform',
              enabled ? 'left-[22px]' : 'left-0.5'
            )} />
          </button>
        </div>
      </div>

      {enabled && (
        <>
          {/* How It Works */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              { step: '1', title: 'Customer Texts', desc: 'They text your number with their order or "menu" to browse', icon: SendHorizontal },
              { step: '2', title: 'AI Builds Order', desc: 'Our AI guides them through the menu and confirms their order', icon: MessageSquare },
              { step: '3', title: 'Pay & Pickup', desc: 'They get a payment link via text. Pay, pick up, done.', icon: CreditCard },
            ].map(s => (
              <div key={s.step} className="card p-4">
                <div className="flex items-center gap-2.5 mb-2">
                  <span className="w-6 h-6 rounded-full bg-[#7C5CFF]/10 flex items-center justify-center text-[10px] font-bold text-[#7C5CFF]">{s.step}</span>
                  <s.icon size={14} className="text-[#7C5CFF]" />
                  <span className="text-sm font-semibold text-[#F5F5F7]">{s.title}</span>
                </div>
                <p className="text-[10px] text-[#A1A1A8] leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>

          {/* Configuration */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Settings */}
            <div className="card p-5 space-y-4">
              <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
                <Settings size={14} className="text-[#A1A1A8]" /> Configuration
              </h3>

              <div>
                <label className="text-[10px] text-[#A1A1A8] uppercase tracking-wider">SMS Number</label>
                <div className="mt-1 flex items-center gap-2">
                  <input
                    type="text"
                    value={smsNumber}
                    onChange={e => setSmsNumber(e.target.value)}
                    disabled={isDemo}
                    className="flex-1 px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] font-mono disabled:opacity-50"
                  />
                  <button
                    onClick={() => navigator.clipboard?.writeText(smsNumber.replace(/[^+\d]/g, ''))}
                    className="p-2 bg-[#1F1F23] rounded-lg hover:bg-[#2A2A2E] transition-colors"
                    title="Copy number"
                  >
                    <Copy size={14} className="text-[#A1A1A8]" />
                  </button>
                </div>
                <p className="text-[10px] text-[#A1A1A8] mt-1">
                  This is the number customers text to place orders.
                  Same Twilio number as your phone ordering line.
                </p>
              </div>

              <div className="pt-2 border-t border-[#1F1F23]">
                <label className="text-[10px] text-[#A1A1A8] uppercase tracking-wider">Welcome Message</label>
                <textarea
                  rows={2}
                  disabled={isDemo}
                  defaultValue={`Welcome to ${biz.name}! Text 'menu' to see what we have, or just tell us what you'd like to order.`}
                  className="mt-1 w-full px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] resize-none disabled:opacity-50"
                />
              </div>

              <div className="pt-2 border-t border-[#1F1F23] space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[#F5F5F7]">Auto-send payment link</p>
                    <p className="text-[10px] text-[#A1A1A8]">Send Square/Stripe payment link after order confirmation</p>
                  </div>
                  <span className="w-9 h-5 rounded-full bg-[#7C5CFF] relative">
                    <span className="absolute top-0.5 left-[18px] w-4 h-4 rounded-full bg-white shadow" />
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-[#F5F5F7]">Order confirmation receipt</p>
                    <p className="text-[10px] text-[#A1A1A8]">Text itemized receipt after payment completes</p>
                  </div>
                  <span className="w-9 h-5 rounded-full bg-[#7C5CFF] relative">
                    <span className="absolute top-0.5 left-[18px] w-4 h-4 rounded-full bg-white shadow" />
                  </span>
                </div>
              </div>

              {isDemo && (
                <div className="p-3 bg-amber-500/5 border border-amber-500/10 rounded-lg">
                  <p className="text-[10px] text-amber-400">
                    Sign up to enable text ordering for your business. Configuration is locked in demo mode.
                  </p>
                </div>
              )}
            </div>

            {/* Live Preview - SMS Conversation */}
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-2">
                  <MessageSquare size={14} className="text-[#7C5CFF]" /> Live Preview
                </h3>
                <button
                  onClick={() => setShowConvo(!showConvo)}
                  className="text-[10px] text-[#7C5CFF] hover:underline"
                >
                  {showConvo ? 'Collapse' : 'Expand'}
                </button>
              </div>

              {showConvo && (
                <div className="bg-[#0A0A0B] rounded-xl p-3 max-h-[420px] overflow-y-auto space-y-2">
                  {/* Phone frame header */}
                  <div className="text-center pb-2 border-b border-[#1F1F23] mb-2">
                    <p className="text-[10px] text-[#A1A1A8]">Messages</p>
                    <p className="text-xs font-medium text-[#F5F5F7]">{biz.name}</p>
                    <p className="text-[10px] text-[#A1A1A8] font-mono">{smsNumber}</p>
                  </div>

                  {DEMO_SMS_CONVO.map((msg, i) => (
                    <div key={i} className={clsx('flex', msg.from === 'customer' ? 'justify-end' : 'justify-start')}>
                      <div className={clsx(
                        'max-w-[80%] px-3 py-2 rounded-2xl text-xs whitespace-pre-line',
                        msg.from === 'customer'
                          ? 'bg-[#7C5CFF] text-white rounded-br-md'
                          : 'bg-[#1F1F23] text-[#F5F5F7] rounded-bl-md'
                      )}>
                        {msg.text}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Promo Banner */}
          <div className="card p-4 border-[#7C5CFF]/10 bg-gradient-to-r from-[#7C5CFF]/5 to-transparent">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center flex-shrink-0">
                <Zap size={16} className="text-[#7C5CFF]" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs text-[#F5F5F7] font-medium">Add "Text to Order" signage in your store</p>
                <p className="text-[10px] text-[#A1A1A8] mt-0.5">
                  Print table tents, window stickers, or add to your menu: <span className="text-[#7C5CFF] font-mono">Text {smsNumber.replace(/[^+\d]/g, '')} to order</span>
                </p>
              </div>
            </div>
          </div>

          {/* Stats (demo) */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Text Orders', value: isDemo ? '47' : '0', sub: 'Last 30 days', color: 'text-[#7C5CFF]' },
              { label: 'Revenue', value: isDemo ? `${biz.currency}1,284` : `${biz.currency}0`, sub: 'Via text orders', color: 'text-[#17C5B0]' },
              { label: 'Avg Order', value: isDemo ? `${biz.currency}27.32` : '-', sub: 'Per text order', color: 'text-[#F5F5F7]' },
              { label: 'Payment Rate', value: isDemo ? '89%' : '-', sub: 'Links clicked & paid', color: 'text-[#17C5B0]' },
            ].map(s => (
              <DashboardTiltCard key={s.label}>
                <div className="p-3.5">
                  <p className="text-[10px] text-[#A1A1A8]">{s.label}</p>
                  <p className={clsx('text-lg font-bold mt-0.5', s.color)}>{s.value}</p>
                  <p className="text-[10px] text-[#A1A1A8] mt-0.5">{s.sub}</p>
                </div>
              </DashboardTiltCard>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

type Tab = 'overview' | 'calls' | 'text_orders' | 'settings'

export default function PhoneOrdersPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { org } = useAuth()
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
    phoneService.getConfig(orgId).then(cfg => {
      setPhoneConfig(cfg)
      if (cfg.exists && cfg.active) {
        setSetupDone(true)
      }
    })
    phoneService.getCalls(orgId).then(c => setRealCalls(c))
  }, [orgId, isDemo])

  const business: PhoneBizConfig = useMemo(() => {
    if (!isDemo && phoneConfig?.exists) {
      return {
        id: phoneConfig.merchant_id,
        name: phoneConfig.business_name || org?.business_name || 'My Business',
        vertical: phoneConfig.business_type || 'restaurant',
        country: 'US',
        currency: '$',
        taxRate: 0.08,
        phone: phoneConfig.phone_number || '',
        greeting: phoneConfig.greeting || '',
        voice: phoneConfig.voice || 'af_bella',
        orderTypes: (phoneConfig.order_types || ['pickup', 'delivery']) as any,
        menu: (phoneConfig.menu_items || []).map((m: any, i: number) => ({
          id: m.id || `item-${i}`,
          name: m.name || '',
          price: m.price || 0,
          category: m.category || 'General',
        })),
      }
    }
    if (!isDemo) {
      return {
        id: orgId || '',
        name: org?.business_name || 'My Business',
        vertical: 'restaurant',
        country: 'US',
        currency: '$',
        taxRate: 0.08,
        phone: '',
        greeting: '',
        voice: 'af_bella',
        orderTypes: ['pickup', 'delivery'] as any,
        menu: [],
      }
    }
    return demoData.business
  }, [phoneConfig, demoData.business, org?.business_name, isDemo, orgId])

  const calls = isDemo ? demoData.calls : (realCalls ?? [])

  const handleWizardDone = useCallback(async () => {
    localStorage.setItem(setupKey, '1')
    setSetupDone(true)
    setShowWizard(false)
    if (orgId && !isDemo) {
      phoneService.getConfig(orgId).then(setPhoneConfig)
    }
  }, [orgId, isDemo])

  if (!setupDone || showWizard) {
    return (
      <div className="space-y-6">
        {!showWizard && (
          <div className="card p-5 border-[#17C5B0]/10">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
                <Phone size={20} className="text-[#17C5B0]" />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-[#F5F5F7]">Welcome to Phone Orders</h2>
                <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                  Set up your AI phone agent in under 2 minutes. It answers calls, takes orders,
                  and sends them straight to your POS — no extra hardware needed.
                </p>
              </div>
            </div>
          </div>
        )}
        <SetupWizard biz={business} onDone={handleWizardDone} connectedPos={connectedPos} orgId={orgId} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Phone Orders</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">AI-powered phone ordering for your business</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setShowConnect(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#1A8FD6] text-white text-xs font-medium rounded-lg hover:bg-[#1A8FD6]/90 transition-colors">
            <Phone size={14} /> Connect Phone
          </button>
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
          { key: 'text_orders' as const, label: 'Text Orders', icon: MessageSquare },
          { key: 'settings' as const, label: 'Settings', icon: Settings },
        ]).map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={tab === t.key ? 'period-btn-active' : 'period-btn-inactive'}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab calls={calls} biz={business} period={period} setPeriod={setPeriod} onViewCall={setSelectedCall} onConnect={() => setShowConnect(true)} />}
      {tab === 'calls' && <CallLogTab calls={calls} biz={business} onViewCall={setSelectedCall} />}
      {tab === 'text_orders' && <TextOrderingTab biz={business} isDemo={isDemo} />}
      {tab === 'settings' && <SettingsTab biz={business} onReconfigure={() => setShowWizard(true)} connectedPos={connectedPos} onConnect={() => setShowConnect(true)} orgId={orgId} />}

      {selectedCall && <TranscriptModal call={selectedCall} biz={business} onClose={() => setSelectedCall(null)} />}
      {showConnect && <ConnectPhoneModal biz={business} onClose={() => setShowConnect(false)} />}
    </div>
  )
}
