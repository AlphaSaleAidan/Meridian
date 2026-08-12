// Live floor wall: every non-ended dial session with rep, state, current
// call and running timers. Data: 5s polling (works on the preview dev store)
// + Supabase Realtime invalidation when the dialer tables are in the
// publication (post-migration prod).
import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Headphones, PauseCircle, PhoneCall } from 'lucide-react'
import { dialerAdminApi, fmtDuration, type LiveSession } from '@/lib/dialer-api'
import { supabase } from '@/lib/supabase'
import { ROLE_BADGES } from '@/lib/role-colors'

function useNow(intervalMs: number): number {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(t)
  }, [intervalMs])
  return now
}

export function AdminLiveBoard() {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['dialer-admin', 'live'],
    queryFn: dialerAdminApi.live,
    refetchInterval: 5000,
  })
  const now = useNow(1000)

  // Realtime enhancement: any change on the dialer tables refreshes the board
  // immediately (polling stays as the floor).
  useEffect(() => {
    if (!supabase) return
    const channel = supabase
      .channel('dialer-admin-live')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'dialer_sessions' },
        () => queryClient.invalidateQueries({ queryKey: ['dialer-admin'] }))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'dialer_calls' },
        () => queryClient.invalidateQueries({ queryKey: ['dialer-admin'] }))
      .subscribe()
    return () => { void supabase?.removeChannel(channel) }
  }, [queryClient])

  const sessions = data?.sessions ?? []

  if (isLoading) {
    return <p className="text-sm text-pm-canada-text-muted py-8 text-center">Loading the floor…</p>
  }
  if (sessions.length === 0) {
    return (
      <div className="text-center py-14 space-y-1.5">
        <Headphones size={22} className="mx-auto text-pm-canada-text-faint" />
        <p className="text-sm text-pm-canada-text-muted">No dial sessions running right now.</p>
        <p className="text-2xs text-pm-canada-text-faint">Reps appear here the moment they start dialing.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
      {sessions.map(s => <SessionCard key={s.id} session={s} now={now} />)}
    </div>
  )
}

function SessionCard({ session: s, now }: { session: LiveSession; now: number }) {
  const call = s.current_call
  const onCall = call?.status === 'connected'
  const inFlight = call && (call.status === 'dialing' || call.status === 'ringing')
  const badge = ROLE_BADGES[s.rep_role as keyof typeof ROLE_BADGES]
  const callSince = call
    ? (onCall && call.answered_at ? Date.parse(call.answered_at) : Date.parse(call.started_at))
    : 0
  const sessionSeconds = Math.floor((now - Date.parse(s.started_at)) / 1000)
  const connectRate = s.dials > 0 ? Math.round((s.connects / s.dials) * 100) : 0

  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4 space-y-3">
      <div className="flex items-center gap-2.5">
        <span className={`w-2 h-2 rounded-full shrink-0 ${
          s.status === 'paused' ? 'bg-pm-amber-orange'
            : onCall ? 'bg-pm-accent animate-pulse'
              : 'bg-pm-amber-gold animate-pulse'
        }`} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-white truncate">{s.rep_name}</p>
          {badge && (
            <span className={`text-2xs px-1.5 py-0.5 rounded ${badge.bg} ${badge.textColor}`}>{badge.text}</span>
          )}
        </div>
        <span className="text-2xs text-pm-canada-text-faint tabular-nums shrink-0">
          {fmtDuration(sessionSeconds)} in session
        </span>
      </div>

      <div className="rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2.5 min-h-[52px]">
        {call ? (
          <div className="flex items-center gap-2.5">
            {s.status === 'paused'
              ? <PauseCircle size={15} className="text-pm-amber-orange shrink-0" />
              : <PhoneCall size={15} className={`shrink-0 ${onCall ? 'text-pm-accent' : 'text-pm-amber-gold'}`} />}
            <div className="min-w-0 flex-1">
              <p className="text-xs text-white truncate">
                {call.business_name || call.contact_name || call.phone_e164}
              </p>
              <p className="text-2xs text-pm-canada-text-faint">
                {onCall ? 'Connected' : inFlight ? call.status : call.status}
                {call.sim ? ' · SIM' : ''}
              </p>
            </div>
            <span className={`text-sm font-semibold tabular-nums shrink-0 ${onCall ? 'text-pm-accent' : 'text-pm-amber-gold'}`}>
              {fmtDuration(Math.max(0, Math.floor((now - callSince) / 1000)))}
            </span>
          </div>
        ) : (
          <p className="text-2xs text-pm-canada-text-faint py-1.5">
            {s.status === 'paused' ? 'Paused between calls' : 'Between calls (wrap-up)'}
          </p>
        )}
      </div>

      <div className="flex items-center justify-between text-2xs text-pm-canada-text-muted tabular-nums">
        <span>{s.dials} dials</span>
        <span>{s.connects} connects ({connectRate}%)</span>
        <span>{fmtDuration(s.talk_seconds)} talk</span>
      </div>
    </div>
  )
}
