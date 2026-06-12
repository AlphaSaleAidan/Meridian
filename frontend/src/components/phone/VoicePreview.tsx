import { useState, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import { Play, Square } from 'lucide-react'
import WaveformVisualizer from './WaveformVisualizer'
import { VOICE_OPTIONS, type VoiceSettings } from '@/lib/phone-orders-demo-data'

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
 *  distinct browser voice. Shared by the voice previews and the test call. */
export function speakWithVoice(
  text: string,
  voiceId: string,
  opts?: { onEnd?: () => void; speed?: number; pitch?: number },
): void {
  if (!text.trim()) { opts?.onEnd?.(); return }
  window.speechSynthesis.cancel()
  const utter = new SpeechSynthesisUtterance(text)
  const sample = VOICE_SAMPLES[voiceId]
  if (sample) {
    utter.pitch = sample.pitch * (opts?.pitch ?? 1)
    utter.rate = sample.rate * (opts?.speed ?? 1)
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
      window.speechSynthesis.cancel()
      setPlaying(false)
      return
    }
    window.speechSynthesis.cancel()
    const option = VOICE_OPTIONS.find(v => v.id === voiceId)
    if (!option) return
    const utter = new SpeechSynthesisUtterance(option.sampleText)
    const sample = VOICE_SAMPLES[voiceId]
    if (sample) { utter.pitch = sample.pitch; utter.rate = sample.rate }
    const preferred = pickBrowserVoice(voiceId)
    if (preferred) utter.voice = preferred
    utter.onend = () => setPlaying(false)
    utter.onerror = () => setPlaying(false)
    setPlaying(true)
    window.speechSynthesis.speak(utter)
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

/* ---------- Full voice preview card with waveform + settings ---------- */
interface VoicePreviewProps {
  voiceId: string
  businessName: string
  greeting: string
  settings: VoiceSettings
  onSettingsChange: (s: VoiceSettings) => void
}

export function VoicePreviewCard({ voiceId, businessName, greeting, settings, onSettingsChange }: VoicePreviewProps) {
  const [playing, setPlaying] = useState(false)

  useEffect(() => {
    return () => { window.speechSynthesis.cancel() }
  }, [])

  function handlePreview() {
    if (playing) {
      window.speechSynthesis.cancel()
      setPlaying(false)
      return
    }
    window.speechSynthesis.cancel()
    const text = greeting || `Thank you for calling ${businessName}! How can I help you today?`
    const utter = new SpeechSynthesisUtterance(text)
    const sample = VOICE_SAMPLES[voiceId]
    if (sample) {
      utter.pitch = sample.pitch * settings.pitch
      utter.rate = sample.rate * settings.speed
    } else {
      utter.pitch = settings.pitch
      utter.rate = settings.speed
    }
    const preferred = pickBrowserVoice(voiceId)
    if (preferred) utter.voice = preferred
    utter.onend = () => setPlaying(false)
    utter.onerror = () => setPlaying(false)
    setPlaying(true)
    window.speechSynthesis.speak(utter)
  }

  return (
    <div className="space-y-4">
      {/* Preview + Waveform */}
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
              {playing ? 'Playing preview...' : 'Preview greeting'}
            </p>
            <p className="text-[10px] text-[#A1A1A8] truncate">
              {VOICE_OPTIONS.find(v => v.id === voiceId)?.label || 'Voice'} &middot;
              {settings.speed.toFixed(1)}x &middot;
              {settings.language === 'en' ? 'English' : settings.language === 'fr' ? 'French' : 'Spanish'}
            </p>
          </div>
        </div>
        <WaveformVisualizer active={playing} barCount={24} height={28} />
      </div>

      {/* Voice tuning sliders */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div>
          <label className="text-[10px] text-[#A1A1A8] block mb-1.5">Speed ({settings.speed.toFixed(1)}x)</label>
          <input type="range" min={0.8} max={1.2} step={0.05} value={settings.speed}
            onChange={e => onSettingsChange({ ...settings, speed: parseFloat(e.target.value) })}
            className="w-full accent-[#1A8FD6] h-1" />
          <div className="flex justify-between text-[8px] text-[#A1A1A8]/50 mt-0.5">
            <span>Slower</span><span>Faster</span>
          </div>
        </div>
        <div>
          <label className="text-[10px] text-[#A1A1A8] block mb-1.5">Pitch ({settings.pitch.toFixed(1)}x)</label>
          <input type="range" min={0.8} max={1.2} step={0.05} value={settings.pitch}
            onChange={e => onSettingsChange({ ...settings, pitch: parseFloat(e.target.value) })}
            className="w-full accent-[#1A8FD6] h-1" />
          <div className="flex justify-between text-[8px] text-[#A1A1A8]/50 mt-0.5">
            <span>Lower</span><span>Higher</span>
          </div>
        </div>
        <div>
          <label className="text-[10px] text-[#A1A1A8] block mb-1.5">Warmth ({Math.round(settings.warmth * 100)}%)</label>
          <input type="range" min={0} max={1} step={0.1} value={settings.warmth}
            onChange={e => onSettingsChange({ ...settings, warmth: parseFloat(e.target.value) })}
            className="w-full accent-[#17C5B0] h-1" />
          <div className="flex justify-between text-[8px] text-[#A1A1A8]/50 mt-0.5">
            <span>Neutral</span><span>Warm</span>
          </div>
        </div>
      </div>

      {/* Language selector */}
      <div>
        <label className="text-[10px] text-[#A1A1A8] block mb-1.5">Language</label>
        <div className="flex gap-2">
          {([
            { key: 'en' as const, label: 'English' },
            { key: 'fr' as const, label: 'French' },
            { key: 'es' as const, label: 'Spanish' },
          ]).map(lang => (
            <button
              key={lang.key}
              onClick={() => onSettingsChange({ ...settings, language: lang.key })}
              className={clsx(
                'px-3 py-1.5 rounded-lg border text-xs font-medium transition-all',
                settings.language === lang.key
                  ? 'border-[#1A8FD6]/30 bg-[#1A8FD6]/5 text-[#1A8FD6]'
                  : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#2A2A30]',
              )}
            >
              {lang.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
