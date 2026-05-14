import { Clock, DollarSign, AlertTriangle, Users, ChevronLeft, ChevronRight, Send } from 'lucide-react'
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

      {/* Publish button */}
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
    </div>
  )
}
