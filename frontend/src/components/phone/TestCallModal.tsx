import { useState, useEffect, useRef, useMemo } from 'react'
import { clsx } from 'clsx'
import { PhoneForwarded, PhoneCall, PhoneOff } from 'lucide-react'
import WaveformVisualizer from './WaveformVisualizer'
import { VOICE_SAMPLES } from './VoicePreview'
import { ensureAnimStyles } from './phone-anim-styles'
import type { PhoneBizConfig } from '@/lib/phone-orders-demo-data'

interface Props {
  biz: PhoneBizConfig
  onClose: () => void
}

export default function TestCallModal({ biz, onClose }: Props) {
  const [elapsed, setElapsed] = useState(0)
  const [phase, setPhase] = useState<'ringing' | 'active' | 'ended'>('ringing')
  const [visibleLines, setVisibleLines] = useState<{ speaker: string; text: string }[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const testTranscript = useMemo(() => [
    { speaker: 'agent', text: biz.greeting },
    { speaker: 'caller', text: "Hi, I'd like to place an order for pickup." },
    { speaker: 'agent', text: 'Of course! What would you like?' },
    { speaker: 'caller', text: `I'll have the ${biz.menu[0]?.name || 'special'}, please.` },
    { speaker: 'agent', text: `Great choice! The ${biz.menu[0]?.name || 'That'} is one of our most popular items. Anything else?` },
    { speaker: 'caller', text: "That's everything." },
    { speaker: 'agent', text: `Your order will be ready in about 15 minutes. Thank you for calling ${biz.name}!` },
  ], [biz])

  useEffect(() => {
    ensureAnimStyles()
    const answerTimeout = setTimeout(() => setPhase('active'), 2000)
    return () => clearTimeout(answerTimeout)
  }, [])

  useEffect(() => {
    if (phase !== 'active') return
    timerRef.current = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [phase])

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

      if (line.speaker === 'agent') {
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
            : /daniel|alex|david|male|mark/i.test(v.name),
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
  const lastLine = visibleLines[visibleLines.length - 1]
  const agentSpeaking = lastLine?.speaker === 'agent'

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
                  line.speaker === 'agent' ? 'bg-[#1F1F23] text-[#F5F5F7]' : 'bg-[#1A8FD6]/15 text-[#F5F5F7]',
                )}>
                  {line.text}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Waveform */}
        {phase === 'active' && (
          <div className="px-4 pb-2">
            <WaveformVisualizer active={agentSpeaking} barCount={16} height={20} color="#17C5B0" />
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
