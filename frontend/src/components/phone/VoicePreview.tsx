import { useState, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import { Play, Square } from 'lucide-react'
import WaveformVisualizer from './WaveformVisualizer'
import { VOICE_OPTIONS } from '@/lib/phone-orders-demo-data'

/** Pitch / rate overrides per voice ID for SpeechSynthesis. Spread wide so each
 *  voice is audibly distinct even when the browser only exposes one voice per
 *  gender (the preview falls back to pitch/rate to differentiate). */
export const VOICE_SAMPLES: Record<string, { pitch: number; rate: number }> = {
  af_bella:   { pitch: 1.05, rate: 0.95 },
  af_sarah:   { pitch: 1.4,  rate: 1.12 },
  af_nicole:  { pitch: 0.9,  rate: 0.88 },
  bf_emma:    { pitch: 1.2,  rate: 1.0  },
  am_adam:    { pitch: 0.65, rate: 0.88 },
  am_michael: { pitch: 1.0,  rate: 1.03 },
  am_echo:    { pitch: 0.85, rate: 0.98 },
  bm_george:  { pitch: 0.75, rate: 0.92 },
}

/** Real Vapi voice samples (docs.vapi.ai) shipped at public/voices/. Preview
 *  plays the ACTUAL voice heard on live calls; SpeechSynthesis remains only for
 *  simulated test-call dialogue (dynamic text can't use fixed samples). */
export const VAPI_SAMPLE_SRC: Record<string, string> = {
  af_bella: '/voices/savannah.mp3',
  af_sarah: '/voices/layla.mp3',
  af_nicole: '/voices/naina.mp3',
  bf_emma: '/voices/emma.mp3',
  am_adam: '/voices/sid.mp3',
  am_michael: '/voices/elliot.mp3',
  am_echo: '/voices/kai.mp3',
  bm_george: '/voices/neil.mp3',
}

let _sharedAudio: HTMLAudioElement | null = null
export function playVapiSample(voiceId: string, onEnd?: () => void): HTMLAudioElement | null {
  const srcUrl = VAPI_SAMPLE_SRC[voiceId]
  if (!srcUrl) { onEnd?.(); return null }
  stopVapiSample()
  const audio = new Audio(srcUrl)
  _sharedAudio = audio
  if (onEnd) { audio.onended = onEnd; audio.onerror = onEnd }
  void audio.play().catch(() => onEnd?.())
  return audio
}
export function stopVapiSample(): void {
  if (_sharedAudio) { _sharedAudio.pause(); _sharedAudio = null }
}

const FEMALE_RE = /samantha|karen|victoria|zira|tessa|moira|fiona|serena|female|woman|google uk english female|google us english/i
const MALE_RE = /daniel|alex|david|mark|fred|rishi|oliver|arthur|male|man|google uk english male/i

function isFemaleVoice(id: string) { return /^[ab]f_/.test(id) }
function isBritishVoice(id: string) { return id.startsWith('bf_') || id.startsWith('bm_') }

/** Resolve a browser SpeechSynthesisVoice for a voice ID. Different IDs of the
 *  same gender map to *different* browser voices (by stable index) so previews
 *  don't all collapse onto the first matching voice. */
function pickBrowserVoice(voiceId: string): SpeechSynthesisVoice | undefined {
  const voices = window.speechSynthesis.getVoices()
  if (!voices.length) return undefined

  const female = isFemaleVoice(voiceId)
  const langRe = isBritishVoice(voiceId) ? /^en-GB/i : /^en/i
  const nameRe = female ? FEMALE_RE : MALE_RE

  let pool = voices.filter(v => langRe.test(v.lang) && nameRe.test(v.name))
  if (!pool.length) pool = voices.filter(v => /^en/i.test(v.lang) && nameRe.test(v.name))
  if (!pool.length) pool = voices.filter(v => /^en/i.test(v.lang))
  if (!pool.length) pool = voices

  // Stable, per-gender index so each same-gender voice lands on a distinct entry.
  const sameGenderIds = VOICE_OPTIONS.filter(o => isFemaleVoice(o.id) === female).map(o => o.id)
  const idx = Math.max(0, sameGenderIds.indexOf(voiceId))
  return pool[idx % pool.length]
}

/** Speak text in the given voice ID, applying the per-voice pitch/rate and a
 *  distinct browser voice. Used by the simulated test call (dynamic dialogue
 *  can't use fixed samples, so speechSynthesis stands in for the real voice). */
export function speakWithVoice(
  text: string,
  voiceId: string,
  opts?: { onEnd?: () => void },
): void {
  if (!text.trim()) { opts?.onEnd?.(); return }
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  const sample = VOICE_SAMPLES[voiceId]
  if (sample) {
    utter.pitch = sample.pitch
    utter.rate = sample.rate
  }
  const preferred = pickBrowserVoice(voiceId)
  if (preferred) utter.voice = preferred
  if (opts?.onEnd) {
    utter.onend = opts.onEnd
    utter.onerror = opts.onEnd
  }
  window.speechSynthesis.speak(utter)
}

/* ---------- Compact play button (for voice grid cards) ---------- */
export function VoicePlayButton({ voiceId, isSelected }: { voiceId: string; isSelected: boolean }) {
  const [playing, setPlaying] = useState(false)

  const handlePlay = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()
    if (playing) {
      stopVapiSample()
      setPlaying(false)
      return
    }
    setPlaying(true)
    playVapiSample(voiceId, () => setPlaying(false))
  }, [playing, voiceId])

  return (
    <button onClick={handlePlay}
      className={clsx(
        'w-6 h-6 rounded-full flex items-center justify-center transition-all flex-shrink-0',
        playing
          ? 'bg-[#1A8FD6] text-white'
          : isSelected ? 'bg-[#1A8FD6]/15 text-[#1A8FD6] hover:bg-[#1A8FD6]/25' : 'bg-[#1F1F23] text-[#A1A1A8] hover:bg-[#2A2A30]',
      )}
      title={playing ? 'Stop' : 'Preview voice'}>
      {playing ? <Square size={8} fill="currentColor" /> : <Play size={10} fill="currentColor" />}
    </button>
  )
}

