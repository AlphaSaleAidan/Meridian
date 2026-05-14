import { Plus, Sparkles, ChevronRight } from 'lucide-react'
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
  recommendations: Recommendation[]
  onApplyRecommendation: (rec: Recommendation) => void
}

const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

const PRIORITY_STYLES = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  recommended: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  optional: 'bg-[#1A8FD6]/10 text-[#1A8FD6] border-[#1A8FD6]/20',
}

function StaffCard({ member }: { member: ScheduleStaffMember }) {
  const availDays = Object.entries(member.availability)
    .filter(([, v]) => v.available)
    .map(([k]) => k.charAt(0).toUpperCase() + k.slice(1, 3))

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
      <div className="text-[9px] text-[#A1A1A8]/30 font-mono flex-shrink-0">
        {availDays.length}d
      </div>
    </div>
  )
}

export default function StaffRosterPanel({
  staff,
  onAddStaff,
  recommendations,
  onApplyRecommendation,
}: Props) {
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
            <StaffCard key={member.id} member={member} />
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
