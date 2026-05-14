import { useState } from 'react'
import { clsx } from 'clsx'
import { AlertTriangle, AlertCircle, Info, CheckCircle2, Bell } from 'lucide-react'
import { generateAnomalies, type Anomaly } from '@/lib/agent-data'
import { formatRelative } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const severityConfig = {
  critical: { color: 'text-red-400', bg: 'bg-red-500/10', border: 'border-red-500/15', icon: AlertTriangle, label: 'Critical' },
  warning:  { color: 'text-amber-400', bg: 'bg-amber-400/10', border: 'border-amber-400/15', icon: AlertCircle, label: 'Warning' },
  info:     { color: 'text-[#1A8FD6]', bg: 'bg-[#1A8FD6]/10', border: 'border-[#1A8FD6]/15', icon: Info, label: 'Info' },
}

function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  const [acked, setAcked] = useState(anomaly.acknowledged)
  const cfg = severityConfig[anomaly.severity]
  const Icon = cfg.icon
  const isNegative = anomaly.deviationPct < 0

  return (
    <DashboardTiltCard className={clsx('card p-4', !acked && cfg.border, acked && 'opacity-60')}>
      <div className="flex items-start gap-3">
        <div className={clsx('w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5', cfg.bg)}>
          <Icon size={16} className={cfg.color} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h4 className="text-sm font-semibold text-[#F5F5F7]">{anomaly.title}</h4>
            <span className={clsx('text-[9px] font-medium px-1.5 py-0.5 rounded-full border', cfg.bg, cfg.color, cfg.border)}>
              {cfg.label}
            </span>
            {acked && (
              <span className="text-[9px] text-[#17C5B0] flex items-center gap-0.5">
                <CheckCircle2 size={8} /> Acknowledged
              </span>
            )}
          </div>
          <p className="text-xs text-[#A1A1A8] leading-relaxed mb-2">{anomaly.description}</p>
          <div className="flex flex-wrap items-center gap-3 text-[10px]">
            <div>
              <span className="text-[#A1A1A8]/40">Expected: </span>
              <span className="font-mono text-[#F5F5F7]">{anomaly.expected}</span>
            </div>
            <div>
              <span className="text-[#A1A1A8]/40">Actual: </span>
              <span className="font-mono text-[#F5F5F7]">{anomaly.actual}</span>
            </div>
            <div>
              <span className="text-[#A1A1A8]/40">Deviation: </span>
              <span className={clsx('font-mono font-semibold', isNegative ? 'text-red-400' : anomaly.deviationPct > 50 ? 'text-red-400' : 'text-amber-400')}>
                {isNegative ? '' : '+'}{anomaly.deviationPct}%
              </span>
            </div>
            {anomaly.zScore != null && (
              <div>
                <span className="text-[#A1A1A8]/40">Z-Score: </span>
                <span className={clsx('font-mono font-semibold', Math.abs(anomaly.zScore) >= 3 ? 'text-red-400' : 'text-amber-400')}>
                  {anomaly.zScore > 0 ? '+' : ''}{anomaly.zScore.toFixed(1)}
                </span>
              </div>
            )}
            {anomaly.luminolScore != null && anomaly.luminolScore > 0 && (
              <div>
                <span className="text-[#A1A1A8]/40">Luminol: </span>
                <span className="font-mono font-semibold text-[#7C5CFF]">{anomaly.luminolScore}</span>
              </div>
            )}
            {anomaly.detectionMethod && (
              <div>
                <span className={clsx(
                  'px-1.5 py-0.5 rounded-full border text-[8px] font-medium',
                  anomaly.detectionMethod === 'ensemble' ? 'bg-[#7C5CFF]/10 text-[#7C5CFF] border-[#7C5CFF]/20' :
                  anomaly.detectionMethod === 'luminol' ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20' :
                  'bg-[#A1A1A8]/10 text-[#A1A1A8] border-[#A1A1A8]/20'
                )}>
                  {anomaly.detectionMethod === 'ensemble' ? 'Z + Luminol' : anomaly.detectionMethod === 'luminol' ? 'Luminol' : 'Z-Score'}
                </span>
              </div>
            )}
            <div>
              <span className="text-[#A1A1A8]/40">Source: </span>
              <span className="text-[#1A8FD6] font-medium">{anomaly.agentSource}</span>
            </div>
            <div className="text-[#A1A1A8]/30 font-mono">{formatRelative(anomaly.detectedAt)}</div>
          </div>
        </div>
        {!acked && (
          <button
            onClick={() => setAcked(true)}
            className="text-[10px] text-[#A1A1A8]/50 hover:text-[#17C5B0] border border-[#1F1F23] hover:border-[#17C5B0]/20 rounded-lg px-2 py-1 transition-colors flex-shrink-0"
          >
            Acknowledge
          </button>
        )}
      </div>
    </DashboardTiltCard>
  )
}

export default function AnomaliesPage() {
  const anomalies = generateAnomalies()

  const unacked = anomalies.filter(a => !a.acknowledged).length
  const critical = anomalies.filter(a => a.severity === 'critical').length
  const warnings = anomalies.filter(a => a.severity === 'warning').length

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Anomaly Detection</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Real-time alerts powered by Transaction Analyst, Peak Hour Optimizer & Inventory Intelligence
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                <Bell size={16} className="text-red-400" />
              </div>
              <div>
                <p className="stat-label">Unacknowledged</p>
                <p className="text-lg font-bold text-red-400 font-mono">{unacked}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
                <AlertTriangle size={16} className="text-red-400" />
              </div>
              <div>
                <p className="stat-label">Critical</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{critical}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <AlertCircle size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Warnings</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{warnings}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <CheckCircle2 size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Total Alerts</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{anomalies.length}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <div className="space-y-3">
          {anomalies
            .sort((a, b) => {
              if (a.acknowledged !== b.acknowledged) return a.acknowledged ? 1 : -1
              const sev = { critical: 0, warning: 1, info: 2 }
              return sev[a.severity] - sev[b.severity]
            })
            .map(a => <AnomalyCard key={a.id} anomaly={a} />)}
        </div>
      </ScrollReveal>
    </div>
  )
}
