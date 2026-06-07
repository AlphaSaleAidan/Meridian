import { useState, useMemo, useCallback, useEffect } from 'react'
import { clsx } from 'clsx'
import {
  CheckCircle2, X, Zap, CalendarClock, ChevronDown, ChevronRight,
  Bot, Clock, TrendingUp, Sparkles, Lock,
} from 'lucide-react'
import { generateTopActions, actionsFromInsights, type TopAction, type ReasoningChain } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { api } from '@/lib/api'
import { useApi } from '@/hooks/useApi'

type ActionStatus = 'completed' | 'rejected'
type ActionState = Record<string, { status: ActionStatus; at: string }>

const DAY_MS = 86_400_000

// Pacific (America/Los_Angeles) offset for an instant, in ms. Negative, since
// Pacific is behind UTC; handles PST/PDT automatically. The server timezone
// cancels out because both sides are parsed in it.
function pacificOffsetMs(now: number): number {
  const d = new Date(now)
  const utc = new Date(d.toLocaleString('en-US', { timeZone: 'UTC' })).getTime()
  const pac = new Date(d.toLocaleString('en-US', { timeZone: 'America/Los_Angeles' })).getTime()
  return pac - utc
}

// Wall-clock ms in Pacific time. Daily/weekly resets land on Pacific midnight
// (matching the "Resets in" countdown) rather than UTC midnight.
function pacificNow(now: number): number {
  return now + pacificOffsetMs(now)
}

function actionKey(a: TopAction): string {
  return `${a.agentSource}|${a.title}`
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 96)
}

function storageKey(orgId: string) {
  return `meridian_action_state_${orgId}`
}

function loadState(orgId: string): ActionState {
  try {
    const raw = localStorage.getItem(storageKey(orgId))
    return raw ? (JSON.parse(raw) as ActionState) : {}
  } catch {
    return {}
  }
}

function saveState(orgId: string, state: ActionState) {
  try {
    localStorage.setItem(storageKey(orgId), JSON.stringify(state))
  } catch {
    /* localStorage unavailable — state stays in-memory for this session */
  }
}

// Rotate an array so the element at `offset` is first. Drives date-seeded rotation.
function rotate<T>(arr: T[], offset: number): T[] {
  if (arr.length === 0) return arr
  const o = ((offset % arr.length) + arr.length) % arr.length
  return [...arr.slice(o), ...arr.slice(0, o)]
}

// A done/rejected mark only counts within its action's current period: daily
// actions (Low effort) reset every 24h, strategic actions reset each week.
// Once the period rolls over the mark is stale and the action is fresh again.
function inPeriod(a: TopAction, entry: { at: string }, today: number, week: number): boolean {
  const entryDay = Math.floor(pacificNow(new Date(entry.at).getTime()) / DAY_MS)
  return a.effort === 'Low' ? entryDay === today : Math.floor(entryDay / 7) === week
}

const cadenceStyles = {
  daily: {
    label: 'Today · Instant win',
    icon: Zap,
    chip: 'bg-[#17C5B0]/10 text-[#17C5B0] border-[#17C5B0]/20',
    accent: 'text-[#17C5B0]',
    ring: 'border-[#17C5B0]/20',
  },
  weekly: {
    label: 'This week · Strategic',
    icon: CalendarClock,
    chip: 'bg-[#c8a82c]/10 text-[#d4af37] border-[#c8a82c]/25',
    accent: 'text-[#d4af37]',
    ring: 'border-[#c8a82c]/20',
  },
} as const

type Cadence = keyof typeof cadenceStyles

