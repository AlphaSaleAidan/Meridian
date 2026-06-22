import { useState, useEffect, useMemo } from 'react'
import { X, Sunrise, Sun, Moon, Clock, Check, Sparkles } from 'lucide-react'
import type { ScheduleStaffMember } from '@/lib/agent-data'
import { timeToMinutes, fmtTime } from './schedule-helpers'

/** A single shift to create (parent fills in date + persistence). */
export interface QuickShiftSpec {
  dayOfWeek: number
  startTime: string
  endTime: string
  role: string
  staffMemberId: string
  breakMinutes: number
}

const TEMPLATES = [
  { key: 'opening', label: 'Opening', icon: Sunrise, start: '08:00', end: '16:00' },
  { key: 'midday', label: 'Midday', icon: Sun, start: '11:00', end: '19:00' },
  { key: 'closing', label: 'Closing', icon: Moon, start: '16:00', end: '23:00' },
  { key: 'custom', label: 'Custom', icon: Clock, start: '09:00', end: '17:00' },
] as const

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function initials(name: string) {
  const p = name.trim().split(/\s+/)
  return ((p[0]?.[0] ?? '') + (p[1]?.[0] ?? '')).toUpperCase() || '?'
}

interface Props {
  open: boolean
  staff: ScheduleStaffMember[]
  defaultDay?: number
  onClose: () => void
  onCreate: (specs: QuickShiftSpec[]) => void
}

