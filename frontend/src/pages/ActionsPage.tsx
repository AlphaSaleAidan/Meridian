import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Target, ChevronDown, ChevronRight, Zap, Clock,
  TrendingUp, AlertTriangle, CheckCircle2, Bot,
} from 'lucide-react'
import { generateTopActions, type TopAction, type ReasoningChain } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const priorityColors: Record<string, { bg: string; text: string; border: string }> = {
  Critical: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
  High: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  Medium: { bg: 'bg-[#1A8FD6]/10', text: 'text-[#1A8FD6]', border: 'border-[#1A8FD6]/20' },
  Low: { bg: 'bg-[#A1A1A8]/10', text: 'text-[#A1A1A8]', border: 'border-[#A1A1A8]/20' },
}

const effortColors: Record<string, string> = {
  Low: 'text-[#17C5B0]',
  Medium: 'text-amber-400',
  High: 'text-red-400',
}

function ReasoningPanel({ reasoning }: { reasoning: ReasoningChain }) {
  return (
    <div className="space-y-3 animate-fade-in">
      <div className="p-3 bg-[#0A0A0B] rounded-lg border border-[#1F1F23]">
        <div className="flex items-center gap-2 mb-2">
          <Bot size={12} className="text-[#7C5CFF]" />
          <span className="text-[10px] font-medium text-[#7C5CFF] uppercase tracking-wider">{reasoning.agentName}</span>
        </div>

        <div className="space-y-3">
          <div>
            <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">Observation (Raw Data)</p>
            <p className="text-xs text-[#F5F5F7] leading-relaxed">{reasoning.observation}</p>
          </div>

          <div>
            <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">Reasoning Chain</p>
            <p className="text-xs text-[#A1A1A8] leading-relaxed italic">{reasoning.reasoning}</p>
          </div>

          <div>
            <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">Conclusion</p>
            <p className="text-xs text-[#17C5B0] leading-relaxed font-medium">{reasoning.conclusion}</p>
          </div>

          <div>
            <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">Expected Impact</p>
            <p className="text-xs text-[#F5F5F7] leading-relaxed">{reasoning.impact}</p>
          </div>
        </div>

        <div className="mt-3 pt-3 border-t border-[#1F1F23]">
          <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-2">Supporting Data</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(reasoning.rawData).map(([key, val]) => (
              <div key={key} className="flex items-center justify-between text-[11px]">
                <span className="text-[#A1A1A8]/50">{key.replace(/_/g, ' ')}</span>
                <span className="font-mono text-[#F5F5F7]">{val}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-3 flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="h-1.5 w-16 bg-[#1F1F23] rounded-full overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0]" style={{ width: `${reasoning.confidence}%` }} />
            </div>
            <span className="text-[10px] font-mono text-[#A1A1A8]">{reasoning.confidence}%</span>
          </div>
          <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full border', priorityColors[reasoning.priority].bg, priorityColors[reasoning.priority].text, priorityColors[reasoning.priority].border)}>
            {reasoning.priority}
          </span>
        </div>
      </div>
    </div>
  )
}

function ActionCard({ action }: { action: TopAction }) {
  const [expanded, setExpanded] = useState(false)
  const pc = priorityColors[action.priority]

  return (
    <div className={clsx('card-hover overflow-hidden transition-all duration-300', expanded && 'border-[#1A8FD6]/20')}>
      <div className="p-4 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-start gap-3">
          <div className={clsx('w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 font-bold text-lg font-mono', pc.bg, pc.text)}>
            {action.rank}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-[#F5F5F7] leading-tight">{action.title}</h3>
              <span className="text-xs font-bold font-mono text-[#17C5B0] flex-shrink-0 whitespace-nowrap">
                +{formatCents(action.impactCents)}/mo
              </span>
            </div>
            <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed line-clamp-2">{action.description}</p>
            <div className="flex items-center gap-3 mt-2">
              <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full border', pc.bg, pc.text, pc.border)}>
                {action.priority}
              </span>
              <span className="text-[10px] text-[#A1A1A8]/50 flex items-center gap-1">
                <Clock size={10} /> Effort: <span className={effortColors[action.effort]}>{action.effort}</span>
              </span>
              <span className="text-[10px] text-[#A1A1A8]/50 font-mono">{action.confidence}% conf</span>
              {expanded ? <ChevronDown size={12} className="text-[#A1A1A8]/30 ml-auto" /> : <ChevronRight size={12} className="text-[#A1A1A8]/30 ml-auto" />}
            </div>
          </div>
        </div>
      </div>
      {expanded && (
        <div className="px-4 pb-4">
          <ReasoningPanel reasoning={action.reasoning} />
        </div>
      )}
    </div>
  )
}

export default function ActionsPage() {
  const actions = generateTopActions()
  const totalImpact = actions.reduce((s, a) => s + a.impactCents, 0)

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Top 3 Actions Today</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              AI-prioritized by ROI potential and effort required
            </p>
          </div>
          <DashboardTiltCard className="card px-4 py-3 hidden sm:block" glowColor="rgba(23, 197, 176, 0.1)">
            <p className="stat-label">Combined Impact</p>
            <p className="text-xl font-bold font-mono text-[#17C5B0]">+{formatCents(totalImpact)}<span className="text-sm text-[#A1A1A8] font-normal">/mo</span></p>
          </DashboardTiltCard>
        </div>
      </ScrollReveal>

      <StaggerContainer className="space-y-3">
        {actions.map(action => (
          <StaggerItem key={action.rank}>
            <ActionCard action={action} />
          </StaggerItem>
        ))}
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 border-[#1A8FD6]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
              <Zap size={16} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">How Actions Are Ranked</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                The Action Prioritizer agent reads all other agent outputs and ranks recommendations using a weighted score:
                <span className="text-[#F5F5F7] font-medium"> ROI potential (40%)</span>,
                <span className="text-[#F5F5F7] font-medium"> implementation effort (25%)</span>,
                <span className="text-[#F5F5F7] font-medium"> confidence score (20%)</span>, and
                <span className="text-[#F5F5F7] font-medium"> time sensitivity (15%)</span>.
                Every recommendation includes the full reasoning chain from the originating agent.
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
