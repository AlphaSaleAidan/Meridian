import { useMemo, useCallback } from 'react'
import { Plus } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember, Holiday } from '@/lib/agent-data'
import type { BusinessType } from '@/lib/demo-context'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate() + n); return r }
function dateStr(d: Date) { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}` }
function fmtTime(t: string) {
  const h = parseInt(t)
  if (h === 0 || h === 12) return `12${h === 0 ? 'a' : 'p'}`
  return h < 12 ? `${h}a` : `${h - 12}p`
}

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
}

export default function WeeklyCalendarGrid({
  shifts, staff, holidays, onShiftClick, onSlotClick, weekStartDate,
}: Props) {
  const todayStr = dateStr(new Date())

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

  const handleCellClick = useCallback((staffId: string, day: number) => {
    const key = `${staffId}-${day}`
    const existing = shiftsByStaffDay.get(key)
    if (existing && existing.length > 0) {
      onShiftClick(existing[0])
    } else {
      onSlotClick(day, 9)
    }
  }, [shiftsByStaffDay, onShiftClick, onSlotClick])

  return (
    <div className="rounded-xl border border-[#1F1F23] overflow-hidden bg-[#0A0A0B]">
      {/* Header row — days */}
      <div className="grid border-b border-[#1F1F23]" style={{ gridTemplateColumns: '140px repeat(7, 1fr)' }}>
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

      {/* Staff rows */}
      {staff.map(member => (
        <div
          key={member.id}
          className="grid border-b border-[#1F1F23] last:border-b-0 hover:bg-[#111113]/50 transition-colors"
          style={{ gridTemplateColumns: '140px repeat(7, 1fr)' }}
        >
          {/* Staff name */}
          <div className="px-3 py-3 flex items-center gap-2 border-r border-[#1F1F23] min-h-[56px]">
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: member.color }} />
            <div className="min-w-0">
              <div className="text-[12px] font-semibold text-[#F5F5F7] truncate">{member.name}</div>
              <div className="text-[10px] text-[#A1A1A8]/40 capitalize">{member.role.replace(/_/g, ' ')}</div>
            </div>
          </div>

          {/* Day cells */}
          {Array.from({ length: 7 }, (_, di) => {
            const key = `${member.id}-${di}`
            const cellShifts = shiftsByStaffDay.get(key) || []
            const isToday = dateStr(addDays(weekStartDate, di)) === todayStr

            return (
              <div
                key={di}
                className={`px-1.5 py-2 border-r border-[#1F1F23] last:border-r-0 cursor-pointer transition-colors min-h-[56px] flex flex-col justify-center gap-1 ${
                  isToday ? 'bg-[#1A8FD6]/[0.04]' : ''
                } hover:bg-[#17C5B0]/[0.06]`}
                onClick={() => handleCellClick(member.id, di)}
              >
                {cellShifts.length > 0 ? (
                  cellShifts.map(s => (
                    <div
                      key={s.id}
                      className="rounded-md px-2 py-1.5 text-center transition-all hover:brightness-125"
                      style={{ backgroundColor: `${member.color}18`, border: `1px solid ${member.color}35` }}
                      onClick={e => { e.stopPropagation(); onShiftClick(s) }}
                    >
                      <div className="text-[11px] font-semibold" style={{ color: member.color }}>
                        {fmtTime(s.startTime)}–{fmtTime(s.endTime)}
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-center opacity-0 hover:opacity-40 transition-opacity">
                    <Plus size={14} className="text-[#A1A1A8]" />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      ))}

      {/* Empty state */}
      {staff.length === 0 && (
        <div className="px-4 py-10 text-center">
          <p className="text-sm text-[#A1A1A8]/40">No staff members yet — add your team to get started</p>
        </div>
      )}
    </div>
  )
}
