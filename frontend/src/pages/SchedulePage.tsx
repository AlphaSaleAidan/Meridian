import { useState, useMemo, useCallback } from 'react'
import { Calendar, Send, Sparkles, FileDown, ChevronLeft, ChevronRight, Plus, Clock, DollarSign, Users, X } from 'lucide-react'
import {
  generateScheduleStaff, generateScheduleShifts, generateRecommendedShifts,
  generatePeakHourHeatmap, getHolidaysForWeek,
  type ScheduleShift, type ScheduleStaffMember,
} from '@/lib/agent-data'
import { getActiveBusinessType, isCanadaPath } from '@/lib/demo-context'
import { formatCents } from '@/lib/format'
import ScrollReveal from '@/components/ScrollReveal'
import AnalyzingDataState from '@/components/AnalyzingDataState'
import { useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import WeeklyCalendarGrid from '@/components/schedule/WeeklyCalendarGrid'
import AddStaffModal from '@/components/schedule/AddStaffModal'
import ShiftEditPopover from '@/components/schedule/ShiftEditPopover'

function getMonday(d: Date): Date {
  const dt = new Date(d), day = dt.getDay()
  dt.setDate(dt.getDate() + (day === 0 ? -6 : 1 - day))
  dt.setHours(0, 0, 0, 0)
  return dt
}
function addWeeks(d: Date, w: number) { const r = new Date(d); r.setDate(r.getDate() + w * 7); return r }
function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate() + n); return r }
function pad2(n: number) { return n < 10 ? `0${n}` : `${n}` }
function formatDateISO(d: Date) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }
function timeToMinutes(t: string) { const [h, m] = t.split(':').map(Number); return h * 60 + (m || 0) }

const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

function buildOptimalSchedule(
  staff: ScheduleStaffMember[],
  peaks: { day: number; hour: number; intensity: number }[],
  weekStart: Date,
): ScheduleShift[] {
  const maxI = Math.max(...peaks.map(p => p.intensity), 1)
  const ranked = [...staff].sort((a, b) => b.hourlyRate - a.hourlyRate)
  const demand = new Map<string, number>()
  for (const c of peaks) {
    const r = c.intensity / maxI
    const need = r > 0.75 ? 3 : r > 0.5 ? 2 : r > 0.25 ? 1 : 0
    if (need > 0) demand.set(`${c.day}-${c.hour}`, need)
  }
  const asgn = new Map<string, Map<number, Set<number>>>()
  ranked.forEach(s => asgn.set(s.id, new Map()))
  const slots = [...demand.entries()]
    .map(([k, need]) => {
      const [d, h] = k.split('-').map(Number)
      return { day: d, hour: h, need, intensity: peaks.find(p => p.day === d && p.hour === h)?.intensity ?? 0 }
    })
    .sort((a, b) => b.intensity - a.intensity)
  for (const slot of slots) {
    let filled = 0
    for (const m of ranked) {
      if (filled >= slot.need) break
      const av = m.availability[DAY_KEYS[slot.day]]
      if (!av?.available || slot.hour < parseInt(av.start) || slot.hour >= parseInt(av.end)) continue
      const dm = asgn.get(m.id)!
      if (!dm.has(slot.day)) dm.set(slot.day, new Set())
      dm.get(slot.day)!.add(slot.hour)
      filled++
    }
  }
  const shifts: ScheduleShift[] = []
  let sid = 1
  for (const [staffId, dayMap] of asgn) {
    const member = staff.find(s => s.id === staffId)
    if (!member) continue
    for (const [day, hrs] of dayMap) {
      if (hrs.size === 0) continue
      const sorted = [...hrs].sort((a, b) => a - b)
      const groups: number[][] = []
      let g = [sorted[0]]
      for (let i = 1; i < sorted.length; i++) {
        if (sorted[i] === g[g.length - 1] + 1) g.push(sorted[i])
        else { groups.push(g); g = [sorted[i]] }
      }
      groups.push(g)
      for (const grp of groups) {
        const sH = grp[0], eH = grp[grp.length - 1] + 1
        shifts.push({
          id: `shift-opt-${sid++}`, staffMemberId: staffId, dayOfWeek: day,
          shiftDate: formatDateISO(addDays(weekStart, day)),
          startTime: `${pad2(sH)}:00`, endTime: `${pad2(eH)}:00`,
          role: member.role, breakMinutes: eH - sH > 5 ? 30 : 0,
          notes: '', status: 'draft', isRecommended: false,
        })
      }
    }
  }
  return shifts
}

