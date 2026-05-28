import { useState, useEffect, useRef, useMemo } from 'react'
import { clsx } from 'clsx'
import { PhoneCall } from 'lucide-react'
import WaveformVisualizer from './WaveformVisualizer'
import { ensureAnimStyles } from './phone-anim-styles'
import type { PhoneBizConfig, PhoneOrderItem } from '@/lib/phone-orders-demo-data'

interface Props {
  biz: PhoneBizConfig
}

/** Simulated live transcript lines for the mini-viewer. */
const LIVE_CONVO_POOL = [
  { speaker: 'caller' as const, text: "Yeah, hi. Can I place an order for pickup?" },
  { speaker: 'agent' as const, text: "Absolutely! What can I get for you?" },
  { speaker: 'caller' as const, text: "I'll have the..." },
  { speaker: 'agent' as const, text: "Great choice! That's a customer favorite." },
  { speaker: 'caller' as const, text: "Can I also add..." },
  { speaker: 'agent' as const, text: "Of course! Anything else?" },
  { speaker: 'caller' as const, text: "Actually, what do you recommend?" },
  { speaker: 'agent' as const, text: "Our most popular item is the..." },
  { speaker: 'caller' as const, text: "Perfect, let's go with that." },
  { speaker: 'agent' as const, text: "Sounds good! Anything else for you today?" },
  { speaker: 'caller' as const, text: "That's everything." },
  { speaker: 'agent' as const, text: "Your total comes to..." },
]

