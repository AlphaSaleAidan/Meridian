// Wrap-up popup — appears the moment a call ends.
//
// Structurally a bespoke card (NOT the inline DispositionGrid relocated):
// outcome-first hierarchy — the two wins are hero tiles, the rest are compact
// chips, notes and callback scheduling are integrated, DNC is a quiet footer
// action. Two states blur-crossfade: "how did it go?" for connected calls, a
// countdown ring for auto-dispositioned ring-outs.
//
// Motion adapted from the FRONTEND UI DEV LINKS libraries and tamed for a
// popup that fires after EVERY call (design-motion frequency gate):
//   * Aceternity "Animated Modal": AnimatePresence overlay + spring entrance,
//     flattened from the demo (no 3D tilt/overshoot; scale .96→1, blur ≤3px).
//   * Magic UI "Animated Circular Progress Bar": pure-SVG ring drained by a 1s
//     linear CSS transition on stroke-dashoffset (zero JS per frame).
// Re-skinned entirely to the pm-canada palette. Full reduced-motion path.
import { useEffect, useRef, useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import {
  AlertTriangle, CalendarClock, CalendarPlus, CheckCircle2, CircleSlash,
  MinusCircle, PauseCircle, PhoneForwarded, PhoneMissed, PhoneOff, PlayCircle,
  Sparkles, ThumbsDown, Voicemail,
} from 'lucide-react'
import { DISPOSITION_LABELS, fmtDuration, type Disposition } from '@/lib/dialer-api'
import type { CompletedCall, QueueEntry } from '@/hooks/useDialerSession'

interface Props {
  open: boolean
  needsDisposition: boolean
  entry: QueueEntry | null
  callSeconds: number
  wrapRemaining: number
  wrapTotal: number
  paused: boolean
  lastCompleted: CompletedCall | null
  notes: string
  onNotes: (v: string) => void
  onSubmit: (
    disposition: Disposition,
    opts?: { callback?: { due_at: string; note?: string }; advance_stage?: string },
  ) => void
  onDialNow: () => void
  onTogglePause: () => void
}

const SECONDARY: { d: Disposition; label: string; icon: typeof PhoneMissed }[] = [
  { d: 'left_voicemail', label: 'Voicemail', icon: Voicemail },
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

export function WrapUpModal({
  open, needsDisposition, entry, callSeconds, wrapRemaining, wrapTotal, paused,
  lastCompleted, notes, onNotes, onSubmit, onDialNow, onTogglePause,
}: Props) {
  const reduceMotion = useReducedMotion()
  const dialogRef = useRef<HTMLDivElement>(null)
  const [callbackOpen, setCallbackOpen] = useState(false)
  const [callbackAt, setCallbackAt] = useState(defaultCallbackTime)
  const [callbackNote, setCallbackNote] = useState('')
  const [dncArmed, setDncArmed] = useState(false)

  useEffect(() => {
    if (open && needsDisposition) dialogRef.current?.focus()
    if (!needsDisposition) { setCallbackOpen(false); setDncArmed(false) }
  }, [open, needsDisposition])

  const submit: Props['onSubmit'] = (d, opts) => {
    setCallbackOpen(false); setDncArmed(false); setCallbackNote('')
    onSubmit(d, opts)
  }

  const overlayAnim = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.01 } }
    : { initial: { opacity: 0, backdropFilter: 'blur(0px)' },
        animate: { opacity: 1, backdropFilter: 'blur(3px)' },
        exit: { opacity: 0, backdropFilter: 'blur(0px)' },
        transition: { duration: 0.16 } }

  const dialogAnim = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 }, transition: { duration: 0.01 } }
    : { initial: { opacity: 0, scale: 0.96, y: 8 },
        animate: { opacity: 1, scale: 1, y: 0,
          transition: { type: 'spring' as const, stiffness: 380, damping: 30 } },
        exit: { opacity: 0, scale: 0.98, transition: { duration: 0.14, ease: [0.32, 0.72, 0, 1] as const } } }

  const stateAnim = {
    initial: reduceMotion ? { opacity: 0 } : { opacity: 0, filter: 'blur(3px)' },
    animate: reduceMotion ? { opacity: 1 } : { opacity: 1, filter: 'blur(0px)' },
    exit: reduceMotion ? { opacity: 0 } : { opacity: 0, filter: 'blur(3px)' },
    transition: { duration: reduceMotion ? 0.01 : 0.15 },
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="wrapup-overlay"
          {...overlayAnim}
          className="fixed inset-0 z-[70] bg-black/65 flex items-center justify-center p-4"
        >
          <motion.div
            key="wrapup-dialog"
            {...dialogAnim}
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label={needsDisposition ? 'Call wrap-up' : 'Next dial countdown'}
            tabIndex={-1}
            className="relative w-full max-w-md bg-pm-canada-surface border border-pm-canada-border rounded-2xl shadow-[0_24px_64px_-12px_rgba(0,0,0,0.7)] outline-none overflow-hidden"
          >
            {/* brand accent hairline — signals this is the wrap-up moment */}
            <div className="h-0.5 w-full bg-gradient-to-r from-transparent via-pm-accent to-transparent" />

            <AnimatePresence mode="wait" initial={false}>
              {needsDisposition ? (
                <motion.div key="disposition" {...stateAnim} className="p-5 space-y-4">
                  {/* Identity header */}
                  <div className="flex items-start gap-3">
                    <div className="mt-0.5 w-9 h-9 rounded-full bg-pm-accent/12 border border-pm-accent/25 flex items-center justify-center shrink-0">
                      <PhoneOff size={16} className="text-pm-accent" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-2xs uppercase tracking-[0.14em] text-pm-accent/80">Call ended</p>
                      <h2 className="text-base font-semibold text-white truncate leading-tight">
                        {entry?.business_name || entry?.contact_name || entry?.phone_e164}
                      </h2>
                      <p className="text-2xs text-pm-canada-text-faint mt-0.5">
                        {entry?.phone_e164}
                        <span className="mx-1.5">·</span>
                        {fmtDuration(callSeconds)} on the line
                      </p>
                    </div>
                  </div>

                  {/* Hero outcomes — the wins get the weight */}
                  <div className="grid grid-cols-2 gap-2">
                    <HeroTile
                      icon={Sparkles} title="Meeting booked" sub="Advances the lead"
                      onClick={() => submit('meeting_booked', { advance_stage: 'appointment_set' })}
                      filled
                    />
                    <HeroTile
                      icon={CheckCircle2} title="Interested" sub="Keep pursuing"
                      onClick={() => submit('interested', { advance_stage: 'contacted' })}
                    />
                  </div>

                  {/* Callback — its own row so scheduling has room */}
                  <button
                    onClick={() => { setCallbackOpen(o => !o); setDncArmed(false) }}
                    className={`w-full inline-flex items-center gap-2 px-3 py-2.5 rounded-xl border text-sm font-medium transition-colors ${
                      callbackOpen
                        ? 'border-pm-amber-gold/40 bg-pm-amber-gold/10 text-pm-amber-gold'
                        : 'border-pm-canada-border text-pm-canada-text-muted hover:text-white hover:border-pm-canada-text-muted'
                    }`}
                  >
                    <CalendarPlus size={15} />
                    Schedule a callback
                  </button>

                  <AnimatePresence initial={false}>
                    {callbackOpen && (
                      <motion.div
                        initial={reduceMotion ? {} : { opacity: 0, height: 0 }}
                        animate={reduceMotion ? {} : { opacity: 1, height: 'auto' }}
                        exit={reduceMotion ? {} : { opacity: 0, height: 0 }}
                        transition={{ duration: 0.18, ease: [0.32, 0.72, 0, 1] }}
                        className="overflow-hidden"
                      >
                        <div className="rounded-xl border border-pm-amber-gold/25 bg-pm-amber-gold/5 p-3 space-y-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <input
                              type="datetime-local" value={callbackAt}
                              onChange={e => setCallbackAt(e.target.value)}
                              aria-label="Callback time"
                              className="rounded-md bg-pm-canada-bg/70 border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-amber-gold/50 [color-scheme:dark]"
                            />
                            <input
                              type="text" value={callbackNote}
                              onChange={e => setCallbackNote(e.target.value)}
                              placeholder="Why (optional)"
                              className="flex-1 min-w-[120px] rounded-md bg-pm-canada-bg/70 border border-pm-canada-border px-2 py-1.5 text-xs text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-amber-gold/50"
                            />
                          </div>
                          <button
                            onClick={() => submit('callback', {
                              callback: { due_at: new Date(callbackAt).toISOString(), note: callbackNote },
                            })}
                            className="w-full px-3 py-1.5 rounded-md bg-pm-amber-gold/15 border border-pm-amber-gold/40 text-xs font-semibold text-pm-amber-gold hover:bg-pm-amber-gold/25 transition-colors"
                          >
                            Schedule callback
                          </button>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Secondary outcomes — compact chips */}
                  <div className="flex flex-wrap gap-1.5">
                    {SECONDARY.map(({ d, label, icon: Icon }) => (
                      <button
                        key={d}
                        onClick={() => submit(d)}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-pm-canada-border text-2xs font-medium text-pm-canada-text-muted hover:text-white hover:border-pm-canada-text-muted transition-colors"
                      >
                        <Icon size={13} className="shrink-0" />
                        {label}
                      </button>
                    ))}
                  </div>

                  {/* Notes */}
                  <textarea
                    value={notes}
                    onChange={e => onNotes(e.target.value)}
                    rows={2}
                    placeholder="Add a note (saved with the outcome)…"
                    className="w-full rounded-xl bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-sm text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50 resize-none"
                  />

                  {/* DNC — quiet, confirm-gated footer */}
                  <div className="pt-1 border-t border-pm-canada-border/60">
                    {!dncArmed ? (
                      <button
                        onClick={() => { setDncArmed(true); setCallbackOpen(false) }}
                        className="inline-flex items-center gap-1.5 text-2xs font-medium text-red-400/70 hover:text-red-400 transition-colors mt-2"
                      >
                        <PhoneOff size={12} />
                        Add to do-not-call list
                      </button>
                    ) : (
                      <div className="mt-2 flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/8 px-3 py-1.5">
                        <AlertTriangle size={13} className="text-red-400 shrink-0" />
                        <span className="text-2xs text-red-400 flex-1">Blocks this number immediately.</span>
                        <button onClick={() => submit('dnc')} className="px-2.5 py-1 rounded-md bg-red-500/15 border border-red-500/40 text-2xs font-semibold text-red-400 hover:bg-red-500/25 transition-colors">
                          Confirm
                        </button>
                        <button onClick={() => setDncArmed(false)} className="text-2xs text-pm-canada-text-muted hover:text-white transition-colors">
                          Cancel
                        </button>
                      </div>
                    )}
                  </div>
                </motion.div>
              ) : (
                <motion.div key="countdown" {...stateAnim} className="p-6 flex flex-col items-center text-center gap-4">
                  {lastCompleted && (
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-pm-canada-bg/60 border border-pm-canada-border">
                      <span className="text-2xs text-pm-canada-text-muted">
                        <span className="text-white">{lastCompleted.entry.business_name || lastCompleted.entry.phone_e164}</span>
                        {' · '}
                        {lastCompleted.disposition === 'blocked'
                          ? 'blocked by gate'
                          : lastCompleted.disposition
                            ? DISPOSITION_LABELS[lastCompleted.disposition]
                            : 'logged'}
                      </span>
                      {lastCompleted.disposition === 'callback' && (
                        <CalendarClock size={11} className="text-pm-amber-gold" />
                      )}
                    </div>
                  )}

                  <CountdownRing remaining={wrapRemaining} total={wrapTotal} paused={paused} reduceMotion={!!reduceMotion} />

                  <p className="text-2xs uppercase tracking-[0.14em] text-pm-canada-text-faint -mt-1">
                    {paused ? 'Paused' : 'Dialing the next lead'}
                  </p>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={onDialNow}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-pm-accent text-pm-canada-bg text-sm font-semibold hover:bg-pm-accent/90 active:scale-[0.97] transition-[background-color,transform]"
                    >
                      <PhoneForwarded size={15} />
                      Dial now
                    </button>
                    <button
                      onClick={onTogglePause}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-pm-canada-border text-sm font-medium text-pm-canada-text-muted hover:text-white hover:border-pm-canada-text-muted active:scale-[0.97] transition-[color,border-color,transform]"
                    >
                      {paused ? <PlayCircle size={15} /> : <PauseCircle size={15} />}
                      {paused ? 'Resume' : 'Hold'}
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}

function HeroTile({ icon: Icon, title, sub, onClick, filled }: {
  icon: typeof Sparkles
  title: string
  sub: string
  onClick: () => void
  filled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      className={`group flex flex-col items-start gap-1.5 p-3 rounded-xl border text-left transition-all active:scale-[0.98] ${
        filled
          ? 'border-pm-accent/40 bg-pm-accent/12 hover:bg-pm-accent/18'
          : 'border-pm-canada-border bg-pm-canada-bg/40 hover:border-pm-accent/40 hover:bg-pm-accent/8'
      }`}
    >
      <Icon size={18} className="text-pm-accent" />
      <span className="text-sm font-semibold text-white leading-tight">{title}</span>
      <span className="text-2xs text-pm-canada-text-faint">{sub}</span>
    </button>
  )
}

// Magic UI "Animated Circular Progress Bar" mechanics: the progress arc drains
// via a 1s LINEAR css transition on stroke-dashoffset (continuous between the
// 1s state ticks, off the JS main thread).
function CountdownRing({ remaining, total, paused, reduceMotion }: {
  remaining: number
  total: number
  paused: boolean
  reduceMotion: boolean
}) {
  const R = 44
  const C = 2 * Math.PI * R
  const fraction = total > 0 ? Math.max(0, Math.min(1, remaining / total)) : 0

  return (
    <div className="relative w-28 h-28" aria-live="polite" aria-label={`Next dial in ${remaining} seconds`}>
      <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
        <circle cx="50" cy="50" r={R} fill="none" strokeWidth="6" className="stroke-pm-canada-border" />
        <circle
          cx="50" cy="50" r={R} fill="none" strokeWidth="6" strokeLinecap="round"
          className={paused ? 'stroke-pm-amber-orange' : 'stroke-pm-accent'}
          strokeDasharray={C}
          strokeDashoffset={C * (1 - fraction)}
          style={{ transition: reduceMotion || paused ? 'none' : 'stroke-dashoffset 1s linear' }}
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-3xl font-semibold text-white tabular-nums">
        {Math.max(0, remaining)}
      </span>
    </div>
  )
}
