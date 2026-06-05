import { useState, useEffect, useRef, useCallback } from 'react'
import { clsx } from 'clsx'
import { PhoneForwarded, PhoneCall, PhoneOff, Mic, MicOff, Send, Loader2 } from 'lucide-react'
import WaveformVisualizer from './WaveformVisualizer'
import { speakWithVoice } from './VoicePreview'
import { ensureAnimStyles } from './phone-anim-styles'
import { phoneService } from '@/lib/phone-service'
import type { PhoneBizConfig } from '@/lib/phone-orders-demo-data'

interface Props {
  biz: PhoneBizConfig
  orgId: string
  onClose: () => void
}

type Line = { speaker: 'agent' | 'caller'; text: string }
type Msg = { role: 'user' | 'assistant'; content: string }

// Web Speech API is unprefixed in some browsers, webkit-prefixed in others.
const SR: any =
  typeof window !== 'undefined'
    ? (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    : undefined

export default function TestCallModal({ biz, orgId, onClose }: Props) {
  const [elapsed, setElapsed] = useState(0)
  const [phase, setPhase] = useState<'ringing' | 'active' | 'ended'>('ringing')
  const [lines, setLines] = useState<Line[]>([])
  const [listening, setListening] = useState(false)
  const [thinking, setThinking] = useState(false)
  const [agentSpeaking, setAgentSpeaking] = useState(false)
  const [textDraft, setTextDraft] = useState('')

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const convoRef = useRef<Msg[]>([])
  const recRef = useRef<any>(null)
  const endedRef = useRef(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  const sttSupported = !!SR

  const greeting =
    (biz.greeting || '').trim() ||
    `Thanks for calling ${biz.name}! What can I get started for you?`

  const speak = useCallback((text: string, onDone?: () => void) => {
    setAgentSpeaking(true)
    speakWithVoice(text, biz.voice, {
      onEnd: () => { setAgentSpeaking(false); onDone?.() },
    })
  }, [biz.voice])

  const startListening = useCallback(() => {
    if (!SR || endedRef.current) return
    try { recRef.current?.stop() } catch { /* noop */ }
    const rec = new SR()
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.maxAlternatives = 1
    rec.continuous = false
    rec.onresult = (e: any) => {
      const transcript = e.results?.[0]?.[0]?.transcript?.trim()
      if (transcript) handleCallerTurn(transcript)
    }
    rec.onend = () => setListening(false)
    rec.onerror = () => setListening(false)
    recRef.current = rec
    try { rec.start(); setListening(true) } catch { setListening(false) }
  }, [])

  const stopListening = useCallback(() => {
    try { recRef.current?.stop() } catch { /* noop */ }
    setListening(false)
  }, [])

  const handleCallerTurn = useCallback(async (text: string) => {
    stopListening()
    setLines(prev => [...prev, { speaker: 'caller', text }])
    convoRef.current = [...convoRef.current, { role: 'user', content: text }]
    setThinking(true)
    try {
      const res = await phoneService.testChat({
        merchant_id: orgId,
        messages: convoRef.current,
        business_name: biz.name,
        greeting: biz.greeting,
        menu_items: (biz.menu || []).map(m => ({ name: m.name, price: m.price, category: (m as any).category })),
        order_types: biz.orderTypes as string[],
      })
      setThinking(false)
      convoRef.current = [...convoRef.current, { role: 'assistant', content: res.reply }]
      setLines(prev => [...prev, { speaker: 'agent', text: res.reply }])
      if (res.ended) {
        speak(res.reply, () => endCall())
        endedRef.current = true
      } else {
        speak(res.reply, () => startListening())
      }
    } catch {
      setThinking(false)
      const fallback = "Sorry, I'm having trouble hearing you. Could you try again?"
      setLines(prev => [...prev, { speaker: 'agent', text: fallback }])
      speak(fallback, () => startListening())
    }
  }, [orgId, biz, speak, startListening, stopListening])

  function endCall() {
    endedRef.current = true
    window.speechSynthesis.cancel()
    stopListening()
    if (timerRef.current) clearInterval(timerRef.current)
    setPhase('ended')
    setTimeout(onClose, 800)
  }

  // Ring → answer
  useEffect(() => {
    ensureAnimStyles()
    const t = setTimeout(() => setPhase('active'), 2000)
    return () => clearTimeout(t)
  }, [])

  // Call timer + opening greeting once active
  useEffect(() => {
    if (phase !== 'active') return
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    convoRef.current = [{ role: 'assistant', content: greeting }]
    setLines([{ speaker: 'agent', text: greeting }])
    speak(greeting, () => startListening())
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
      window.speechSynthesis.cancel()
      try { recRef.current?.stop() } catch { /* noop */ }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase])

  // Auto-scroll transcript
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [lines, thinking])

  const fmtElapsed = `${Math.floor(elapsed / 60)}:${String(elapsed % 60).padStart(2, '0')}`

  function submitText(e: React.FormEvent) {
    e.preventDefault()
    const v = textDraft.trim()
    if (!v || thinking || agentSpeaking) return
    setTextDraft('')
    handleCallerTurn(v)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" onClick={endCall}>
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
              <p className="text-[10px] text-[#A1A1A8] mt-1">
                {agentSpeaking ? 'Agent speaking…' : thinking ? 'Thinking…' : listening ? 'Listening — speak now' : 'Tap the mic to talk'}
              </p>
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

        {/* Transcript */}
        {phase === 'active' && (
          <div ref={scrollRef} className="px-4 py-3 max-h-52 overflow-y-auto space-y-2">
            {lines.map((line, i) => (
              <div key={i} className={clsx('flex', line.speaker === 'agent' ? 'justify-start' : 'justify-end')}>
                <div className={clsx(
                  'max-w-[85%] px-3 py-1.5 rounded-xl text-xs',
                  line.speaker === 'agent' ? 'bg-[#1F1F23] text-[#F5F5F7]' : 'bg-[#1A8FD6]/15 text-[#F5F5F7]',
                )}>
                  {line.text}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex justify-start">
                <div className="px-3 py-1.5 rounded-xl bg-[#1F1F23] text-[#A1A1A8]">
                  <Loader2 size={12} className="animate-spin" />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Waveform */}
        {phase === 'active' && (
          <div className="px-4 pb-2">
            <WaveformVisualizer active={agentSpeaking || listening} barCount={16} height={20} color={listening ? '#1A8FD6' : '#17C5B0'} />
          </div>
        )}

        {/* Controls */}
        {phase === 'active' && (
          <div className="px-4 pb-3 space-y-2">
            {sttSupported ? (
              <div className="flex items-center justify-center gap-3">
                <button
                  onClick={() => (listening ? stopListening() : startListening())}
                  disabled={thinking || agentSpeaking}
                  className={clsx(
                    'flex items-center gap-2 px-5 py-2.5 rounded-full text-xs font-medium transition-colors disabled:opacity-40',
                    listening ? 'bg-[#1A8FD6] text-white' : 'bg-[#1F1F23] text-[#F5F5F7] hover:bg-[#2A2A30]',
                  )}
                >
                  {listening ? <Mic size={14} /> : <MicOff size={14} />}
                  {listening ? 'Listening…' : 'Talk'}
                </button>
              </div>
            ) : (
              <form onSubmit={submitText} className="flex items-center gap-2">
                <input
                  value={textDraft}
                  onChange={e => setTextDraft(e.target.value)}
                  placeholder="Type what you'd say…"
                  disabled={thinking || agentSpeaking}
                  className="flex-1 px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/40 disabled:opacity-40"
                />
                <button type="submit" disabled={thinking || agentSpeaking || !textDraft.trim()} className="p-2 rounded-lg bg-[#1A8FD6] text-white disabled:opacity-40">
                  <Send size={14} />
                </button>
              </form>
            )}
            {!sttSupported && (
              <p className="text-[9px] text-[#A1A1A8]/50 text-center">Voice input isn't supported in this browser — type to test instead.</p>
            )}
          </div>
        )}

        {/* Hang Up */}
        {phase !== 'ended' && (
          <div className="px-5 py-4 border-t border-[#1F1F23] flex justify-center">
            <button
              onClick={endCall}
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
