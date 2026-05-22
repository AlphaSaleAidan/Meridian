import { useMemo } from 'react'
import { Sparkles } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember, PeakHourCell, Holiday } from '@/lib/agent-data'
import type { BusinessType } from '@/lib/demo-context'

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const BIZ_HOURS: Record<string, { open: number; close: number }> = {
  coffee_shop: { open: 5, close: 21 },
  restaurant: { open: 10, close: 23 },
  fast_food: { open: 5, close: 23 },
  auto_shop: { open: 7, close: 19 },
  smoke_shop: { open: 10, close: 22 },
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

function timeToMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + (m || 0)
}

function formatHourLabel(hour: number): string {
  if (hour === 0) return '12 AM'
  if (hour < 12) return `${hour} AM`
  if (hour === 12) return '12 PM'
  return `${hour - 12} PM`
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function formatDateShort(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  peakHours: PeakHourCell[]
  holidays: Holiday[]
  onShiftClick: (shift: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
  weekStartDate: Date
  businessType: BusinessType
}

export default function WeeklyCalendarGrid({
  shifts,
  staff,
  peakHours,
  holidays,
  onShiftClick,
  onSlotClick,
  weekStartDate,
  businessType,
}: Props) {
  const hours = BIZ_HOURS[businessType] || BIZ_HOURS.coffee_shop
  const hourRange = useMemo(() => {
    const arr: number[] = []
    for (let h = hours.open; h < hours.close; h++) arr.push(h)
    return arr
  }, [hours.open, hours.close])

  const totalHours = hourRange.length
  const rowHeightPx = 48

  const staffMap = useMemo(() => {
    const map = new Map<string, ScheduleStaffMember>()
    staff.forEach(s => map.set(s.id, s))
    return map
  }, [staff])

  // Build peak intensity lookup
  const peakLookup = useMemo(() => {
    const map = new Map<string, number>()
    const maxIntensity = Math.max(...peakHours.map(c => c.intensity), 1)
    peakHours.forEach(c => {
      map.set(`${c.day}-${c.hour}`, c.intensity / maxIntensity)
    })
    return map
  }, [peakHours])

  // Holiday dates lookup
  const holidayByDate = useMemo(() => {
    const map = new Map<string, Holiday>()
    holidays.forEach(h => map.set(h.date, h))
    return map
  }, [holidays])

  const today = new Date()
  const todayStr = `${today.getFullYear()}-${pad2(today.getMonth() + 1)}-${pad2(today.getDate())}`
  const nowHour = today.getHours()
  const nowMinute = today.getMinutes()

  return (
    <div className="card overflow-hidden border-[#1F1F23] rounded-xl">
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          {/* Day headers */}
          <div className="grid grid-cols-[56px_repeat(7,1fr)] bg-[#111113] border-b border-[#1F1F23]">
            <div className="p-2" />
            {DAY_NAMES.map((day, di) => {
              const date = addDays(weekStartDate, di)
              const dateStr = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
              const holiday = holidayByDate.get(dateStr)
              const isWeekend = di >= 5
              const isToday = dateStr === todayStr

              return (
                <div
                  key={day}
                  className={`px-2 py-3 text-center border-l border-[#1F1F23] ${isWeekend ? 'bg-[#0A0A0B]/60' : ''} ${isToday ? 'bg-[#1A8FD6]/[0.04]' : ''}`}
                >
                  <div className={`text-[11px] font-bold uppercase tracking-wide ${isToday ? 'text-[#1A8FD6]' : 'text-[#F5F5F7]/80'}`}>{day}</div>
                  <div className={`text-[11px] mt-0.5 ${isToday ? 'text-[#1A8FD6]/80 font-semibold' : 'text-[#A1A1A8]/50'}`}>{formatDateShort(date)}</div>
                  {holiday && (
                    <div className="mt-1.5 px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-500/10 text-amber-400 truncate">
                      {holiday.name}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Hour rows */}
          <div className="relative">
            {hourRange.map((hour, hi) => {
              const isEvenHour = hour % 2 === 0
              return (
                <div
                  key={hour}
                  className={`grid grid-cols-[56px_repeat(7,1fr)] border-b ${isEvenHour ? 'border-[#1F1F23]/70' : 'border-[#1F1F23]/30'}`}
                  style={{ height: rowHeightPx }}
                >
                  {/* Hour label */}
                  <div className="flex items-start justify-end pr-2 pt-1">
                    <span className={`text-[10px] font-mono ${isEvenHour ? 'text-[#A1A1A8]/60 font-medium' : 'text-[#A1A1A8]/30'}`}>
                      {formatHourLabel(hour)}
                    </span>
                  </div>

                  {/* Day cells */}
                  {DAY_NAMES.map((_, di) => {
                    const date = addDays(weekStartDate, di)
                    const dateStr = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
                    const isToday = dateStr === todayStr
                    const isWeekend = di >= 5
                    const intensity = peakLookup.get(`${di}-${hour}`) || 0

                    let bgColor = 'transparent'
                    if (intensity > 0.75) bgColor = 'rgba(23, 197, 176, 0.06)'
                    else if (intensity > 0.5) bgColor = 'rgba(23, 197, 176, 0.04)'
                    else if (intensity > 0.25) bgColor = 'rgba(26, 143, 214, 0.03)'

                    if (isWeekend && bgColor === 'transparent') bgColor = 'rgba(10,10,11,0.3)'

                    return (
                      <div
                        key={di}
                        className={`border-l border-[#1F1F23]/40 cursor-pointer hover:bg-[#1A8FD6]/[0.06] transition-colors relative ${isToday ? 'bg-[#1A8FD6]/[0.02]' : ''}`}
                        style={{ backgroundColor: isToday && bgColor === 'transparent' ? undefined : bgColor }}
                        onClick={() => onSlotClick(di, hour)}
                      />
                    )
                  })}
                </div>
              )
            })}

            {/* Current time indicator */}
            {(() => {
              const todayIndex = (() => {
                for (let di = 0; di < 7; di++) {
                  const date = addDays(weekStartDate, di)
                  const dateStr = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
                  if (dateStr === todayStr) return di
                }
                return -1
              })()
              if (todayIndex < 0) return null
              if (nowHour < hours.open || nowHour >= hours.close) return null

              const gridStartMins = hours.open * 60
              const totalMins = totalHours * 60
              const currentMins = nowHour * 60 + nowMinute
              const topPct = ((currentMins - gridStartMins) / totalMins) * 100

              return (
                <div
                  className="absolute pointer-events-none z-30"
                  style={{
                    top: `${topPct}%`,
                    left: `calc(56px + (100% - 56px) * ${todayIndex} / 7)`,
                    width: `calc((100% - 56px) / 7)`,
                  }}
                >
                  <div className="relative">
                    <div className="absolute -left-[4px] -top-[4px] w-2 h-2 rounded-full bg-[#EF4444]" />
                    <div className="h-[2px] bg-[#EF4444]/80 w-full" />
                  </div>
                </div>
              )
            })()}

            {/* Shift blocks overlay — stacked horizontally when overlapping */}
            {(() => {
              const grouped = new Map<string, typeof shifts>()
              shifts.forEach(s => {
                const key = `${s.dayOfWeek}-${s.startTime}`
                if (!grouped.has(key)) grouped.set(key, [])
                grouped.get(key)!.push(s)
              })

              return shifts.map((shift) => {
                const startMins = timeToMinutes(shift.startTime)
                const endMins = timeToMinutes(shift.endTime)
                const gridStartMins = hours.open * 60
                const totalMins = totalHours * 60

                const topPct = ((startMins - gridStartMins) / totalMins) * 100
                const heightPct = ((endMins - startMins) / totalMins) * 100

                if (topPct < 0 || topPct >= 100) return null

                const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
                const color = member?.color || '#A1A1A8'
                const day = shift.dayOfWeek

                const groupKey = `${day}-${shift.startTime}`
                const group = grouped.get(groupKey) || [shift]
                const idx = group.indexOf(shift)
                const count = group.length

                const leftCalc = count > 1
                  ? `calc(56px + (100% - 56px) * ${day} / 7 + 3px + (100% - 56px) / 7 * ${idx} / ${count})`
                  : `calc(56px + (100% - 56px) * ${day / 7} + 3px)`
                const widthCalc = count > 1
                  ? `calc((100% - 56px) / 7 / ${count} - 3px)`
                  : `calc((100% - 56px) / 7 - 6px)`

                const durationHrs = ((endMins - startMins) / 60).toFixed(1)

                return (
                  <div
                    key={shift.id}
                    className="absolute cursor-pointer transition-all hover:brightness-110 hover:z-20 z-10 group/shift"
                    style={{
                      top: `${topPct}%`,
                      height: `${Math.max(heightPct, 2.5)}%`,
                      left: leftCalc,
                      width: widthCalc,
                    }}
                    onClick={(e) => {
                      e.stopPropagation()
                      onShiftClick(shift)
                    }}
                  >
                    <div
                      className={`h-full rounded-md px-2 py-1 overflow-hidden shadow-sm group-hover/shift:shadow-md transition-shadow ${shift.isRecommended ? 'border border-dashed' : 'border'}`}
                      style={{
                        backgroundColor: `${color}18`,
                        borderColor: `${color}50`,
                      }}
                    >
                      <div className="flex items-center gap-1">
                        {shift.isRecommended && (
                          <Sparkles size={10} className="text-amber-400 flex-shrink-0" />
                        )}
                        <span
                          className="text-[11px] font-semibold truncate leading-tight"
                          style={{ color }}
                        >
                          {member?.name || 'Unassigned'}
                        </span>
                      </div>
                      {heightPct > 5 && (
                        <div className="text-[9px] text-[#A1A1A8]/70 font-mono mt-0.5 leading-tight">
                          {shift.startTime}–{shift.endTime} ({durationHrs}h)
                        </div>
                      )}
                      {heightPct > 10 && member?.role && (
                        <div className="text-[8px] text-[#A1A1A8]/40 mt-0.5 capitalize truncate">
                          {member.role.replace(/_/g, ' ')}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })
            })()}
          </div>
        </div>
      </div>
    </div>
  )
}
