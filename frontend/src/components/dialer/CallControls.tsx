// In-call controls: mute, hang up / skip, and a DTMF keypad for punching
// through IVR menus ("press 1 for the pro shop"). The big idle-state control is
// the session starter (lives in the page); these only matter while a leg is live.
import { useEffect, useState } from 'react'
import { Grid3x3, Mic, MicOff, PhoneOff, SkipForward } from 'lucide-react'
import type { DialerPhase } from '@/hooks/useDialerSession'

interface Props {
  phase: DialerPhase
  onHangup: () => void
  onMute: (muted: boolean) => void
  onDtmf: (digit: string) => void
}

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '*', '0', '#']

export function CallControls({ phase, onHangup, onMute, onDtmf }: Props) {
  const [muted, setMuted] = useState(false)
  const [padOpen, setPadOpen] = useState(false)
  const [sent, setSent] = useState('')
  const inCall = phase === 'connected'
  const inFlight = phase === 'dialing' || phase === 'ringing'

  // A new call always starts unmuted, with a fresh keypad.
  useEffect(() => {
    if (phase === 'dialing') { setMuted(false); setPadOpen(false); setSent('') }
  }, [phase])

  if (!inCall && !inFlight) return null

  const press = (d: string) => {
    onDtmf(d)
    setSent(prev => (prev + d).slice(-16))
  }

  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl px-4 py-3 space-y-3">
      <div className="flex items-center justify-center gap-3">
        {inCall && (
          <>
            <button
              onClick={() => { const next = !muted; setMuted(next); onMute(next) }}
              aria-pressed={muted}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium transition-colors ${
                muted
                  ? 'border-pm-amber-orange/40 bg-pm-amber-orange/10 text-pm-amber-orange'
                  : 'border-pm-canada-border text-pm-canada-text-muted hover:text-white'
              }`}
            >
              {muted ? <MicOff size={15} /> : <Mic size={15} />}
              {muted ? 'Muted' : 'Mute'}
            </button>
            <button
              onClick={() => setPadOpen(o => !o)}
              aria-pressed={padOpen}
              aria-label="Toggle keypad"
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-medium transition-colors ${
                padOpen
                  ? 'border-pm-accent/40 bg-pm-accent/10 text-pm-accent'
                  : 'border-pm-canada-border text-pm-canada-text-muted hover:text-white'
              }`}
            >
              <Grid3x3 size={15} />
              Keypad
            </button>
          </>
        )}
        <button
          onClick={onHangup}
          className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-red-500/15 border border-red-500/40 text-xs font-semibold text-red-400 hover:bg-red-500/25 transition-colors"
        >
          {inCall ? <PhoneOff size={15} /> : <SkipForward size={15} />}
          {inCall ? 'Hang up' : 'Skip'}
        </button>
      </div>

      {inCall && padOpen && (
        <div className="flex flex-col items-center gap-2">
          <div className="h-5 text-sm text-pm-canada-text-muted tabular-nums tracking-widest" aria-live="polite">
            {sent || <span className="text-pm-canada-text-faint text-xs tracking-normal">Tones go straight to the call</span>}
          </div>
          <div className="grid grid-cols-3 gap-1.5">
            {KEYS.map(k => (
              <button
                key={k}
                onClick={() => press(k)}
                className="w-14 h-11 rounded-lg border border-pm-canada-border bg-pm-canada-bg text-base font-medium text-white tabular-nums hover:border-pm-accent/40 hover:text-pm-accent active:bg-pm-accent/10 transition-colors"
              >
                {k}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
