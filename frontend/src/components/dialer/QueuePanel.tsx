// The rep's ready-to-dial pool. Each row shows the compliance gate state
// (callable / DNC / outside-window) and the "has ___ POS" enrichment, so the
// rep sees who's next and why before dialing. Recapture ordering is server-side
// (next_action_at) — this list is already the ready queue.
//
// The Regions block on top breaks the pool down by state/province and lets the
// rep pick which regions to work — the selection scopes the visible list AND
// the next dialing session (empty selection = dial everything).
import { PhoneOff, Clock, CreditCard, MapPin } from 'lucide-react'
import { fmtCents, posLabel, type DialerQueue, type QueueLead } from '@/lib/dialer-api'
import type { QueueEntry } from '@/hooks/useDialerSession'

interface Props {
  queue: DialerQueue | null
  currentEntry: QueueEntry | null
  dialedIds: Set<string>
  regionCounts: [string, number][]
  selectedRegions: string[]
  onToggleRegion: (region: string) => void
  onClearRegions: () => void
}

export function QueuePanel({
  queue, currentEntry, dialedIds,
  regionCounts, selectedRegions, onToggleRegion, onClearRegions,
}: Props) {
  if (!queue) return null
  const leads = queue.leads

  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-pm-canada-border flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-white">Call queue</h2>
        <span className="text-2xs text-pm-canada-text-faint">
          {leads.length} ready{selectedRegions.length > 0 && ` · ${selectedRegions.join(', ')}`}
        </span>
      </div>

      {regionCounts.length > 1 && (
        <div className="px-4 py-2.5 border-b border-pm-canada-border/60">
          <p className="text-2xs text-pm-canada-text-faint uppercase tracking-wide flex items-center gap-1 mb-1.5">
            <MapPin size={10} />Regions — pick what to dial
          </p>
          <div className="flex items-center gap-1.5 flex-wrap">
            <button
              onClick={onClearRegions}
              className={`px-2 py-0.5 rounded-full text-2xs font-medium transition-colors ${
                selectedRegions.length === 0
                  ? 'bg-pm-accent/15 text-pm-accent'
                  : 'bg-pm-canada-bg text-pm-canada-text-muted hover:text-white'
              }`}
            >
              All
            </button>
            {regionCounts.map(([region, count]) => (
              <button
                key={region}
                onClick={() => onToggleRegion(region)}
                aria-pressed={selectedRegions.includes(region)}
                className={`px-2 py-0.5 rounded-full text-2xs font-medium transition-colors ${
                  selectedRegions.includes(region)
                    ? 'bg-pm-accent/15 text-pm-accent'
                    : 'bg-pm-canada-bg text-pm-canada-text-muted hover:text-white'
                }`}
              >
                {region} <span className="tabular-nums">{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="max-h-[560px] overflow-y-auto divide-y divide-pm-canada-border/60">
        {leads.map(ld => (
          <Row key={ld.id} entry={ld} active={currentEntry?.id === ld.id} done={dialedIds.has(ld.id)} />
        ))}
        {leads.length === 0 && (
          <div className="px-4 py-10 text-center text-sm text-pm-canada-text-muted">
            {selectedRegions.length > 0
              ? 'No leads ready in the selected regions — widen the selection.'
              : 'No leads ready to dial. Import a list or add one to get started.'}
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ entry, active, done }: { entry: QueueLead; active: boolean; done: boolean }) {
  return (
    <div className={`px-4 py-2.5 flex items-center gap-3 ${active ? 'bg-pm-accent/8 border-l-2 border-l-pm-accent' : ''} ${done && !active ? 'opacity-40' : ''}`}>
      <GateDot entry={entry} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white truncate">{entry.business_name || entry.contact_name || entry.phone_e164}</p>
        <p className="text-2xs truncate flex items-center gap-1.5 text-pm-canada-text-faint">
          <span className="inline-flex items-center gap-0.5">
            <CreditCard size={10} />{posLabel(entry.pos_system)}
          </span>
          {entry.est_monthly_value > 0 && <span>· {fmtCents(entry.est_monthly_value)}</span>}
          {(entry.city || entry.province) && (
            <span>· {[entry.city, entry.province].filter(Boolean).join(', ')}</span>
          )}
        </p>
      </div>
      {entry.local_time && (
        <span className="text-2xs text-pm-canada-text-faint tabular-nums shrink-0">
          {entry.local_time.slice(11, 16)} local
        </span>
      )}
    </div>
  )
}

function GateDot({ entry }: { entry: QueueLead }) {
  if (entry.on_dnc) {
    return <PhoneOff size={13} className="text-red-400 shrink-0" aria-label="On do-not-call list" />
  }
  if (!entry.callable_now) {
    return <Clock size={13} className="text-pm-amber-orange shrink-0" aria-label="Outside calling window" />
  }
  return <span className="w-2 h-2 rounded-full bg-pm-accent shrink-0" aria-label="Callable now" />
}
