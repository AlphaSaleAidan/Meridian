import { useState } from 'react'
import { clsx } from 'clsx'
import { Users, Shield, AlertTriangle, UserMinus, Heart } from 'lucide-react'
import { generateRFMSegments, generateRFMMatrix, type RFMSegment, type RFMCell } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

function RFMMatrixViz({ cells }: { cells: RFMCell[] }) {
  const maxCount = Math.max(...cells.map(c => c.count))
  const dayLabels = ['R=5 (Recent)', 'R=4', 'R=3', 'R=2', 'R=1 (Old)']
  const freqLabels = ['F=1', 'F=2', 'F=3', 'F=4', 'F=5 (Frequent)']

  return (
    <div className="card p-4 sm:p-5">
      <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">RFM Customer Matrix</h3>
      <div className="overflow-x-auto">
        <div className="min-w-[480px]">
          <div className="flex items-end gap-1 mb-1 pl-24">
            {freqLabels.map(l => (
              <div key={l} className="flex-1 text-center text-[9px] text-[#A1A1A8]/40">{l}</div>
            ))}
          </div>
          <div className="space-y-1">
            {[0, 1, 2, 3, 4].map(rowIdx => (
              <div key={rowIdx} className="flex items-center gap-1">
                <div className="w-24 text-right pr-2 text-[9px] text-[#A1A1A8]/40 flex-shrink-0">{dayLabels[rowIdx]}</div>
                {[0, 1, 2, 3, 4].map(colIdx => {
                  const cell = cells[rowIdx * 5 + colIdx]
                  const opacity = Math.max(0.15, cell.count / maxCount)
                  return (
                    <div
                      key={colIdx}
                      className="flex-1 aspect-square rounded-md flex flex-col items-center justify-center relative group cursor-default"
                      style={{ backgroundColor: cell.color, opacity }}
                    >
                      <span className="text-[10px] font-bold text-white/90">{cell.count}</span>
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#F5F5F7] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                        {cell.label}: {cell.count} customers
                      </div>
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-3 mt-4 flex-wrap">
            {[
              { label: 'Champions', color: '#17C5B0' },
              { label: 'Loyal', color: '#1A8FD6' },
              { label: 'At Risk', color: '#F97316' },
              { label: 'Lost', color: '#6B7280' },
            ].map(l => (
              <div key={l.label} className="flex items-center gap-1.5">
                <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: l.color }} />
                <span className="text-[10px] text-[#A1A1A8]">{l.label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

function SegmentCard({ segment }: { segment: RFMSegment }) {
  return (
    <div className="card-hover p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full" style={{ backgroundColor: segment.color }} />
          <h4 className="text-sm font-semibold text-[#F5F5F7]">{segment.name}</h4>
        </div>
        <span className="text-xs font-mono text-[#A1A1A8]">{segment.count} customers</span>
      </div>
      <p className="text-xs text-[#A1A1A8]/60 mb-3">{segment.description}</p>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Avg Spend</p>
          <p className="text-xs font-bold font-mono text-[#F5F5F7]">{formatCents(segment.avgSpendCents)}</p>
        </div>
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Frequency</p>
          <p className="text-xs font-bold font-mono text-[#F5F5F7]">{segment.avgFrequency}x/mo</p>
        </div>
        <div>
          <p className="text-[10px] text-[#A1A1A8]/40">Retention</p>
          <p className={clsx('text-xs font-bold font-mono', segment.retentionScore >= 70 ? 'text-[#17C5B0]' : segment.retentionScore >= 40 ? 'text-amber-400' : 'text-red-400')}>
            {segment.retentionScore}%
          </p>
        </div>
      </div>
      <div className="mt-2 h-1.5 bg-[#1F1F23] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${segment.retentionScore}%`, backgroundColor: segment.color }}
        />
      </div>
    </div>
  )
}

export default function CustomersPage() {
  const segments = generateRFMSegments()
  const matrix = generateRFMMatrix()

  const totalCustomers = segments.reduce((s, seg) => s + seg.count, 0)
  const vipCount = segments.filter(s => s.name === 'Champions' || s.name === 'Loyal').reduce((s, seg) => s + seg.count, 0)
  const atRiskCount = segments.filter(s => s.name === 'At Risk' || s.name === 'Needs Attention').reduce((s, seg) => s + seg.count, 0)
  const avgRetention = Math.round(segments.reduce((s, seg) => s + seg.retentionScore * seg.count, 0) / totalCustomers)

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Customer Intelligence</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            RFM segmentation powered by Customer Segmentor & Retention Strategist agents
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Users size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Total</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{totalCustomers}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Shield size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">VIPs</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{vipCount}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <AlertTriangle size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">At Risk</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{atRiskCount}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <Heart size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">Retention</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{avgRetention}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <RFMMatrixViz cells={matrix} />
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.15}>
        <h2 className="text-lg font-semibold text-[#F5F5F7] mb-3">Customer Segments</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {segments.map(seg => (
            <SegmentCard key={seg.name} segment={seg} />
          ))}
        </div>
      </ScrollReveal>
    </div>
  )
}
