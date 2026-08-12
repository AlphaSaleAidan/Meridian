// Booking slot-picker — fired from the "Meeting booked" outcome. Picks a
// date/time/duration, then books: the backend promotes the phone lead into the
// pipeline AND creates the calendar appointment in one call. Quick-slot chips
// keep the common case (tomorrow AM/PM) to two clicks.
import { useState } from 'react'
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion'
import { CalendarCheck, X } from 'lucide-react'
import type { QueueEntry } from '@/hooks/useDialerSession'

interface Props {
  open: boolean
  entry: QueueEntry | null
  onCancel: () => void
  onConfirm: (spec: { scheduled_at: string; duration_min: number; title: string; notes: string }) => Promise<void>
}

function pad(n: number) { return String(n).padStart(2, '0') }
function localValue(d: Date) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
function atHour(daysAhead: number, hour: number) {
  const d = new Date()
  d.setDate(d.getDate() + daysAhead)
  d.setHours(hour, 0, 0, 0)
  return d
}

const QUICK = [
  { label: 'Tomorrow 10a', d: () => atHour(1, 10) },
  { label: 'Tomorrow 2p', d: () => atHour(1, 14) },
  { label: 'In 2 days 11a', d: () => atHour(2, 11) },
]
const DURATIONS = [15, 30, 45, 60]

export function BookingModal({ open, entry, onCancel, onConfirm }: Props) {
  const reduceMotion = useReducedMotion()
  const [when, setWhen] = useState(() => localValue(atHour(1, 10)))
  const [duration, setDuration] = useState(30)
  const [notes, setNotes] = useState('')
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const confirm = async () => {
    setSaving(true); setErr(null)
    try {
      await onConfirm({
        scheduled_at: new Date(when).toISOString(),
        duration_min: duration,
        title: `Demo — ${entry?.business_name || 'Prospect'}`,
        notes,
      })
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Could not book')
      setSaving(false)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="booking-overlay"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: reduceMotion ? 0.01 : 0.16 }}
          className="fixed inset-0 z-[80] bg-black/70 flex items-center justify-center p-4"
        >
          <motion.div
            key="booking-dialog"
            initial={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.96, y: 8 }}
            animate={reduceMotion ? { opacity: 1 } : { opacity: 1, scale: 1, y: 0,
              transition: { type: 'spring', stiffness: 380, damping: 30 } }}
            exit={reduceMotion ? { opacity: 0 } : { opacity: 0, scale: 0.98, transition: { duration: 0.14 } }}
            role="dialog" aria-modal="true" aria-label="Book a demo"
            className="w-full max-w-md bg-pm-canada-surface border border-pm-canada-border rounded-2xl shadow-[0_24px_64px_-12px_rgba(0,0,0,0.7)] overflow-hidden"
          >
            <div className="h-0.5 w-full bg-gradient-to-r from-transparent via-pm-accent to-transparent" />
            <div className="p-5 space-y-4">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 w-9 h-9 rounded-full bg-pm-accent/12 border border-pm-accent/25 flex items-center justify-center shrink-0">
                  <CalendarCheck size={16} className="text-pm-accent" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-2xs uppercase tracking-[0.14em] text-pm-accent/80">Book a demo</p>
                  <h2 className="text-base font-semibold text-white truncate">{entry?.business_name || 'Prospect'}</h2>
                  <p className="text-2xs text-pm-canada-text-faint">Books the slot and sends this lead to your pipeline.</p>
                </div>
                <button onClick={onCancel} aria-label="Cancel" className="text-pm-canada-text-faint hover:text-white transition-colors">
                  <X size={16} />
                </button>
              </div>

              <div className="flex flex-wrap gap-1.5">
                {QUICK.map(q => (
                  <button
                    key={q.label}
                    onClick={() => setWhen(localValue(q.d()))}
                    className="px-2.5 py-1.5 rounded-lg border border-pm-canada-border text-2xs font-medium text-pm-canada-text-muted hover:text-pm-accent hover:border-pm-accent/40 transition-colors"
                  >
                    {q.label}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label htmlFor="booking-when" className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">When</label>
                  <input
                    id="booking-when" type="datetime-local" value={when}
                    onChange={e => setWhen(e.target.value)}
                    className="mt-1 block rounded-lg bg-pm-canada-bg/70 border border-pm-canada-border px-2.5 py-2 text-sm text-white focus:outline-none focus:border-pm-accent/50 [color-scheme:dark]"
                  />
                </div>
                <div>
                  <span className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">Length</span>
                  <div className="mt-1 flex gap-1">
                    {DURATIONS.map(d => (
                      <button
                        key={d}
                        onClick={() => setDuration(d)}
                        className={`px-2.5 py-2 rounded-lg text-xs font-medium border transition-colors ${
                          duration === d
                            ? 'border-pm-accent/40 bg-pm-accent/12 text-pm-accent'
                            : 'border-pm-canada-border text-pm-canada-text-muted hover:text-white'
                        }`}
                      >
                        {d}m
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <input
                type="text" value={notes} onChange={e => setNotes(e.target.value)}
                placeholder="Agenda / notes (optional)"
                className="w-full rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-sm text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50"
              />

              {err && <p className="text-2xs text-red-400">{err}</p>}

              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={confirm} disabled={saving}
                  className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-pm-accent text-pm-canada-bg text-sm font-semibold hover:bg-pm-accent/90 active:scale-[0.98] disabled:opacity-60 transition-[background-color,transform]"
                >
                  <CalendarCheck size={15} />
                  {saving ? 'Booking…' : 'Book & send to pipeline'}
                </button>
                <button
                  onClick={onCancel}
                  className="px-4 py-2.5 rounded-lg border border-pm-canada-border text-sm font-medium text-pm-canada-text-muted hover:text-white transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
