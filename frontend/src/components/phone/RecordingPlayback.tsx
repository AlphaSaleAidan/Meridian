import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { Play, Pause } from 'lucide-react'
import WaveformVisualizer from './WaveformVisualizer'
import { VOICE_SAMPLES } from './VoicePreview'
import { ensureAnimStyles } from './phone-anim-styles'
import { VOICE_OPTIONS } from '@/lib/phone-orders-demo-data'

interface Props {
  transcript: { speaker: string; text: string; time: string }[]
  voiceId?: string
}

export default function RecordingPlayback({ transcript, voiceId }: Props) {
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
    const sample = voiceId ? VOICE_SAMPLES[voiceId] : undefined
    if (sample) {
      utter.pitch = sample.pitch
      utter.rate = sample.rate
    }
    const isFemale = voiceId?.startsWith('af_')
    const voices = window.speechSynthesis.getVoices()
    const preferred = voices.find(v =>
      isFemale
        ? /samantha|karen|victoria|zira|female/i.test(v.name)
        : /daniel|alex|david|male|mark/i.test(v.name),
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
          playing ? 'bg-[#17C5B0] text-white' : 'bg-[#1A8FD6]/15 text-[#1A8FD6] hover:bg-[#1A8FD6]/25',
        )}
      >
        {playing ? <Pause size={12} /> : <Play size={12} fill="currentColor" />}
      </button>
      <div className="flex-1">
        <WaveformVisualizer active={playing} barCount={16} height={20} color={playing ? '#17C5B0' : '#1F1F23'} />
      </div>
      <span className="text-[10px] text-[#A1A1A8] flex-shrink-0">
        {playing ? 'Playing...' : 'Play Recording'}
      </span>
    </div>
  )
}
