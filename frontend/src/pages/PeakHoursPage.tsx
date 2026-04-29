import { clsx } from 'clsx'
import { Clock, TrendingUp, Users, Zap } from 'lucide-react'
import { generatePeakHourHeatmap, type PeakHourCell } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import ScrollReveal, { StaggerContainer, StaggerItem } from '@/components/ScrollReveal'
import DashboardTiltCard from '@/components/DashboardTiltCard'

const dayNames = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const hourLabels = Array.from({ length: 24 }, (_, i) => {
  if (i === 0) return '12a'
  if (i < 12) return `${i}a`
  if (i === 12) return '12p'
  return `${i - 12}p`
})

function HeatmapGrid({ cells }: { cells: PeakHourCell[] }) {
  const maxIntensity = Math.max(...cells.map(c => c.intensity))

  return (
    <div className="card p-4 sm:p-5">
      <h3 className="text-sm font-semibold text-[#F5F5F7] mb-4">Weekly Transaction Heatmap</h3>
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          <div className="flex items-end gap-px mb-1 pl-10">
            {hourLabels.map((h, i) => (
              <div key={i} className="flex-1 text-center text-[8px] text-[#A1A1A8]/30">{i % 2 === 0 ? h : ''}</div>
            ))}
          </div>
          <div className="space-y-px">
            {dayNames.map((day, dayIdx) => (
              <div key={day} className="flex items-center gap-px">
                <div className="w-10 text-right pr-2 text-[10px] text-[#A1A1A8]/50 flex-shrink-0">{day}</div>
                {Array.from({ length: 24 }, (_, hour) => {
                  const cell = cells.find(c => c.day === dayIdx && c.hour === hour)
                  const intensity = cell?.intensity || 0
                  const normalized = maxIntensity > 0 ? intensity / maxIntensity : 0

                  let bg: string
                  if (normalized === 0) bg = '#1F1F23'
                  else if (normalized < 0.25) bg = 'rgba(26, 143, 214, 0.15)'
                  else if (normalized < 0.5) bg = 'rgba(26, 143, 214, 0.35)'
                  else if (normalized < 0.75) bg = 'rgba(23, 197, 176, 0.5)'
                  else bg = 'rgba(23, 197, 176, 0.8)'

                  return (
                    <div
                      key={hour}
                      className="flex-1 aspect-[2/1] rounded-[2px] group relative cursor-default"
                      style={{ backgroundColor: bg }}
                    >
                      {cell && cell.intensity > 0 && (
                        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#0A0A0B] border border-[#1F1F23] rounded text-[10px] text-[#F5F5F7] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                          {day} {hourLabels[hour]}: {cell.transactions} txns, {formatCents(cell.revenue)}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
          <div className="flex items-center justify-center gap-2 mt-4">
            <span className="text-[9px] text-[#A1A1A8]/40">Low</span>
            <div className="flex gap-px">
              {['#1F1F23', 'rgba(26, 143, 214, 0.15)', 'rgba(26, 143, 214, 0.35)', 'rgba(23, 197, 176, 0.5)', 'rgba(23, 197, 176, 0.8)'].map((c, i) => (
                <div key={i} className="w-6 h-3 rounded-sm" style={{ backgroundColor: c }} />
              ))}
            </div>
            <span className="text-[9px] text-[#A1A1A8]/40">High</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function PeakHoursPage() {
  const cells = generatePeakHourHeatmap()

  const peakCell = cells.reduce((max, c) => c.intensity > max.intensity ? c : max, cells[0])
  const totalTxns = cells.reduce((s, c) => s + c.transactions, 0)
  const morningRevenue = cells.filter(c => c.hour >= 7 && c.hour < 10).reduce((s, c) => s + c.revenue, 0)
  const totalRevenue = cells.reduce((s, c) => s + c.revenue, 0)
  const morningPct = totalRevenue > 0 ? Math.round(morningRevenue / totalRevenue * 100) : 0

  return (
    <div className="space-y-6">
      <ScrollReveal variant="fadeUp">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Peak Hours</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Powered by Peak Hour Optimizer agent • Transaction density analysis
          </p>
        </div>
      </ScrollReveal>

      <StaggerContainer className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <Zap size={16} className="text-[#17C5B0]" />
              </div>
              <div>
                <p className="stat-label">Peak Hour</p>
                <p className="text-lg font-bold text-[#17C5B0] font-mono">{hourLabels[peakCell.hour]}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
                <Clock size={16} className="text-[#1A8FD6]" />
              </div>
              <div>
                <p className="stat-label">Peak Day</p>
                <p className="text-lg font-bold text-[#F5F5F7] font-mono">{dayNames[peakCell.day]}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#7C5CFF]/10 flex items-center justify-center">
                <TrendingUp size={16} className="text-[#7C5CFF]" />
              </div>
              <div>
                <p className="stat-label">AM Revenue</p>
                <p className="text-lg font-bold text-[#7C5CFF] font-mono">{morningPct}%</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
        <StaggerItem>
          <DashboardTiltCard className="card p-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-400/10 flex items-center justify-center">
                <Users size={16} className="text-amber-400" />
              </div>
              <div>
                <p className="stat-label">Weekly Txns</p>
                <p className="text-lg font-bold text-amber-400 font-mono">{totalTxns.toLocaleString()}</p>
              </div>
            </div>
          </DashboardTiltCard>
        </StaggerItem>
      </StaggerContainer>

      <ScrollReveal variant="fadeUp" delay={0.1}>
        <HeatmapGrid cells={cells} />
      </ScrollReveal>

      <ScrollReveal variant="fadeUp" delay={0.15}>
        <div className="card p-4 border-[#17C5B0]/10">
          <div className="flex items-start gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
              <Zap size={16} className="text-[#17C5B0]" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-[#F5F5F7]">Peak Hour Optimizer Recommendation</h3>
              <p className="text-xs text-[#A1A1A8] mt-1 leading-relaxed">
                Your <span className="text-[#F5F5F7] font-medium">7-9AM window</span> generates {morningPct}% of daily revenue
                but current staffing is 1 person below optimal. Adding 1 staff member during this window would
                reduce average queue time from 4.2 to 2.1 minutes and recover an estimated
                <span className="text-[#17C5B0] font-medium"> $520/month</span> in lost walkout revenue.
                <span className="text-[#A1A1A8]/50"> (Confidence: 88%)</span>
              </p>
            </div>
          </div>
        </div>
      </ScrollReveal>
    </div>
  )
}
