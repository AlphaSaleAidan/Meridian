// The contact the rep is talking to right now: business identity + enrichment
// (POS system, est. value, vertical, attempt history) + inline notes + a
// one-click "Send to pipeline". Notes save with the disposition.
import { useState } from 'react'
import {
  Building2, Globe, MapPin, Phone, User, ShieldCheck, Repeat,
  CreditCard, DollarSign, ArrowRightCircle, Check,
} from 'lucide-react'
import { DISPOSITION_LABELS, fmtCents, posLabel } from '@/lib/dialer-api'
import type { QueueEntry } from '@/hooks/useDialerSession'

interface Props {
  entry: QueueEntry | null
  notes: string
  onNotes: (v: string) => void
  notesEnabled: boolean
  onSendToPipeline: () => Promise<void>
}

const POS_TONE: Record<string, string> = {
  none: 'bg-pm-amber-orange/12 text-pm-amber-orange border-pm-amber-orange/25',
  unknown: 'bg-pm-canada-bg text-pm-canada-text-muted border-pm-canada-border',
}

export function ContactCard({ entry, notes, onNotes, notesEnabled, onSendToPipeline }: Props) {
  const [promoting, setPromoting] = useState(false)
  const [promoted, setPromoted] = useState(false)

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
  const pos = isLead ? entry.pos_system : 'unknown'
  const posTone = POS_TONE[pos] ?? 'bg-pm-accent/10 text-pm-accent border-pm-accent/20'

  const promote = async () => {
    setPromoting(true)
    try { await onSendToPipeline(); setPromoted(true) }
    finally { setPromoting(false) }
  }

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
            {isLead && entry.website && (
              <a href={entry.website.startsWith('http') ? entry.website : `https://${entry.website}`}
                 target="_blank" rel="noreferrer"
                 className="inline-flex items-center gap-1 text-pm-accent/80 hover:text-pm-accent">
                <Globe size={12} />{entry.website.replace(/^https?:\/\//, '')}
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Enrichment strip — the "has ___ POS" + value context on every call */}
      {isLead && (
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-medium border ${posTone}`}>
            <CreditCard size={12} />{posLabel(pos)}
          </span>
          {entry.est_monthly_value > 0 && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-medium bg-pm-canada-bg border border-pm-canada-border text-pm-canada-text-muted">
              <DollarSign size={12} />{fmtCents(entry.est_monthly_value)} est.
            </span>
          )}
          {entry.vertical && (
            <span className="inline-flex items-center px-2.5 py-1 rounded-lg text-2xs font-medium bg-pm-canada-bg border border-pm-canada-border text-pm-canada-text-muted capitalize">
              {entry.vertical}
            </span>
          )}
          {entry.attempts > 0 && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-2xs font-medium bg-pm-canada-bg border border-pm-canada-border text-pm-canada-text-faint">
              <Repeat size={12} />attempt #{entry.attempts + 1}
              {entry.last_disposition && ` · last: ${DISPOSITION_LABELS[entry.last_disposition]}`}
            </span>
          )}
        </div>
      )}

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-2xs text-pm-canada-text-faint min-w-0">
          <ShieldCheck size={12} className="text-pm-accent shrink-0" />
          <span className="truncate">
            {entry.local_time ? `${entry.local_time.slice(11, 16)} for them` : 'Local time unknown'}
            {entry.window_label ? ` · ${entry.window_label}` : ''}
          </span>
        </div>
        {isLead && (
          <button
            onClick={promote}
            disabled={promoting || promoted}
            className={`shrink-0 inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-2xs font-medium border transition-colors ${
              promoted
                ? 'border-pm-accent/40 bg-pm-accent/10 text-pm-accent'
                : 'border-pm-canada-border text-pm-canada-text-muted hover:text-pm-accent hover:border-pm-accent/40'
            } disabled:opacity-60`}
            title="Create a pipeline lead from this number"
          >
            {promoted ? <Check size={13} /> : <ArrowRightCircle size={13} />}
            {promoted ? 'In pipeline' : 'Send to pipeline'}
          </button>
        )}
      </div>

      <div>
        <label htmlFor="dialer-call-notes" className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">
          Call notes
        </label>
        <textarea
          id="dialer-call-notes"
          value={notes}
          onChange={e => onNotes(e.target.value)}
          disabled={!notesEnabled}
          rows={3}
          placeholder={notesEnabled ? 'Type while you talk — saved with the disposition' : 'Notes open when a call starts'}
          className="mt-1 w-full rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-sm text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50 disabled:opacity-50 resize-none"
        />
      </div>
    </div>
  )
}
