import { useState, useEffect } from 'react'
import { X, Trash2 } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'

interface Props {
  shift: ScheduleShift | null
  staff: ScheduleStaffMember[]
  onClose: () => void
  onSave: (updated: ScheduleShift) => void
  onDelete: (shiftId: string) => void
}

export default function ShiftEditPopover({ shift, staff, onClose, onSave, onDelete }: Props) {
  const [staffMemberId, setStaffMemberId] = useState('')
  const [startTime, setStartTime] = useState('09:00')
  const [endTime, setEndTime] = useState('17:00')
  const [breakMinutes, setBreakMinutes] = useState('0')
  const [notes, setNotes] = useState('')
  const [role, setRole] = useState('')

  // Sync state when shift changes
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

  if (!shift) return null

  // Auto-fill role when staff member changes
  function handleStaffChange(id: string) {
    setStaffMemberId(id)
    const member = staff.find(s => s.id === id)
    if (member) setRole(member.role)
  }

  const currentShift = shift  // Narrow for closures

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#1F1F23]">
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Edit Shift</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8]">
            <X size={16} />
          </button>
        </div>

        {/* Body */}
        <div className="px-4 py-3 space-y-3">
          {/* Staff member */}
          <div>
            <label className="text-[10px] font-medium text-[#A1A1A8]/60 block mb-1">Staff Member</label>
            <select
              value={staffMemberId}
              onChange={(e) => handleStaffChange(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none"
            >
              <option value="">Unassigned</option>
              {staff.map(s => (
                <option key={s.id} value={s.id}>{s.name} ({s.role.replace(/_/g, ' ')})</option>
              ))}
            </select>
          </div>

          {/* Role */}
          <div>
            <label className="text-[10px] font-medium text-[#A1A1A8]/60 block mb-1">Role</label>
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none"
              placeholder="Role"
            />
          </div>

          {/* Time */}
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] font-medium text-[#A1A1A8]/60 block mb-1">Start</label>
              <input
                type="time"
                value={startTime}
                onChange={(e) => setStartTime(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-[10px] font-medium text-[#A1A1A8]/60 block mb-1">End</label>
              <input
                type="time"
                value={endTime}
                onChange={(e) => setEndTime(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none"
              />
            </div>
          </div>

          {/* Break */}
          <div>
            <label className="text-[10px] font-medium text-[#A1A1A8]/60 block mb-1">Break (minutes)</label>
            <input
              type="number"
              min="0"
              step="5"
              value={breakMinutes}
              onChange={(e) => setBreakMinutes(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="text-[10px] font-medium text-[#A1A1A8]/60 block mb-1">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="w-full px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] focus:border-[#1A8FD6]/40 focus:outline-none resize-none"
              placeholder="Optional notes..."
            />
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#1F1F23]">
          <button
            onClick={handleDelete}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[11px] font-medium text-red-400 hover:bg-red-500/10 transition-colors"
          >
            <Trash2 size={12} />
            Delete
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-[11px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg text-[11px] font-medium bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 transition-all"
            >
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
