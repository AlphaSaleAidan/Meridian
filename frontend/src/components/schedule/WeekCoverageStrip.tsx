import { useMemo } from 'react'
import { ShieldCheck, AlertTriangle } from 'lucide-react'
import type { ScheduleShift } from '@/lib/agent-data'
import { computeDayCoverage, coverageTone, fmtTime, addDays, type DayCoverage } from './schedule-helpers'

const DAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S']
const DAY_FULL = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

interface Props {
  weekStartDate: Date
  shifts: ScheduleShift[]
  peaks: { day: number; hour: number; intensity: number }[]
  selectedDay?: number
  onSelectDay?: (day: number) => void
}

export default function WeekCoverageStrip({ weekStartDate, shifts, peaks, selectedDay, onSelectDay }: Props) {
  const coverage = useMemo<DayCoverage[]>(
    () => Array.from({ length: 7 }, (_, d) => computeDayCoverage(d, shifts, peaks)),
    [shifts, peaks],
  )

  // Headline insight: how many busy days are fully covered + the weakest day.
  const { coveredCount, demandDays, worst } = useMemo(() => {
    const withDemand = coverage.filter(c => c.demandHours > 0)
    const covered = withDemand.filter(c => c.score >= 0.9).length
    const worstDay = withDemand
      .filter(c => c.score < 0.9)
      .sort((a, b) => a.score - b.score)[0] ?? null
    return { coveredCount: covered, demandDays: withDemand.length, worst: worstDay }
  }, [coverage])

  const allCovered = demandDays > 0 && coveredCount === demandDays
  const hasData = coverage.some(c => c.demandHours > 0 || c.scheduledStaff > 0)
  if (!hasData) return null

  return (
    <div className="rounded-2xl bg-[#0E0E10] border border-[#1F1F23] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-[13px] font-bold text-[#F5F5F7]">Week at a glance</span>
          {demandDays > 0 && (
            <span className="text-[11px] text-[#A1A1A8]/60">{coveredCount}/{demandDays} busy days covered</span>
          )}
        </div>
      </div>

      {/* Coverage bars — one per day */}
      <div className="flex items-end gap-1.5 sm:gap-2 h-20">
        {coverage.map(c => {
          const tone = coverageTone(c)
          const d = addDays(weekStartDate, c.day)
          const isSel = selectedDay === c.day
          // bar height: scale score; give empty days a faint stub.
          const pct = c.demandHours === 0 && c.scheduledStaff === 0 ? 6 : Math.max(14, Math.round(c.score * 100))
          return (
            <button
              key={c.day}
              onClick={() => onSelectDay?.(c.day)}
              aria-label={`${DAY_FULL[c.day]} ${d.getDate()} — ${tone.label}`}
              className={`group flex-1 flex flex-col items-center justify-end h-full gap-1.5 rounded-lg transition-all
                ${onSelectDay ? 'cursor-pointer active:scale-95' : 'cursor-default'}
                ${isSel ? 'bg-[#17C5B0]/[0.06]' : 'hover:bg-[#1F1F23]/40'}`}
            >
              <div className="w-full flex-1 flex items-end justify-center px-1">
                <div
                  className="w-full max-w-[26px] rounded-md transition-all"
                  style={{
                    height: `${pct}%`,
                    backgroundColor: tone.fg,
                    opacity: tone.label === 'empty' ? 0.5 : (isSel ? 1 : 0.85),
                    boxShadow: isSel ? `0 0 14px -2px ${tone.fg}` : 'none',
                  }}
                />
              </div>
              <span className={`text-[11px] font-bold leading-none ${isSel ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/55'}`}>{DAYS[c.day]}</span>
              <span className={`text-[10px] leading-none ${isSel ? 'text-[#A1A1A8]' : 'text-[#A1A1A8]/35'}`}>{d.getDate()}</span>
            </button>
          )
        })}
      </div>

      {/* Plain-language insight */}
      <div className="mt-3 pt-3 border-t border-[#1F1F23] flex items-start gap-2">
        {allCovered ? (
          <>
            <ShieldCheck size={15} className="text-[#17C5B0] shrink-0 mt-0.5" />
            <p className="text-[12px] text-[#A1A1A8]">Every busy hour is covered this week. Nice work.</p>
          </>
        ) : worst ? (
          <>
            <AlertTriangle size={15} className="text-[#D4A843] shrink-0 mt-0.5" />
            <p className="text-[12px] text-[#A1A1A8]">
              <span className="font-semibold text-[#F5F5F7]">{DAY_FULL[worst.day]}</span> is light
              {worst.worstGap ? (
                <> around <span className="font-semibold text-[#F5F5F7]">{fmtTime(`${worst.worstGap.hour}:00`)}</span> — add {worst.worstGap.need - worst.worstGap.have} more.</>
              ) : ' on its busiest hours.'}
            </p>
          </>
        ) : (
          <>
            <ShieldCheck size={15} className="text-[#A1A1A8]/50 shrink-0 mt-0.5" />
            <p className="text-[12px] text-[#A1A1A8]/70">Add shifts to see coverage against your busy hours.</p>
          </>
        )}
      </div>
    </div>
  )
}
