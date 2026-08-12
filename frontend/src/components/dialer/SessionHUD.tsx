// Session heads-up display: phase pill, live timers, session stats, wrap-up
// countdown, pause/stop. Pure presentation — all state lives in
// useDialerSession.
import { Pause, Play, Square, Radio } from 'lucide-react'
import { fmtDuration, type DialerSession } from '@/lib/dialer-api'
import type { DialerPhase } from '@/hooks/useDialerSession'

const PHASE_META: Record<DialerPhase, { label: string; cls: string; pulse?: boolean }> = {
  idle: { label: 'Idle', cls: 'bg-pm-canada-border text-pm-canada-text-muted' },
  starting: { label: 'Starting', cls: 'bg-pm-accent/10 text-pm-accent', pulse: true },
  dialing: { label: 'Dialing', cls: 'bg-pm-amber-gold/10 text-pm-amber-gold', pulse: true },
  ringing: { label: 'Ringing', cls: 'bg-pm-amber-gold/10 text-pm-amber-gold', pulse: true },
  connected: { label: 'Connected', cls: 'bg-pm-accent/15 text-pm-accent', pulse: true },
  wrapup: { label: 'Wrap-up', cls: 'bg-pm-purple/15 text-purple-300' },
  complete: { label: 'Queue complete', cls: 'bg-pm-accent/10 text-pm-accent' },
}

interface Props {
  phase: DialerPhase
  paused: boolean
  session: DialerSession | null
  callSeconds: number
  wrapRemaining: number
  needsDisposition: boolean
  remaining: number
  softphoneMode: 'sim' | 'webrtc' | null
  devStore: boolean
  onTogglePause: () => void
  onStop: () => void
}

export function SessionHUD({
  phase, paused, session, callSeconds, wrapRemaining, needsDisposition,
  remaining, softphoneMode, devStore, onTogglePause, onStop,
}: Props) {
  const meta = PHASE_META[phase]
  const connectRate = session && session.dials > 0
    ? Math.round((session.connects / session.dials) * 100) : 0

  return (
    <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-4">
      <div className="flex items-center gap-3 flex-wrap">
        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${paused ? 'bg-pm-amber-orange/15 text-pm-amber-orange' : meta.cls}`}>
          <span className={`w-1.5 h-1.5 rounded-full bg-current ${!paused && meta.pulse ? 'animate-pulse' : ''}`} />
          {paused ? 'Paused' : meta.label}
        </span>

        {softphoneMode === 'sim' && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-pm-amber-orange/15 text-pm-amber-orange border border-pm-amber-orange/30">
            <Radio size={12} />
            SIM MODE — no live calls
          </span>
        )}
        {devStore && (
          <span className="text-2xs text-pm-canada-text-faint">
            Preview data plane — sessions held in memory
          </span>
        )}

        <div className="ml-auto flex items-center gap-2">
          {session && (
            <>
              <button
                onClick={onTogglePause}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-pm-canada-border text-pm-canada-text-muted hover:text-pm-accent hover:border-pm-accent/40 transition-colors"
              >
                {paused ? <Play size={14} /> : <Pause size={14} />}
                {paused ? 'Resume' : 'Pause'}
              </button>
              <button
                onClick={onStop}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors"
              >
                <Square size={13} />
                End session
              </button>
            </>
          )}
        </div>
      </div>

      {session && (
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-3 mt-4">
          <Stat label="Dials" value={String(session.dials)} />
          <Stat label="Connects" value={String(session.connects)} />
          <Stat label="Connect rate" value={`${connectRate}%`} />
          <Stat label="Talk time" value={fmtDuration(session.talk_seconds)} />
          <Stat label="In queue" value={String(remaining)} />
          <Stat
            label={phase === 'wrapup' && !needsDisposition ? 'Next dial in' : 'Call timer'}
            value={phase === 'wrapup' && !needsDisposition
              ? `${wrapRemaining}s`
              : fmtDuration(callSeconds)}
            accent={phase === 'connected' || (phase === 'wrapup' && !needsDisposition)}
          />
        </div>
      )}
    </div>
  )
}

function Stat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="rounded-lg bg-pm-canada-bg/60 border border-pm-canada-border px-3 py-2">
      <p className="text-2xs uppercase tracking-wide text-pm-canada-text-faint">{label}</p>
      <p className={`text-lg font-semibold tabular-nums ${accent ? 'text-pm-accent' : 'text-white'}`}>{value}</p>
    </div>
  )
}
