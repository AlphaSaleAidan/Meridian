import { useState, useMemo } from 'react'
import { Plus } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { fmtTime } from './schedule-helpers'

function pad2(n: number) { return n < 10 ? `0${n}` : `${n}` }
function formatDateISO(d: Date) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }
function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate() + n); return r }

const MOBILE_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  holidays: { date: string; name: string }[]
  weekStartDate: Date
  onShiftClick: (s: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
}

export default function MobileDayView({ shifts, staff, holidays, weekStartDate, onShiftClick, onSlotClick }: Props) {
  const [day, setDay] = useState(() => {
    const now = new Date(), todayStr = formatDateISO(now)
    for (let i = 0; i < 7; i++) {
      if (formatDateISO(addDays(weekStartDate, i)) === todayStr) return i
    }
    return 0
  })

  const staffMap = useMemo(() => new Map(staff.map(s => [s.id, s])), [staff])
  const todayStr = formatDateISO(new Date())
  const selectedDate = addDays(weekStartDate, day)
  const selectedDateStr = formatDateISO(selectedDate)
  const isToday = selectedDateStr === todayStr
  const holiday = holidays.find(h => h.date === selectedDateStr)

  const dayShifts = useMemo(
    () => shifts.filter(s => s.dayOfWeek === day && !s.isRecommended)
      .sort((a, b) => a.startTime.localeCompare(b.startTime)),
    [shifts, day],
  )

  return (
    <div className="lg:hidden space-y-3">
      {/* Day tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {MOBILE_DAYS.map((name, di) => {
          const d = addDays(weekStartDate, di)
          const isSel = di === day
          const isTod = formatDateISO(d) === todayStr
          const cnt = shifts.filter(s => s.dayOfWeek === di && !s.isRecommended).length
          return (
            <button key={di} onClick={() => setDay(di)}
              className={`flex-1 min-w-[44px] flex flex-col items-center py-2 rounded-lg transition-all ${
                isSel ? 'bg-[#17C5B0]/10 border border-[#17C5B0]/30' : 'border border-transparent hover:bg-[#1F1F23]'
              }`}>
              <span className={`text-[10px] font-bold uppercase ${isSel ? 'text-[#17C5B0]' : isTod ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60'}`}>{name}</span>
              <span className={`text-[13px] font-semibold ${isSel ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/40'}`}>{d.getDate()}</span>
              {cnt > 0 && <div className={`mt-0.5 w-1.5 h-1.5 rounded-full ${isSel ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/25'}`} />}
            </button>
          )
        })}
      </div>

      {/* Day header */}
      <div className="flex items-center justify-between px-1">
        <div>
          <span className="text-sm font-semibold text-[#F5F5F7]">
            {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
          </span>
          {isToday && <span className="ml-2 text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 px-1.5 py-0.5 rounded">Today</span>}
          {holiday && <span className="ml-2 text-[10px] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">{holiday.name}</span>}
        </div>
        <span className="text-[11px] text-[#A1A1A8]/40 font-mono">{dayShifts.length} shifts</span>
      </div>

      {/* Shift cards */}
      <div className="space-y-2">
        {dayShifts.map(shift => {
          const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
          const color = member?.color || '#A1A1A8'
          return (
            <button key={shift.id} onClick={() => onShiftClick(shift)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-[#111113] border border-[#1F1F23] hover:bg-[#1A1A1D] transition-colors text-left">
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-semibold text-[#F5F5F7] truncate">{member?.name || 'Unassigned'}</div>
                <div className="text-[11px] text-[#A1A1A8]/50 capitalize">{member?.role?.replace(/_/g, ' ') || shift.role}</div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[12px] font-mono text-[#F5F5F7]/80">{fmtTime(shift.startTime)}-{fmtTime(shift.endTime)}</div>
              </div>
            </button>
          )
        })}

        {dayShifts.length === 0 && (
          <div className="text-center py-8">
            <p className="text-sm text-[#A1A1A8]/30">No shifts scheduled</p>
          </div>
        )}

        <button onClick={() => onSlotClick(day, 9)}
          className="w-full flex items-center justify-center gap-1.5 py-3 rounded-xl border border-dashed border-[#1F1F23] text-xs text-[#A1A1A8]/50 hover:text-[#A1A1A8] hover:border-[#333] transition-colors">
          <Plus size={14} /> Add shift
        </button>
      </div>
    </div>
  )
}
