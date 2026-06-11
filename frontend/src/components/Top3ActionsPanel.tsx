import { useState, useMemo, useCallback } from 'react'
import { clsx } from 'clsx'
import {
  CheckCircle2, X, Zap, CalendarClock, ChevronDown, ChevronRight,
  Bot, Clock, TrendingUp, Sparkles,
} from 'lucide-react'
import { generateTopActions, type TopAction, type ReasoningChain } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { api } from '@/lib/api'
import { useApi } from '@/hooks/useApi'

type ActionStatus = 'completed' | 'rejected'
type ActionState = Record<string, { status: ActionStatus; at: string }>

const DAY_MS = 86_400_000

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
  onComplete,
  onReject,
}: {
  action: TopAction
  cadence: Cadence
  onComplete: (a: TopAction) => void
  onReject: (a: TopAction) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const s = cadenceStyles[cadence]
  const CadenceIcon = s.icon

  return (
    <div className={clsx('card-hover overflow-hidden transition-all duration-300', expanded && s.ring)}>
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0', s.chip)}>
            <CadenceIcon size={18} />
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
              <h3 className="text-sm font-semibold text-[#F5F5F7] leading-tight">{action.title}</h3>
              <span className={clsx('text-sm font-bold font-mono flex-shrink-0 whitespace-nowrap', s.accent)}>
                +{formatCents(action.impactCents)}/mo
              </span>
            </div>
            <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">{action.description}</p>

            <div className="flex items-center gap-2 mt-3">
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

export default function Top3ActionsPanel({ showHeader = true }: { showHeader?: boolean }) {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const apiData = useApi(() => api.actions(orgId), [orgId])
  const pool: TopAction[] = isDemo ? generateTopActions() : (apiData.data?.actions ?? [])

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

  const today = Math.floor(Date.now() / DAY_MS)
  const week = Math.floor(today / 7)

  const { daily, weekly, capturedCents, completedCount } = useMemo(() => {
    const acted = (a: TopAction) => state[actionKey(a)]
    const instant = pool.filter(a => a.effort === 'Low')
    const strategic = pool.filter(a => a.effort !== 'Low')

    const daily = rotate(instant, today).filter(a => !acted(a)).slice(0, 2)
    const weekly = rotate(strategic, week).filter(a => !acted(a)).slice(0, 1)

    const completed = pool.filter(a => acted(a)?.status === 'completed')
    return {
      daily,
      weekly,
      capturedCents: completed.reduce((sum, a) => sum + a.impactCents, 0),
      completedCount: completed.length,
    }
  }, [pool, state, today, week])

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

  const pipelineCents = [...daily, ...weekly].reduce((sum, a) => sum + a.impactCents, 0)

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
            <ActionItem key={actionKey(a)} action={a} cadence="daily" onComplete={onComplete} onReject={onReject} />
          ))
        : <EmptySlot cadence="daily" />}

      {weekly.length > 0
        ? weekly.map(a => (
            <ActionItem key={actionKey(a)} action={a} cadence="weekly" onComplete={onComplete} onReject={onReject} />
          ))
        : <EmptySlot cadence="weekly" />}
    </div>
  )
}
