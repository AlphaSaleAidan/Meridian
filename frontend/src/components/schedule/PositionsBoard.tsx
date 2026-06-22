import { useMemo, useState } from 'react'
import {
  DndContext, DragOverlay, PointerSensor, TouchSensor, MouseSensor,
  useSensor, useSensors, useDraggable, useDroppable,
  type DragStartEvent, type DragEndEvent,
} from '@dnd-kit/core'
import { X, UserPlus, Check, AlertTriangle, GripVertical } from 'lucide-react'
import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { fmtTime, timeToMinutes, isStaffAvailable, getStaffWeeklyHours, getRoleColor } from './schedule-helpers'
import { positionsForType, requiredSlotsForDay, type PositionDef } from './schedule-positions'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
function pad2(n: number) { return n < 10 ? `0${n}` : `${n}` }
function isoFor(weekStart: Date, day: number) {
  const d = new Date(weekStart); d.setDate(d.getDate() + day)
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}
function initials(name: string) {
  const p = name.trim().split(/\s+/)
  return ((p[0]?.[0] ?? '') + (p[1]?.[0] ?? '')).toUpperCase() || '?'
}

/** Where an assignment lands: an existing shift, or a brand-new position slot. */
export type AssignTarget =
  | { kind: 'shift'; shiftId: string }
  | { kind: 'new'; dayOfWeek: number; role: string; start: string; end: string; breakMinutes: number }

interface Row {
  key: string
  def: PositionDef
  color: string
  shift: ScheduleShift | null     // existing shift in this slot (may be unassigned)
  needed: boolean                  // a required-but-missing slot (no shift yet)
  target: AssignTarget
}

interface Props {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  businessType: string
  peaks: { day: number; hour: number; intensity: number }[]
  weekStartDate: Date
  day: number
  onDayChange: (day: number) => void
  onAssign: (target: AssignTarget, staffId: string | null) => void
  onShiftClick: (s: ScheduleShift) => void
}

/* ---------- draggable staff chip (pool) ---------- */
function StaffChip({ member, hours }: { member: ScheduleStaffMember; hours: number }) {
  const { attributes, listeners, setNodeRef, isDragging } = useDraggable({
    id: `staff:${member.id}`, data: { staffId: member.id },
  })
  return (
    <button ref={setNodeRef} {...listeners} {...attributes}
      className={`flex items-center gap-2 pl-1 pr-3 py-1.5 rounded-full border touch-none select-none transition-all ${
        isDragging ? 'opacity-30' : 'active:scale-95'
      }`}
      style={{ backgroundColor: `${member.color}1A`, borderColor: `${member.color}55` }}>
      <GripVertical size={12} className="text-[#A1A1A8]/40 -ml-0.5" />
      <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
        style={{ backgroundColor: `${member.color}2E`, color: member.color }}>{initials(member.name)}</span>
      <span className="text-[12px] font-semibold text-[#F5F5F7]">{member.name.split(' ')[0]}</span>
      <span className="text-[10px] text-[#A1A1A8]/50 tabular-nums">{hours.toFixed(0)}h</span>
    </button>
  )
}

