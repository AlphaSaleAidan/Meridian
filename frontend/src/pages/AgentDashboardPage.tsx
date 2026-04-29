import { useState } from 'react'
import { clsx } from 'clsx'
import {
  Bot, Activity, Zap, Clock, ChevronDown, ChevronRight,
  TrendingUp, AlertTriangle, Target, Brain,
} from 'lucide-react'
import { generateAgents, type AgentInfo } from '@/lib/agent-data'
import { formatRelative } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const categoryColors: Record<string, string> = {
  analysis: 'text-[#1A8FD6] bg-[#1A8FD6]/10',
  forecasting: 'text-[#7C5CFF] bg-[#7C5CFF]/10',
  optimization: 'text-[#17C5B0] bg-[#17C5B0]/10',
  strategy: 'text-amber-400 bg-amber-400/10',
  coordination: 'text-[#4FE3C1] bg-[#4FE3C1]/10',
}

const statusColors: Record<string, { dot: string; text: string }> = {
  active: { dot: 'bg-[#17C5B0]', text: 'text-[#17C5B0]' },
  running: { dot: 'bg-[#1A8FD6] animate-pulse', text: 'text-[#1A8FD6]' },
  idle: { dot: 'bg-[#A1A1A8]/40', text: 'text-[#A1A1A8]/60' },
  error: { dot: 'bg-red-400', text: 'text-red-400' },
}

function AgentCard({ agent }: { agent: AgentInfo }) {
  const [expanded, setExpanded] = useState(false)
  const sc = statusColors[agent.status]
  const cc = categoryColors[agent.category]

  return (
    <div
      className={clsx(
        'card-hover p-4 cursor-pointer transition-all duration-300',
        expanded && 'border-[#1A8FD6]/20 bg-[#141416]'
      )}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start gap-3">
        <div className={clsx('p-2 rounded-lg flex-shrink-0', cc.split(' ')[1])}>
          <Bot size={16} className={cc.split(' ')[0]} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <h4 className="text-sm font-semibold text-[#F5F5F7] truncate">{agent.name}</h4>
              <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', sc.dot)} />
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-[10px] font-mono text-[#A1A1A8]/50">{agent.confidence}%</span>
              {expanded ? <ChevronDown size={14} className="text-[#A1A1A8]/40" /> : <ChevronRight size={14} className="text-[#A1A1A8]/40" />}
            </div>
          </div>
          <p className="text-xs text-[#A1A1A8]/60 mt-0.5 truncate">{agent.latestFinding}</p>
          <div className="flex items-center gap-3 mt-2">
            <span className={clsx('text-[10px] font-medium px-2 py-0.5 rounded-full', cc)}>{agent.category}</span>
            <span className="text-[10px] text-[#A1A1A8]/40">{agent.findings} findings</span>
            <span className="text-[10px] text-[#A1A1A8]/40">{formatRelative(agent.lastRun)}</span>
          </div>
        </div>
      </div>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-[#1F1F23] space-y-2 animate-fade-in">
          <p className="text-xs text-[#A1A1A8] leading-relaxed">{agent.description}</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-[#A1A1A8]/40">Last Run</span>
              <p className="text-[#A1A1A8] font-mono">{formatRelative(agent.lastRun)}</p>
            </div>
            <div>
              <span className="text-[#A1A1A8]/40">Next Run</span>
              <p className="text-[#A1A1A8] font-mono">{formatRelative(agent.nextRun)}</p>
            </div>
          </div>
          <div className="p-3 bg-[#0A0A0B] rounded-lg border border-[#1F1F23]">
            <p className="text-[10px] font-medium text-[#A1A1A8]/60 uppercase tracking-wider mb-1">Latest Finding</p>
            <p className="text-xs text-[#F5F5F7] leading-relaxed">{agent.latestFinding}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1.5 bg-[#1F1F23] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] transition-all duration-700"
                style={{ width: `${agent.confidence}%` }}
              />
            </div>
            <span className="text-[10px] font-mono text-[#A1A1A8]">{agent.confidence}% confidence</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default function AgentDashboardPage() {
  const agents = generateAgents()
  const [filter, setFilter] = useState<string>('')

  const activeCount = agents.filter(a => a.status === 'active' || a.status === 'running').length
  const totalFindings = agents.reduce((s, a) => s + a.findings, 0)
  const avgConfidence = Math.round(agents.reduce((s, a) => s + a.confidence, 0) / agents.length)

  const filtered = filter ? agents.filter(a => a.category === filter) : agents
  const categories = [...new Set(agents.map(a => a.category))]

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Agent Intelligence</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            <span className="font-mono">{agents.length}</span> agents deployed • <span className="font-mono">{activeCount}</span> active • <span className="font-mono">{totalFindings}</span> total findings
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Activity size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Active</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{activeCount}/{agents.length}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Zap size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Findings</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{totalFindings}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <Brain size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Avg Confidence</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{avgConfidence}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <Target size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Actions Today</p>
                <p className="text-lg font-bold text-amber-400 font-mono">3</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
          <button
            onClick={() => setFilter('')}
            className={clsx(
              'px-3 py-1.5 text-xs font-medium rounded-full transition-all border whitespace-nowrap',
              !filter ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20' : 'text-[#A1A1A8] border-[#1F1F23] hover:text-[#F5F5F7]'
            )}
          >
            All ({agents.length})
          </button>
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={clsx(
                'px-3 py-1.5 text-xs font-medium rounded-full transition-all border whitespace-nowrap capitalize',
                filter === cat ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20' : 'text-[#A1A1A8] border-[#1F1F23] hover:text-[#F5F5F7]'
              )}
            >
              {cat} ({agents.filter(a => a.category === cat).length})
            </button>
          ))}
        </div>
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="space-y-2">
          {filtered.map(agent => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </ScrollReveal>
    </div>
  )
}
