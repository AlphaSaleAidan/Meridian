import { useMemo } from 'react'
import { Plus, ChevronRight, CalendarDays, Coffee, Radio } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { fmtTime, timeToMinutes, getNowNext } from './schedule-helpers'

function pad2(n: number) { return n < 10 ? `0${n}` : `${n}` }
function formatDateISO(d: Date) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }
function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate() + n); return r }

const MOBILE_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function initials(name: string) {
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}
function hoursLabel(mins: number) {
  if (mins <= 0) return '0h'
  return `${(mins / 60).toFixed(mins % 60 === 0 ? 0 : 1)}h`
}

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  holidays: { date: string; name: string }[]
  weekStartDate: Date
  day: number
  onDayChange: (day: number) => void
  onShiftClick: (s: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
}

export default function MobileDayView({ shifts, staff, holidays, weekStartDate, day, onDayChange, onShiftClick, onSlotClick }: Props) {
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

  // Day-level summary so the merchant sees the shape of the day at a glance.
  const dayMinutes = useMemo(
    () => dayShifts.reduce((sum, s) =>
      sum + Math.max(0, timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes), 0),
    [dayShifts],
  )

  // "Right now" glance — only meaningful while looking at today.
  const nowNext = useMemo(() => {
    if (!isToday) return null
    const now = new Date()
    return getNowNext(shifts, staffMap, day, now.getHours() * 60 + now.getMinutes())
  }, [isToday, shifts, staffMap, day])

  return (
    <div className="lg:hidden space-y-3 pb-24">
      {/* Day tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        {MOBILE_DAYS.map((name, di) => {
          const d = addDays(weekStartDate, di)
          const isSel = di === day
          const isTod = formatDateISO(d) === todayStr
          const cnt = shifts.filter(s => s.dayOfWeek === di && !s.isRecommended).length
          return (
            <button key={di} onClick={() => onDayChange(di)}
              aria-label={`${name} ${d.getDate()}, ${cnt} shifts`}
              className={`flex-1 min-w-[46px] flex flex-col items-center gap-0.5 py-2.5 rounded-2xl transition-all active:scale-95 ${
                isSel
                  ? 'bg-gradient-to-b from-[#17C5B0]/20 to-[#1A8FD6]/10 border border-[#17C5B0]/40 shadow-lg shadow-[#17C5B0]/10'
                  : 'border border-[#1F1F23] hover:bg-[#1F1F23]'
              }`}>
              <span className={`text-[10px] font-bold uppercase tracking-wide ${isSel ? 'text-[#17C5B0]' : isTod ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/55'}`}>{name}</span>
              <span className={`text-[15px] font-bold leading-none ${isSel ? 'text-[#F5F5F7]' : isTod ? 'text-[#F5F5F7]/80' : 'text-[#A1A1A8]/40'}`}>{d.getDate()}</span>
              <div className={`mt-0.5 h-1.5 transition-all ${cnt > 0 ? 'w-1.5 rounded-full' : 'w-0'} ${isSel ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/30'}`} />
            </button>
          )
        })}
      </div>

      {/* "Right now" live card — today only */}
      {nowNext && (nowNext.onNow.length > 0 || nowNext.next) && (
        <div className="rounded-2xl bg-gradient-to-br from-[#17C5B0]/[0.10] to-[#1A8FD6]/[0.06] border border-[#17C5B0]/25 p-3.5">
          <div className="flex items-center gap-1.5 mb-2">
            <Radio size={13} className="text-[#17C5B0] animate-pulse" />
            <span className="text-[11px] font-bold uppercase tracking-wide text-[#17C5B0]">On now</span>
            <span className="text-[12px] font-semibold text-[#F5F5F7]/80 ml-auto">{nowNext.onNow.length} working</span>
          </div>
          {nowNext.onNow.length > 0 ? (
            <div className="flex items-center gap-1.5 flex-wrap">
              {nowNext.onNow.map(({ shift, member }) => (
                <span key={shift.id} className="flex items-center gap-1.5 pl-1 pr-2.5 py-1 rounded-full bg-[#0A0A0B]/40 border border-[#1F1F23]">
                  <span className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold"
                    style={{ backgroundColor: `${member?.color ?? '#A1A1A8'}22`, color: member?.color ?? '#A1A1A8' }}>
                    {member ? initials(member.name) : '?'}
                  </span>
                  <span className="text-[12px] font-semibold text-[#F5F5F7]">{member?.name?.split(' ')[0] ?? 'Open'}</span>
                  <span className="text-[10px] text-[#A1A1A8]/60">til {fmtTime(shift.endTime)}</span>
                </span>
              ))}
            </div>
          ) : (
            <p className="text-[12px] text-[#A1A1A8]/70">No one's on the clock right now.</p>
          )}
          {nowNext.next && (
            <p className="text-[12px] text-[#A1A1A8] mt-2 pt-2 border-t border-[#17C5B0]/15">
              Next up: <span className="font-semibold text-[#F5F5F7]">{nowNext.next.member?.name?.split(' ')[0] ?? 'Open shift'}</span> at <span className="font-semibold text-[#F5F5F7]">{fmtTime(nowNext.next.shift.startTime)}</span>
            </p>
          )}
        </div>
      )}

      {/* Day header + summary */}
      <div className="flex items-end justify-between px-1">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[15px] font-bold text-[#F5F5F7]">
              {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
            </span>
            {isToday && <span className="text-[10px] font-semibold text-[#1A8FD6] bg-[#1A8FD6]/10 px-2 py-0.5 rounded-full">Today</span>}
            {holiday && <span className="text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded-full">{holiday.name}</span>}
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-[13px] font-bold text-[#F5F5F7]">{hoursLabel(dayMinutes)}</div>
          <div className="text-[10px] text-[#A1A1A8]/50">{dayShifts.length} shift{dayShifts.length === 1 ? '' : 's'}</div>
        </div>
      </div>

      {/* Shift cards */}
      <div className="space-y-2.5">
        {dayShifts.map(shift => {
          const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
          const color = member?.color || '#A1A1A8'
          const mins = Math.max(0, timeToMinutes(shift.endTime) - timeToMinutes(shift.startTime) - shift.breakMinutes)
          const roleLabel = (member?.role || shift.role || 'any').replace(/_/g, ' ')
          return (
            <button key={shift.id} onClick={() => onShiftClick(shift)}
              className="group w-full flex items-center gap-3 p-3 rounded-2xl bg-[#111113] border border-[#1F1F23]
                         hover:border-[#2A2A30] hover:bg-[#16161A] active:scale-[0.99] transition-all text-left
                         relative overflow-hidden">
              {/* color spine */}
              <span className="absolute left-0 top-0 bottom-0 w-1" style={{ backgroundColor: color }} />
              {/* avatar */}
              <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 text-[12px] font-bold ml-1"
                style={{ backgroundColor: `${color}22`, color, border: `1px solid ${color}40` }}>
                {member ? initials(member.name) : '+'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-[14px] font-bold text-[#F5F5F7] truncate">{member?.name || 'Unassigned'}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[11px] font-medium capitalize px-1.5 py-0.5 rounded-md"
                    style={{ backgroundColor: `${color}1A`, color }}>{roleLabel}</span>
                  {shift.breakMinutes > 0 && (
                    <span className="flex items-center gap-0.5 text-[10px] text-[#A1A1A8]/45">
                      <Coffee size={10} />{shift.breakMinutes}m
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right shrink-0">
                <div className="text-[13px] font-semibold text-[#F5F5F7]/90 tabular-nums">{fmtTime(shift.startTime)}–{fmtTime(shift.endTime)}</div>
                <div className="text-[11px] text-[#17C5B0]/80 font-medium">{hoursLabel(mins)}</div>
              </div>
              <ChevronRight size={16} className="text-[#A1A1A8]/25 group-hover:text-[#A1A1A8]/50 transition-colors shrink-0 -ml-1" />
            </button>
          )
        })}

        {dayShifts.length === 0 && (
          <div className="flex flex-col items-center text-center py-10 px-6 rounded-2xl border border-dashed border-[#1F1F23]">
            <div className="w-12 h-12 rounded-2xl bg-[#1A8FD6]/10 flex items-center justify-center mb-3">
              <CalendarDays size={22} className="text-[#1A8FD6]/70" />
            </div>
            <p className="text-sm font-semibold text-[#F5F5F7]/80">Nothing scheduled yet</p>
            <p className="text-[12px] text-[#A1A1A8]/50 mt-1">Tap below to add the first shift for this day.</p>
          </div>
        )}

        <button onClick={() => onSlotClick(day, 9)}
          className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl border border-dashed border-[#2A2A30]
                     text-[13px] font-semibold text-[#A1A1A8]/70 hover:text-[#17C5B0] hover:border-[#17C5B0]/40
                     hover:bg-[#17C5B0]/[0.04] active:scale-[0.99] transition-all">
          <Plus size={16} /> Add shift
        </button>
      </div>
    </div>
  )
}
