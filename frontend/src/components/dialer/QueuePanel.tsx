// Upcoming work: due callbacks pinned on top, then the rep's callable leads.
// Every entry carries the backend's dial-time gate annotation so the rep can
// see WHY something is skipped (DNC / outside window) before it's ever dialed.
import { CalendarClock, PhoneOff, Clock } from 'lucide-react'
import type { DialerQueue, QueueCallback, QueueLead } from '@/lib/dialer-api'
import type { QueueEntry } from '@/hooks/useDialerSession'

interface Props {
  queue: DialerQueue | null
  currentEntry: QueueEntry | null
  dialedIds: Set<string>
}

export function QueuePanel({ queue, currentEntry, dialedIds }: Props) {
  if (!queue) return null
  const callbacks = queue.callbacks
  const leads = queue.leads

  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-pm-canada-border flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-white">Call queue</h2>
        <span className="text-2xs text-pm-canada-text-faint">
          {callbacks.length + leads.length} in list
        </span>
      </div>

      <div className="max-h-[560px] overflow-y-auto divide-y divide-pm-canada-border/60">
        {callbacks.map(cb => (
          <Row
            key={`cb-${cb.id}`}
            entry={cb}
            active={currentEntry?.id === cb.id}
            done={dialedIds.has(cb.id)}
            sub={<span className="inline-flex items-center gap-1 text-pm-amber-gold"><CalendarClock size={11} />Callback {new Date(cb.due_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}</span>}
          />
        ))}
        {leads.map(ld => (
          <Row
            key={ld.id}
            entry={ld}
            active={currentEntry?.id === ld.id}
            done={dialedIds.has(ld.id)}
            sub={<span className="text-pm-canada-text-faint">{[ld.stage.replace(/_/g, ' '), ld.city].filter(Boolean).join(' · ')}</span>}
          />
        ))}
        {callbacks.length + leads.length === 0 && (
          <div className="px-4 py-10 text-center text-sm text-pm-canada-text-muted">
            No callable leads assigned to you yet.
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ entry, active, done, sub }: {
  entry: QueueLead | QueueCallback
  active: boolean
  done: boolean
  sub: React.ReactNode
}) {
  return (
    <div className={`px-4 py-2.5 flex items-center gap-3 ${active ? 'bg-pm-accent/8 border-l-2 border-l-pm-accent' : ''} ${done && !active ? 'opacity-40' : ''}`}>
      <GateDot entry={entry} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white truncate">{entry.business_name || entry.contact_name || entry.phone_e164}</p>
        <p className="text-2xs truncate">{sub}</p>
      </div>
      {entry.local_time && (
        <span className="text-2xs text-pm-canada-text-faint tabular-nums shrink-0">
          {entry.local_time.slice(11, 16)} local
        </span>
      )}
    </div>
  )
}

function GateDot({ entry }: { entry: QueueLead | QueueCallback }) {
  if (entry.on_dnc) {
    return <PhoneOff size={13} className="text-red-400 shrink-0" aria-label="On do-not-call list" />
  }
  if (!entry.callable_now) {
    return <Clock size={13} className="text-pm-amber-orange shrink-0" aria-label="Outside calling window" />
  }
  return <span className="w-2 h-2 rounded-full bg-pm-accent shrink-0" aria-label="Callable now" />
}
