import { useState, useEffect, useMemo } from 'react'
import { X, Trash2, Scissors, DollarSign, Clock } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { ROLE_GROUPS, timeToMinutes, fmtTime } from './schedule-helpers'

interface Props {
  shift: ScheduleShift | null
  staff: ScheduleStaffMember[]
  onClose: () => void
  onSave: (updated: ScheduleShift) => void
  onDelete: (shiftId: string) => void
  onSplitShift?: (original: ScheduleShift, firstEnd: string, secondStart: string) => void
}

const ALL_ROLES = ROLE_GROUPS.flatMap(g => g.roles.map(r => ({ role: r, group: g.label })))
const DAY_NAMES = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

// iOS Safari zooms the viewport when focusing an input whose font-size < 16px.
// Every field here is text-base (16px) so the sheet never jumps on focus.
const FIELD =
  'w-full px-3.5 py-3 rounded-xl bg-[#1F1F23] border border-[#1F1F23] text-base text-[#F5F5F7] ' +
  'focus:border-[#1A8FD6]/50 focus:ring-2 focus:ring-[#1A8FD6]/15 focus:outline-none transition-colors'
const FIELD_LABEL = 'text-[11px] font-semibold uppercase tracking-wide text-[#A1A1A8]/60 block mb-1.5'

