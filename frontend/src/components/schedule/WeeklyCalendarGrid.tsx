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
  if (hour === 0) return '12a'
  if (hour < 12) return `${hour}a`
  if (hour === 12) return '12p'
  return `${hour - 12}p`
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

  return (
    <div className="card overflow-hidden">
      <div className="overflow-x-auto">
        <div className="min-w-[700px]">
          {/* Day headers */}
          <div className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-[#1F1F23]">
            <div className="p-2 text-[10px] text-[#A1A1A8]/40 font-mono" />
            {DAY_NAMES.map((day, di) => {
              const date = addDays(weekStartDate, di)
              const dateStr = `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`
              const holiday = holidayByDate.get(dateStr)
              const isWeekend = di >= 5

              return (
                <div
                  key={day}
                  className={`p-2 text-center border-l border-[#1F1F23] ${isWeekend ? 'bg-[#1F1F23]/30' : ''}`}
                >
                  <div className="text-[11px] font-semibold text-[#F5F5F7]">{day}</div>
                  <div className="text-[10px] text-[#A1A1A8]/50 font-mono">{formatDateShort(date)}</div>
                  {holiday && (
                    <div className="mt-1 px-1.5 py-0.5 rounded text-[8px] font-medium bg-amber-500/10 text-amber-400 truncate">
                      {holiday.name}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Hour rows */}
          <div className="relative">
            {hourRange.map((hour) => (
              <div
                key={hour}
                className="grid grid-cols-[60px_repeat(7,1fr)] border-b border-[#1F1F23]/50"
                style={{ height: rowHeightPx }}
              >
                {/* Hour label */}
                <div className="flex items-start justify-end pr-2 pt-1">
                  <span className="text-[10px] text-[#A1A1A8]/40 font-mono">
                    {formatHourLabel(hour)}
                  </span>
                </div>

                {/* Day cells */}
                {DAY_NAMES.map((_, di) => {
                  const intensity = peakLookup.get(`${di}-${hour}`) || 0

                  let bgColor = 'transparent'
                  if (intensity > 0.75) bgColor = 'rgba(23, 197, 176, 0.06)'
                  else if (intensity > 0.5) bgColor = 'rgba(23, 197, 176, 0.04)'
                  else if (intensity > 0.25) bgColor = 'rgba(26, 143, 214, 0.03)'

                  return (
                    <div
                      key={di}
                      className="border-l border-[#1F1F23]/50 cursor-pointer hover:bg-[#1F1F23]/20 transition-colors relative"
                      style={{ backgroundColor: bgColor }}
                      onClick={() => onSlotClick(di, hour)}
                    />
                  )
                })}
              </div>
            ))}

            {/* Shift blocks overlay */}
            {shifts.map((shift) => {
              const startMins = timeToMinutes(shift.startTime)
              const endMins = timeToMinutes(shift.endTime)
              const gridStartMins = hours.open * 60
              const totalMins = totalHours * 60

              const topPct = ((startMins - gridStartMins) / totalMins) * 100
              const heightPct = ((endMins - startMins) / totalMins) * 100

              if (topPct < 0 || topPct >= 100) return null

              const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
              const color = member?.color || '#A1A1A8'
              const colStart = shift.dayOfWeek + 2  // +2 because col 1 is the hour label

              const durationHrs = ((endMins - startMins) / 60).toFixed(1)

              return (
                <div
                  key={shift.id}
                  className="absolute cursor-pointer transition-all hover:scale-[1.02] hover:z-20 z-10"
                  style={{
                    top: `${topPct}%`,
                    height: `${Math.max(heightPct, 2)}%`,
                    left: `calc(${((colStart - 2) / 7) * 100}% + 60px + ${((colStart - 2) * 0.5)}px + 2px)`,
                    width: `calc(${100 / 7}% - 6px)`,
                  }}
                  onClick={(e) => {
                    e.stopPropagation()
                    onShiftClick(shift)
                  }}
                >
                  <div
                    className={`h-full rounded-md px-1.5 py-1 overflow-hidden ${shift.isRecommended ? 'border border-dashed' : 'border'}`}
                    style={{
                      backgroundColor: `${color}15`,
                      borderColor: `${color}40`,
                    }}
                  >
                    <div className="flex items-center gap-1">
                      {shift.isRecommended && (
                        <Sparkles size={10} className="text-amber-400 flex-shrink-0" />
                      )}
                      <span
                        className="text-[10px] font-semibold truncate"
                        style={{ color }}
                      >
                        {member?.name || 'Unassigned'}
                      </span>
                    </div>
                    {heightPct > 6 && (
                      <div className="text-[9px] text-[#A1A1A8]/60 font-mono mt-0.5">
                        {shift.startTime}–{shift.endTime} ({durationHrs}h)
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
