import { useState } from 'react'
import { X, Plus, Pencil, Trash2, Check, Briefcase } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { getRoleColor } from './schedule-helpers'

/**
 * Manage positions — a compact micro-wizard for the schedule's role list.
 *
 * Positions are plain role strings that live on staff + shift rows, so this
 * modal edits the list (add / rename / remove) and the parent applies renames
 * to the affected rows via the existing staff/shift update endpoints.
 */

const fmtRole = (r: string) => r.replace(/_/g, ' ')
const normalizeRole = (s: string) => s.trim().toLowerCase().replace(/\s+/g, '_')

interface Props {
  open: boolean
  onClose: () => void
  positions: string[]
  staff: ScheduleStaffMember[]
  shifts: ScheduleShift[]
  onAdd: (role: string) => void
  onRename: (oldRole: string, newRole: string) => void
  onDelete: (role: string) => void
}

export default function ManagePositionsModal({
  open, onClose, positions, staff, shifts, onAdd, onRename, onDelete,
}: Props) {
  const [editing, setEditing] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  const [newValue, setNewValue] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)

  if (!open) return null

  const usage = (role: string) => ({
    staff: staff.filter(s => s.role === role).length,
    shifts: shifts.filter(s => s.role === role && !s.isRecommended).length,
  })

  const commitRename = (oldRole: string) => {
    const next = normalizeRole(editValue)
    setEditing(null)
    if (!next || next === oldRole) return
    if (positions.includes(next)) return // already exists — no-op
    onRename(oldRole, next)
  }

  const commitAdd = () => {
    const next = normalizeRole(newValue)
    if (!next || positions.includes(next)) return
    onAdd(next)
    setNewValue('')
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-md bg-[#0A0A0B] border border-[#1F1F23] rounded-xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23]">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
              <Briefcase size={14} className="text-[#1A8FD6]" />
            </div>
            <h2 className="text-sm font-semibold text-[#F5F5F7]">Manage positions</h2>
          </div>
          <button aria-label="Close" onClick={onClose} className="p-1 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8]">
            <X size={16} />
          </button>
        </div>

        {/* Step 1 — what positions do */}
        <div className="px-5 pt-4">
          <p className="text-[12px] text-[#A1A1A8] leading-relaxed">
            <span className="text-[#F5F5F7] font-medium">Positions</span> are the roles you
            schedule — every staff member and shift has one, and Auto-fill staffs each
            position from your sales history. Rename them to match how your team talks,
            add ones you're missing, or remove ones you don't use.
          </p>
          <p className="text-[10px] text-[#A1A1A8]/50 mt-1.5">
            Renaming updates every staff member and shift that has the position.
          </p>
        </div>

        {/* Step 2 — editable list */}
        <div className="px-5 py-4 space-y-1.5 max-h-[45vh] overflow-y-auto">
          {positions.map(role => {
            const u = usage(role)
            const inUse = u.staff > 0 || u.shifts > 0
            const isEditing = editing === role
            return (
              <div key={role} className="flex items-center gap-2 px-2.5 py-2 rounded-lg bg-[#111113] border border-[#1F1F23]">
                <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: getRoleColor(role) }} />
                {isEditing ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={e => setEditValue(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') commitRename(role)
                      if (e.key === 'Escape') setEditing(null)
                    }}
                    className="flex-1 min-w-0 px-2 py-1 rounded bg-[#1F1F23] border border-[#1A8FD6]/40 text-[13px] text-[#F5F5F7] capitalize focus:outline-none"
                  />
                ) : (
                  <span className="flex-1 min-w-0 text-[13px] font-medium text-[#F5F5F7] capitalize truncate">{fmtRole(role)}</span>
                )}
                {!isEditing && inUse && (
                  <span className="text-[10px] text-[#A1A1A8]/45 flex-shrink-0 tabular-nums">
                    {u.staff > 0 && `${u.staff} staff`}{u.staff > 0 && u.shifts > 0 && ' · '}{u.shifts > 0 && `${u.shifts} shifts`}
                  </span>
                )}
                {isEditing ? (
                  <button onClick={() => commitRename(role)} aria-label="Save name"
                    className="p-1.5 rounded-lg text-[#17C5B0] hover:bg-[#17C5B0]/10 transition-colors flex-shrink-0">
                    <Check size={14} />
                  </button>
                ) : (
                  <>
                    <button
                      onClick={() => { setEditing(role); setEditValue(fmtRole(role)); setConfirmDelete(null) }}
                      aria-label={`Rename ${fmtRole(role)}`} title="Rename"
                      className="p-1.5 rounded-lg text-[#A1A1A8]/60 hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors flex-shrink-0">
                      <Pencil size={13} />
                    </button>
                    {confirmDelete === role ? (
                      <button
                        onClick={() => { setConfirmDelete(null); onDelete(role) }}
                        className="px-2 py-1 rounded-lg text-[10px] font-semibold text-red-400 bg-red-500/10 hover:bg-red-500/20 transition-colors flex-shrink-0">
                        Remove?
                      </button>
                    ) : (
                      <button
                        onClick={() => setConfirmDelete(role)}
                        disabled={inUse}
                        aria-label={`Remove ${fmtRole(role)}`}
                        title={inUse ? 'In use — reassign or rename first' : 'Remove position'}
                        className="p-1.5 rounded-lg text-[#A1A1A8]/60 hover:text-red-400 hover:bg-red-500/10 transition-colors flex-shrink-0 disabled:opacity-25 disabled:hover:text-[#A1A1A8]/60 disabled:hover:bg-transparent disabled:cursor-not-allowed">
                        <Trash2 size={13} />
                      </button>
                    )}
                  </>
                )}
              </div>
            )
          })}
          {positions.length === 0 && (
            <p className="text-[12px] text-[#A1A1A8]/50 text-center py-3">No positions yet — add your first one below.</p>
          )}
        </div>

        {/* Step 3 — add new */}
        <div className="px-5 pb-4">
          <div className="flex items-center gap-2">
            <input
              value={newValue}
              onChange={e => setNewValue(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') commitAdd() }}
              placeholder="Add a position (e.g. Dishwasher)"
              className="flex-1 px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/40 focus:border-[#1A8FD6]/40 focus:outline-none transition-colors"
            />
            <button
              onClick={commitAdd}
              disabled={!normalizeRole(newValue) || positions.includes(normalizeRole(newValue))}
              className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              <Plus size={14} /> Add
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end px-5 py-3 border-t border-[#1F1F23]">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-[#1F1F23] text-[#F5F5F7] hover:bg-[#2A2A30] transition-colors">
            Done
          </button>
        </div>
      </div>
    </div>
  )
}