export default function ShiftEditPopover({ shift, staff, onClose, onSave, onDelete, onSplitShift }: Props) {
  const [staffMemberId, setStaffMemberId] = useState('')
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('17:00')
  const [breakMinutes, setBreakMinutes] = useState('0')
  const [notes, setNotes] = useState('')
  const [role, setRole] = useState('')

  useEffect(() => {
    if (shift) {
      setStaffMemberId(shift.staffMemberId || '')
      setStartTime(shift.startTime)
      setEndTime(shift.endTime)
      setBreakMinutes(String(shift.breakMinutes))
      setNotes(shift.notes)
      setRole(shift.role)
    }
  }, [shift])

  // Close on Escape; lock background scroll while the sheet is open.
  useEffect(() => {
    if (!shift) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
    }
  }, [shift, onClose])

  const selectedMember = useMemo(
    () => staff.find(s => s.id === staffMemberId),
    [staff, staffMemberId],
  )

  // Shift duration (net of break) + cost.
  const durMins = useMemo(
    () => timeToMinutes(endTime) - timeToMinutes(startTime) - (parseInt(breakMinutes) || 0),
    [startTime, endTime, breakMinutes],
  )
  const shiftCost = useMemo(() => {
    if (!selectedMember || durMins <= 0) return null
    return Math.round(selectedMember.hourlyRate * (durMins / 60))
  }, [selectedMember, durMins])

  if (!shift) return null

  function handleStaffChange(id: string) {
    setStaffMemberId(id)
    const member = staff.find(s => s.id === id)
    if (member) setRole(member.role)
  }

  const currentShift = shift

  function handleSave() {
    onSave({
      ...currentShift,
      staffMemberId: staffMemberId || null,
      startTime,
      endTime,
      breakMinutes: parseInt(breakMinutes) || 0,
      notes,
      role: role || currentShift.role,
    })
    onClose()
  }

  function handleDelete() {
    onDelete(currentShift.id)
    onClose()
  }

  function handleSplit() {
    if (!onSplitShift) return
    // Split at the midpoint with a gap
    const startMins = timeToMinutes(startTime)
    const endMins = timeToMinutes(endTime)
    const mid = Math.floor((startMins + endMins) / 2)
    const firstEnd = `${String(Math.floor(mid / 60)).padStart(2, '0')}:${String(mid % 60).padStart(2, '0')}`
    const secondStart = `${String(Math.floor((mid + 60) / 60)).padStart(2, '0')}:${String((mid + 60) % 60).padStart(2, '0')}`
    onSplitShift(currentShift, firstEnd, secondStart)
    onClose()
  }

  const canSplit = (timeToMinutes(endTime) - timeToMinutes(startTime)) >= 240 // at least 4 hours
  const durLabel = durMins > 0 ? `${(durMins / 60).toFixed(durMins % 60 === 0 ? 0 : 1)}h` : '—'

  return (
    <div className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center sm:p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose} />

      <div
        role="dialog"
        aria-modal="true"
        aria-label="Edit shift"
        className="relative w-full sm:max-w-md bg-[#0A0A0B] border-t sm:border border-[#1F1F23]
                   rounded-t-3xl sm:rounded-2xl shadow-2xl flex flex-col max-h-[92vh]
                   animate-in slide-in-from-bottom sm:zoom-in-95 sm:fade-in duration-300"
      >
        {/* Mobile grab handle */}
        <div className="sm:hidden flex justify-center pt-2.5 pb-1">
          <div className="w-10 h-1.5 rounded-full bg-[#2A2A30]" />
        </div>

        {/* Header — shows which day + the live duration for context */}
        <div className="flex items-center gap-2 px-5 pt-2 pb-3 sm:py-4 border-b border-[#1F1F23]">
          <div className="min-w-0 flex-1">
            <h3 className="text-base font-bold text-[#F5F5F7]">Edit shift</h3>
            <p className="text-[12px] text-[#A1A1A8]/70 mt-0.5 truncate">
              {DAY_NAMES[currentShift.dayOfWeek] ?? 'Shift'} · {fmtTime(startTime)}–{fmtTime(endTime)}
            </p>
          </div>
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 shrink-0">
            <Clock size={12} className="text-[#1A8FD6]" />
            <span className="text-[12px] font-semibold text-[#1A8FD6]">{durLabel}</span>
          </div>
          <button aria-label="Close shift editor" onClick={onClose}
            className="p-2 -mr-1 rounded-xl hover:bg-[#1F1F23] text-[#A1A1A8] active:scale-95 transition-all shrink-0">
            <X size={18} />
          </button>
        </div>

        {/* Body (scrolls if it gets tall) */}
        <div className="px-5 py-4 space-y-4 overflow-y-auto">
          {/* Staff member */}
          <div>
            <label className={FIELD_LABEL}>Staff member</label>
            <select value={staffMemberId} onChange={(e) => handleStaffChange(e.target.value)} className={FIELD}>
              <option value="">Unassigned</option>
              {staff.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.role.replace(/_/g, ' ')})</option>
              ))}
            </select>
          </div>

          {/* Role */}
          <div>
            <label className={FIELD_LABEL}>Role</label>
            <select value={role} onChange={(e) => setRole(e.target.value)} className={`${FIELD} capitalize`}>
              <option value="">Select role…</option>
              {ALL_ROLES.map(({ role: r, group }) => (
                <option key={r} value={r}>{r.replace(/_/g, ' ')} ({group})</option>
              ))}
            </select>
          </div>

          {/* Time */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className={FIELD_LABEL}>Start</label>
              <input type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} className={FIELD} />
            </div>
            <div>
              <label className={FIELD_LABEL}>End</label>
              <input type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} className={FIELD} />
            </div>
          </div>

          {/* Break */}
          <div>
            <label className={FIELD_LABEL}>Break (minutes)</label>
            <input type="number" min="0" step="5" inputMode="numeric"
              value={breakMinutes} onChange={(e) => setBreakMinutes(e.target.value)} className={FIELD} />
          </div>

          {/* Shift cost */}
          {shiftCost !== null && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-xl bg-[#17C5B0]/[0.07] border border-[#17C5B0]/20">
              <div className="w-9 h-9 rounded-full bg-[#17C5B0]/15 flex items-center justify-center shrink-0">
                <DollarSign size={16} className="text-[#17C5B0]" />
              </div>
              <div className="flex-1">
                <span className="text-[11px] text-[#A1A1A8]/60">Shift cost</span>
                <div className="text-[15px] font-bold text-[#17C5B0]">${(shiftCost / 100).toFixed(2)}</div>
              </div>
              <span className="text-[11px] text-[#A1A1A8]/40">
                {durLabel} · ${(selectedMember!.hourlyRate / 100).toFixed(0)}/hr
              </span>
            </div>
          )}

          {/* Notes */}
          <div>
            <label className={FIELD_LABEL}>Notes</label>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2}
              className={`${FIELD} resize-none`} placeholder="Optional notes…" />
          </div>
        </div>

        {/* Footer — sticky, thumb-sized, safe-area aware */}
        <div className="border-t border-[#1F1F23] px-5 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:pb-4 space-y-3">
          {/* Destructive / split row */}
          <div className="flex items-center gap-2">
            <button onClick={handleDelete}
              className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-[13px] font-semibold
                         text-red-400 bg-red-500/[0.06] hover:bg-red-500/10 active:scale-[0.98] transition-all">
              <Trash2 size={14} />Delete
            </button>
            {canSplit && onSplitShift && (
              <button onClick={handleSplit} title="Split into two shifts with a break"
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-[13px] font-semibold
                           text-[#9B7FD4] bg-[#9B7FD4]/[0.06] hover:bg-[#9B7FD4]/10 active:scale-[0.98] transition-all">
                <Scissors size={14} />Split
              </button>
            )}
          </div>
          {/* Primary row */}
          <div className="flex items-center gap-2">
            <button onClick={onClose}
              className="px-5 py-3 rounded-xl text-sm font-semibold text-[#A1A1A8] hover:text-[#F5F5F7]
                         hover:bg-[#1F1F23] active:scale-[0.98] transition-all">
              Cancel
            </button>
            <button onClick={handleSave}
              className="flex-1 py-3 rounded-xl text-sm font-bold text-white active:scale-[0.98] transition-all
                         bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] shadow-lg shadow-[#1A8FD6]/20 hover:brightness-110">
              Save shift
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
