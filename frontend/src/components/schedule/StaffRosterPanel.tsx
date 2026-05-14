import { useState } from 'react'
import { Plus, Sparkles, ChevronRight, Pencil, Check } from 'lucide-react'
import type { ScheduleStaffMember, ScheduleShift } from '@/lib/agent-data'

interface Recommendation {
  id: string
  reason: string
  priority: 'critical' | 'recommended' | 'optional'
  dayOfWeek: number
  startTime: string
  endTime: string
}

interface Props {
  staff: ScheduleStaffMember[]
  onAddStaff: () => void
  onUpdateStaff?: (id: string, updates: Partial<ScheduleStaffMember>) => void
  recommendations: Recommendation[]
  onApplyRecommendation: (rec: Recommendation) => void
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const PRIORITY_STYLES = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  recommended: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  optional: 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20',
}

function StaffCard({ member, onUpdateRate }: { member: ScheduleStaffMember; onUpdateRate?: (id: string, cents: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [rateInput, setRateInput] = useState(String(member.hourlyRate / 100))

  const availDays = Object.entries(member.availability)
    .filter(([, v]) => v.available)
    .map(([k]) => k.charAt(0).toUpperCase() + k.slice(1, 3))

  function commitRate() {
    const parsed = parseFloat(rateInput)
    if (!isNaN(parsed) && parsed >= 0 && parsed <= 500) {
      onUpdateRate?.(member.id, Math.round(parsed * 100))
    }
    setEditing(false)
  }

  return (
    <div className="flex items-center gap-2.5 p-2.5 rounded-lg hover:bg-[#1F1F23]/40 transition-colors cursor-default group">
      <div
        className="w-3 h-3 rounded-full flex-shrink-0"
        style={{ backgroundColor: member.color }}
      />
      <div className="flex-1 min-w-0">
        <div className="text-[12px] font-semibold text-[#F5F5F7] truncate">
          {member.name}
        </div>
        <div className="text-[10px] text-[#A1A1A8]/50 capitalize">
          {member.role.replace(/_/g, ' ')}
        </div>
      </div>
      <div className="flex flex-col items-end flex-shrink-0">
        {editing ? (
          <div className="flex items-center gap-0.5">
            <span className="text-[9px] text-[#A1A1A8]/40">$</span>
            <input
              type="number"
              step="0.25"
              min="0"
              max="500"
              value={rateInput}
              onChange={e => setRateInput(e.target.value)}
              onBlur={commitRate}
              onKeyDown={e => { if (e.key === 'Enter') commitRate(); if (e.key === 'Escape') setEditing(false) }}
              autoFocus
              className="w-12 px-1 py-0.5 rounded bg-[#1F1F23] border border-[#1A8FD6]/40 text-[10px] text-[#F5F5F7] font-mono text-right focus:outline-none"
            />
            <button onClick={commitRate} className="p-0.5 text-[#17C5B0] hover:text-[#17C5B0]/80">
              <Check size={10} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => { setRateInput(String(member.hourlyRate / 100)); setEditing(true) }}
            className="flex items-center gap-0.5 text-[9px] text-[#17C5B0]/70 font-mono font-medium hover:text-[#17C5B0] transition-colors group/rate"
            title="Click to edit hourly rate"
          >
            ${(member.hourlyRate / 100).toFixed(0)}/hr
            <Pencil size={8} className="opacity-0 group-hover/rate:opacity-60 transition-opacity" />
          </button>
        )}
        <span className="text-[9px] text-[#A1A1A8]/30 font-mono">
          {availDays.length}d
        </span>
      </div>
    </div>
  )
}

export default function StaffRosterPanel({
  staff,
  onAddStaff,
  onUpdateStaff,
  recommendations,
  onApplyRecommendation,
}: Props) {
  function handleUpdateRate(id: string, cents: number) {
    onUpdateStaff?.(id, { hourlyRate: cents })
  }

  const top3 = recommendations.slice(0, 3)

  return (
    <div className="space-y-4">
      {/* Staff Roster */}
      <div className="card p-3">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-[12px] font-semibold text-[#F5F5F7]">Staff Roster</h3>
          <button
            onClick={onAddStaff}
            className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium text-[#17C5B0] bg-[#17C5B0]/10 hover:bg-[#17C5B0]/15 transition-colors"
          >
            <Plus size={12} />
            Add
          </button>
        </div>
        <div className="space-y-0.5">
          {staff.map((member) => (
            <StaffCard key={member.id} member={member} onUpdateRate={handleUpdateRate} />
          ))}
        </div>
        {staff.length === 0 && (
          <p className="text-[11px] text-[#A1A1A8]/40 text-center py-4">
            No staff members yet
          </p>
        )}
      </div>

      {/* AI Recommendations */}
      {top3.length > 0 && (
        <div className="card p-3">
          <div className="flex items-center gap-1.5 mb-3">
            <Sparkles size={14} className="text-amber-400" />
            <h3 className="text-[12px] font-semibold text-[#F5F5F7]">AI Suggestions</h3>
          </div>
          <div className="space-y-2">
            {top3.map((rec) => (
              <div
                key={rec.id}
                className={`rounded-lg border p-2.5 ${PRIORITY_STYLES[rec.priority]}`}
              >
                <div className="flex items-center gap-1.5 mb-1">
                  <span className="text-[9px] font-bold uppercase tracking-wider">
                    {rec.priority}
                  </span>
                  <span className="text-[9px] opacity-60 font-mono">
                    {DAY_NAMES[rec.dayOfWeek]} {rec.startTime}–{rec.endTime}
                  </span>
                </div>
                <p className="text-[10px] leading-relaxed opacity-80 mb-2">
                  {rec.reason}
                </p>
                <button
                  onClick={() => onApplyRecommendation(rec)}
                  className="flex items-center gap-1 text-[10px] font-medium opacity-80 hover:opacity-100 transition-opacity"
                >
                  Add to Schedule
                  <ChevronRight size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
