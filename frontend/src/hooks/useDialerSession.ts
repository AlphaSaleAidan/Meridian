// Power-dial session state machine for the SR Auto Dialer.
//
//   idle → (start) → dialing → ringing → connected → wrapup → dialing → … → complete
//                        ↘ blocked/ring-out (auto-disposition) → wrapup ↗
//
// Rules encoded here (mirrors docs/AUTODIALER_PLAN.md):
//   * POST /calls is the compliance gate — a blocked entry never touches the
//     softphone; it's logged and the pointer advances.
//   * Ring-outs (no_answer / busy) and unanswered hangups auto-disposition so
//     the rep only stops for real conversations.
//   * Answered calls REQUIRE a manual disposition before the wrap-up
//     countdown starts; countdown end auto-dials the next entry.
//   * Pause halts auto-advance (mid-countdown included); Stop ends the session.
import { useCallback, useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  dialerApi,
  type DialerCall, type DialerMarket, type DialerQueue, type DialerSession,
  type Disposition, type QueueCallback, type QueueLead,
} from '@/lib/dialer-api'
import { createSoftphone, type Softphone, type SoftphoneEvent } from '@/lib/dialer-softphone'

export type QueueEntry = QueueLead | QueueCallback

export type DialerPhase =
  | 'idle' | 'starting' | 'dialing' | 'ringing' | 'connected' | 'wrapup' | 'complete'

export interface CompletedCall {
  entry: QueueEntry
  call: DialerCall | null
  disposition: Disposition | 'blocked' | null
  blockedReason?: string
}

const AUTO_DISPOSITIONS: Record<string, Disposition> = {
  no_answer: 'no_answer',
  busy: 'busy',
  hangup: 'no_answer', // rep skipped before answer
}

