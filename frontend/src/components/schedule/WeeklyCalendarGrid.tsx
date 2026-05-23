import { useMemo, useState, useCallback, type DragEvent } from 'react'
import { Sparkles, ChevronLeft, ChevronRight } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember, PeakHourCell, Holiday } from '@/lib/agent-data'
import type { BusinessType } from '@/lib/demo-context'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const DAY_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const BIZ_HOURS: Record<string, { open: number; close: number }> = {
  coffee_shop: { open: 5, close: 21 },
  restaurant: { open: 10, close: 23 },
  fast_food: { open: 5, close: 23 },
  auto_shop: { open: 7, close: 19 },
  smoke_shop: { open: 10, close: 22 },
}

const ROW_H = 56

function pad2(n: number) { return n < 10 ? `0${n}` : `${n}` }
function timeToMinutes(t: string) { const [h, m] = t.split(':').map(Number); return h * 60 + (m || 0) }
function formatHour(h: number) { return h === 0 ? '12a' : h < 12 ? `${h}a` : h === 12 ? '12p' : `${h - 12}p` }
function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate() + n); return r }
function fmtDate(d: Date) { return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }) }
function dateStr(d: Date) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  peakHours: PeakHourCell[]
  holidays: Holiday[]
  onShiftClick: (shift: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
  onShiftMove: (shiftId: string, newDay: number, newStartHour: number) => void
  weekStartDate: Date
  businessType: BusinessType
}

