import { useMemo } from 'react'
import { Users, AlertTriangle } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { getStaffWeeklyHours, overtimeTone } from './schedule-helpers'

const FULL_WEEK = 40 // hours — overtime reference line

function initials(name: string) {
  const p = name.trim().split(/\s+/)
  return ((p[0]?.[0] ?? '') + (p[1]?.[0] ?? '')).toUpperCase() || '?'
}
function hoursLabel(h: number) {
  return `${h.toFixed(h % 1 === 0 ? 0 : 1)}h`
}

interface Props {
  staff: ScheduleStaffMember[]
  shifts: ScheduleShift[]
}

export default function TeamHoursPanel({ staff, shifts }: Props) {
  const rows = useMemo(() => {
    return staff
      .map(m => ({ member: m, hours: getStaffWeeklyHours(m.id, shifts) }))
      .sort((a, b) => b.hours - a.hours)
  }, [staff, shifts])

  if (rows.length === 0) return null

  const otCount = rows.filter(r => r.hours >= FULL_WEEK).length
  const unassignedShifts = shifts.filter(s => !s.isRecommended && !s.staffMemberId).length

  return (
    <div className="rounded-2xl bg-[#0E0E10] border border-[#1F1F23] p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Users size={15} className="text-[#1A8FD6]" />
          <span className="text-[13px] font-bold text-[#F5F5F7]">Team this week</span>
        </div>
        {otCount > 0 && (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-[#E06B5E] bg-[#E06B5E]/10 px-2 py-0.5 rounded-full">
            <AlertTriangle size={11} />{otCount} over 40h
          </span>
        )}
      </div>

      <div className="space-y-2.5">
        {rows.map(({ member, hours }) => {
          const tone = overtimeTone(hours)
          const pct = Math.min(100, Math.round((hours / FULL_WEEK) * 100))
          const barColor = tone?.fg ?? member.color
          return (
            <div key={member.id} className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-[11px] font-bold"
                style={{ backgroundColor: `${member.color}22`, color: member.color, border: `1px solid ${member.color}40` }}>
                {initials(member.name)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[13px] font-semibold text-[#F5F5F7] truncate">{member.name}</span>
                  <span className="text-[12px] font-bold tabular-nums shrink-0" style={{ color: tone?.fg ?? '#F5F5F7' }}>
                    {hoursLabel(hours)}
                  </span>
                </div>
                {/* hours bar vs the 40h line */}
                <div className="mt-1 h-1.5 rounded-full bg-[#1F1F23] overflow-hidden">
                  <div className="h-full rounded-full transition-all"
                    style={{ width: `${Math.max(2, pct)}%`, backgroundColor: barColor, opacity: 0.9 }} />
                </div>
              </div>
              {tone && (
                <span className="text-[10px] font-semibold shrink-0 px-1.5 py-0.5 rounded-md"
                  style={{ color: tone.fg, backgroundColor: `${tone.fg}1A` }}>
                  {tone.label === 'over' ? 'OT' : 'near OT'}
                </span>
              )}
            </div>
          )
        })}
      </div>

      {unassignedShifts > 0 && (
        <div className="mt-3 pt-3 border-t border-[#1F1F23]">
          <p className="text-[12px] text-[#A1A1A8]">
            <span className="font-semibold text-[#D4A843]">{unassignedShifts}</span> open shift{unassignedShifts === 1 ? '' : 's'} still need a name.
          </p>
        </div>
      )}
    </div>
  )
}
