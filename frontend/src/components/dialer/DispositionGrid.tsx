// One-click dispositions — the auto-advance trigger. Two need extra input:
// callback (when + note) and DNC (explicit confirm; writes the internal DNC
// list instantly, server-side). Meeting-booked / interested also advance the
// lead's pipeline stage (backend-guarded to the rep's own lead).
import { useState } from 'react'
import {
  CalendarPlus, CheckCircle2, Voicemail, PhoneMissed, CircleSlash,
  ThumbsDown, PhoneOff, AlertTriangle, Sparkles, MinusCircle,
} from 'lucide-react'
import type { Disposition } from '@/lib/dialer-api'

interface Props {
  enabled: boolean
  onSubmit: (
    disposition: Disposition,
    opts?: { callback?: { due_at: string; note?: string }; advance_stage?: string },
  ) => void
}

const PRIMARY: { d: Disposition; label: string; icon: typeof CheckCircle2; accent?: boolean; stage?: string }[] = [
  { d: 'meeting_booked', label: 'Meeting booked', icon: Sparkles, accent: true, stage: 'appointment_set' },
  { d: 'interested', label: 'Interested', icon: CheckCircle2, accent: true, stage: 'contacted' },
  { d: 'callback', label: 'Callback', icon: CalendarPlus },
  { d: 'left_voicemail', label: 'Left voicemail', icon: Voicemail },
  { d: 'no_answer', label: 'No answer', icon: PhoneMissed },
  { d: 'busy', label: 'Busy', icon: CircleSlash },
  { d: 'bad_number', label: 'Bad number', icon: MinusCircle },
  { d: 'not_interested', label: 'Not interested', icon: ThumbsDown },
]

function defaultCallbackTime(): string {
  const t = new Date(Date.now() + 24 * 3600 * 1000)
  t.setMinutes(0, 0, 0)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}T${pad(t.getHours())}:00`
}

export function DispositionGrid({ enabled, onSubmit }: Props) {
  const [callbackOpen, setCallbackOpen] = useState(false)
  const [callbackAt, setCallbackAt] = useState(defaultCallbackTime)
  const [callbackNote, setCallbackNote] = useState('')
  const [dncArmed, setDncArmed] = useState(false)

  const reset = () => { setCallbackOpen(false); setDncArmed(false); setCallbackNote('') }
  const submit: Props['onSubmit'] = (d, opts) => { reset(); onSubmit(d, opts) }

  return (
    <div className={`bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4 ${enabled ? '' : 'opacity-50 pointer-events-none'}`}>
      <div className="flex items-baseline justify-between mb-3">
        <h2 className="text-sm font-semibold text-white">Disposition</h2>
        <span className="text-2xs text-pm-canada-text-faint">
          {enabled ? 'Pick one to wrap up and auto-advance' : 'Available after the call ends'}
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {PRIMARY.map(({ d, label, icon: Icon, accent, stage }) => (
          <button
            key={d}
            onClick={() => {
              if (d === 'callback') { setCallbackOpen(o => !o); setDncArmed(false); return }
              submit(d, stage ? { advance_stage: stage } : undefined)
            }}
            className={`inline-flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-medium transition-colors text-left ${
              accent
                ? 'border-pm-accent/30 bg-pm-accent/8 text-pm-accent hover:bg-pm-accent/15'
                : d === 'callback' && callbackOpen
                  ? 'border-pm-amber-gold/40 bg-pm-amber-gold/10 text-pm-amber-gold'
                  : 'border-pm-canada-border text-pm-canada-text-muted hover:text-white hover:border-pm-canada-text-muted'
            }`}
          >
            <Icon size={14} className="shrink-0" />
            {label}
          </button>
        ))}
      </div>

      {callbackOpen && (
        <div className="mt-3 rounded-lg border border-pm-amber-gold/25 bg-pm-amber-gold/5 p-3 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="dialer-callback-at" className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">
              Call back at
            </label>
            <input
              id="dialer-callback-at"
              type="datetime-local"
              value={callbackAt}
              onChange={e => setCallbackAt(e.target.value)}
              className="rounded-md bg-pm-canada-bg/70 border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-amber-gold/50 [color-scheme:dark]"
            />
            <input
              type="text"
              value={callbackNote}
              onChange={e => setCallbackNote(e.target.value)}
              placeholder="Why (optional)"
              className="flex-1 min-w-[140px] rounded-md bg-pm-canada-bg/70 border border-pm-canada-border px-2 py-1.5 text-xs text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-amber-gold/50"
            />
            <button
              onClick={() => submit('callback', {
                callback: { due_at: new Date(callbackAt).toISOString(), note: callbackNote },
              })}
              className="px-3 py-1.5 rounded-md bg-pm-amber-gold/15 border border-pm-amber-gold/40 text-xs font-semibold text-pm-amber-gold hover:bg-pm-amber-gold/25 transition-colors"
            >
              Schedule
            </button>
          </div>
        </div>
      )}

      <div className="mt-3 flex items-center gap-2">
        {!dncArmed ? (
          <button
            onClick={() => { setDncArmed(true); setCallbackOpen(false) }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-red-500/25 text-2xs font-medium text-red-400/80 hover:bg-red-500/10 transition-colors"
          >
            <PhoneOff size={12} />
            Do not call…
          </button>
        ) : (
          <div className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/8 px-3 py-1.5">
            <AlertTriangle size={13} className="text-red-400" />
            <span className="text-2xs text-red-400">Adds this number to the DNC list immediately.</span>
            <button
              onClick={() => submit('dnc')}
              className="px-2.5 py-1 rounded-md bg-red-500/15 border border-red-500/40 text-2xs font-semibold text-red-400 hover:bg-red-500/25 transition-colors"
            >
              Confirm DNC
            </button>
            <button
              onClick={() => setDncArmed(false)}
              className="text-2xs text-pm-canada-text-muted hover:text-white transition-colors"
            >
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
