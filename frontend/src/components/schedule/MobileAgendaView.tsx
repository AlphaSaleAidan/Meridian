import { useState } from 'react'
import { ChevronDown, Plus } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember, Holiday } from '@/lib/agent-data'

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  holidays: Holiday[]
  onShiftClick: (shift: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
  weekStartDate: Date
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function isToday(d: Date): boolean {
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}

export default function MobileAgendaView({ shifts, staff, holidays, onShiftClick, onSlotClick, weekStartDate }: Props) {
  const [collapsed, setCollapsed] = useState<Record<number, boolean>>({})

  const days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date(weekStartDate)
    date.setDate(date.getDate() + i)
    return date
  })

  const staffMap = new Map(staff.map(s => [s.id, s]))

  return (
    <div className="space-y-2">
      {days.map((date, dayIdx) => {
        const dayShifts = shifts
          .filter(s => s.dayOfWeek === dayIdx && !s.isRecommended)
          .sort((a, b) => a.startTime.localeCompare(b.startTime))
        const dayHolidays = holidays.filter(h => h.date === date.toISOString().slice(0, 10))
        const today = isToday(date)

        if (dayShifts.length === 0 && !today && dayHolidays.length === 0) return null

        const isCollapsed = collapsed[dayIdx] ?? false

        return (
          <div key={dayIdx} className="rounded-xl bg-[#111113] border border-[#1F1F23]">
            <button
              onClick={() => setCollapsed(p => ({ ...p, [dayIdx]: !isCollapsed }))}
              className="w-full flex items-center justify-between px-4 py-3 text-left"
            >
              <div className="flex items-center gap-2">
                <span className={`text-sm font-semibold ${today ? 'text-[#1A8FD6]' : 'text-[#F5F5F7]'}`}>
                  {DAY_NAMES[dayIdx]}
                </span>
                <span className="text-xs text-[#A1A1A8]">{formatDate(date)}</span>
                {today && <span className="text-[10px] bg-[#1A8FD6]/15 text-[#1A8FD6] px-1.5 py-0.5 rounded font-medium">Today</span>}
                {dayHolidays.map(h => (
                  <span key={h.date} className="text-[10px] bg-amber-500/15 text-amber-400 px-1.5 py-0.5 rounded font-medium">{h.name}</span>
                ))}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-[#A1A1A8]">{dayShifts.length} shift{dayShifts.length !== 1 ? 's' : ''}</span>
                <ChevronDown size={14} className={`text-[#A1A1A8] transition-transform ${isCollapsed ? '-rotate-90' : ''}`} />
              </div>
            </button>

            {!isCollapsed && (
              <div className="px-4 pb-3 space-y-1.5">
                {dayShifts.map(shift => {
                  const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
                  return (
                    <button
                      key={shift.id}
                      onClick={() => onShiftClick(shift)}
                      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg bg-[#0A0A0B] hover:bg-[#1F1F23] transition-colors text-left"
                    >
                      <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: member?.color ?? '#555' }} />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-[#F5F5F7] truncate">{member?.name ?? 'Unassigned'}</p>
                        <p className="text-xs text-[#A1A1A8]">{shift.startTime}–{shift.endTime} · {shift.role}</p>
                      </div>
                    </button>
                  )
                })}
                <button
                  onClick={() => onSlotClick(dayIdx, 9)}
                  className="w-full flex items-center justify-center gap-1 py-2 rounded-lg border border-dashed border-[#1F1F23] text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#333] transition-colors"
                >
                  <Plus size={12} /> Add
                </button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