/* ---------- Full voice preview card with waveform ---------- */
/** Plays the REAL Vapi studio sample for the selected voice. No tuning
 *  sliders: Vapi native voices accept no speed/pitch params, so any knob here
 *  would be placebo (the old Speed/Pitch/Warmth sliders never persisted and
 *  never touched live calls — removed after Aidan's live testing). */
interface VoicePreviewProps {
  voiceId: string
}

export function VoicePreviewCard({ voiceId }: VoicePreviewProps) {
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    return () => { window.speechSynthesis.cancel(); stopVapiSample() }
  }, [])

  function handlePreview() {
    if (playing) {
      stopVapiSample()
      setPlaying(false)
      return
    }
    // Real Vapi sample — the exact voice live calls use.
    setPlaying(true)
    playVapiSample(voiceId, () => setPlaying(false))
  }

  return (
    <div className="bg-[#111113] border border-[#1F1F23] rounded-lg p-4">
      <div className="flex items-center gap-3 mb-3">
        <button
          onClick={handlePreview}
          className={clsx(
            'w-10 h-10 rounded-full flex items-center justify-center transition-all flex-shrink-0',
            playing ? 'bg-[#17C5B0] text-white' : 'bg-[#1A8FD6]/15 text-[#1A8FD6] hover:bg-[#1A8FD6]/25',
          )}
        >
          {playing ? <Square size={14} fill="currentColor" /> : <Play size={16} fill="currentColor" />}
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[#F5F5F7]">
            {playing ? 'Playing preview...' : 'Preview voice'}
          </p>
          <p className="text-[10px] text-[#A1A1A8] truncate">
            {VOICE_OPTIONS.find(v => v.id === voiceId)?.label || 'Voice'}
          </p>
        </div>
      </div>
      <WaveformVisualizer active={playing} barCount={24} height={28} />
      <p className="text-[10px] text-[#A1A1A8] mt-3">
        This is the exact studio voice callers hear on live calls.
      </p>
    </div>
  )
}
