// The contact the rep is talking to right now: lead details + compliance
// context + inline notes. Notes save with the disposition (server-side).
import { Building2, MapPin, Phone, User, CalendarClock, ShieldCheck } from 'lucide-react'
import type { QueueEntry } from '@/hooks/useDialerSession'

interface Props {
  entry: QueueEntry | null
  notes: string
  onNotes: (v: string) => void
  notesEnabled: boolean
}

export function ContactCard({ entry, notes, onNotes, notesEnabled }: Props) {
  if (!entry) {
    return (
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-8 text-center">
        <p className="text-sm text-pm-canada-text-muted">
          Start a session and the current contact appears here.
        </p>
      </div>
    )
  }

  const isLead = entry.kind === 'lead'
  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-white truncate flex items-center gap-2">
            <Building2 size={17} className="text-pm-accent shrink-0" />
            {entry.business_name || 'Unnamed business'}
          </h2>
          <div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-pm-canada-text-muted">
            {entry.contact_name && (
              <span className="inline-flex items-center gap-1"><User size={12} />{entry.contact_name}</span>
            )}
            <span className="inline-flex items-center gap-1 tabular-nums"><Phone size={12} />{entry.phone_e164}</span>
            {isLead && (entry.city || entry.province) && (
              <span className="inline-flex items-center gap-1"><MapPin size={12} />{[entry.city, entry.province].filter(Boolean).join(', ')}</span>
            )}
          </div>
        </div>
        {isLead && (
          <span className="shrink-0 px-2 py-0.5 rounded-full text-2xs font-medium bg-pm-accent/10 text-pm-accent border border-pm-accent/20">
            {entry.stage.replace(/_/g, ' ')}
          </span>
        )}
      </div>

      <div className="flex items-center gap-2 text-2xs text-pm-canada-text-faint">
        <ShieldCheck size={12} className="text-pm-accent" />
        <span>
          {entry.local_time ? `${entry.local_time.slice(11, 16)} for them` : 'Local time unknown'}
          {entry.window_label ? ` · ${entry.window_label}` : ''}
        </span>
      </div>

      {entry.kind === 'callback' && entry.note && (
        <div className="rounded-lg bg-pm-amber-gold/8 border border-pm-amber-gold/20 px-3 py-2 text-xs text-pm-amber-gold flex items-start gap-2">
          <CalendarClock size={13} className="mt-0.5 shrink-0" />
          <span>Callback note: {entry.note}</span>
        </div>
      )}
      {isLead && entry.notes && (
        <div className="rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2">
          <p className="text-2xs uppercase tracking-wide text-pm-canada-text-faint mb-1">Lead notes</p>
          <p className="text-xs text-pm-canada-text-muted whitespace-pre-wrap line-clamp-4">{entry.notes}</p>
        </div>
      )}

      <div>
        <label htmlFor="dialer-call-notes" className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">
          Call notes
        </label>
        <textarea
          id="dialer-call-notes"
          value={notes}
          onChange={e => onNotes(e.target.value)}
          disabled={!notesEnabled}
          rows={4}
          placeholder={notesEnabled ? 'Type while you talk — saved with the disposition' : 'Notes open when a call starts'}
          className="mt-1 w-full rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-sm text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50 disabled:opacity-50 resize-none"
        />
      </div>
    </div>
  )
}
