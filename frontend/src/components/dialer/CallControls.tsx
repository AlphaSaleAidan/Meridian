// In-call controls: mute, hang up / skip. The big idle-state control is the
// session starter (lives in the page); these only matter while a leg is live.
import { useEffect, useState } from 'react'
import { Mic, MicOff, PhoneOff, SkipForward } from 'lucide-react'
import type { DialerPhase } from '@/hooks/useDialerSession'

interface Props {
  phase: DialerPhase
  onHangup: () => void
  onMute: (muted: boolean) => void
}

export function CallControls({ phase, onHangup, onMute }: Props) {
  const [muted, setMuted] = useState(false)
  const inCall = phase === 'connected'
  const inFlight = phase === 'dialing' || phase === 'ringing'

  // A new call always starts unmuted.
  useEffect(() => {
    if (phase === 'dialing') setMuted(false)
  }, [phase])

  if (!inCall && !inFlight) return null

  return (
    <div className="flex items-center justify-center gap-3 bg-pm-canada-surface border border-pm-canada-border rounded-xl px-4 py-3">
      {inCall && (
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
      )}
      <button
        onClick={onHangup}
        className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-red-500/15 border border-red-500/40 text-xs font-semibold text-red-400 hover:bg-red-500/25 transition-colors"
      >
        {inCall ? <PhoneOff size={15} /> : <SkipForward size={15} />}
        {inCall ? 'Hang up' : 'Skip'}
      </button>
    </div>
  )
}