export default function LiveCallsBanner({ biz }: Props) {
  const [activeCalls, setActiveCalls] = useState(() => Math.random() < 0.5 ? 1 : 0)
  const [lineIndex, setLineIndex] = useState(0)
  const [visibleLines, setVisibleLines] = useState<typeof LIVE_CONVO_POOL>([])
  const [orderItems, setOrderItems] = useState<PhoneOrderItem[]>([])
  const [agentSpeaking, setAgentSpeaking] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Build live transcript lines with actual menu items
  const liveConvo = useMemo(() => {
    if (biz.menu.length === 0) return LIVE_CONVO_POOL
    const item1 = biz.menu[Math.floor(Math.random() * biz.menu.length)]
    const item2 = biz.menu[Math.floor(Math.random() * biz.menu.length)]
    return [
      { speaker: 'caller' as const, text: "Yeah, hi. Can I place an order for pickup?" },
      { speaker: 'agent' as const, text: "Absolutely! What can I get for you?" },
      { speaker: 'caller' as const, text: `I'll have the ${item1.name}, please.` },
      { speaker: 'agent' as const, text: `Great choice! The ${item1.name} is one of our most popular. Anything else?` },
      { speaker: 'caller' as const, text: `Hmm, can I also get the ${item2.name}?` },
      { speaker: 'agent' as const, text: `Of course! Adding the ${item2.name}. Anything else?` },
      { speaker: 'caller' as const, text: "That's everything." },
      { speaker: 'agent' as const, text: `Your total comes to ${biz.currency}${(item1.price + item2.price).toFixed(2)} before tax. Can I get a name?` },
    ]
  }, [biz])

  useEffect(() => {
    ensureAnimStyles()
    const interval = setInterval(() => {
      setActiveCalls(Math.random() < 0.4 ? 1 : 0)
    }, 30000)
    return () => clearInterval(interval)
  }, [])

  // Advance the live transcript
  useEffect(() => {
    if (activeCalls === 0) {
      setVisibleLines([])
      setLineIndex(0)
      setOrderItems([])
      return
    }

    const interval = setInterval(() => {
      setLineIndex(prev => {
        const next = prev + 1
        if (next > liveConvo.length) return 0
        const line = liveConvo[prev]
        if (line) {
          setVisibleLines(vl => {
            const updated = [...vl, line].slice(-4)
            return updated
          })
          setAgentSpeaking(line.speaker === 'agent')
          // Simulate building order items
          if (line.speaker === 'caller' && line.text.includes('have the')) {
            const menuMatch = biz.menu.find(m => line.text.includes(m.name))
            if (menuMatch) {
              setOrderItems(oi => [...oi, { name: menuMatch.name, qty: 1, price: menuMatch.price }])
            }
          }
          if (line.speaker === 'caller' && line.text.includes('also get the')) {
            const menuMatch = biz.menu.find(m => line.text.includes(m.name))
            if (menuMatch) {
              setOrderItems(oi => [...oi, { name: menuMatch.name, qty: 1, price: menuMatch.price }])
            }
          }
        }
        return next
      })
    }, 3500)

    return () => clearInterval(interval)
  }, [activeCalls, liveConvo, biz.menu])

  // Auto-scroll transcript
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [visibleLines])

  if (activeCalls === 0) {
    return (
      <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg border bg-[#111113] border-[#1F1F23] transition-colors">
        <span className="w-2.5 h-2.5 rounded-full bg-[#A1A1A8]/40" />
        <span className="text-xs font-medium text-[#A1A1A8]">No active calls</span>
      </div>
    )
  }

  return (
    <div className="rounded-lg border bg-[#17C5B0]/5 border-[#17C5B0]/20 overflow-hidden transition-colors">
      {/* Header bar */}
      <div className="flex items-center gap-2.5 px-4 py-2.5">
        <div className="relative flex items-center justify-center">
          <span className="w-2.5 h-2.5 rounded-full bg-[#17C5B0] live-pulse-ring" />
        </div>
        <span className="text-xs font-medium text-[#17C5B0]">
          {activeCalls} active call
        </span>

        {/* Mini waveform when agent is speaking */}
        <div className="flex-1 flex justify-center">
          {agentSpeaking && (
            <div className="flex items-center gap-1.5">
              <span className="text-[9px] text-[#17C5B0]/60">Agent speaking</span>
              <WaveformVisualizer active barCount={8} height={14} color="#17C5B0" />
            </div>
          )}
        </div>

        <PhoneCall size={12} className="text-[#17C5B0] animate-pulse" />
      </div>

      {/* Mini live transcript */}
      {visibleLines.length > 0 && (
        <div className="px-4 pb-3 flex gap-3">
          {/* Transcript scroll */}
          <div ref={scrollRef} className="flex-1 space-y-1.5 max-h-20 overflow-y-auto">
            {visibleLines.map((line, i) => (
              <div key={i} className={clsx('flex', line.speaker === 'agent' ? 'justify-start' : 'justify-end')}>
                <div className={clsx(
                  'max-w-[85%] px-2.5 py-1 rounded-lg text-[10px] leading-relaxed',
                  line.speaker === 'agent'
                    ? 'bg-[#1F1F23] text-[#F5F5F7]'
                    : 'bg-[#1A8FD6]/10 text-[#F5F5F7]',
                )}>
                  {line.text}
                </div>
              </div>
            ))}
          </div>

          {/* Live order building */}
          {orderItems.length > 0 && (
            <div className="w-36 flex-shrink-0 bg-[#111113] rounded-lg p-2 border border-[#1F1F23]">
              <p className="text-[8px] text-[#A1A1A8] font-medium mb-1 uppercase tracking-wider">Order</p>
              {orderItems.map((item, i) => (
                <div key={i} className="flex justify-between text-[10px] py-0.5">
                  <span className="text-[#F5F5F7] truncate">{item.name}</span>
                  <span className="text-[#17C5B0] font-mono ml-1">{biz.currency}{item.price.toFixed(2)}</span>
                </div>
              ))}
              <div className="border-t border-[#1F1F23] mt-1 pt-1 flex justify-between text-[10px] font-medium">
                <span className="text-[#A1A1A8]">Total</span>
                <span className="text-[#17C5B0] font-mono">
                  {biz.currency}{orderItems.reduce((s, i) => s + i.price, 0).toFixed(2)}
                </span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
