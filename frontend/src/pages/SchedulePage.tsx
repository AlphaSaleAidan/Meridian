import { useState, useMemo, useCallback } from 'react'
import { Calendar, Send, Sparkles, FileDown, X } from 'lucide-react'
import {
  generateScheduleStaff, generateScheduleShifts, generateRecommendedShifts,
  generatePeakHourHeatmap, getHolidaysForWeek,
  type ScheduleShift, type ScheduleStaffMember,
} from '@/lib/agent-data'
import { getActiveBusinessType, isCanadaPath } from '@/lib/demo-context'
import ScrollReveal from '@/components/ScrollReveal'
import AnalyzingDataState from '@/components/AnalyzingDataState'
import { useIsDemo } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'
import WeeklyCalendarGrid from '@/components/schedule/WeeklyCalendarGrid'
import MobileAgendaView from '@/components/schedule/MobileAgendaView'
import StaffRosterPanel from '@/components/schedule/StaffRosterPanel'
import WeekSummaryPanel from '@/components/schedule/WeekSummaryPanel'
import AddStaffModal from '@/components/schedule/AddStaffModal'
import ShiftEditPopover from '@/components/schedule/ShiftEditPopover'

/* ── helpers ──────────────────────────────────────────── */
function getMonday(d: Date): Date {
  const dt = new Date(d), day = dt.getDay()
  dt.setDate(dt.getDate() + (day === 0 ? -6 : 1 - day))
  dt.setHours(0, 0, 0, 0)
  return dt
}
function addWeeks(d: Date, w: number) { const r = new Date(d); r.setDate(r.getDate() + w * 7); return r }
function pad2(n: number) { return n < 10 ? `0${n}` : `${n}` }
function formatDateISO(d: Date) { return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}` }
function addDays(d: Date, n: number) { const r = new Date(d); r.setDate(r.getDate() + n); return r }

const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

/* ── optimal schedule builder ─────────────────────────── */
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

/* ── component ────────────────────────────────────────── */
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
  const recommendations = useMemo(
    () => (showDemoSchedule ? generateRecommendedShifts(weekStartDate) : []),
    [showDemoSchedule, weekStartDate])
  const peakHours = useMemo(() => generatePeakHourHeatmap(), [])
  const holidays = useMemo(
    () => getHolidaysForWeek(weekStartDate, country as 'US' | 'CA'),
    [weekStartDate, country])
  const allShifts = useMemo(
    () => [...shifts, ...recommendations.filter(r => !shifts.some(s => s.id === r.id))],
    [shifts, recommendations])
  const panelRecs = useMemo(() => recommendations.map(r => ({
    id: r.id, reason: r.recommendationReason || '',
    priority: r.priority || ('recommended' as const),
    dayOfWeek: r.dayOfWeek, startTime: r.startTime, endTime: r.endTime,
  })), [recommendations])

  const showToast = useCallback((msg: string) => {
    setToast(msg); setTimeout(() => setToast(null), 4000)
  }, [])

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
  const handleUpdateStaff = useCallback((id: string, u: Partial<ScheduleStaffMember>) => {
    setStaff(prev => prev.map(s => (s.id === id ? { ...s, ...u } : s)))
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

  const handleApplyRecommendation = useCallback(
    (rec: { id: string; dayOfWeek: number; startTime: string; endTime: string }) => {
      const found = recommendations.find(r => r.id === rec.id)
      if (found) setShifts(prev => [...prev, { ...found, id: `shift-rec-${Date.now()}`, isRecommended: false, status: 'draft' }])
    }, [recommendations])

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
      showToast(`Optimal schedule generated — ${opt.length} shifts across ${used} staff`)
    }, 1500)
  }, [staff, peakHours, weekStartDate, showToast])

  const handlePublish = useCallback(() => {
    setIsPublished(true)
    setShifts(prev => prev.map(s => ({ ...s, status: 'published' as const })))
    const cnt = new Set(shifts.filter(s => !s.isRecommended && s.staffMemberId).map(s => s.staffMemberId)).size
    showToast(`Schedule published — ${cnt} staff notified`)
  }, [shifts, showToast])

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
    <div className="space-y-5">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center">
              <Calendar size={20} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#F5F5F7]">Schedule</h1>
              <p className="text-sm text-[#A1A1A8] mt-0.5">AI-powered staff scheduling</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleGenerate} disabled={isGenerating}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-white shadow-lg shadow-[#17C5B0]/20 hover:shadow-[#17C5B0]/30 hover:brightness-110 disabled:opacity-60">
              <Sparkles size={14} className={isGenerating ? 'animate-spin' : ''} />
              {isGenerating ? 'Generating…' : 'Generate Optimal Schedule'}
            </button>
            <button onClick={handlePublish}
              disabled={shifts.filter(s => !s.isRecommended).length === 0 || isPublished}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${isPublished
                ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-30'}`}>
              <Send size={13} />{isPublished ? 'Published' : 'Publish'}
            </button>
            <button onClick={handleDownloadPdf}
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
              <FileDown size={13} />PDF
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

      {/* Generating animation */}
      {isGenerating && (
        <div className="flex items-center justify-center gap-3 py-6">
          <span className="relative flex items-center justify-center">
            <span className="absolute h-8 w-8 rounded-full bg-[#17C5B0]/20 animate-ping" />
            <Sparkles size={20} className="text-[#17C5B0] animate-pulse relative" />
          </span>
          <span className="text-sm text-[#A1A1A8]">Analyzing peak hours and staff availability...</span>
        </div>
      )}

      {/* 3-column layout */}
      {!isGenerating && (
        <ScrollReveal variant="fadeUp" delay={0.05}>
          <div className="flex flex-col lg:flex-row gap-4">
            <div className="hidden lg:block w-[240px] flex-shrink-0">
              <StaffRosterPanel staff={staff} onAddStaff={() => setShowAddStaff(true)}
                onUpdateStaff={handleUpdateStaff} recommendations={panelRecs}
                onApplyRecommendation={handleApplyRecommendation} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="hidden lg:block">
                <WeeklyCalendarGrid shifts={allShifts} staff={staff} peakHours={peakHours}
                  holidays={holidays} onShiftClick={handleShiftClick} onSlotClick={handleSlotClick}
                  onShiftMove={handleShiftMove} weekStartDate={weekStartDate} businessType={businessType} />
              </div>
              <div className="lg:hidden">
                <MobileAgendaView shifts={allShifts} staff={staff} holidays={holidays}
                  onShiftClick={handleShiftClick} onSlotClick={handleSlotClick} weekStartDate={weekStartDate} />
              </div>
            </div>
            <div className="w-full lg:w-[240px] flex-shrink-0">
              <WeekSummaryPanel shifts={shifts} staff={staff} holidays={holidays}
                weekStartDate={weekStartDate} peakHours={peakHours} onPublish={handlePublish}
                isPublished={isPublished} portalContext={portalContext as 'us' | 'ca'}
                onPrevWeek={handlePrevWeek} onNextWeek={handleNextWeek} onDownloadPdf={handleDownloadPdf} />
            </div>
            <div className="lg:hidden">
              <StaffRosterPanel staff={staff} onAddStaff={() => setShowAddStaff(true)}
                onUpdateStaff={handleUpdateStaff} recommendations={panelRecs}
                onApplyRecommendation={handleApplyRecommendation} />
            </div>
          </div>
        </ScrollReveal>
      )}

      <AddStaffModal open={showAddStaff} onClose={() => setShowAddStaff(false)}
        onSave={handleAddStaff} businessType={businessType} />
      <ShiftEditPopover shift={selectedShift} staff={staff} onClose={() => setSelectedShift(null)}
        onSave={handleShiftSave} onDelete={handleShiftDelete} />
    </div>
  )
}
