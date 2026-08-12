// Smaller admin console panels: analytics, team callbacks, DNC manager.
// Split from the live board / calls table to keep each surface readable.
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PhoneOff, Plus, Trash2 } from 'lucide-react'
import {
  DISPOSITION_LABELS, dialerAdminApi, fmtDuration, type Disposition,
} from '@/lib/dialer-api'

// ── Analytics ─────────────────────────────────────────────────────────────────

export function AdminAnalytics() {
  const [days, setDays] = useState(7)
  const { data, isLoading } = useQuery({
    queryKey: ['dialer-admin', 'analytics', days],
    queryFn: () => dialerAdminApi.analytics(days),
    refetchInterval: 30000,
  })

  if (isLoading || !data) {
    return <p className="text-sm text-pm-canada-text-muted py-8 text-center">Crunching the numbers…</p>
  }
  const t = data.totals

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 flex-1">
          <Tile label="Dials" value={String(t.dials)} />
          <Tile label="Connects" value={String(t.connects)} />
          <Tile label="Connect rate" value={`${Math.round(t.connect_rate * 100)}%`} accent />
          <Tile label="Talk time" value={fmtDuration(t.talk_seconds)} />
          <Tile label="Blocked by gate" value={String(t.blocked)} />
        </div>
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          aria-label="Analytics range"
          className="ml-3 rounded-lg bg-pm-canada-surface border border-pm-canada-border px-2 py-1.5 text-xs text-white focus:outline-none focus:border-pm-accent/50"
        >
          <option value={1}>Today</option>
          <option value={7}>7 days</option>
          <option value={30}>30 days</option>
        </select>
      </div>

      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-pm-canada-border text-2xs uppercase tracking-wide text-pm-canada-text-faint">
              <th className="px-4 py-2.5 font-medium">Rep</th>
              <th className="px-4 py-2.5 font-medium">Dials</th>
              <th className="px-4 py-2.5 font-medium">Connects</th>
              <th className="px-4 py-2.5 font-medium">Rate</th>
              <th className="px-4 py-2.5 font-medium">Talk</th>
              <th className="px-4 py-2.5 font-medium">Meetings</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-pm-canada-border/60">
            {data.reps.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-sm text-pm-canada-text-muted">No dialing activity in this window.</td></tr>
            )}
            {data.reps.map(r => (
              <tr key={r.rep_id}>
                <td className="px-4 py-2.5 text-xs text-white">{r.rep_name}</td>
                <td className="px-4 py-2.5 text-xs text-pm-canada-text-muted tabular-nums">{r.dials}</td>
                <td className="px-4 py-2.5 text-xs text-pm-canada-text-muted tabular-nums">{r.connects}</td>
                <td className="px-4 py-2.5 text-xs text-pm-accent tabular-nums">{Math.round(r.connect_rate * 100)}%</td>
                <td className="px-4 py-2.5 text-xs text-pm-canada-text-muted tabular-nums">{fmtDuration(r.talk_seconds)}</td>
                <td className="px-4 py-2.5 text-xs text-white tabular-nums">{r.dispositions.meeting_booked ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {Object.keys(t.dispositions).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {(Object.entries(t.dispositions) as [Disposition, number][])
            .sort((a, b) => b[1] - a[1])
            .map(([d, n]) => (
              <span key={d} className="px-2.5 py-1 rounded-full bg-pm-canada-surface border border-pm-canada-border text-2xs text-pm-canada-text-muted">
                {DISPOSITION_LABELS[d] ?? d} <span className="text-white font-semibold tabular-nums ml-1">{n}</span>
              </span>
            ))}
        </div>
      )}
    </div>
  )
}

function Tile({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg bg-pm-canada-surface border border-pm-canada-border px-3 py-2.5">
      <p className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">{label}</p>
      <p className={`text-xl font-semibold tabular-nums ${accent ? 'text-pm-accent' : 'text-white'}`}>{value}</p>
    </div>
  )
}

// ── Team callbacks ────────────────────────────────────────────────────────────

export function AdminCallbacks() {
  const { data, isLoading } = useQuery({
    queryKey: ['dialer-admin', 'callbacks'],
    queryFn: () => dialerAdminApi.callbacks('pending'),
    refetchInterval: 30000,
  })
  const rows = data?.callbacks ?? []

  if (isLoading) {
    return <p className="text-sm text-pm-canada-text-muted py-8 text-center">Loading callbacks…</p>
  }
  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-pm-canada-border text-2xs uppercase tracking-wide text-pm-canada-text-faint">
            <th className="px-4 py-2.5 font-medium">Due</th>
            <th className="px-4 py-2.5 font-medium">Rep</th>
            <th className="px-4 py-2.5 font-medium">Contact</th>
            <th className="px-4 py-2.5 font-medium">Note</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-pm-canada-border/60">
          {rows.length === 0 && (
            <tr><td colSpan={4} className="px-4 py-8 text-center text-sm text-pm-canada-text-muted">No pending callbacks.</td></tr>
          )}
          {rows.map(cb => {
            const due = new Date(cb.due_at)
            const overdue = due.getTime() < Date.now()
            return (
              <tr key={cb.id}>
                <td className={`px-4 py-2.5 text-xs whitespace-nowrap tabular-nums ${overdue ? 'text-pm-amber-orange' : 'text-pm-canada-text-muted'}`}>
                  {due.toLocaleDateString([], { month: 'short', day: 'numeric' })}{' '}
                  {due.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}
                  {overdue ? ' · overdue' : ''}
                </td>
                <td className="px-4 py-2.5 text-xs text-white whitespace-nowrap">{cb.rep_name}</td>
                <td className="px-4 py-2.5 text-xs">
                  <span className="text-white">{cb.business_name || cb.contact_name || '—'}</span>
                  <span className="text-pm-canada-text-faint ml-2 tabular-nums">{cb.phone_e164}</span>
                </td>
                <td className="px-4 py-2.5 text-xs text-pm-canada-text-muted max-w-[280px] truncate">{cb.note || '—'}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── DNC manager ───────────────────────────────────────────────────────────────

export function AdminDncPanel() {
  const queryClient = useQueryClient()
  const [phone, setPhone] = useState('')
  const [reason, setReason] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['dialer-admin', 'dnc'],
    queryFn: dialerAdminApi.dncList,
  })
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['dialer-admin', 'dnc'] })
  const add = useMutation({
    mutationFn: () => dialerAdminApi.dncAdd(phone, 'canada', reason),
    onSuccess: () => { setPhone(''); setReason(''); invalidate() },
  })
  const remove = useMutation({
    mutationFn: (p: string) => dialerAdminApi.dncRemove(p),
    onSuccess: invalidate,
  })

  const entries = data?.entries ?? []

  return (
    <div className="space-y-3">
      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
        <p className="text-2xs text-pm-canada-text-faint mb-2">
          Internal do-not-call list — checked before every dial, in both markets. The national DNCL
          subscription is a separate obligation; this list is on top of it, not instead of it.
        </p>
        <div className="flex flex-wrap gap-2">
          <input
            value={phone}
            onChange={e => setPhone(e.target.value)}
            placeholder="Phone number"
            aria-label="Phone number to block"
            className="rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-xs text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50"
          />
          <input
            value={reason}
            onChange={e => setReason(e.target.value)}
            placeholder="Reason (optional)"
            aria-label="Reason"
            className="flex-1 min-w-[160px] rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2 text-xs text-white placeholder:text-pm-canada-text-faint focus:outline-none focus:border-pm-accent/50"
          />
          <button
            onClick={() => phone.trim() && add.mutate()}
            disabled={!phone.trim() || add.isPending}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30 text-xs font-medium text-red-400 hover:bg-red-500/20 disabled:opacity-40 transition-colors"
          >
            <Plus size={13} />
            Block number
          </button>
        </div>
        {add.isError && (
          <p className="text-2xs text-red-400 mt-2">{(add.error as Error).message}</p>
        )}
      </div>

      <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl divide-y divide-pm-canada-border/60">
        {isLoading && <p className="px-4 py-6 text-sm text-pm-canada-text-muted text-center">Loading…</p>}
        {!isLoading && entries.length === 0 && (
          <div className="px-4 py-10 text-center space-y-1.5">
            <PhoneOff size={20} className="mx-auto text-pm-canada-text-faint" />
            <p className="text-sm text-pm-canada-text-muted">The internal DNC list is empty.</p>
          </div>
        )}
        {entries.map(e => (
          <div key={e.id} className="px-4 py-2.5 flex items-center gap-3">
            <span className="text-sm text-white tabular-nums">{e.phone_e164}</span>
            <span className="text-2xs px-1.5 py-0.5 rounded bg-pm-canada-bg text-pm-canada-text-faint uppercase">{e.market}</span>
            <span className="text-2xs text-pm-canada-text-muted flex-1 truncate">{e.reason}</span>
            <button
              onClick={() => remove.mutate(e.phone_e164)}
              aria-label={`Remove ${e.phone_e164} from DNC`}
              className="p-1.5 rounded-md text-pm-canada-text-faint hover:text-red-400 hover:bg-red-500/10 transition-colors"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