export function useDialerSession(market: DialerMarket) {
  const queryClient = useQueryClient()
  const queueQuery = useQuery<DialerQueue>({
    queryKey: ['dialer', 'queue', market],
    queryFn: () => dialerApi.queue(market),
    staleTime: 30_000,
  })

  const [phase, setPhase] = useState<DialerPhase>('idle')
  const [paused, setPaused] = useState(false)
  const [session, setSession] = useState<DialerSession | null>(null)
  const [currentEntry, setCurrentEntry] = useState<QueueEntry | null>(null)
  const [currentCall, setCurrentCall] = useState<DialerCall | null>(null)
  const [needsDisposition, setNeedsDisposition] = useState(false)
  const [callSeconds, setCallSeconds] = useState(0)
  const [wrapRemaining, setWrapRemaining] = useState(0)
  const [notes, setNotes] = useState('')
  const [softphoneMode, setSoftphoneMode] = useState<'sim' | 'webrtc' | null>(null)
  const [log, setLog] = useState<CompletedCall[]>([])
  const [error, setError] = useState<string | null>(null)

  const softphoneRef = useRef<Softphone | null>(null)
  const workingQueue = useRef<QueueEntry[]>([])
  const pointer = useRef(0)
  const sessionRef = useRef<DialerSession | null>(null)
  const callRef = useRef<DialerCall | null>(null)
  const entryRef = useRef<QueueEntry | null>(null)
  const phaseRef = useRef<DialerPhase>('idle')
  const pausedRef = useRef(false)
  const needsDispositionRef = useRef(false)
  const wrapRemainingRef = useRef(0)
  // True from softphone.dial() until its 'ended' event — the guard that makes
  // dialNext idempotent (a stray double-fire must never skip ahead mid-call).
  const inFlightRef = useRef(false)
  const dialStartedAt = useRef(0)
  const answeredAt = useRef(0)
  const tickTimer = useRef<ReturnType<typeof setInterval> | null>(null)
  const wrapTimer = useRef<ReturnType<typeof setInterval> | null>(null)

  const setPhaseSafe = (p: DialerPhase) => { phaseRef.current = p; setPhase(p) }
  const setNeedsDispositionSafe = (v: boolean) => {
    needsDispositionRef.current = v
    setNeedsDisposition(v)
  }

  const clearTimers = () => {
    if (tickTimer.current) { clearInterval(tickTimer.current); tickTimer.current = null }
    if (wrapTimer.current) { clearInterval(wrapTimer.current); wrapTimer.current = null }
  }

  useEffect(() => () => {
    clearTimers()
    softphoneRef.current?.destroy()
  }, [])

  const invalidateQueue = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['dialer', 'queue', market] })
  }, [queryClient, market])

  // ── Advance / wrap-up ──────────────────────────────────────────────────────

  // NOTE: countdown state lives in a ref and the interval callback owns all
  // side effects — setState updaters stay pure (React may invoke updaters
  // twice; a side-effectful updater double-fired dialNext and burned through
  // the queue mid-call — caught in the 2026-08-12 E2E run).
  const beginWrapup = useCallback((seconds: number) => {
    setPhaseSafe('wrapup')
    setNeedsDispositionSafe(false)
    wrapRemainingRef.current = seconds
    setWrapRemaining(seconds)
    clearTimers()
    wrapTimer.current = setInterval(() => {
      if (pausedRef.current) return
      wrapRemainingRef.current -= 1
      setWrapRemaining(Math.max(0, wrapRemainingRef.current))
      if (wrapRemainingRef.current <= 0) {
        clearTimers()
        dialNextRef.current()
      }
    }, 1000)
  }, [])

  const dialEntry = useCallback(async (entry: QueueEntry) => {
    const sess = sessionRef.current
    if (!sess) return
    entryRef.current = entry
    setCurrentEntry(entry)
    setCurrentCall(null)
    setNotes('')
    setCallSeconds(0)
    setError(null)
    setPhaseSafe('dialing')
    dialStartedAt.current = Date.now()
    answeredAt.current = 0

    try {
      const { call, gate } = await dialerApi.startCall({
        session_id: sess.id,
        market,
        phone: entry.phone_e164,
        lead_id: entry.kind === 'lead' ? entry.id : entry.lead_id,
        business_name: entry.business_name,
        contact_name: entry.contact_name,
        sim: softphoneRef.current?.mode === 'sim',
      })
      callRef.current = call
      setCurrentCall(call)
      if (!gate.allowed) {
        setLog(prev => [{ entry, call, disposition: 'blocked', blockedReason: gate.reason }, ...prev])
        setTimeout(() => dialNextRef.current(), 900)
        return
      }
      setSession(s => s ? { ...s, dials: s.dials + 1 } : s)
      inFlightRef.current = true
      await softphoneRef.current?.dial(entry.phone_e164)
      // Duration ticker (dial → end).
      tickTimer.current = setInterval(() => {
        setCallSeconds(Math.floor((Date.now() - dialStartedAt.current) / 1000))
      }, 1000)
    } catch (err) {
      inFlightRef.current = false
      setError(err instanceof Error ? err.message : 'Dial failed')
      setPhaseSafe('wrapup')
      setNeedsDispositionSafe(false)
      setWrapRemaining(0)
    }
  }, [market])

  const dialNext = useCallback(() => {
    if (inFlightRef.current) return
    clearTimers()
    if (pausedRef.current || !sessionRef.current) return
    const q = workingQueue.current
    while (pointer.current < q.length) {
      const entry = q[pointer.current]
      pointer.current += 1
      // DNC'd entries are pre-annotated — never dial them; log the skip.
      if (entry.on_dnc) {
        setLog(prev => [{ entry, call: null, disposition: 'blocked', blockedReason: 'dnc' }, ...prev])
        continue
      }
      void dialEntry(entry)
      return
    }
    setCurrentEntry(null)
    setCurrentCall(null)
    setPhaseSafe('complete')
  }, [dialEntry])
  const dialNextRef = useRef(dialNext)
  dialNextRef.current = dialNext

  // ── Softphone events ───────────────────────────────────────────────────────

  const onSoftphoneEvent = useCallback((ev: SoftphoneEvent) => {
    const call = callRef.current
    if (!call) return
    if (ev.type === 'ringing') {
      setPhaseSafe('ringing')
      void dialerApi.patchCall(call.id, { status: 'ringing' }).catch(() => undefined)
    } else if (ev.type === 'answered') {
      answeredAt.current = Date.now()
      setPhaseSafe('connected')
      setSession(s => s ? { ...s, connects: s.connects + 1 } : s)
      void dialerApi.patchCall(call.id, { status: 'connected' }).catch(() => undefined)
    } else if (ev.type === 'ended') {
      inFlightRef.current = false
      clearTimers()
      const durationSeconds = Math.floor((Date.now() - dialStartedAt.current) / 1000)
      const talkSeconds = answeredAt.current
        ? Math.floor((Date.now() - answeredAt.current) / 1000) : 0
      void dialerApi.patchCall(call.id, {
        status: 'ended', duration_seconds: durationSeconds, talk_seconds: talkSeconds,
      }).catch(() => undefined)
      if (talkSeconds > 0) {
        setSession(s => s ? { ...s, talk_seconds: s.talk_seconds + talkSeconds } : s)
      }

      const auto = !answeredAt.current && ev.cause in AUTO_DISPOSITIONS
        ? AUTO_DISPOSITIONS[ev.cause] : null
      if (auto) {
        const entry = entryRef.current
        void dialerApi.disposition(call.id, { disposition: auto }).catch(() => undefined)
        if (entry) setLog(prev => [{ entry, call, disposition: auto }, ...prev])
        beginWrapup(sessionRef.current?.wrap_up_seconds ?? 15)
      } else {
        // A real conversation happened — hold for a manual disposition.
        setPhaseSafe('wrapup')
        setNeedsDispositionSafe(true)
        setWrapRemaining(0)
      }
    }
  }, [beginWrapup])

  // ── Public actions ─────────────────────────────────────────────────────────

  const start = useCallback(async (wrapUpSeconds: number) => {
    setPhaseSafe('starting')
    setError(null)
    try {
      const [{ session: sess }, queue] = await Promise.all([
        dialerApi.startSession(market, wrapUpSeconds),
        queueQuery.data ? Promise.resolve(queueQuery.data) : dialerApi.queue(market),
      ])
      sessionRef.current = sess
      setSession(sess)
      const entries: QueueEntry[] = [...queue.callbacks, ...queue.leads.filter(l => !l.recently_attempted)]
      workingQueue.current = entries
      pointer.current = 0
      setLog([])
      setPaused(false)
      pausedRef.current = false
      if (!softphoneRef.current) {
        softphoneRef.current = await createSoftphone(onSoftphoneEvent, dialerApi.webrtcToken)
        setSoftphoneMode(softphoneRef.current.mode)
      }
      dialNextRef.current()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start the session')
      setPhaseSafe('idle')
    }
  }, [market, onSoftphoneEvent, queueQuery.data])

  const togglePause = useCallback(() => {
    const next = !pausedRef.current
    pausedRef.current = next
    setPaused(next)
    // Resuming after the countdown already hit zero while paused: advance now.
    if (!next && phaseRef.current === 'wrapup'
        && !needsDispositionRef.current && wrapRemainingRef.current <= 0) {
      dialNextRef.current()
    }
  }, [])

  const hangup = useCallback(() => {
    softphoneRef.current?.hangup()
  }, [])

  /** Skip the remaining wrap-up countdown and dial the next lead now. */
  const dialNow = useCallback(() => {
    if (phaseRef.current !== 'wrapup' || needsDispositionRef.current) return
    clearTimers()
    dialNextRef.current()
  }, [])

  const setMuted = useCallback((muted: boolean) => {
    softphoneRef.current?.setMuted(muted)
  }, [])

  const submitDisposition = useCallback(async (
    disposition: Disposition,
    opts: { callback?: { due_at: string; note?: string }; advance_stage?: string } = {},
  ) => {
    const call = callRef.current
    const entry = entryRef.current
    if (!call) return
    try {
      await dialerApi.disposition(call.id, { disposition, notes, ...opts })
      if (entry) setLog(prev => [{ entry, call, disposition }, ...prev])
      setNotes('')
      invalidateQueue()
      beginWrapup(sessionRef.current?.wrap_up_seconds ?? 15)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save the disposition')
    }
  }, [notes, beginWrapup, invalidateQueue])

  const stop = useCallback(async () => {
    clearTimers()
    softphoneRef.current?.hangup()
    inFlightRef.current = false
    const sess = sessionRef.current
    sessionRef.current = null
    setPhaseSafe('idle')
    setPaused(false)
    pausedRef.current = false
    setCurrentEntry(null)
    setCurrentCall(null)
    setNeedsDispositionSafe(false)
    invalidateQueue()
    if (sess) {
      try { await dialerApi.patchSession(sess.id, 'ended') } catch { /* already gone */ }
    }
    setSession(null)
  }, [invalidateQueue])

  const remaining = workingQueue.current.length - pointer.current

  return {
    phase, paused, session, currentEntry, currentCall, needsDisposition,
    callSeconds, wrapRemaining, notes, setNotes, softphoneMode, log, error,
    queue: queueQuery.data ?? null,
    queueLoading: queueQuery.isLoading,
    queueError: queueQuery.error,
    remaining: Math.max(0, remaining),
    start, stop, togglePause, hangup, setMuted, submitDisposition, dialNow,
    skip: hangup, // during dialing/ringing a hangup IS the skip
  }
}