export default function QuickBuildSheet({ open, staff, defaultDay, onClose, onCreate }: Props) {
  const [template, setTemplate] = useState<string>('opening')
  const [customStart, setCustomStart] = useState('09:00')
  const [customEnd, setCustomEnd] = useState('17:00')
  const [staffIds, setStaffIds] = useState<Set<string>>(new Set())
  const [days, setDays] = useState<Set<number>>(new Set())
  const [breakOn, setBreakOn] = useState(true)

  // Reset to a sensible starting point each time it opens.
  useEffect(() => {
    if (open) {
      setTemplate('opening')
      setStaffIds(new Set())
      setDays(new Set(defaultDay != null ? [defaultDay] : []))
      setBreakOn(true)
    }
  }, [open, defaultDay])

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { window.removeEventListener('keydown', onKey); document.body.style.overflow = prev }
  }, [open, onClose])

  const tpl = TEMPLATES.find(t => t.key === template) ?? TEMPLATES[0]
  const start = template === 'custom' ? customStart : tpl.start
  const end = template === 'custom' ? customEnd : tpl.end
  const durMins = Math.max(0, timeToMinutes(end) - timeToMinutes(start))
  const brk = breakOn && durMins > 5 * 60 ? 30 : 0
  const count = staffIds.size * days.size

  const summary = useMemo(() => {
    if (count === 0) return 'Pick staff and days'
    const net = Math.max(0, durMins - brk) / 60
    return `${count} shift${count === 1 ? '' : 's'} · ${net.toFixed(net % 1 === 0 ? 0 : 1)}h each`
  }, [count, durMins, brk])

  if (!open) return null

  const toggleStaff = (id: string) =>
    setStaffIds(prev => { const n = new Set(prev); n.has(id) ? n.delete(id) : n.add(id); return n })
  const toggleDay = (d: number) =>
    setDays(prev => { const n = new Set(prev); n.has(d) ? n.delete(d) : n.add(d); return n })

  function handleCreate() {
    if (count === 0) return
    const specs: QuickShiftSpec[] = []
    for (const id of staffIds) {
      const member = staff.find(s => s.id === id)
      for (const d of days) {
        specs.push({
          dayOfWeek: d, startTime: start, endTime: end,
          role: member?.role ?? 'any', staffMemberId: id, breakMinutes: brk,
        })
      }
    }
    onCreate(specs)
    onClose()
  }

  const sectionTitle = 'text-[11px] font-bold uppercase tracking-wide text-[#A1A1A8]/55 mb-2'

  return (
    <div className="fixed inset-0 z-[70] flex items-end sm:items-center justify-center sm:p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200" onClick={onClose} />

      <div role="dialog" aria-modal="true" aria-label="Quick build shifts"
        className="relative w-full sm:max-w-lg bg-[#0A0A0B] border-t sm:border border-[#1F1F23]
                   rounded-t-3xl sm:rounded-3xl shadow-2xl flex flex-col max-h-[94vh]
                   animate-in slide-in-from-bottom sm:zoom-in-95 sm:fade-in duration-300">
        {/* grab handle */}
        <div className="sm:hidden flex justify-center pt-2.5 pb-1">
          <div className="w-10 h-1.5 rounded-full bg-[#2A2A30]" />
        </div>

        {/* header */}
        <div className="flex items-center gap-3 px-5 pt-2 pb-3 sm:py-4 border-b border-[#1F1F23]">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#17C5B0] to-[#1A8FD6] flex items-center justify-center shrink-0">
            <Sparkles size={17} className="text-white" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-bold text-[#F5F5F7]">Quick build</h3>
            <p className="text-[12px] text-[#A1A1A8]/70">Add many shifts in a few taps</p>
          </div>
          <button aria-label="Close" onClick={onClose}
            className="p-2 -mr-1 rounded-xl hover:bg-[#1F1F23] text-[#A1A1A8] active:scale-95 transition-all">
            <X size={18} />
          </button>
        </div>

        {/* body */}
        <div className="px-5 py-4 space-y-5 overflow-y-auto">
          {/* 1 · Shift type */}
          <div>
            <p className={sectionTitle}>1 · Shift</p>
            <div className="grid grid-cols-4 gap-2">
              {TEMPLATES.map(t => {
                const Icon = t.icon
                const active = template === t.key
                return (
                  <button key={t.key} onClick={() => setTemplate(t.key)}
                    className={`flex flex-col items-center gap-1.5 py-3 rounded-2xl border transition-all active:scale-95 ${
                      active
                        ? 'border-[#17C5B0]/50 bg-gradient-to-b from-[#17C5B0]/15 to-[#1A8FD6]/[0.06] shadow-lg shadow-[#17C5B0]/10'
                        : 'border-[#1F1F23] hover:bg-[#1F1F23]'
                    }`}>
                    <Icon size={18} className={active ? 'text-[#17C5B0]' : 'text-[#A1A1A8]/60'} />
                    <span className={`text-[12px] font-semibold ${active ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/70'}`}>{t.label}</span>
                  </button>
                )
              })}
            </div>
            {template === 'custom' ? (
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div>
                  <label className="text-[11px] text-[#A1A1A8]/60 block mb-1">Start</label>
                  <input type="time" value={customStart} onChange={e => setCustomStart(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-[#1F1F23] border border-[#1F1F23] text-base text-[#F5F5F7] focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
                <div>
                  <label className="text-[11px] text-[#A1A1A8]/60 block mb-1">End</label>
                  <input type="time" value={customEnd} onChange={e => setCustomEnd(e.target.value)}
                    className="w-full px-3 py-2.5 rounded-xl bg-[#1F1F23] border border-[#1F1F23] text-base text-[#F5F5F7] focus:border-[#1A8FD6]/50 focus:outline-none" />
                </div>
              </div>
            ) : (
              <p className="text-[12px] text-[#A1A1A8]/60 mt-2 text-center">{fmtTime(start)} – {fmtTime(end)}</p>
            )}
          </div>

          {/* 2 · Who */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className={`${sectionTitle} mb-0`}>2 · Who</p>
              <button onClick={() => setStaffIds(staffIds.size === staff.length ? new Set() : new Set(staff.map(s => s.id)))}
                className="text-[11px] font-semibold text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                {staffIds.size === staff.length ? 'Clear' : 'Select all'}
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {staff.map(m => {
                const on = staffIds.has(m.id)
                return (
                  <button key={m.id} onClick={() => toggleStaff(m.id)}
                    className={`flex items-center gap-2 pl-1 pr-3 py-1 rounded-full border transition-all active:scale-95 ${
                      on ? 'border-transparent' : 'border-[#1F1F23] hover:bg-[#1F1F23]'
                    }`}
                    style={on ? { backgroundColor: `${m.color}1F`, boxShadow: `inset 0 0 0 1px ${m.color}66` } : undefined}>
                    <span className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold"
                      style={{ backgroundColor: `${m.color}2A`, color: m.color }}>{initials(m.name)}</span>
                    <span className={`text-[13px] font-semibold ${on ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/70'}`}>{m.name.split(' ')[0]}</span>
                    {on && <Check size={13} style={{ color: m.color }} />}
                  </button>
                )
              })}
            </div>
          </div>

          {/* 3 · Days */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className={`${sectionTitle} mb-0`}>3 · Which days</p>
              <div className="flex gap-3">
                <button onClick={() => setDays(new Set([0, 1, 2, 3, 4]))}
                  className="text-[11px] font-semibold text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">Weekdays</button>
                <button onClick={() => setDays(new Set([0, 1, 2, 3, 4, 5, 6]))}
                  className="text-[11px] font-semibold text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">All week</button>
              </div>
            </div>
            <div className="flex gap-1.5">
              {DAYS.map((name, d) => {
                const on = days.has(d)
                return (
                  <button key={d} onClick={() => toggleDay(d)}
                    className={`flex-1 py-2.5 rounded-xl text-[12px] font-bold transition-all active:scale-95 ${
                      on
                        ? 'bg-gradient-to-b from-[#17C5B0] to-[#1A8FD6] text-white shadow-lg shadow-[#1A8FD6]/20'
                        : 'bg-[#1F1F23] text-[#A1A1A8]/60 hover:text-[#F5F5F7]'
                    }`}>{name[0]}</button>
                )
              })}
            </div>
          </div>

          {/* break toggle */}
          <button onClick={() => setBreakOn(v => !v)}
            className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-[#111113] border border-[#1F1F23] active:scale-[0.99] transition-all">
            <span className="text-[13px] text-[#F5F5F7]">Auto 30-min break on long shifts</span>
            <span className={`relative w-10 h-6 rounded-full transition-colors ${breakOn ? 'bg-[#17C5B0]' : 'bg-[#2A2A30]'}`}>
              <span className={`absolute top-0.5 w-5 h-5 rounded-full bg-white transition-all ${breakOn ? 'left-[18px]' : 'left-0.5'}`} />
            </span>
          </button>
        </div>

        {/* footer */}
        <div className="border-t border-[#1F1F23] px-5 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] sm:pb-4">
          <button onClick={handleCreate} disabled={count === 0}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl text-sm font-bold text-white
                       bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] shadow-lg shadow-[#1A8FD6]/25
                       hover:brightness-110 active:scale-[0.99] transition-all disabled:opacity-40 disabled:active:scale-100">
            <Sparkles size={16} />
            {count > 0 ? `Add ${summary}` : summary}
          </button>
        </div>
      </div>
    </div>
  )
}
