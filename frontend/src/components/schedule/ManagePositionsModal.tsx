import { useState } from 'react'
import { X, Plus, Trash2, Briefcase } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { getRoleColor } from './schedule-helpers'
import type { PositionDef } from './schedule-positions'

/**
 * Manage positions — edit the merchant's position defs directly: name,
 * staff needed (headcount), start/end times, add + delete.
 *
 * Every change persists immediately via onChange (no save button). Renaming a
 * position also renames its role string; the parent writes that through to the
 * staff/shift rows that carry it (so it survives on any device).
 */

const fmtRole = (r: string) => r.replace(/_/g, ' ')
const normalizeRole = (s: string) => s.trim().toLowerCase().replace(/\s+/g, '_')

interface Props {
  open: boolean
  onClose: () => void
  defs: PositionDef[]
  staff: ScheduleStaffMember[]
  shifts: ScheduleShift[]
  /** Persist the full defs list — called on every change. */
  onChange: (defs: PositionDef[]) => void
  /** Write a role rename through to staff/shift rows that carry the old role. */
  onRenameRole: (oldRole: string, newRole: string) => void
}

export default function ManagePositionsModal({
  open, onClose, defs, staff, shifts, onChange, onRenameRole,
}: Props) {
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newCount, setNewCount] = useState('1')
  const [newStart, setNewStart] = useState('09:00')
  const [newEnd, setNewEnd] = useState('17:00')

  if (!open) return null

  const usage = (role: string) => ({
    staff: staff.filter(s => s.role === role).length,
    shifts: shifts.filter(s => s.role === role && !s.isRecommended).length,
  })

  const update = (key: string, patch: Partial<PositionDef>) =>
    onChange(defs.map(d => (d.key === key ? { ...d, ...patch } : d)))

  const commitRename = (def: PositionDef, raw: string) => {
    const label = raw.trim()
    if (!label || label === def.label) return
    const oldRole = def.role
    const newRole = normalizeRole(label)
    // Sibling defs sharing the role (other time blocks of the same job) follow
    // the rename so they keep matching the renamed staff.
    onChange(defs.map(d => {
      if (d.key === def.key) return { ...d, label, role: newRole }
      return d.role === oldRole ? { ...d, role: newRole } : d
    }))
    if (newRole !== oldRole) onRenameRole(oldRole, newRole)
  }

  const commitBase = (def: PositionDef, raw: string) => {
    if (raw === '') return // mid-edit — snap back on blur
    const n = Math.max(0, Math.round(Number(raw)))
    if (Number.isFinite(n) && n !== def.base) update(def.key, { base: n })
  }

  const commitAdd = () => {
    const label = newName.trim()
    if (!label) return
    const role = normalizeRole(label)
    const base = Math.max(0, Math.round(Number(newCount)) || 0)
    onChange([...defs, {
      key: `custom-${role}-${Date.now().toString(36)}`,
      label, role, start: newStart, end: newEnd, base,
    }])
    setNewName(''); setNewCount('1')
  }

  const inputCls = 'px-2 py-1 rounded bg-[#1F1F23] border border-transparent focus:border-[#1A8FD6]/40 text-[12px] text-[#F5F5F7] focus:outline-none transition-colors'

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

        {/* What positions do */}
        <div className="px-5 pt-4">
          <p className="text-[12px] text-[#A1A1A8] leading-relaxed">
            <span className="text-[#F5F5F7] font-medium">Positions</span> are the slots on your
            board — each has a name, how many staff it needs, and a time block. Auto-fill
            staffs them from your sales history. Rename, resize, retime, add, or remove
            them — changes save automatically.
          </p>
          <p className="text-[10px] text-[#A1A1A8]/50 mt-1.5">
            Renaming updates every staff member and shift that has the position.
          </p>
        </div>

        {/* Editable defs list */}
        <div className="px-5 py-4 space-y-1.5 max-h-[45vh] overflow-y-auto">
          {defs.map(def => {
            const u = usage(def.role)
            const inUse = u.staff > 0 || u.shifts > 0
            const usageLabel = [u.staff > 0 && `${u.staff} staff`, u.shifts > 0 && `${u.shifts} shift${u.shifts === 1 ? '' : 's'}`]
              .filter(Boolean).join(' / ')
            return (
              <div key={def.key} className="px-2.5 py-2 rounded-lg bg-[#111113] border border-[#1F1F23] space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: getRoleColor(def.role) }} />
                  <input
                    defaultValue={def.label}
                    aria-label={`Rename ${def.label}`}
                    onBlur={e => commitRename(def, e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
                    className="flex-1 min-w-0 px-2 py-1 rounded bg-transparent border border-transparent hover:border-[#2A2A30] focus:border-[#1A8FD6]/40 focus:bg-[#1F1F23] text-[13px] font-medium text-[#F5F5F7] focus:outline-none transition-colors"
                  />
                  {inUse && (
                    <span className="text-[10px] text-[#A1A1A8]/45 flex-shrink-0 tabular-nums">{usageLabel}</span>
                  )}
                  <button
                    onClick={() => setConfirmDelete(confirmDelete === def.key ? null : def.key)}
                    aria-label={`Remove ${def.label}`} title="Remove position"
                    className="p-1.5 rounded-lg text-[#A1A1A8]/60 hover:text-red-400 hover:bg-red-500/10 transition-colors flex-shrink-0">
                    <Trash2 size={13} />
                  </button>
                </div>
                <div className="flex items-center gap-2 pl-4 flex-wrap">
                  <label className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8]/60">
                    Staff needed
                    <input
                      type="number" min={0} step={1}
                      defaultValue={def.base}
                      aria-label={`Staff needed for ${def.label}`}
                      onChange={e => commitBase(def, e.target.value)}
                      onBlur={e => { if (e.target.value === '') e.target.value = String(def.base) }}
                      className={`${inputCls} w-14 tabular-nums`}
                    />
                  </label>
                  <label className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8]/60 ml-auto">
                    <input
                      type="time" value={def.start}
                      aria-label={`${def.label} start time`}
                      onChange={e => { if (e.target.value) update(def.key, { start: e.target.value }) }}
                      className={inputCls}
                    />
                    –
                    <input
                      type="time" value={def.end}
                      aria-label={`${def.label} end time`}
                      onChange={e => { if (e.target.value) update(def.key, { end: e.target.value }) }}
                      className={inputCls}
                    />
                  </label>
                </div>
                {confirmDelete === def.key && (
                  <div className="flex items-center gap-2 pl-4 pt-0.5">
                    <p className="flex-1 text-[10px] text-[#A1A1A8]/60 leading-snug">
                      {inUse
                        ? `${usageLabel} keep "${fmtRole(def.role)}" as their role label — the position disappears from the board.`
                        : 'Not in use — safe to remove.'}
                    </p>
                    <button
                      onClick={() => { setConfirmDelete(null); onChange(defs.filter(d => d.key !== def.key)) }}
                      className="px-2 py-1 rounded-lg text-[10px] font-semibold text-red-400 bg-red-500/10 hover:bg-red-500/20 transition-colors flex-shrink-0">
                      Remove
                    </button>
                    <button
                      onClick={() => setConfirmDelete(null)}
                      className="px-2 py-1 rounded-lg text-[10px] font-medium text-[#A1A1A8] hover:bg-[#1F1F23] transition-colors flex-shrink-0">
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            )
          })}
          {defs.length === 0 && (
            <p className="text-[12px] text-[#A1A1A8]/50 text-center py-3">No positions yet — add your first one below.</p>
          )}
        </div>

        {/* Add position */}
        <div className="px-5 pb-4 space-y-2">
          <div className="flex items-center gap-2">
            <input
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') commitAdd() }}
              placeholder="Add a position (e.g. Dishwasher)"
              className="flex-1 px-3 py-2 rounded-lg bg-[#1F1F23] border border-[#1F1F23] text-sm text-[#F5F5F7] placeholder:text-[#A1A1A8]/40 focus:border-[#1A8FD6]/40 focus:outline-none transition-colors"
            />
            <button
              onClick={commitAdd}
              disabled={!newName.trim()}
              className="flex items-center gap-1 px-3 py-2 rounded-lg text-sm font-medium bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              <Plus size={14} /> Add
            </button>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8]/60">
              Staff needed
              <input
                type="number" min={0} step={1}
                value={newCount}
                aria-label="Staff needed for new position"
                onChange={e => setNewCount(e.target.value)}
                className={`${inputCls} w-14 tabular-nums`}
              />
            </label>
            <label className="flex items-center gap-1.5 text-[10px] text-[#A1A1A8]/60 ml-auto">
              <input type="time" value={newStart} aria-label="New position start time"
                onChange={e => { if (e.target.value) setNewStart(e.target.value) }} className={inputCls} />
              –
              <input type="time" value={newEnd} aria-label="New position end time"
                onChange={e => { if (e.target.value) setNewEnd(e.target.value) }} className={inputCls} />
            </label>
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
