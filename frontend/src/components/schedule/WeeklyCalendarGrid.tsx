import { useState, useMemo, useCallback } from 'react'
import { Plus, ChevronDown, ChevronRight, AlertTriangle } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember, Holiday } from '@/lib/agent-data'
import type { BusinessType } from '@/lib/demo-context'
import {
  groupStaffByRole, getStaffWeeklyHours, isStaffAvailable,
  fmtTime, addDays, dateStr, DAY_KEYS,
} from './schedule-helpers'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const OVERTIME_THRESHOLD = 40

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  peakHours: { day: number; hour: number; intensity: number }[]
  holidays: Holiday[]
  onShiftClick: (shift: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
  onShiftMove: (shiftId: string, newDay: number, newStartHour: number) => void
  weekStartDate: Date
  businessType: BusinessType
  roleFilter?: string
}

export default function WeeklyCalendarGrid({
  shifts, staff, holidays, onShiftClick, onSlotClick, weekStartDate,
  roleFilter,
}: Props) {
  const todayStr = dateStr(new Date())
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({})

  const holidayByDate = useMemo(() => {
    const m = new Map<string, Holiday>()
    holidays.forEach(h => m.set(h.date, h))
    return m
  }, [holidays])

  const shiftsByStaffDay = useMemo(() => {
    const m = new Map<string, ScheduleShift[]>()
    for (const s of shifts) {
      if (s.isRecommended) continue
      const key = `${s.staffMemberId || 'unassigned'}-${s.dayOfWeek}`
      const arr = m.get(key) || []
      arr.push(s)
      m.set(key, arr)
    }
    return m
  }, [shifts])

  const roleGroups = useMemo(
    () => groupStaffByRole(staff, roleFilter),
    [staff, roleFilter],
  )

  const weeklyHoursMap = useMemo(() => {
    const m = new Map<string, number>()
    for (const member of staff) {
      m.set(member.id, getStaffWeeklyHours(member.id, shifts))
    }
    return m
  }, [staff, shifts])

  const toggleGroup = useCallback((key: string) => {
    setCollapsedGroups(prev => ({ ...prev, [key]: !prev[key] }))
  }, [])

  const handleCellClick = useCallback((staffId: string, day: number) => {
    const key = `${staffId}-${day}`
    const existing = shiftsByStaffDay.get(key)
    if (existing && existing.length > 0) {
      onShiftClick(existing[0])
    } else {
      onSlotClick(day, 9)
    }
  }, [shiftsByStaffDay, onShiftClick, onSlotClick])

  const gridCols = '180px repeat(7, 1fr)'

  return (
    <div className="rounded-xl border border-[#1F1F23] overflow-hidden bg-[#0A0A0B]">
      {/* Header row */}
      <div className="grid border-b border-[#1F1F23]" style={{ gridTemplateColumns: gridCols }}>
        <div className="px-3 py-2.5 text-[11px] font-semibold text-[#A1A1A8]/50 uppercase tracking-wider border-r border-[#1F1F23]">
          Staff
        </div>
        {DAY_NAMES.map((name, di) => {
          const d = addDays(weekStartDate, di)
          const ds = dateStr(d)
          const isToday = ds === todayStr
          const hol = holidayByDate.get(ds)
          return (
            <div key={di} className={`px-2 py-2.5 text-center border-r border-[#1F1F23] last:border-r-0 ${isToday ? 'bg-[#1A8FD6]/[0.06]' : ''}`}>
              <div className={`text-[11px] font-bold uppercase tracking-wider ${isToday ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60'}`}>
                {name}
              </div>
              <div className={`text-[13px] font-semibold mt-0.5 ${isToday ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/40'}`}>
                {d.getDate()}
              </div>
              {hol && (
                <div className="text-[9px] text-amber-400 font-medium mt-0.5 truncate">{hol.name}</div>
              )}
            </div>
          )
        })}
      </div>

      {/* Role-grouped staff rows */}
      {roleGroups.map(({ group, members }) => {
        const isCollapsed = collapsedGroups[group.key] ?? false
        return (
          <div key={group.key}>
            {/* Role group header */}
            <button
              onClick={() => toggleGroup(group.key)}
              className="grid w-full border-b border-[#1F1F23] bg-[#111113] hover:bg-[#151518] transition-colors cursor-pointer"
              style={{ gridTemplateColumns: gridCols }}
            >
              <div className="col-span-8 px-3 py-1.5 flex items-center gap-2">
                {isCollapsed
                  ? <ChevronRight size={12} className="text-[#A1A1A8]/50" />
                  : <ChevronDown size={12} className="text-[#A1A1A8]/50" />}
                <div className="w-2 h-2 rounded-full" style={{ backgroundColor: group.color }} />
                <span className="text-[11px] font-bold text-[#F5F5F7]/80 uppercase tracking-wider">
                  {group.label}
                </span>
                <span className="text-[10px] text-[#A1A1A8]/40 font-mono">
                  {members.length}
                </span>
              </div>
            </button>

            {/* Staff rows within group */}
            {!isCollapsed && members.map(member => {
              const weekHrs = weeklyHoursMap.get(member.id) || 0
              const isOvertime = weekHrs > OVERTIME_THRESHOLD
              return (
                <div
                  key={member.id}
                  className="grid border-b border-[#1F1F23] last:border-b-0 hover:bg-[#111113]/50 transition-colors"
                  style={{ gridTemplateColumns: gridCols }}
                >
                  {/* Staff name cell */}
                  <div className="px-3 py-2 flex items-center gap-2 border-r border-[#1F1F23] min-h-[52px]">
                    <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: member.color }} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[12px] font-semibold text-[#F5F5F7] truncate">
                          {member.name}
                        </span>
                        {isOvertime && (
                          <span className="flex-shrink-0 inline-flex items-center gap-0.5 px-1 py-0.5 rounded text-[8px] font-bold bg-red-500/15 text-red-400 border border-red-500/20">
                            <AlertTriangle size={8} />OT
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-[#A1A1A8]/40 capitalize">
                          {member.role.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[9px] text-[#A1A1A8]/25 font-mono">
                          {weekHrs.toFixed(1)}h
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Day cells */}
                  {Array.from({ length: 7 }, (_, di) => {
                    const key = `${member.id}-${di}`
                    const cellShifts = shiftsByStaffDay.get(key) || []
                    const isToday = dateStr(addDays(weekStartDate, di)) === todayStr
                    const available = isStaffAvailable(member, di)

                    return (
                      <div
                        key={di}
                        className={`px-1 py-1.5 border-r border-[#1F1F23] last:border-r-0 cursor-pointer transition-colors min-h-[52px] flex flex-col justify-center gap-0.5 relative ${
                          isToday ? 'bg-[#1A8FD6]/[0.04]' : ''
                        } hover:bg-[#17C5B0]/[0.06]`}
                        onClick={() => handleCellClick(member.id, di)}
                      >
                        {/* Unavailable diagonal stripe pattern */}
                        {!available && cellShifts.length === 0 && (
                          <div
                            className="absolute inset-0 opacity-[0.07] pointer-events-none"
                            style={{
                              backgroundImage: 'repeating-linear-gradient(135deg, transparent, transparent 3px, #A1A1A8 3px, #A1A1A8 4px)',
                            }}
                          />
                        )}

                        {cellShifts.length > 0 ? (
                          cellShifts.map(s => (
                            <ShiftBlock
                              key={s.id}
                              shift={s}
                              color={member.color}
                              onShiftClick={onShiftClick}
                            />
                          ))
                        ) : (
                          <div className="flex items-center justify-center opacity-0 hover:opacity-40 transition-opacity h-full">
                            <Plus size={12} className="text-[#A1A1A8]" />
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )
            })}
          </div>
        )
      })}

      {/* Empty state */}
      {staff.length === 0 && (
        <div className="px-4 py-10 text-center">
          <p className="text-sm text-[#A1A1A8]/40">No staff members yet — add your team to get started</p>
        </div>
      )}
    </div>
  )
}

/** Visual shift block — colored bar with time range */
function ShiftBlock({
  shift, color, onShiftClick,
}: {
  shift: ScheduleShift
  color: string
  onShiftClick: (s: ScheduleShift) => void
}) {
  return (
    <div
      className="rounded-md px-1.5 py-1 transition-all hover:brightness-125 cursor-pointer"
      style={{
        background: `linear-gradient(135deg, ${color}20, ${color}10)`,
        border: `1px solid ${color}35`,
        borderLeft: `3px solid ${color}`,
      }}
      onClick={e => { e.stopPropagation(); onShiftClick(shift) }}
    >
      <div className="text-[10px] font-bold leading-tight" style={{ color }}>
        {fmtTime(shift.startTime)}-{fmtTime(shift.endTime)}
      </div>
    </div>
  )
}
