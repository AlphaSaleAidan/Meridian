// The full Auto Dialer tab, market-agnostic — Canada and US portal pages are
// thin wrappers around this. Owns nothing itself: state machine in
// useDialerSession, presentation in the sibling components.
import { useMemo, useState } from 'react'
import { Phone, PlayCircle, AlertTriangle } from 'lucide-react'
import { DISPOSITION_LABELS, type DialerMarket } from '@/lib/dialer-api'
import { useDialerSession } from '@/hooks/useDialerSession'
import { SessionHUD } from './SessionHUD'
import { QueuePanel } from './QueuePanel'
import { ContactCard } from './ContactCard'
import { DispositionGrid } from './DispositionGrid'
import { CallControls } from './CallControls'

const WRAP_CHOICES = [5, 10, 15, 30, 60]

export function AutoDialerScreen({ market }: { market: DialerMarket }) {
  const d = useDialerSession(market)
  const [wrapUp, setWrapUp] = useState(15)

  const dialedIds = useMemo(
    () => new Set(d.log.map(l => l.entry.id)),
    [d.log],
  )
  const callableCount = d.queue
    ? d.queue.callbacks.length + d.queue.leads.filter(l => l.callable_now).length
    : 0
  const idle = d.phase === 'idle' || d.phase === 'complete'

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-white flex items-center gap-2">
            <Phone size={20} className="text-pm-accent" />
            Auto Dialer
          </h1>
          <p className="text-xs text-pm-canada-text-muted mt-0.5">
            Power dial your queue — callbacks first, one call at a time, auto-advance after wrap-up.
          </p>
        </div>

        {idle && (
          <div className="flex items-center gap-2">
            <label htmlFor="dialer-wrapup" className="text-2xs text-pm-canada-text-faint uppercase tracking-wide">
              Wrap-up
            </label>
            <select
              id="dialer-wrapup"
              value={wrapUp}
              onChange={e => setWrapUp(Number(e.target.value))}
              className="rounded-lg bg-pm-canada-surface border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-accent/50"
            >
              {WRAP_CHOICES.map(s => <option key={s} value={s}>{s}s</option>)}
            </select>
            <button
              onClick={() => d.start(wrapUp)}
              disabled={d.queueLoading || callableCount === 0 || d.phase === 'starting'}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-pm-accent text-pm-canada-bg text-sm font-semibold hover:bg-pm-accent/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <PlayCircle size={16} />
              {d.phase === 'complete' ? 'Restart session' : 'Start dialing'}
              {callableCount > 0 && <span className="tabular-nums">({callableCount})</span>}
            </button>
          </div>
        )}
      </div>

      {d.error && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 flex items-center gap-2 text-xs text-red-400">
          <AlertTriangle size={14} className="shrink-0" />
          {d.error}
        </div>
      )}

      <SessionHUD
        phase={d.phase}
        paused={d.paused}
        session={d.session}
        callSeconds={d.callSeconds}
        wrapRemaining={d.wrapRemaining}
        needsDisposition={d.needsDisposition}
        remaining={d.remaining}
        softphoneMode={d.softphoneMode}
        devStore={d.queue?.dev_store ?? false}
        onTogglePause={d.togglePause}
        onStop={d.stop}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-1">
          <QueuePanel queue={d.queue} currentEntry={d.currentEntry} dialedIds={dialedIds} />
        </div>

        <div className="lg:col-span-2 space-y-4">
          <ContactCard
            entry={d.currentEntry}
            notes={d.notes}
            onNotes={d.setNotes}
            notesEnabled={d.phase === 'connected' || (d.phase === 'wrapup' && d.needsDisposition)}
          />
          <CallControls phase={d.phase} onHangup={d.hangup} onMute={d.setMuted} />
          <DispositionGrid
            enabled={d.phase === 'wrapup' && d.needsDisposition}
            onSubmit={d.submitDisposition}
          />
          {d.log.length > 0 && <RecentActivity log={d.log} />}
        </div>
      </div>
    </div>
  )
}

function RecentActivity({ log }: { log: ReturnType<typeof useDialerSession>['log'] }) {
  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-hidden">
      <div className="px-4 py-2.5 border-b border-pm-canada-border">
        <h2 className="text-sm font-semibold text-white">This session</h2>
      </div>
      <div className="max-h-56 overflow-y-auto divide-y divide-pm-canada-border/60">
        {log.map((item, i) => (
          <div key={`${item.entry.id}-${i}`} className="px-4 py-2 flex items-center gap-3 text-xs">
            <span className="text-white truncate flex-1">
              {item.entry.business_name || item.entry.contact_name || item.entry.phone_e164}
            </span>
            {item.disposition === 'blocked' ? (
              <span className="shrink-0 px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-2xs font-medium">
                Blocked · {item.blockedReason === 'dnc' ? 'DNC list' : item.blockedReason === 'calling_window' ? 'outside window' : item.blockedReason}
              </span>
            ) : (
              <span className="shrink-0 px-2 py-0.5 rounded-full bg-pm-canada-bg text-pm-canada-text-muted text-2xs font-medium">
                {item.disposition ? DISPOSITION_LABELS[item.disposition] : '—'}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
