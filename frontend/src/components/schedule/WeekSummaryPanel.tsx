import { Clock, DollarSign, AlertTriangle, Users, ChevronLeft, ChevronRight, Send, Download, TrendingUp, Lightbulb } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember, Holiday, PeakHourCell } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  holidays: Holiday[]
  weekStartDate: Date
  peakHours: PeakHourCell[]
  onPublish: () => void
  isPublished: boolean
  portalContext: 'us' | 'ca'
  onPrevWeek: () => void
  onNextWeek: () => void
  onDownloadPdf?: () => void
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function timeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + (m || 0)
}

function formatWeekRange(start: Date): string {
  const end = addDays(start, 6)
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  return `${start.toLocaleDateString('en-US', opts)} – ${end.toLocaleDateString('en-US', opts)}`
}

export default function WeekSummaryPanel({
  shifts,
  staff,
  holidays,
  weekStartDate,
  peakHours,
  onPublish,
  isPublished,
  portalContext,
  onPrevWeek,
  onNextWeek,
  onDownloadPdf,
}: Props) {
  const staffMap = new Map<string, ScheduleStaffMember>()
  staff.forEach(s => staffMap.set(s.id, s))

  // Total scheduled hours
  const realShifts = shifts.filter(s => !s.isRecommended)
  const totalMinutes = realShifts.reduce((sum, s) => {
    const dur = timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes
    return sum + Math.max(0, dur)
  }, 0)
  const totalHours = (totalMinutes / 60).toFixed(1)

  // Labor cost
  const totalLaborCents = realShifts.reduce((sum, s) => {
    const member = s.staffMemberId ? staffMap.get(s.staffMemberId) : null
    if (!member) return sum
    const dur = (timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes) / 60
    return sum + Math.round(member.hourlyRate * Math.max(0, dur))
  }, 0)

  // Labor % (labor cost / estimated weekly revenue)
  const ESTIMATED_WEEKLY_REVENUE_CENTS = 500000  // $5,000/week for demo
  const laborPercent = ESTIMATED_WEEKLY_REVENUE_CENTS > 0
    ? (totalLaborCents / ESTIMATED_WEEKLY_REVENUE_CENTS) * 100
    : 0
  const laborPercentColor = laborPercent > 35
    ? 'text-red-400'
    : laborPercent >= 30
    ? 'text-amber-400'
    : 'text-[#17C5B0]'
  const laborPercentBg = laborPercent > 35
    ? 'bg-red-500/10'
    : laborPercent >= 30
    ? 'bg-amber-500/10'
    : 'bg-[#17C5B0]/10'

  // Coverage gaps: hours where scheduled staff < recommended
  // Simplified: compare staff count per hour against peak intensity thresholds
  const coverageGaps = (() => {
    let gaps = 0
    for (let day = 0; day < 7; day++) {
      for (let hour = 0; hour < 24; hour++) {
        const peakCell = peakHours.find(c => c.day === day && c.hour === hour)
        if (!peakCell || peakCell.intensity === 0) continue

        const maxIntensity = Math.max(...peakHours.map(c => c.intensity), 1)
        const normalized = peakCell.intensity / maxIntensity

        // Recommended staff count based on intensity
        const recommended = normalized > 0.7 ? 3 : normalized > 0.4 ? 2 : 1

        // Count scheduled staff for this hour
        const scheduled = realShifts.filter(s => {
          if (s.dayOfWeek !== day) return false
          const startH = parseInt(s.startTime.split(':')[0])
          const endH = parseInt(s.endTime.split(':')[0])
          return hour >= startH && hour < endH
        }).length

        if (scheduled < recommended) gaps++
      }
    }
    return gaps
  })()

  // Per-staff cost breakdown
  const staffCosts = (() => {
    const costs: { id: string; name: string; hours: number; cost: number; rate: number }[] = []
    for (const member of staff) {
      const memberShifts = realShifts.filter(s => s.staffMemberId === member.id)
      const mins = memberShifts.reduce((sum, s) => {
        const dur = timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes
        return sum + Math.max(0, dur)
      }, 0)
      if (mins > 0) {
        costs.push({
          id: member.id,
          name: member.name,
          hours: mins / 60,
          cost: Math.round(member.hourlyRate * (mins / 60)),
          rate: member.hourlyRate,
        })
      }
    }
    return costs.sort((a, b) => b.cost - a.cost)
  })()

  const avgHourlyRate = staffCosts.length > 0
    ? Math.round(staffCosts.reduce((s, c) => s + c.rate, 0) / staffCosts.length)
    : 0

  // Labor optimization insights
  const laborInsights: string[] = (() => {
    const tips: string[] = []
    if (staffCosts.length >= 2) {
      const most = staffCosts[0]
      const least = staffCosts[staffCosts.length - 1]
      if (most.rate > least.rate * 1.5) {
        tips.push(`${most.name} costs $${(most.rate / 100).toFixed(0)}/hr — swap some shifts with ${least.name} ($${(least.rate / 100).toFixed(0)}/hr) to save`)
      }
    }
    if (laborPercent > 35) {
      tips.push('Labor above 35% of revenue — reduce hours or shift to lower-cost staff')
    }
    if (coverageGaps > 3) {
      tips.push(`${coverageGaps} coverage gaps — fill with lower-cost staff for savings`)
    }
    if (totalMinutes > 0 && staffCosts.length > 0) {
      const costPerOpHour = totalLaborCents / (totalMinutes / 60)
      if (costPerOpHour > 5000) {
        tips.push(`$${(costPerOpHour / 100).toFixed(0)}/hr operating cost is high — balance shift distribution`)
      }
    }
    return tips.slice(0, 3)
  })()

  // Overstaffed hours
  const overstaffed = (() => {
    let over = 0
    for (let day = 0; day < 7; day++) {
      for (let hour = 0; hour < 24; hour++) {
        const peakCell = peakHours.find(c => c.day === day && c.hour === hour)
        if (!peakCell || peakCell.intensity === 0) continue

        const maxIntensity = Math.max(...peakHours.map(c => c.intensity), 1)
        const normalized = peakCell.intensity / maxIntensity
        const recommended = normalized > 0.7 ? 3 : normalized > 0.4 ? 2 : 1

        const scheduled = realShifts.filter(s => {
          if (s.dayOfWeek !== day) return false
          const startH = parseInt(s.startTime.split(':')[0])
          const endH = parseInt(s.endTime.split(':')[0])
          return hour >= startH && hour < endH
        }).length

        if (scheduled > recommended + 1) over++
      }
    }
    return over
  })()

  return (
    <div className="space-y-4">
      {/* Week navigation */}
      <div className="card p-3">
        <div className="flex items-center justify-between mb-1">
          <button
            onClick={onPrevWeek}
            className="p-1 rounded hover:bg-[#1F1F23] transition-colors text-[#A1A1A8]"
          >
            <ChevronLeft size={16} />
          </button>
          <h3 className="text-[12px] font-semibold text-[#F5F5F7]">
            {formatWeekRange(weekStartDate)}
          </h3>
          <button
            onClick={onNextWeek}
            className="p-1 rounded hover:bg-[#1F1F23] transition-colors text-[#A1A1A8]"
          >
            <ChevronRight size={16} />
          </button>
        </div>
        <div className="text-[10px] text-[#A1A1A8]/40 text-center font-mono">
          {weekStartDate.getFullYear()}
        </div>
      </div>

      {/* Metrics */}
      <div className="card p-3 space-y-3">
        <h3 className="text-[11px] font-semibold text-[#A1A1A8]/60 uppercase tracking-wider">
          Week Summary
        </h3>
        <div className="space-y-2.5">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
              <Clock size={14} className="text-[#1A8FD6]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-[#A1A1A8]/50">Total Hours</p>
              <p className="text-sm font-bold text-[#F5F5F7] font-mono">{totalHours}h</p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center flex-shrink-0">
              <DollarSign size={14} className="text-[#17C5B0]" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-[#A1A1A8]/50">Labor Cost</p>
              <p className="text-sm font-bold text-[#F5F5F7] font-mono">
                {totalLaborCents > 0 ? formatCents(totalLaborCents) : '--'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${laborPercentBg}`}>
              <TrendingUp size={14} className={laborPercentColor} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-[#A1A1A8]/50">Labor %</p>
              <p className={`text-sm font-bold font-mono ${laborPercentColor}`}>
                {totalLaborCents > 0 ? `${laborPercent.toFixed(1)}%` : '--'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${coverageGaps > 0 ? 'bg-amber-500/10' : 'bg-[#17C5B0]/10'}`}>
              <AlertTriangle size={14} className={coverageGaps > 0 ? 'text-amber-400' : 'text-[#17C5B0]'} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-[#A1A1A8]/50">Coverage Gaps</p>
              <p className={`text-sm font-bold font-mono ${coverageGaps > 0 ? 'text-amber-400' : 'text-[#17C5B0]'}`}>
                {coverageGaps > 0 ? `${coverageGaps} hrs` : 'None'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <div className={`w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 ${overstaffed > 0 ? 'bg-[#1A8FD6]/10' : 'bg-[#1F1F23]'}`}>
              <Users size={14} className={overstaffed > 0 ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/30'} />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-[#A1A1A8]/50">Overstaffed</p>
              <p className="text-sm font-bold text-[#F5F5F7] font-mono">
                {overstaffed > 0 ? `${overstaffed} hrs` : 'None'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Labor Insights */}
      {staffCosts.length > 0 && (
        <div className="card p-3 space-y-3">
          <div className="flex items-center gap-1.5">
            <Lightbulb size={13} className="text-amber-400" />
            <h3 className="text-[11px] font-semibold text-[#A1A1A8]/60 uppercase tracking-wider">
              Labor Insights
            </h3>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#A1A1A8]/50">Avg Rate</span>
              <span className="text-[11px] font-bold text-[#F5F5F7] font-mono">
                ${(avgHourlyRate / 100).toFixed(0)}/hr
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-[#A1A1A8]/50">Cost/Op Hour</span>
              <span className="text-[11px] font-bold text-[#F5F5F7] font-mono">
                {totalMinutes > 0 ? `$${(totalLaborCents / (totalMinutes / 60) / 100).toFixed(0)}/hr` : '--'}
              </span>
            </div>
          </div>

          {/* Per-staff breakdown */}
          <div className="space-y-1">
            <p className="text-[9px] text-[#A1A1A8]/40 uppercase tracking-wider">Staff Breakdown</p>
            {staffCosts.slice(0, 5).map(sc => (
              <div key={sc.id} className="flex items-center justify-between">
                <span className="text-[10px] text-[#A1A1A8]/60 truncate max-w-[120px]">{sc.name}</span>
                <div className="flex items-center gap-2">
                  <span className="text-[9px] text-[#A1A1A8]/30 font-mono">{sc.hours.toFixed(1)}h</span>
                  <span className="text-[10px] font-medium text-[#F5F5F7] font-mono">
                    ${(sc.cost / 100).toFixed(0)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Optimization tips */}
          {laborInsights.length > 0 && (
            <div className="space-y-1.5 pt-1 border-t border-[#1F1F23]">
              {laborInsights.map((tip, i) => (
                <p key={i} className="text-[9px] leading-relaxed text-amber-400/70">
                  {tip}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Holiday alerts */}
      {holidays.length > 0 && (
        <div className="space-y-2">
          {holidays.map((h) => (
            <div
              key={h.date}
              className="card p-2.5 border-amber-500/10 bg-amber-500/5"
            >
              <div className="flex items-center gap-1.5 mb-0.5">
                <span className="text-amber-400 text-[10px] font-bold">{h.name}</span>
              </div>
              <div className="text-[9px] text-[#A1A1A8]/50 font-mono">{h.date}</div>
              {h.trafficMultiplier !== 1.0 && (
                <div className={`text-[9px] mt-1 font-medium ${h.trafficMultiplier > 1 ? 'text-[#17C5B0]' : 'text-amber-400'}`}>
                  Expected traffic: {h.trafficMultiplier > 1 ? '+' : ''}{((h.trafficMultiplier - 1) * 100).toFixed(0)}%
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="space-y-2">
        <button
          onClick={onPublish}
          disabled={realShifts.length === 0 || isPublished}
          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-semibold transition-all ${
            isPublished
              ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20 cursor-default'
              : realShifts.length === 0
              ? 'bg-[#1F1F23] text-[#A1A1A8]/30 cursor-not-allowed'
              : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 active:scale-[0.98]'
          }`}
        >
          <Send size={14} />
          {isPublished ? 'Published' : 'Publish Schedule'}
        </button>

        {onDownloadPdf && (
          <button
            onClick={onDownloadPdf}
            disabled={realShifts.length === 0}
            className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-[12px] font-semibold transition-all ${
              realShifts.length === 0
                ? 'bg-[#1F1F23] text-[#A1A1A8]/30 cursor-not-allowed'
                : 'bg-[#1F1F23] text-[#A1A1A8] hover:bg-[#2A2A2E] hover:text-[#F5F5F7] active:scale-[0.98]'
            }`}
          >
            <Download size={13} />
            Download PDF
          </button>
        )}
      </div>
    </div>
  )
}
