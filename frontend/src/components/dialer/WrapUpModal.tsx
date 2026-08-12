// Wrap-up popup — appears the moment a call ends.
//
// Mechanics adapted from the FRONTEND UI DEV LINKS component list:
//   * Aceternity "Animated Modal" (ui.aceternity.com/components/animated-modal):
//     AnimatePresence overlay + spring content entrance. Stock demo values
//     (rotateX 40, damping 15, 10px backdrop blur) are deliberately flattened —
//     this popup fires after EVERY call, so entrance is scale .96 / y 8 /
//     spring(380,30) ≈ 200ms, exit subtler and faster, blur capped at 3px.
//   * Magic UI "Animated Circular Progress Bar": pure-SVG ring driven by a 1s
//     linear CSS transition on stroke-dashoffset — drains continuously between
//     countdown ticks with zero JS per frame.
// Re-skinned entirely to the pm-canada palette (no library defaults survive).
// Reduced motion: entrance/exit collapse to a fade, the ring steps per second.
import { useEffect, useRef } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { CalendarClock, PauseCircle, PhoneForwarded, PlayCircle } from 'lucide-react'
import { DISPOSITION_LABELS, fmtDuration, type Disposition } from '@/lib/dialer-api'
import type { CompletedCall, QueueEntry } from '@/hooks/useDialerSession'
import { DispositionGrid } from './DispositionGrid'

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

export function WrapUpModal({
  open, needsDisposition, entry, callSeconds, wrapRemaining, wrapTotal, paused,
  lastCompleted, notes, onNotes, onSubmit, onDialNow, onTogglePause,
}: Props) {
  const reduceMotion = useReducedMotion()
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) dialogRef.current?.focus()
  }, [open, needsDisposition])

  const overlayAnim = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 },
        transition: { duration: 0.01 } }
    : { initial: { opacity: 0, backdropFilter: 'blur(0px)' },
        animate: { opacity: 1, backdropFilter: 'blur(3px)' },
        exit: { opacity: 0, backdropFilter: 'blur(0px)' },
        transition: { duration: 0.16 } }

  const dialogAnim = reduceMotion
    ? { initial: { opacity: 0 }, animate: { opacity: 1 }, exit: { opacity: 0 },
        transition: { duration: 0.01 } }
    : { initial: { opacity: 0, scale: 0.96, y: 8 },
        animate: { opacity: 1, scale: 1, y: 0,
          transition: { type: 'spring' as const, stiffness: 380, damping: 30 } },
        exit: { opacity: 0, scale: 0.98,
          transition: { duration: 0.14, ease: [0.32, 0.72, 0, 1] as const } } }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="wrapup-overlay"
          {...overlayAnim}
          className="fixed inset-0 z-[70] bg-black/60 flex items-center justify-center p-4"
        >
          <motion.div
            key="wrapup-dialog"
            {...dialogAnim}
            ref={dialogRef}
            role="dialog"
            aria-modal="true"
            aria-label={needsDisposition ? 'Call wrap-up' : 'Next dial countdown'}
            tabIndex={-1}
            className="w-full max-w-lg bg-pm-canada-surface border border-pm-canada-border rounded-2xl shadow-[0_16px_48px_rgba(0,0,0,0.5)] outline-none overflow-hidden"
          >
            <AnimatePresence mode="wait" initial={false}>
              {needsDisposition ? (
                <motion.div
                  key="disposition"
                  initial={reduceMotion ? { opacity: 0 } : { opacity: 0, filter: 'blur(3px)' }}
                  animate={reduceMotion ? { opacity: 1 } : { opacity: 1, filter: 'blur(0px)' }}
                  exit={reduceMotion ? { opacity: 0 } : { opacity: 0, filter: 'blur(3px)' }}
                  transition={{ duration: reduceMotion ? 0.01 : 0.15 }}
                  className="p-5 space-y-4"
                >
                  <div className="flex items-baseline justify-between gap-3">
                    <div className="min-w-0">
                      <h2 className="text-base font-semibold text-white">Call ended — how did it go?</h2>
                      <p className="text-xs text-pm-canada-text-muted mt-0.5 truncate">
                        {entry?.business_name || entry?.contact_name || entry?.phone_e164}
                        <span className="text-pm-canada-text-faint"> · {fmtDuration(callSeconds)} on the line</span>
                      </p>
                    </div>
                  </div>

                  <div>
                    <label htmlFor="wrapup-notes" className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">
                      Call notes
                    </label>
                    <textarea
                      id="wrapup-notes"
                      value={notes}
                      onChange={e => onNotes(e.target.value)}
                      rows={3}
                      placeholder="Finish your notes — saved with the disposition"
                      className="mt-1 w-full rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-sm text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50 resize-none"
                    />
                  </div>

                  <DispositionGrid enabled onSubmit={onSubmit} />
                </motion.div>
              ) : (
                <motion.div
                  key="countdown"
                  initial={reduceMotion ? { opacity: 0 } : { opacity: 0, filter: 'blur(3px)' }}
                  animate={reduceMotion ? { opacity: 1 } : { opacity: 1, filter: 'blur(0px)' }}
                  exit={reduceMotion ? { opacity: 0 } : { opacity: 0, filter: 'blur(3px)' }}
                  transition={{ duration: reduceMotion ? 0.01 : 0.15 }}
                  className="p-6 flex flex-col items-center text-center gap-4"
                >
                  {lastCompleted && (
                    <p className="text-xs text-pm-canada-text-muted">
                      <span className="text-white">{lastCompleted.entry.business_name || lastCompleted.entry.phone_e164}</span>
                      {' — '}
                      {lastCompleted.disposition === 'blocked'
                        ? 'blocked by the compliance gate'
                        : lastCompleted.disposition
                          ? DISPOSITION_LABELS[lastCompleted.disposition]
                          : 'logged'}
                      {lastCompleted.disposition === 'callback' && (
                        <CalendarClock size={12} className="inline ml-1 text-pm-amber-gold" />
                      )}
                    </p>
                  )}

                  <CountdownRing
                    remaining={wrapRemaining}
                    total={wrapTotal}
                    paused={paused}
                    reduceMotion={!!reduceMotion}
                  />

                  <p className="text-2xs uppercase tracking-wide text-pm-canada-text-faint -mt-1">
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

// Magic UI "Animated Circular Progress Bar" mechanics: two SVG circles, the
// progress arc drains via a 1s LINEAR css transition on stroke-dashoffset
// (linear = correct easing for progress; continuous between 1s ticks).
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
        <circle cx="50" cy="50" r={R} fill="none" strokeWidth="6"
                className="stroke-pm-canada-border" />
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