/* ---------- droppable position slot ---------- */
function Slot({ row, staffMap, onTap, onClear, onOpen }: {
  row: Row
  staffMap: Map<string, ScheduleStaffMember>
  onTap: (row: Row) => void
  onClear: (row: Row) => void
  onOpen: (s: ScheduleShift) => void
}) {
  const { setNodeRef, isOver } = useDroppable({ id: row.key, data: { target: row.target } })
  const member = row.shift?.staffMemberId ? staffMap.get(row.shift.staffMemberId) : null
  const color = row.color

  if (member) {
    return (
      <div ref={setNodeRef}
        className={`flex items-center gap-2.5 p-2 rounded-xl border transition-all ${
          isOver ? 'border-[#17C5B0] bg-[#17C5B0]/10' : 'border-[#1F1F23] bg-[#111113]'
        }`}>
        <button onClick={() => row.shift && onOpen(row.shift)} className="flex items-center gap-2.5 flex-1 min-w-0 text-left">
          <span className="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-bold shrink-0"
            style={{ backgroundColor: `${member.color}26`, color: member.color, border: `1px solid ${member.color}45` }}>
            {initials(member.name)}
          </span>
          <span className="flex-1 min-w-0">
            <span className="block text-[13px] font-bold text-[#F5F5F7] truncate">{member.name}</span>
            <span className="block text-[11px] text-[#A1A1A8]/55">{fmtTime(row.def.start)}–{fmtTime(row.def.end)}</span>
          </span>
        </button>
        <button onClick={() => onClear(row)} aria-label="Remove from position"
          className="p-1.5 rounded-lg text-[#A1A1A8]/50 hover:text-red-400 hover:bg-red-500/10 active:scale-95 transition-all shrink-0">
          <X size={15} />
        </button>
      </div>
    )
  }

  // empty (open shift or a needed phantom)
  return (
    <button ref={setNodeRef} onClick={() => onTap(row)}
      className={`w-full flex items-center gap-2.5 p-2 rounded-xl border border-dashed transition-all active:scale-[0.99] ${
        isOver ? 'border-[#17C5B0] bg-[#17C5B0]/10'
        : row.needed ? 'border-[#D4A843]/40 bg-[#D4A843]/[0.05] hover:bg-[#D4A843]/10'
        : 'border-[#2A2A30] bg-[#0E0E10] hover:bg-[#1F1F23]/40'
      }`}>
      <span className="w-9 h-9 rounded-full border border-dashed flex items-center justify-center shrink-0"
        style={{ borderColor: `${color}66` }}>
        <UserPlus size={15} style={{ color }} />
      </span>
      <span className="flex-1 text-left">
        <span className="block text-[12px] font-semibold" style={{ color: row.needed ? '#D4A843' : '#A1A1A8' }}>
          {row.needed ? 'Needs someone' : 'Open'}
        </span>
        <span className="block text-[11px] text-[#A1A1A8]/45">{fmtTime(row.def.start)}–{fmtTime(row.def.end)} · tap or drag</span>
      </span>
    </button>
  )
}