export default function WeeklyCalendarGrid({
  shifts, staff, peakHours, holidays,
  onShiftClick, onSlotClick, onShiftMove,
  weekStartDate, businessType,
}: Props) {
  const biz = BIZ_HOURS[businessType] || BIZ_HOURS.coffee_shop
  const hourRange = useMemo(() => {
    const a: number[] = []
    for (let h = biz.open; h < biz.close; h++) a.push(h)
    return a
  }, [biz.open, biz.close])

  const today = new Date()
  const todayS = dateStr(today)
  const todayDow = (() => {
    for (let di = 0; di < 7; di++) {
      if (dateStr(addDays(weekStartDate, di)) === todayS) return di
    }
    return 0
  })()

  const [selectedDay, setSelectedDay] = useState(todayDow)

  const staffMap = useMemo(() => {
    const m = new Map<string, ScheduleStaffMember>()
    staff.forEach(s => m.set(s.id, s))
    return m
  }, [staff])

  const peakLookup = useMemo(() => {
    const m = new Map<string, number>()
    const mx = Math.max(...peakHours.map(c => c.intensity), 1)
    peakHours.forEach(c => m.set(`${c.day}-${c.hour}`, c.intensity / mx))
    return m
  }, [peakHours])

  const holidayByDate = useMemo(() => {
    const m = new Map<string, Holiday>()
    holidays.forEach(h => m.set(h.date, h))
    return m
  }, [holidays])

  // Shifts for selected day
  const dayShifts = useMemo(
    () => shifts.filter(s => s.dayOfWeek === selectedDay).sort((a, b) => timeToMinutes(a.startTime) - timeToMinutes(b.startTime)),
    [shifts, selectedDay],
  )

  // Week overview: shift count per day
  const dayCounts = useMemo(() => {
    const counts = new Array(7).fill(0)
    shifts.forEach(s => { if (!s.isRecommended) counts[s.dayOfWeek]++ })
    return counts
  }, [shifts])

  // Drag state
  const [draggingId, setDraggingId] = useState<string | null>(null)
  const [dropHour, setDropHour] = useState<number | null>(null)

  const handleDragStart = useCallback((e: DragEvent<HTMLDivElement>, shift: ScheduleShift) => {
    e.dataTransfer.setData('text/plain', shift.id)
    e.dataTransfer.effectAllowed = 'move'
    setDraggingId(shift.id)
  }, [])
  const handleDragEnd = useCallback(() => { setDraggingId(null); setDropHour(null) }, [])
  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>, hour: number) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'
    setDropHour(hour)
  }, [])
  const handleDrop = useCallback((e: DragEvent<HTMLDivElement>, hour: number) => {
    e.preventDefault()
    const id = e.dataTransfer.getData('text/plain')
    if (id) onShiftMove(id, selectedDay, hour)
    setDraggingId(null); setDropHour(null)
  }, [onShiftMove, selectedDay])

  const selectedDate = addDays(weekStartDate, selectedDay)
  const selectedDateStr = dateStr(selectedDate)
  const isToday = selectedDateStr === todayS
  const holiday = holidayByDate.get(selectedDateStr)

  return (
    <div className="space-y-3">
      {/* Week day tabs */}
      <div className="card p-1.5 flex items-center gap-1">
        <button onClick={() => setSelectedDay(d => Math.max(0, d - 1))}
          className="p-1.5 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8] transition-colors flex-shrink-0">
          <ChevronLeft size={16} />
        </button>
        <div className="flex-1 grid grid-cols-7 gap-1">
          {DAY_NAMES.map((name, di) => {
            const d = addDays(weekStartDate, di)
            const ds = dateStr(d)
            const isSel = di === selectedDay
            const isTod = ds === todayS
            const cnt = dayCounts[di]
            return (
              <button
                key={di}
                onClick={() => setSelectedDay(di)}
                className={`relative flex flex-col items-center py-2 px-1 rounded-lg text-center transition-all ${
                  isSel
                    ? 'bg-[#17C5B0]/10 border border-[#17C5B0]/30'
                    : 'hover:bg-[#1F1F23] border border-transparent'
                }`}
              >
                <span className={`text-[11px] font-bold uppercase tracking-wider ${
                  isSel ? 'text-[#17C5B0]' : isTod ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/70'
                }`}>{name}</span>
                <span className={`text-[13px] font-semibold mt-0.5 ${
                  isSel ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/50'
                }`}>{d.getDate()}</span>
                {cnt > 0 && (
                  <div className={`mt-1 flex gap-0.5`}>
                    {Array.from({ length: Math.min(cnt, 5) }).map((_, i) => (
                      <div key={i} className={`w-1 h-1 rounded-full ${isSel ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/30'}`} />
                    ))}
                  </div>
                )}
              </button>
            )
          })}
        </div>
        <button onClick={() => setSelectedDay(d => Math.min(6, d + 1))}
          className="p-1.5 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8] transition-colors flex-shrink-0">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* Day header */}
      <div className="flex items-center justify-between px-1">
        <div>
          <h3 className="text-[15px] font-bold text-[#F5F5F7]">
            {DAY_FULL[selectedDay]}, {fmtDate(selectedDate)}
            {isToday && <span className="ml-2 text-[11px] font-medium text-[#1A8FD6]">Today</span>}
          </h3>
          {holiday && (
            <span className="text-[11px] font-semibold text-amber-400">{holiday.name}</span>
          )}
        </div>
        <div className="text-[12px] text-[#A1A1A8]/50 font-mono">
          {dayShifts.filter(s => !s.isRecommended).length} shifts
        </div>
      </div>

      {/* Day timeline */}
      <div className="card overflow-hidden rounded-xl bg-[#0A0A0B]">
        <div className="relative" style={{ height: hourRange.length * ROW_H }}>
          {/* Hour rows */}
          {hourRange.map(hour => {
            const intensity = peakLookup.get(`${selectedDay}-${hour}`) || 0
            const isDrop = dropHour === hour
            let bg = 'transparent'
            if (isDrop) bg = 'rgba(23,197,176,0.12)'
            else if (intensity > 0.75) bg = 'rgba(23,197,176,0.06)'
            else if (intensity > 0.5) bg = 'rgba(23,197,176,0.03)'

            return (
              <div
                key={hour}
                className={`absolute left-0 right-0 flex border-b transition-colors ${
                  hour % 2 === 0 ? 'border-[#1F1F23]/60' : 'border-[#1F1F23]/25'
                } ${isDrop ? 'ring-1 ring-inset ring-[#17C5B0]/30' : ''}`}
                style={{ top: (hour - biz.open) * ROW_H, height: ROW_H, backgroundColor: bg !== 'transparent' ? bg : undefined }}
                onClick={() => onSlotClick(selectedDay, hour)}
                onDragOver={e => handleDragOver(e, hour)}
                onDragLeave={() => setDropHour(null)}
                onDrop={e => handleDrop(e, hour)}
              >
                <div className="w-[52px] flex-shrink-0 flex items-start justify-end pr-2 pt-1.5">
                  <span className={`text-[11px] font-mono ${hour % 2 === 0 ? 'text-[#A1A1A8]/60' : 'text-[#A1A1A8]/25'}`}>
                    {formatHour(hour)}
                  </span>
                </div>
                <div className="flex-1 cursor-pointer hover:bg-[#1A8FD6]/[0.04] transition-colors" />
              </div>
            )
          })}

          {/* Current time line */}
          {isToday && today.getHours() >= biz.open && today.getHours() < biz.close && (
            <div
              className="absolute left-[52px] right-0 pointer-events-none z-30"
              style={{ top: ((today.getHours() * 60 + today.getMinutes() - biz.open * 60) / 60) * ROW_H }}
            >
              <div className="relative">
                <div className="absolute -left-1 -top-1 w-2.5 h-2.5 rounded-full bg-[#EF4444]" />
                <div className="h-[2px] bg-[#EF4444]/70 w-full" />
              </div>
            </div>
          )}

          {/* Shift blocks */}
          {dayShifts.map(shift => {
            const sMins = timeToMinutes(shift.startTime)
            const eMins = timeToMinutes(shift.endTime)
            const topPx = ((sMins - biz.open * 60) / 60) * ROW_H
            const hPx = ((eMins - sMins) / 60) * ROW_H
            if (topPx < 0 || topPx >= hourRange.length * ROW_H) return null

            const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
            const color = member?.color || '#A1A1A8'
            const isDragging = draggingId === shift.id
            const durH = ((eMins - sMins) / 60)

            return (
              <div
                key={shift.id}
                draggable
                onDragStart={e => handleDragStart(e, shift)}
                onDragEnd={handleDragEnd}
                className={`absolute transition-all group/shift ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
                style={{
                  top: topPx + 2,
                  height: Math.max(hPx - 4, 28),
                  left: 56,
                  right: 8,
                  opacity: isDragging ? 0.35 : 1,
                  zIndex: isDragging ? 30 : 10,
                }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.zIndex = '25' }}
                onMouseLeave={e => { if (!isDragging) (e.currentTarget as HTMLElement).style.zIndex = '10' }}
                onClick={e => { e.stopPropagation(); onShiftClick(shift) }}
              >
                <div
                  className={`h-full rounded-lg overflow-hidden shadow-sm group-hover/shift:shadow-lg group-hover/shift:brightness-110 transition-all flex items-center gap-3 px-3 ${
                    shift.isRecommended ? 'border border-dashed' : 'border'
                  }`}
                  style={{ backgroundColor: `${color}15`, borderColor: `${color}40` }}
                >
                  {/* Color dot */}
                  <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />

                  {/* Name + role */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      {shift.isRecommended && <Sparkles size={12} className="text-amber-400 flex-shrink-0" />}
                      <span className="text-[13px] font-semibold truncate" style={{ color }}>
                        {member?.name || 'Unassigned'}
                      </span>
                      {member?.role && (
                        <span className="text-[11px] text-[#A1A1A8]/50 capitalize truncate hidden sm:inline">
                          {member.role.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Time + duration */}
                  <div className="flex-shrink-0 text-right">
                    <div className="text-[12px] font-mono text-[#F5F5F7]/80">
                      {shift.startTime} – {shift.endTime}
                    </div>
                    <div className="text-[10px] font-mono text-[#A1A1A8]/40">
                      {durH.toFixed(1)}h{shift.breakMinutes > 0 ? ` (${shift.breakMinutes}m break)` : ''}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
