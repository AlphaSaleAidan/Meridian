import { useMemo } from 'react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { formatCents } from '@/lib/format'
import { timeToMinutes, addDays, dateStr } from './schedule-helpers'

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  weekStartDate: Date
}

/** Summary row at the bottom of the grid showing daily totals */
export default function ScheduleSummaryRow({ shifts, staff, weekStartDate }: Props) {
  const todayStr = dateStr(new Date())
  const staffMap = useMemo(() => new Map(staff.map(s => [s.id, s])), [staff])

  const dailyStats = useMemo(() => {
    const realShifts = shifts.filter(s => !s.isRecommended)
    return Array.from({ length: 7 }, (_, di) => {
      const dayShifts = realShifts.filter(s => s.dayOfWeek === di)
      const staffIds = new Set(dayShifts.map(s => s.staffMemberId).filter(Boolean))
      let totalMins = 0
      let totalCostCents = 0
      for (const s of dayShifts) {
        const dur = Math.max(0, timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes)
        totalMins += dur
        if (s.staffMemberId) {
          const member = staffMap.get(s.staffMemberId)
          if (member) totalCostCents += Math.round(member.hourlyRate * (dur / 60))
        }
      }
      return {
        hours: (totalMins / 60).toFixed(1),
        cost: totalCostCents,
        staffCount: staffIds.size,
      }
    })
  }, [shifts, staffMap])

  return (
    <div
      className="grid border-t-2 border-[#1A8FD6]/20 bg-[#0D0D10]"
      style={{ gridTemplateColumns: '180px repeat(7, 1fr)' }}
    >
      <div className="px-3 py-2 flex items-center border-r border-[#1F1F23]">
        <span className="text-[10px] font-bold text-[#A1A1A8]/50 uppercase tracking-wider">
          Daily Totals
        </span>
      </div>
      {dailyStats.map((stat, di) => {
        const isToday = dateStr(addDays(weekStartDate, di)) === todayStr
        return (
          <div
            key={di}
            className={`px-1.5 py-2 border-r border-[#1F1F23] last:border-r-0 text-center space-y-0.5 ${
              isToday ? 'bg-[#1A8FD6]/[0.06]' : ''
            }`}
          >
            <div className="text-[11px] font-bold text-[#F5F5F7] font-mono">
              {stat.hours}h
            </div>
            <div className="text-[9px] text-[#17C5B0] font-mono font-medium">
              {stat.cost > 0 ? formatCents(stat.cost) : '--'}
            </div>
            <div className="text-[9px] text-[#A1A1A8]/40 font-mono">
              {stat.staffCount} staff
            </div>
          </div>
        )
      })}
    </div>
  )
}