export default function PositionsBoard({
  shifts, staff, businessType, peaks, weekStartDate, day, onDayChange, onAssign, onShiftClick,
}: Props) {
  const [activeStaffId, setActiveStaffId] = useState<string | null>(null)
  const [picker, setPicker] = useState<Row | null>(null)

  const staffMap = useMemo(() => new Map(staff.map(s => [s.id, s])), [staff])
  const defs = useMemo(() => positionsForType(businessType), [businessType])

  const sensors = useSensors(
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 160, tolerance: 8 } }),
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
  )

  // Build the position rows for the selected day: required slots reconciled with
  // existing shifts (matched by role + start hour).
  const { rows, filled, needed } = useMemo(() => {
    const dayShifts = shifts.filter(s => s.dayOfWeek === day && !s.isRecommended)
    const required = requiredSlotsForDay(defs, day, peaks)
    const reqByPos = new Map<string, number>()
    required.forEach(s => reqByPos.set(s.positionKey, (reqByPos.get(s.positionKey) ?? 0) + 1))

    const rows: Row[] = []
    let filledCount = 0, neededCount = 0
    for (const def of defs) {
      const matching = dayShifts.filter(s => s.role === def.role && Math.abs(parseInt(s.startTime) - parseInt(def.start)) <= 1)
      const reqCount = reqByPos.get(def.key) ?? 0
      const total = Math.max(reqCount, matching.length)
      for (let i = 0; i < total; i++) {
        const shift = matching[i] ?? null
        const assigned = !!shift?.staffMemberId
        if (assigned) filledCount++
        else if (i < reqCount) neededCount++
        rows.push({
          key: `${def.key}-${i}`,
          def,
          color: getRoleColor(def.role),
          shift,
          needed: !shift && i < reqCount,
          target: shift
            ? { kind: 'shift', shiftId: shift.id }
            : { kind: 'new', dayOfWeek: day, role: def.role, start: def.start, end: def.end, breakMinutes: timeToMinutes(def.end) - timeToMinutes(def.start) > 300 ? 30 : 0 },
        })
      }
    }
    return { rows, filled: filledCount, needed: neededCount }
  }, [shifts, defs, day, peaks])

  // group rows by position for display
  const groups = useMemo(() => {
    const m = new Map<string, { def: PositionDef; rows: Row[] }>()
    for (const r of rows) {
      if (!m.has(r.def.key)) m.set(r.def.key, { def: r.def, rows: [] })
      m.get(r.def.key)!.rows.push(r)
    }
    return [...m.values()]
  }, [rows])

  // staff available for the picked slot's day (not double-booked at that time)
  const pickerCandidates = useMemo(() => {
    if (!picker) return []
    const t = picker.target
    const start = t.kind === 'new' ? t.start : picker.def.start
    const end = t.kind === 'new' ? t.end : picker.def.end
    const sMin = timeToMinutes(start), eMin = timeToMinutes(end)
    return staff.filter(m => {
      if (!isStaffAvailable(m, day)) return false
      const overlaps = shifts.some(s => s.dayOfWeek === day && s.staffMemberId === m.id && !s.isRecommended &&
        sMin < timeToMinutes(s.endTime) && eMin > timeToMinutes(s.startTime))
      return !overlaps
    })
  }, [picker, staff, shifts, day])

  const activeMember = activeStaffId ? staffMap.get(activeStaffId) : null

  function handleDragEnd(e: DragEndEvent) {
    setActiveStaffId(null)
    const staffId = e.active.data.current?.staffId as string | undefined
    const target = e.over?.data.current?.target as AssignTarget | undefined
    if (staffId && target) onAssign(target, staffId)
  }

  return (
    <DndContext sensors={sensors}
      onDragStart={(e: DragStartEvent) => setActiveStaffId(e.active.data.current?.staffId ?? null)}
      onDragEnd={handleDragEnd} onDragCancel={() => setActiveStaffId(null)}>

      {/* Day tabs */}
      <div className="flex gap-1.5 overflow-x-auto pb-1 -mx-1 px-1">
        {DAYS.map((name, di) => {
          const d = new Date(weekStartDate); d.setDate(d.getDate() + di)
          const isSel = di === day
          return (
            <button key={di} onClick={() => onDayChange(di)}
              className={`flex-1 min-w-[46px] flex flex-col items-center gap-0.5 py-2.5 rounded-2xl transition-all active:scale-95 ${
                isSel ? 'bg-gradient-to-b from-[#17C5B0]/20 to-[#1A8FD6]/10 border border-[#17C5B0]/40' : 'border border-[#1F1F23] hover:bg-[#1F1F23]'
              }`}>
              <span className={`text-[10px] font-bold uppercase tracking-wide ${isSel ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/55'}`}>{name}</span>
              <span className={`text-[15px] font-bold leading-none ${isSel ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/40'}`}>{d.getDate()}</span>
            </button>
          )
        })}
      </div>

      {/* Fill summary */}
      <div className="flex items-center justify-between mt-3 mb-2 px-1">
        <span className="text-[13px] font-bold text-[#F5F5F7]">Positions</span>
        {needed > 0 ? (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-[#D4A843] bg-[#D4A843]/10 px-2 py-0.5 rounded-full">
            <AlertTriangle size={11} />{needed} to fill
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-semibold text-[#17C5B0] bg-[#17C5B0]/10 px-2 py-0.5 rounded-full">
            <Check size={11} />All filled
          </span>
        )}
      </div>

      {/* Position groups */}
      <div className="space-y-3">
        {groups.map(g => (
          <div key={g.def.key}>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="w-2 h-2 rounded-full" style={{ backgroundColor: getRoleColor(g.def.role) }} />
              <span className="text-[12px] font-bold text-[#F5F5F7]">{g.def.label}</span>
              <span className="text-[11px] text-[#A1A1A8]/45">{fmtTime(g.def.start)}–{fmtTime(g.def.end)}</span>
              <span className="text-[11px] text-[#A1A1A8]/40 ml-auto">{g.rows.filter(r => r.shift?.staffMemberId).length}/{g.rows.length}</span>
            </div>
            <div className="space-y-1.5">
              {g.rows.map(r => (
                <Slot key={r.key} row={r} staffMap={staffMap}
                  onTap={setPicker} onClear={() => r.shift && onAssign({ kind: 'shift', shiftId: r.shift.id }, null)}
                  onOpen={onShiftClick} />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Staff pool — de-emphasized, sticky-ish at the bottom */}
      <div className="mt-4 rounded-2xl bg-[#0E0E10] border border-[#1F1F23] p-3">
        <p className="text-[11px] font-bold uppercase tracking-wide text-[#A1A1A8]/45 mb-2">
          Staff pool · drag a name into a slot
        </p>
        <div className="flex flex-wrap gap-2">
          {staff.map(m => <StaffChip key={m.id} member={m} hours={getStaffWeeklyHours(m.id, shifts)} />)}
          {staff.length === 0 && <span className="text-[12px] text-[#A1A1A8]/40">Add staff to start assigning.</span>}
        </div>
      </div>

      {/* Drag preview */}
      <DragOverlay>
        {activeMember && (
          <div className="flex items-center gap-2 pl-1 pr-3 py-1.5 rounded-full border shadow-2xl"
            style={{ backgroundColor: `${activeMember.color}26`, borderColor: activeMember.color }}>
            <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
              style={{ backgroundColor: `${activeMember.color}3A`, color: activeMember.color }}>{initials(activeMember.name)}</span>
            <span className="text-[12px] font-semibold text-[#F5F5F7]">{activeMember.name.split(' ')[0]}</span>
          </div>
        )}
      </DragOverlay>

      {/* Tap-to-assign picker */}
      {picker && (
        <div className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center sm:p-4">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={() => setPicker(null)} />
          <div className="relative w-full sm:max-w-sm bg-[#0A0A0B] border-t sm:border border-[#1F1F23] rounded-t-3xl sm:rounded-2xl shadow-2xl flex flex-col max-h-[80vh] animate-in slide-in-from-bottom sm:zoom-in-95 duration-300">
            <div className="sm:hidden flex justify-center pt-2.5 pb-1"><div className="w-10 h-1.5 rounded-full bg-[#2A2A30]" /></div>
            <div className="flex items-center justify-between px-5 py-3 border-b border-[#1F1F23]">
              <div>
                <h3 className="text-[15px] font-bold text-[#F5F5F7]">{picker.def.label}</h3>
                <p className="text-[12px] text-[#A1A1A8]/60">{fmtTime(picker.def.start)}–{fmtTime(picker.def.end)} · pick someone</p>
              </div>
              <button onClick={() => setPicker(null)} className="p-2 rounded-xl hover:bg-[#1F1F23] text-[#A1A1A8]"><X size={18} /></button>
            </div>
            <div className="px-3 py-3 overflow-y-auto pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
              {pickerCandidates.length === 0 && (
                <p className="text-[13px] text-[#A1A1A8]/50 px-2 py-4 text-center">No one's available for this slot.</p>
              )}
              {pickerCandidates.map(m => (
                <button key={m.id} onClick={() => { onAssign(picker.target, m.id); setPicker(null) }}
                  className="w-full flex items-center gap-3 p-2.5 rounded-xl hover:bg-[#1F1F23] active:scale-[0.99] transition-all text-left">
                  <span className="w-9 h-9 rounded-full flex items-center justify-center text-[12px] font-bold shrink-0"
                    style={{ backgroundColor: `${m.color}26`, color: m.color }}>{initials(m.name)}</span>
                  <span className="flex-1 min-w-0">
                    <span className="block text-[13px] font-semibold text-[#F5F5F7] truncate">{m.name}</span>
                    <span className="block text-[11px] text-[#A1A1A8]/50 capitalize">{m.role.replace(/_/g, ' ')} · {getStaffWeeklyHours(m.id, shifts).toFixed(0)}h this week</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </DndContext>
  )
}