const MOBILE_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

function MobileDayView({ shifts, staff, holidays, weekStartDate, onShiftClick, onSlotClick }: {
  shifts: ScheduleShift[]
  staff: ScheduleStaffMember[]
  holidays: { date: string; name: string }[]
  weekStartDate: Date
  onShiftClick: (s: ScheduleShift) => void
  onSlotClick: (day: number, hour: number) => void
}) {
  const [day, setDay] = useState(() => {
    const now = new Date(), todayStr = formatDateISO(now)
    for (let i = 0; i < 7; i++) {
      if (formatDateISO(addDays(weekStartDate, i)) === todayStr) return i
    }
    return 0
  })

  const staffMap = useMemo(() => new Map(staff.map(s => [s.id, s])), [staff])
  const todayStr = formatDateISO(new Date())
  const selectedDate = addDays(weekStartDate, day)
  const selectedDateStr = formatDateISO(selectedDate)
  const isToday = selectedDateStr === todayStr
  const holiday = holidays.find(h => h.date === selectedDateStr)

  const dayShifts = useMemo(
    () => shifts.filter(s => s.dayOfWeek === day && !s.isRecommended)
      .sort((a, b) => a.startTime.localeCompare(b.startTime)),
    [shifts, day],
  )

  return (
    <div className="lg:hidden space-y-3">
      {/* Day tabs */}
      <div className="flex gap-1 overflow-x-auto pb-1">
        {MOBILE_DAYS.map((name, di) => {
          const d = addDays(weekStartDate, di)
          const isSel = di === day
          const isTod = formatDateISO(d) === todayStr
          const cnt = shifts.filter(s => s.dayOfWeek === di && !s.isRecommended).length
          return (
            <button key={di} onClick={() => setDay(di)}
              className={`flex-1 min-w-[44px] flex flex-col items-center py-2 rounded-lg transition-all ${
                isSel ? 'bg-[#17C5B0]/10 border border-[#17C5B0]/30' : 'border border-transparent hover:bg-[#1F1F23]'
              }`}>
              <span className={`text-[10px] font-bold uppercase ${isSel ? 'text-[#17C5B0]' : isTod ? 'text-[#1A8FD6]' : 'text-[#A1A1A8]/60'}`}>{name}</span>
              <span className={`text-[13px] font-semibold ${isSel ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]/40'}`}>{d.getDate()}</span>
              {cnt > 0 && <div className={`mt-0.5 w-1.5 h-1.5 rounded-full ${isSel ? 'bg-[#17C5B0]' : 'bg-[#A1A1A8]/25'}`} />}
            </button>
          )
        })}
      </div>

      {/* Day header */}
      <div className="flex items-center justify-between px-1">
        <div>
          <span className="text-sm font-semibold text-[#F5F5F7]">
            {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
          </span>
          {isToday && <span className="ml-2 text-[10px] font-medium text-[#1A8FD6] bg-[#1A8FD6]/10 px-1.5 py-0.5 rounded">Today</span>}
          {holiday && <span className="ml-2 text-[10px] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">{holiday.name}</span>}
        </div>
        <span className="text-[11px] text-[#A1A1A8]/40 font-mono">{dayShifts.length} shifts</span>
      </div>

      {/* Shift cards */}
      <div className="space-y-2">
        {dayShifts.map(shift => {
          const member = shift.staffMemberId ? staffMap.get(shift.staffMemberId) : null
          const color = member?.color || '#A1A1A8'
          return (
            <button key={shift.id} onClick={() => onShiftClick(shift)}
              className="w-full flex items-center gap-3 px-4 py-3 rounded-xl bg-[#111113] border border-[#1F1F23] hover:bg-[#1A1A1D] transition-colors text-left">
              <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
              <div className="flex-1 min-w-0">
                <div className="text-[13px] font-semibold text-[#F5F5F7] truncate">{member?.name || 'Unassigned'}</div>
                <div className="text-[11px] text-[#A1A1A8]/50 capitalize">{member?.role?.replace(/_/g, ' ') || shift.role}</div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="text-[12px] font-mono text-[#F5F5F7]/80">{shift.startTime}–{shift.endTime}</div>
              </div>
            </button>
          )
        })}

        {dayShifts.length === 0 && (
          <div className="text-center py-8">
            <p className="text-sm text-[#A1A1A8]/30">No shifts scheduled</p>
          </div>
        )}

        <button onClick={() => onSlotClick(day, 9)}
          className="w-full flex items-center justify-center gap-1.5 py-3 rounded-xl border border-dashed border-[#1F1F23] text-xs text-[#A1A1A8]/50 hover:text-[#A1A1A8] hover:border-[#333] transition-colors">
          <Plus size={14} /> Add shift
        </button>
      </div>
    </div>
  )
}

export default function SchedulePage() {
  const isDemo = useIsDemo()
  const { org } = useAuth()
  const businessType = getActiveBusinessType()
  const portalContext = isCanadaPath() ? 'ca' : 'us'
  const country = portalContext === 'ca' ? 'CA' : 'US'
  const [weekStartDate, setWeekStartDate] = useState(() => getMonday(new Date()))
  const [showAddStaff, setShowAddStaff] = useState(false)
  const [selectedShift, setSelectedShift] = useState<ScheduleShift | null>(null)
  const [isPublished, setIsPublished] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const showDemoSchedule = isDemo || isCanadaPath()

  const [staff, setStaff] = useState<ScheduleStaffMember[]>(() =>
    showDemoSchedule ? generateScheduleStaff() : [])
  const [shifts, setShifts] = useState<ScheduleShift[]>(() =>
    showDemoSchedule ? generateScheduleShifts(weekStartDate) : [])
  const peakHours = useMemo(() => generatePeakHourHeatmap(), [])
  const holidays = useMemo(
    () => getHolidaysForWeek(weekStartDate, country as 'US' | 'CA'),
    [weekStartDate, country])

  const showToast = useCallback((msg: string) => {
    setToast(msg); setTimeout(() => setToast(null), 4000)
  }, [])

  const weekEnd = addDays(weekStartDate, 6)
  const weekLabel = `${weekStartDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} – ${weekEnd.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}`

  // Stats
  const realShifts = useMemo(() => shifts.filter(s => !s.isRecommended), [shifts])
  const totalHours = useMemo(() => {
    const mins = realShifts.reduce((sum, s) => {
      return sum + Math.max(0, timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes)
    }, 0)
    return (mins / 60).toFixed(1)
  }, [realShifts])
  const totalLaborCents = useMemo(() => {
    const staffMap = new Map(staff.map(s => [s.id, s]))
    return realShifts.reduce((sum, s) => {
      const member = s.staffMemberId ? staffMap.get(s.staffMemberId) : null
      if (!member) return sum
      const hrs = Math.max(0, (timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes) / 60)
      return sum + Math.round(member.hourlyRate * hrs)
    }, 0)
  }, [realShifts, staff])
  const staffScheduled = useMemo(() =>
    new Set(realShifts.map(s => s.staffMemberId).filter(Boolean)).size
  , [realShifts])

  // Handlers
  const handlePrevWeek = useCallback(() => {
    const prev = addWeeks(weekStartDate, -1)
    setWeekStartDate(prev); setIsPublished(false); setToast(null)
    if (showDemoSchedule) setShifts(generateScheduleShifts(prev))
  }, [weekStartDate, showDemoSchedule])

  const handleNextWeek = useCallback(() => {
    const next = addWeeks(weekStartDate, 1)
    setWeekStartDate(next); setIsPublished(false); setToast(null)
    if (showDemoSchedule) setShifts(generateScheduleShifts(next))
  }, [weekStartDate, showDemoSchedule])

  const handleAddStaff = useCallback((m: Omit<ScheduleStaffMember, 'id'>) => {
    setStaff(prev => [...prev, { ...m, id: `staff-${Date.now()}` }])
  }, [])

  const handleShiftClick = useCallback((s: ScheduleShift) => setSelectedShift(s), [])

  const handleSlotClick = useCallback((day: number, hour: number) => {
    const d = addDays(weekStartDate, day)
    const ns: ScheduleShift = {
      id: `shift-new-${Date.now()}`, staffMemberId: null, dayOfWeek: day,
      shiftDate: formatDateISO(d), startTime: `${pad2(hour)}:00`,
      endTime: `${pad2(Math.min(hour + 4, 23))}:00`, role: 'any',
      breakMinutes: 0, notes: '', status: 'draft', isRecommended: false,
    }
    setShifts(prev => [...prev, ns]); setSelectedShift(ns)
  }, [weekStartDate])

  const handleShiftSave = useCallback((u: ScheduleShift) => {
    setShifts(prev => prev.map(s => (s.id === u.id ? u : s)))
  }, [])
  const handleShiftDelete = useCallback((id: string) => {
    setShifts(prev => prev.filter(s => s.id !== id))
  }, [])

  const handleShiftMove = useCallback((shiftId: string, newDay: number, newStartHour: number) => {
    setShifts(prev => prev.map(s => {
      if (s.id !== shiftId) return s
      const dur = parseInt(s.endTime) - parseInt(s.startTime)
      const eH = Math.min(newStartHour + dur, 23)
      return { ...s, dayOfWeek: newDay, shiftDate: formatDateISO(addDays(weekStartDate, newDay)),
        startTime: `${pad2(newStartHour)}:00`, endTime: `${pad2(eH)}:00` }
    }))
  }, [weekStartDate])

  const handleGenerate = useCallback(() => {
    setIsGenerating(true)
    setTimeout(() => {
      const opt = buildOptimalSchedule(staff, peakHours, weekStartDate)
      setShifts(opt); setIsPublished(false); setIsGenerating(false)
      const used = new Set(opt.map(s => s.staffMemberId).filter(Boolean)).size
      showToast(`Schedule generated — ${opt.length} shifts across ${used} staff`)
    }, 1200)
  }, [staff, peakHours, weekStartDate, showToast])

  const handlePublish = useCallback(() => {
    setIsPublished(true)
    setShifts(prev => prev.map(s => ({ ...s, status: 'published' as const })))
    showToast(`Schedule published — ${staffScheduled} staff notified`)
  }, [staffScheduled, showToast])

  const handleDownloadPdf = useCallback(async () => {
    const { generateSchedulePdf } = await import('@/lib/generate-schedule-pdf')
    const blob = await generateSchedulePdf({ shifts, staff, weekStartDate, businessName: org?.business_name })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `schedule-${formatDateISO(weekStartDate)}.pdf`; a.click()
    URL.revokeObjectURL(url)
  }, [shifts, staff, weekStartDate])

  if (!showDemoSchedule) {
    return (
      <div className="space-y-6">
        <ScrollReveal variant="fadeUp">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Schedule</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">AI-powered staff scheduling with peak hour optimization</p>
          </div>
        </ScrollReveal>
        <AnalyzingDataState title="Setting up your schedule"
          description="Connect your POS to import staff data and generate AI-optimized schedules based on your transaction patterns." />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center">
              <Calendar size={20} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#F5F5F7]">Schedule</h1>
              <p className="text-[12px] text-[#A1A1A8] mt-0.5">AI-powered staff scheduling</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={() => setShowAddStaff(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
              <Plus size={13} />Staff
            </button>
            <button onClick={handleGenerate} disabled={isGenerating || staff.length === 0}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-white shadow-lg shadow-[#17C5B0]/20 hover:shadow-[#17C5B0]/30 hover:brightness-110 disabled:opacity-40">
              <Sparkles size={14} className={isGenerating ? 'animate-spin' : ''} />
              {isGenerating ? 'Generating…' : 'Generate'}
            </button>
            <button onClick={handlePublish}
              disabled={realShifts.length === 0 || isPublished}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${isPublished
                ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-30'}`}>
              <Send size={13} />{isPublished ? 'Published' : 'Publish'}
            </button>
            <button onClick={handleDownloadPdf}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
              <FileDown size={13} />
            </button>
          </div>
        </div>
      </ScrollReveal>

      {/* Toast */}
      {toast && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-300 flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg bg-[#111113] border-t-2 border-[#17C5B0] shadow-lg text-sm text-[#F5F5F7]">
          <span>{toast}</span>
          <button onClick={() => setToast(null)} className="text-[#A1A1A8] hover:text-[#F5F5F7]"><X size={14} /></button>
        </div>
      )}

      {/* Week nav + stats bar */}
      <ScrollReveal variant="fadeUp" delay={0.03}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-1">
          <div className="flex items-center gap-2">
            <button onClick={handlePrevWeek}
              className="p-1.5 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8] transition-colors">
              <ChevronLeft size={16} />
            </button>
            <span className="text-sm font-semibold text-[#F5F5F7] min-w-[200px] text-center">
              {weekLabel}
            </span>
            <button onClick={handleNextWeek}
              className="p-1.5 rounded-lg hover:bg-[#1F1F23] text-[#A1A1A8] transition-colors">
              <ChevronRight size={16} />
            </button>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5">
              <Users size={13} className="text-[#A1A1A8]/50" />
              <span className="text-[12px] font-mono text-[#A1A1A8]">{staffScheduled}/{staff.length} staff</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock size={13} className="text-[#A1A1A8]/50" />
              <span className="text-[12px] font-mono text-[#A1A1A8]">{totalHours}h</span>
            </div>
            <div className="flex items-center gap-1.5">
              <DollarSign size={13} className="text-[#A1A1A8]/50" />
              <span className="text-[12px] font-mono text-[#A1A1A8]">{totalLaborCents > 0 ? formatCents(totalLaborCents) : '--'}</span>
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* Generating state */}
      {isGenerating && (
        <div className="flex items-center justify-center gap-3 py-8">
          <span className="relative flex items-center justify-center">
            <span className="absolute h-8 w-8 rounded-full bg-[#17C5B0]/20 animate-ping" />
            <Sparkles size={20} className="text-[#17C5B0] animate-pulse relative" />
          </span>
          <span className="text-sm text-[#A1A1A8]">Analyzing peak hours and staff availability…</span>
        </div>
      )}

      {/* Desktop grid */}
      {!isGenerating && (
        <ScrollReveal variant="fadeUp" delay={0.05}>
          <div className="hidden lg:block overflow-x-auto">
            <WeeklyCalendarGrid
              shifts={shifts} staff={staff} peakHours={peakHours}
              holidays={holidays} onShiftClick={handleShiftClick}
              onSlotClick={handleSlotClick} onShiftMove={handleShiftMove}
              weekStartDate={weekStartDate} businessType={businessType}
            />
          </div>
        </ScrollReveal>
      )}

      {/* Mobile day view */}
      {!isGenerating && (
        <MobileDayView
          shifts={shifts} staff={staff} holidays={holidays}
          weekStartDate={weekStartDate}
          onShiftClick={handleShiftClick} onSlotClick={handleSlotClick}
        />
      )}

      <AddStaffModal open={showAddStaff} onClose={() => setShowAddStaff(false)}
        onSave={handleAddStaff} businessType={businessType} />
      <ShiftEditPopover shift={selectedShift} staff={staff} onClose={() => setSelectedShift(null)}
        onSave={handleShiftSave} onDelete={handleShiftDelete} />
    </div>
  )
}