function WhyPanel({ reasoning }: { reasoning: ReasoningChain }) {
  return (
    <div className="mt-3 p-3 bg-[#0A0A0B] rounded-lg border border-[#1F1F23] space-y-3 animate-fade-in">
      <div className="flex items-center gap-2">
        <Bot size={12} className="text-[#7C5CFF]" />
        <span className="text-[10px] font-medium text-[#7C5CFF] uppercase tracking-wider">{reasoning.agentName}</span>
      </div>
      <div>
        <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">What we saw</p>
        <p className="text-xs text-[#F5F5F7] leading-relaxed">{reasoning.observation}</p>
      </div>
      <div>
        <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">Why it moves money</p>
        <p className="text-xs text-[#A1A1A8] leading-relaxed italic">{reasoning.reasoning}</p>
      </div>
      <div className="grid grid-cols-2 gap-2 pt-1">
        {Object.entries(reasoning.rawData).map(([key, val]) => (
          <div key={key} className="flex items-center justify-between text-[11px]">
            <span className="text-[#A1A1A8]/50">{key.replace(/_/g, ' ')}</span>
            <span className="font-mono text-[#F5F5F7]">{val}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function ActionItem({
  action,
  cadence,
  done = false,
  onComplete,
  onReject,
}: {
  action: TopAction
  cadence: Cadence
  done?: boolean
  onComplete: (a: TopAction) => void
  onReject: (a: TopAction) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const s = cadenceStyles[cadence]
  const CadenceIcon = s.icon

  return (
    <div className={clsx('card-hover overflow-hidden transition-all duration-300', expanded && s.ring, done && 'opacity-80')}>
      <div className={clsx('p-4', done && 'bg-[#17C5B0]/[0.04]')}>
        <div className="flex items-start gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0',
            done ? 'bg-[#17C5B0]/15 text-[#17C5B0]' : s.chip,
          )}>
            {done ? <CheckCircle2 size={18} /> : <CadenceIcon size={18} />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={clsx('text-[10px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider', s.chip)}>
                {s.label}
              </span>
              <span className="text-[10px] text-[#A1A1A8]/50 flex items-center gap-1">
                <Clock size={10} /> {action.effort} effort
              </span>
            </div>
            <div className="flex items-start justify-between gap-2">
              <h3 className={clsx(
                'text-sm font-semibold leading-tight',
                done ? 'text-[#A1A1A8] line-through decoration-[#17C5B0]/40' : 'text-[#F5F5F7]',
              )}>{action.title}</h3>
              <span className={clsx('text-sm font-bold font-mono flex-shrink-0 whitespace-nowrap', s.accent)}>
                +{formatCents(action.impactCents)}/mo
              </span>
            </div>
            <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">{action.description}</p>

            <div className="flex items-center gap-2 mt-3">
              {done ? (
                <span className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#17C5B0]/10 text-[#17C5B0] text-xs font-semibold">
                  <CheckCircle2 size={14} /> Done · captured {cadence === 'daily' ? 'today' : 'this week'}
                </span>
              ) : (
                <>
                  <button
                    onClick={() => onComplete(action)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold hover:bg-[#17C5B0]/90 transition-colors"
                  >
                    <CheckCircle2 size={14} /> Mark done
                  </button>
                  <button
                    onClick={() => onReject(action)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#1F1F23] text-[#A1A1A8] text-xs font-medium hover:bg-[#2A2A2F] hover:text-[#F5F5F7] transition-colors"
                  >
                    <X size={14} /> Reject
                  </button>
                </>
              )}
              <button
                onClick={() => setExpanded(v => !v)}
                className="ml-auto flex items-center gap-1 text-[10px] text-[#A1A1A8]/60 hover:text-[#A1A1A8] transition-colors"
              >
                {action.confidence}% confidence
                {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              </button>
            </div>
          </div>
        </div>
        {expanded && <WhyPanel reasoning={action.reasoning} />}
      </div>
    </div>
  )
}

// Counts down to the next daily reset (the UTC-day boundary that reseeds the
// `today` rotation). Self-contained so the 1s tick only re-renders the timer,
// not the whole panel.
function ResetTimer() {
  const msUntilReset = () => DAY_MS - (pacificNow(Date.now()) % DAY_MS)
  const [msLeft, setMsLeft] = useState(msUntilReset)
  useEffect(() => {
    const id = setInterval(() => setMsLeft(msUntilReset()), 1000)
    return () => clearInterval(id)
  }, [])
  const total = Math.max(0, Math.floor(msLeft / 1000))
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const sec = total % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    <div className="text-right">
      <p className="text-[10px] text-[#A1A1A8]/60 uppercase tracking-wider">Resets in · PT</p>
      <p className="text-sm font-bold font-mono text-[#A1A1A8] flex items-center gap-1 justify-end tabular-nums">
        <Clock size={12} className="text-[#A1A1A8]/60" />
        {pad(h)}h {pad(m)}m {pad(sec)}s
      </p>
    </div>
  )
}

function EmptySlot({ cadence }: { cadence: Cadence }) {
  const s = cadenceStyles[cadence]
  return (
    <div className="card p-4 border-dashed border-[#1F1F23] flex items-center gap-3">
      <div className="w-9 h-9 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
        <CheckCircle2 size={16} className="text-[#17C5B0]" />
      </div>
      <p className="text-xs text-[#A1A1A8]">
        {cadence === 'daily'
          ? "You're all caught up on today's instant wins — fresh ones land tomorrow."
          : "This week's strategic move is handled. A new one unlocks next week."}
      </p>
    </div>
  )
}

// The standby agents we name in the pre-connection teaser, so the merchant sees
// that real model agents are assigned to the work before any POS is wired up.
const STANDBY_AGENTS: { name: string; covers: string }[] = [
  { name: 'Pricing Power', covers: 'safe price increases' },
  { name: 'Inventory Intelligence', covers: 'stockout & reorder timing' },
  { name: 'Staffing', covers: 'peak-hour coverage' },
  { name: 'Money Left on Table', covers: 'your biggest weekly lever' },
]

// Pre-connection state: no POS is wired up yet, so there's no transaction data to
// reason over. Show the merchant exactly what's coming and which model agents are
// assigned, with a locked treatment instead of a fake/empty action.
function PreConnectionState() {
  return (
    <div className="card p-5 border border-[#1F1F23] space-y-4">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#7C5CFF]/10 border border-[#7C5CFF]/20 flex items-center justify-center flex-shrink-0">
          <Lock size={18} className="text-[#7C5CFF]" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Your daily actions unlock at connection</h3>
          <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
            Once your POS is connected, these agents start analyzing your real sales and post
            two fresh instant wins each day plus one strategic move each week — each with the
            exact dollar impact and the reasoning behind it.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {STANDBY_AGENTS.map(a => (
          <div key={a.name} className="flex items-center gap-2.5 p-2.5 rounded-lg bg-[#0A0A0B] border border-dashed border-[#1F1F23]">
            <Bot size={14} className="text-[#7C5CFF] flex-shrink-0" />
            <div className="min-w-0">
              <p className="text-xs font-medium text-[#F5F5F7] truncate">{a.name}</p>
              <p className="text-[10px] text-[#A1A1A8]/70 truncate">Watching {a.covers}</p>
            </div>
            <span className="ml-auto text-[9px] font-semibold uppercase tracking-wider text-[#A1A1A8]/50 flex items-center gap-1 flex-shrink-0">
              <span className="w-1.5 h-1.5 rounded-full bg-[#A1A1A8]/40" /> Standby
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Connected, but no insights have been generated yet (POS just wired up; agents
// haven't completed their first pass). An honest "analyzing" state — NOT the
// "all caught up" empty slot, which would falsely imply work was already done.
function WarmingState() {
  return (
    <div className="card p-5 border border-[#1F1F23] flex items-start gap-3">
      <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center flex-shrink-0 animate-pulse">
        <Sparkles size={18} className="text-[#17C5B0]" />
      </div>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-[#F5F5F7]">Your agents are analyzing your sales</h3>
        <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
          We're crunching your transactions now. Your first prioritized actions — each with a
          dollar impact and the model agent behind it — appear here within 24 hours of your
          first sync.
        </p>
      </div>
    </div>
  )
}

// Minimal header (title + subtitle only) for the pre-connection and warming
// states, where the live ResetTimer / pipeline / captured figures don't apply.
function SimpleHeader({ subtitle }: { subtitle: string }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
        <Sparkles size={16} className="text-[#17C5B0]" />
      </div>
      <div>
        <h2 className="text-sm font-bold text-[#F5F5F7]">Your Top 3 Actions</h2>
        <p className="text-[11px] text-[#A1A1A8]">{subtitle}</p>
      </div>
    </div>
  )
}

export default function Top3ActionsPanel({ showHeader = true, connected = true }: { showHeader?: boolean; connected?: boolean }) {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  // Skip the API call entirely when we know there's no POS connection — there
  // would be no data to score and the panel renders the pre-connection teaser.
  const apiData = useApi(() => (isDemo || connected ? api.actions(orgId) : Promise.resolve({ actions: [] })), [orgId, isDemo, connected])
  const pool: TopAction[] = isDemo
    ? generateTopActions()
    : actionsFromInsights(apiData.data?.actions ?? [])

  const [state, setState] = useState<ActionState>(() => loadState(orgId))

  const act = useCallback(
    (a: TopAction, status: ActionStatus) => {
      setState(prev => {
        const next = { ...prev, [actionKey(a)]: { status, at: new Date().toISOString() } }
        saveState(orgId, next)
        return next
      })
    },
    [orgId],
  )

  const onComplete = useCallback((a: TopAction) => act(a, 'completed'), [act])
  const onReject = useCallback((a: TopAction) => act(a, 'rejected'), [act])

  const today = Math.floor(pacificNow(Date.now()) / DAY_MS)
  const week = Math.floor(today / 7)

  const { daily, weekly, doneKeys, capturedCents, completedCount } = useMemo(() => {
    // Mark for this action, but only if it's still within the current period.
    const entryOf = (a: TopAction) => {
      const e = state[actionKey(a)]
      return e && inPeriod(a, e, today, week) ? e : undefined
    }
    const instant = pool.filter(a => a.effort === 'Low')
    const strategic = pool.filter(a => a.effort !== 'Low')

    // Rejected (this period) drops out so a fresh action rotates into its slot.
    // Completed stays put — it holds its slot in a done state until the reset.
    const notRejected = (a: TopAction) => entryOf(a)?.status !== 'rejected'
    const daily = rotate(instant, today).filter(notRejected).slice(0, 2)
    const weekly = rotate(strategic, week).filter(notRejected).slice(0, 1)

    const doneKeys = new Set<string>()
    for (const a of [...daily, ...weekly]) {
      if (entryOf(a)?.status === 'completed') doneKeys.add(actionKey(a))
    }

    const completed = [...daily, ...weekly].filter(a => doneKeys.has(actionKey(a)))
    return {
      daily,
      weekly,
      doneKeys,
      capturedCents: completed.reduce((sum, a) => sum + a.impactCents, 0),
      completedCount: completed.length,
    }
  }, [pool, state, today, week])

  // Pre-connection: no POS wired up — show the locked teaser + standby agents.
  // (No data dependency, so this takes precedence over the loading skeleton.)
  if (!isDemo && !connected) {
    return (
      <div className="space-y-3">
        {showHeader && <SimpleHeader subtitle="Unlock two fresh wins daily and one strategic move each week" />}
        <PreConnectionState />
      </div>
    )
  }

  if (!isDemo && apiData.loading) {
    return (
      <div className="card p-6 animate-pulse">
        <div className="h-4 w-40 bg-[#1F1F23] rounded mb-4" />
        <div className="space-y-3">
          <div className="h-20 bg-[#1F1F23]/60 rounded-xl" />
          <div className="h-20 bg-[#1F1F23]/60 rounded-xl" />
        </div>
      </div>
    )
  }

  // Connected, but the agents haven't produced any insights yet — honest
  // "analyzing" state rather than the misleading "all caught up" empty slots.
  if (!isDemo && connected && pool.length === 0) {
    return (
      <div className="space-y-3">
        {showHeader && <SimpleHeader subtitle="Two fresh wins daily, one strategic move each week" />}
        <WarmingState />
      </div>
    )
  }

  const pipelineCents = [...daily, ...weekly]
    .filter(a => !doneKeys.has(actionKey(a)))
    .reduce((sum, a) => sum + a.impactCents, 0)

  return (
    <div className="space-y-3">
      {showHeader && (
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
              <Sparkles size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-[#F5F5F7]">Your Top 3 Actions</h2>
              <p className="text-[11px] text-[#A1A1A8]">Two fresh wins daily, one strategic move each week</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <ResetTimer />
            {pipelineCents > 0 && (
              <div className="text-right">
                <p className="text-[10px] text-[#A1A1A8]/60 uppercase tracking-wider">On the table</p>
                <p className="text-sm font-bold font-mono text-[#17C5B0]">+{formatCents(pipelineCents)}/mo</p>
              </div>
            )}
            {completedCount > 0 && (
              <div className="text-right flex items-center gap-1.5">
                <TrendingUp size={14} className="text-[#17C5B0]" />
                <div>
                  <p className="text-[10px] text-[#A1A1A8]/60 uppercase tracking-wider">Captured</p>
                  <p className="text-sm font-bold font-mono text-[#F5F5F7]">+{formatCents(capturedCents)}/mo</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {daily.length > 0
        ? daily.map(a => (
            <ActionItem key={actionKey(a)} action={a} cadence="daily" done={doneKeys.has(actionKey(a))} onComplete={onComplete} onReject={onReject} />
          ))
        : <EmptySlot cadence="daily" />}

      {weekly.length > 0
        ? weekly.map(a => (
            <ActionItem key={actionKey(a)} action={a} cadence="weekly" done={doneKeys.has(actionKey(a))} onComplete={onComplete} onReject={onReject} />
          ))
        : <EmptySlot cadence="weekly" />}
    </div>
  )
}
