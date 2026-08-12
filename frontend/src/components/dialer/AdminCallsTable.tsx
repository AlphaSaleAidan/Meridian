// Call history with post-hoc processing: filter, inspect notes, correct a
// disposition (audited server-side via disposition_by).
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronDown, ChevronUp } from 'lucide-react'
import {
  DISPOSITION_LABELS, dialerAdminApi, fmtDuration,
  type DialerCall, type Disposition,
} from '@/lib/dialer-api'

const ALL_DISPOSITIONS = Object.keys(DISPOSITION_LABELS) as Disposition[]

export function AdminCallsTable() {
  const queryClient = useQueryClient()
  const [days, setDays] = useState(7)
  const [disposition, setDisposition] = useState('')
  const [openId, setOpenId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['dialer-admin', 'calls', days, disposition],
    queryFn: () => dialerAdminApi.calls({ days, disposition: disposition || undefined, limit: 300 }),
    refetchInterval: 15000,
  })

  const patch = useMutation({
    mutationFn: ({ id, body }: { id: string; body: { disposition?: Disposition; notes?: string } }) =>
      dialerAdminApi.patchCall(id, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['dialer-admin'] }),
  })

  const calls = data?.calls ?? []

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          aria-label="Time range"
          className="rounded-lg bg-pm-canada-surface border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-accent/50"
        >
          <option value={1}>Today</option>
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
        </select>
        <select
          value={disposition}
          onChange={e => setDisposition(e.target.value)}
          aria-label="Disposition filter"
          className="rounded-lg bg-pm-canada-surface border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-accent/50"
        >
          <option value="">All dispositions</option>
          {ALL_DISPOSITIONS.map(d => <option key={d} value={d}>{DISPOSITION_LABELS[d]}</option>)}
        </select>
        <span className="text-2xs text-pm-canada-text-faint ml-auto">{calls.length} calls</span>
      </div>

      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-pm-canada-border text-2xs uppercase tracking-wide text-pm-canada-text-faint">
              <th className="px-4 py-2.5 font-medium">When</th>
              <th className="px-4 py-2.5 font-medium">Rep</th>
              <th className="px-4 py-2.5 font-medium">Contact</th>
              <th className="px-4 py-2.5 font-medium">Talk</th>
              <th className="px-4 py-2.5 font-medium">Outcome</th>
              <th className="px-2 py-2.5" />
            </tr>
          </thead>
          <tbody className="divide-y divide-pm-canada-border/60">
            {isLoading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-pm-canada-text-muted">Loading…</td></tr>
            )}
            {!isLoading && calls.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-pm-canada-text-muted">No calls in this window.</td></tr>
            )}
            {calls.map(c => (
              <CallRow
                key={c.id}
                call={c}
                open={openId === c.id}
                onToggle={() => setOpenId(openId === c.id ? null : c.id)}
                onPatch={body => patch.mutate({ id: c.id, body })}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function OutcomeBadge({ call }: { call: DialerCall }) {
  if (call.status === 'blocked') {
    return (
      <span className="px-2 py-0.5 rounded-full bg-red-500/10 text-red-400 text-2xs font-medium">
        Blocked · {call.blocked_reason === 'dnc' ? 'DNC' : call.blocked_reason === 'calling_window' ? 'window' : call.blocked_reason}
      </span>
    )
  }
  if (call.status === 'connected' || call.status === 'ringing' || call.status === 'dialing') {
    return <span className="px-2 py-0.5 rounded-full bg-pm-accent/10 text-pm-accent text-2xs font-medium animate-pulse">Live · {call.status}</span>
  }
  if (!call.disposition) {
    return <span className="px-2 py-0.5 rounded-full bg-pm-canada-bg text-pm-canada-text-faint text-2xs font-medium">No disposition</span>
  }
  const positive = call.disposition === 'meeting_booked' || call.disposition === 'interested'
  return (
    <span className={`px-2 py-0.5 rounded-full text-2xs font-medium ${positive ? 'bg-pm-accent/10 text-pm-accent' : 'bg-pm-canada-bg text-pm-canada-text-muted'}`}>
      {DISPOSITION_LABELS[call.disposition]}
    </span>
  )
}

function CallRow({ call, open, onToggle, onPatch }: {
  call: DialerCall
  open: boolean
  onToggle: () => void
  onPatch: (body: { disposition?: Disposition; notes?: string }) => void
}) {
  const [notesDraft, setNotesDraft] = useState<string | null>(null)
  const when = new Date(call.created_at)

  return (
    <>
      <tr className="hover:bg-pm-canada-bg/40 cursor-pointer" onClick={onToggle}>
        <td className="px-4 py-2.5 text-xs text-pm-canada-text-muted whitespace-nowrap tabular-nums">
          {when.toLocaleDateString([], { month: 'short', day: 'numeric' })}{' '}
          {when.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
        </td>
        <td className="px-4 py-2.5 text-xs text-white whitespace-nowrap">{call.rep_name}</td>
        <td className="px-4 py-2.5 text-xs">
          <span className="text-white">{call.business_name || call.contact_name || '—'}</span>
          <span className="text-pm-canada-text-faint ml-2 tabular-nums">{call.phone_e164}</span>
          {call.sim && <span className="ml-2 text-2xs text-pm-amber-orange">SIM</span>}
        </td>
        <td className="px-4 py-2.5 text-xs text-pm-canada-text-muted tabular-nums">{fmtDuration(call.talk_seconds)}</td>
        <td className="px-4 py-2.5"><OutcomeBadge call={call} /></td>
        <td className="px-2 py-2.5 text-pm-canada-text-faint">{open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</td>
      </tr>
      {open && (
        <tr className="bg-pm-canada-bg/30">
          <td colSpan={6} className="px-4 py-3">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1">
                <p className="text-2xs uppercase tracking-wide text-pm-canada-text-faint mb-1">Notes</p>
                <textarea
                  value={notesDraft ?? call.notes}
                  onChange={e => setNotesDraft(e.target.value)}
                  rows={2}
                  className="w-full rounded-lg bg-pm-canada-surface border border-pm-canada-border px-3 py-2 text-xs text-white focus:outline-none focus:border-pm-accent/50 resize-none"
                />
              </div>
              <div className="sm:w-56 space-y-2">
                <p className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">Correct disposition</p>
                <select
                  value={call.disposition ?? ''}
                  onChange={e => e.target.value && onPatch({ disposition: e.target.value as Disposition })}
                  className="w-full rounded-lg bg-pm-canada-surface border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-accent/50"
                >
                  <option value="" disabled>Set disposition…</option>
                  {ALL_DISPOSITIONS.map(d => <option key={d} value={d}>{DISPOSITION_LABELS[d]}</option>)}
                </select>
                {notesDraft !== null && notesDraft !== call.notes && (
                  <button
                    onClick={() => { onPatch({ notes: notesDraft }); setNotesDraft(null) }}
                    className="w-full px-3 py-1.5 rounded-lg bg-pm-accent/10 border border-pm-accent/30 text-xs font-medium text-pm-accent hover:bg-pm-accent/20 transition-colors"
                  >
                    Save notes
                  </button>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
