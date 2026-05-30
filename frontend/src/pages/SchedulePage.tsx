import { useState, useMemo, useCallback, useEffect } from 'react'
import { Calendar, Send, Sparkles, FileDown, ChevronLeft, ChevronRight, Plus, Clock, DollarSign, Users, X, Copy, Percent } from 'lucide-react'
import {
  generateScheduleStaff, generateScheduleShifts,
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
import MobileDayView from '@/components/schedule/MobileDayView'
import RecommendationsPanel from '@/components/schedule/RecommendationsPanel'
import { ROLE_GROUPS, getLaborTarget, laborPctTone } from '@/components/schedule/schedule-helpers'
import { api } from '@/lib/api'
import {
  isUuid, shiftFromApi, shiftToApiCreate, shiftToApiUpdate,
  staffFromApi, staffToApiCreate,
} from '@/lib/schedule-api'

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
  const demand = new Map<string, number>()
  for (const c of peaks) {
    const r = c.intensity / maxI
    const need = r > 0.75 ? 3 : r > 0.5 ? 2 : r > 0.25 ? 1 : 0
    if (need > 0) demand.set(`${c.day}-${c.hour}`, need)
  }
  // Track minutes already assigned per staff member during this generation.
  const minutesAssigned = new Map<string, number>()
  staff.forEach(s => minutesAssigned.set(s.id, 0))
  const asgn = new Map<string, Map<number, Set<number>>>()
  staff.forEach(s => asgn.set(s.id, new Map()))
  const slots = [...demand.entries()]
    .map(([k, need]) => {
      const [d, h] = k.split('-').map(Number)
      return { day: d, hour: h, need, intensity: peaks.find(p => p.day === d && p.hour === h)?.intensity ?? 0 }
    })
    .sort((a, b) => b.intensity - a.intensity)
  const OVERTIME_THRESHOLD_MIN = 40 * 60
  for (const slot of slots) {
    // Sort candidates by (least-loaded first, then cheapest). This
    // distributes hours evenly AND prefers cheaper labor for equivalent staff.
    const candidates = [...staff].sort((a, b) => {
      const ma = minutesAssigned.get(a.id) ?? 0
      const mb = minutesAssigned.get(b.id) ?? 0
      if (ma !== mb) return ma - mb
      return a.hourlyRate - b.hourlyRate
    })
    let filled = 0
    for (const m of candidates) {
      if (filled >= slot.need) break
      const av = m.availability[DAY_KEYS[slot.day]]
      if (!av?.available || slot.hour < parseInt(av.start) || slot.hour >= parseInt(av.end)) continue
      const dm = asgn.get(m.id)!
      // Skip if already assigned this exact hour on this day.
      if (dm.get(slot.day)?.has(slot.hour)) continue
      // Overtime guard: skip if adding this hour would push past 40h/week,
      // UNLESS no cheaper candidate is available later in this loop.
      const currentMins = minutesAssigned.get(m.id) ?? 0
      if (currentMins + 60 > OVERTIME_THRESHOLD_MIN) {
        const cheaperAvailable = candidates.some(other => {
          if (other.id === m.id) return false
          if (other.hourlyRate >= m.hourlyRate) return false
          const otherMins = minutesAssigned.get(other.id) ?? 0
          if (otherMins + 60 > OVERTIME_THRESHOLD_MIN) return false
          const oav = other.availability[DAY_KEYS[slot.day]]
          if (!oav?.available || slot.hour < parseInt(oav.start) || slot.hour >= parseInt(oav.end)) return false
          const odm = asgn.get(other.id)!
          if (odm.get(slot.day)?.has(slot.hour)) return false
          return true
        })
        if (cheaperAvailable) continue
      }
      if (!dm.has(slot.day)) dm.set(slot.day, new Set())
      dm.get(slot.day)!.add(slot.hour)
      minutesAssigned.set(m.id, currentMins + 60)
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

/** Role filter pills for 7shifts-style filtering */
const FILTER_OPTIONS = [
  { key: 'all', label: 'All Roles' },
  ...ROLE_GROUPS.map(g => ({ key: g.key, label: g.label, color: g.color })),
]

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
  const [roleFilter, setRoleFilter] = useState('all')
  const showDemoSchedule = isDemo || isCanadaPath()

  const [staff, setStaff] = useState<ScheduleStaffMember[]>(() =>
    showDemoSchedule ? generateScheduleStaff() : [])
  const [shifts, setShifts] = useState<ScheduleShift[]>(() =>
    showDemoSchedule ? generateScheduleShifts(weekStartDate) : [])
  const [livePeakHours, setLivePeakHours] = useState<{ day: number; hour: number; intensity: number }[] | null>(null)
  const [projectedRevenueCents, setProjectedRevenueCents] = useState<number | null>(null)

  // Backend wiring: real org_id must be a UUID (backend validation).
  const merchantId = org?.org_id ?? ''
  const liveMode = !showDemoSchedule && isUuid(merchantId)

  // Load staff + peak hours once per merchant.
  useEffect(() => {
    if (!liveMode) return
    let cancelled = false
    api.scheduleStaff(merchantId)
      .then(res => { if (!cancelled) setStaff(res.staff.map(staffFromApi)) })
      .catch(e => console.warn('scheduleStaff load failed:', e))
    api.schedulePeakHours(merchantId, 8)
      .then(res => {
        if (cancelled) return
        // Only override the synthetic heatmap if the real one has signal.
        setLivePeakHours(res.peaks.length > 0
          ? res.peaks.map(p => ({ day: p.day, hour: p.hour, intensity: p.intensity }))
          : null)
      })
      .catch(e => console.warn('schedulePeakHours load failed:', e))
    api.scheduleProjectedRevenue(merchantId, 8)
      .then(res => { if (!cancelled) setProjectedRevenueCents(res.projected_weekly_cents) })
      .catch(e => console.warn('scheduleProjectedRevenue load failed:', e))
    return () => { cancelled = true }
  }, [liveMode, merchantId])

  // Load shifts when week changes.
  useEffect(() => {
    if (!liveMode) return
    let cancelled = false
    const ws = formatDateISO(weekStartDate)
    api.scheduleShifts(merchantId, ws)
      .then(res => {
        if (cancelled) return
        setShifts(res.shifts.map(shiftFromApi))
        setIsPublished(res.shifts.length > 0 && res.shifts.every(s => s.status === 'published'))
      })
      .catch(e => console.warn('scheduleShifts load failed:', e))
    return () => { cancelled = true }
  }, [liveMode, merchantId, weekStartDate])
  const peakHours = useMemo(
    () => livePeakHours ?? generatePeakHourHeatmap(),
    [livePeakHours],
  )
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

  // Labor cost as % of projected weekly revenue.
  // Live: pulled from /api/schedule/projected-revenue.
  // Demo: typical weekly revenue by business type so the % feels real.
  // Calibrated to land mid-band given the schedule generator's actual labor cost
  // per business type. Without this calibration the demo restaurant showed 19.7%
  // (understaffed amber) instead of the realistic 28-32% green band.
  const DEMO_WEEKLY_REVENUE_CENTS: Record<string, number> = {
    coffee_shop: 31_000_00,
    restaurant:  23_000_00,
    fast_food:   22_000_00,
    auto_shop:   22_000_00,
    smoke_shop:  40_000_00,
  }
  const effectiveRevenueCents =
    projectedRevenueCents ?? DEMO_WEEKLY_REVENUE_CENTS[businessType] ?? 0
  const laborPct = effectiveRevenueCents > 0
    ? (totalLaborCents / effectiveRevenueCents) * 100
    : null
  const laborTarget = useMemo(() => getLaborTarget(businessType), [businessType])
  const laborTone = laborPct !== null
    ? laborPctTone(laborPct, laborTarget.targetPct, laborTarget.warningPct, laborTarget.floorPct)
    : null

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

  const handleCopyPrevWeek = useCallback(async () => {
    const prevWeekStart = addWeeks(weekStartDate, -1)
    let sourceShifts: ScheduleShift[]
    if (liveMode) {
      try {
        const res = await api.scheduleShifts(merchantId, formatDateISO(prevWeekStart))
        sourceShifts = res.shifts.map(shiftFromApi)
      } catch (e) {
        console.warn('copy: load previous week failed:', e)
        showToast('Could not load previous week')
        return
      }
    } else {
      sourceShifts = showDemoSchedule
        ? generateScheduleShifts(prevWeekStart)
        : shifts
    }
    const copied = sourceShifts
      .filter(s => !s.isRecommended)
      .map((s, i) => ({
        ...s,
        id: `shift-copy-${Date.now()}-${i}`,
        shiftDate: formatDateISO(addDays(weekStartDate, s.dayOfWeek)),
        status: 'draft' as const,
      }))
    setShifts(copied)
    setIsPublished(false)
    if (liveMode) {
      const portal = portalContext as 'us' | 'ca'
      const ws = formatDateISO(weekStartDate)
      try {
        const results = await Promise.all(copied.map(s =>
          api.scheduleCreateShift(shiftToApiCreate(s, merchantId, portal, ws))
        ))
        setShifts(results.map(r => shiftFromApi(r.shift)))
        showToast(`Copied ${results.length} shifts from previous week`)
      } catch (e) {
        console.warn('copy: persist failed:', e)
        // Refresh from server to get whatever did persist.
        const refresh = await api.scheduleShifts(merchantId, ws).catch(() => null)
        if (refresh) setShifts(refresh.shifts.map(shiftFromApi))
        showToast('Some shifts failed to save — refreshed from server')
      }
    } else {
      showToast(`Copied ${copied.length} shifts from previous week`)
    }
  }, [liveMode, merchantId, portalContext, weekStartDate, showDemoSchedule, shifts, showToast])

  const handleAddStaff = useCallback(async (m: Omit<ScheduleStaffMember, 'id'>) => {
    const optimistic: ScheduleStaffMember = { ...m, id: `staff-${Date.now()}` }
    setStaff(prev => [...prev, optimistic])
    if (!liveMode) return
    try {
      const portal = portalContext as 'us' | 'ca'
      const res = await api.scheduleCreateStaff(staffToApiCreate(m, merchantId, portal))
      setStaff(prev => prev.map(s => s.id === optimistic.id ? staffFromApi(res.staff_member) : s))
    } catch (e) {
      console.warn('createStaff failed:', e)
      setStaff(prev => prev.filter(s => s.id !== optimistic.id))
      showToast('Could not save staff member — check your connection')
    }
  }, [liveMode, merchantId, portalContext, showToast])

  const handleShiftClick = useCallback((s: ScheduleShift) => setSelectedShift(s), [])

  const handleAcceptRecommendation = useCallback(async (rec: {
    dayOfWeek: number; startTime: string; endTime: string; role: string
  }) => {
    const d = addDays(weekStartDate, rec.dayOfWeek)
    const tempId = `shift-rec-${Date.now()}`
    const ns: ScheduleShift = {
      id: tempId, staffMemberId: null, dayOfWeek: rec.dayOfWeek,
      shiftDate: formatDateISO(d), startTime: rec.startTime,
      endTime: rec.endTime, role: rec.role,
      breakMinutes: 0, notes: 'Added from AI recommendation',
      status: 'draft', isRecommended: false,
    }
    setShifts(prev => [...prev, ns])
    setIsPublished(false)
    showToast('Recommendation added — assign a staff member')
    if (!liveMode) return
    try {
      const portal = portalContext as 'us' | 'ca'
      const res = await api.scheduleCreateShift(
        shiftToApiCreate(ns, merchantId, portal, formatDateISO(weekStartDate)),
      )
      const saved = shiftFromApi(res.shift)
      setShifts(prev => prev.map(s => (s.id === tempId ? saved : s)))
    } catch (e) {
      console.warn('accept recommendation persist failed:', e)
      setShifts(prev => prev.filter(s => s.id !== tempId))
      showToast('Could not save recommendation')
    }
  }, [liveMode, merchantId, portalContext, weekStartDate, showToast])

  const handleSlotClick = useCallback(async (day: number, hour: number) => {
    const d = addDays(weekStartDate, day)
    const tempId = `shift-new-${Date.now()}`
    const ns: ScheduleShift = {
      id: tempId, staffMemberId: null, dayOfWeek: day,
      shiftDate: formatDateISO(d), startTime: `${pad2(hour)}:00`,
      endTime: `${pad2(Math.min(hour + 4, 23))}:00`, role: 'any',
      breakMinutes: 0, notes: '', status: 'draft', isRecommended: false,
    }
    setShifts(prev => [...prev, ns]); setSelectedShift(ns)
    if (!liveMode) return
    try {
      const portal = portalContext as 'us' | 'ca'
      const res = await api.scheduleCreateShift(
        shiftToApiCreate(ns, merchantId, portal, formatDateISO(weekStartDate)),
      )
      const saved = shiftFromApi(res.shift)
      setShifts(prev => prev.map(s => (s.id === tempId ? saved : s)))
      setSelectedShift(prev => (prev?.id === tempId ? saved : prev))
    } catch (e) {
      console.warn('createShift failed:', e)
      setShifts(prev => prev.filter(s => s.id !== tempId))
      setSelectedShift(prev => (prev?.id === tempId ? null : prev))
      showToast('Could not create shift')
    }
  }, [liveMode, merchantId, portalContext, weekStartDate, showToast])

  const handleShiftSave = useCallback(async (u: ScheduleShift) => {
    const prevShift = shifts.find(s => s.id === u.id)
    setShifts(prev => prev.map(s => (s.id === u.id ? u : s)))
    if (!liveMode || !isUuid(u.id)) return
    try {
      await api.scheduleUpdateShift(u.id, shiftToApiUpdate(u))
    } catch (e) {
      console.warn('updateShift failed:', e)
      if (prevShift) setShifts(prev => prev.map(s => (s.id === u.id ? prevShift : s)))
      showToast('Could not save shift changes')
    }
  }, [liveMode, shifts, showToast])

  const handleShiftDelete = useCallback(async (id: string) => {
    const prevShift = shifts.find(s => s.id === id)
    setShifts(prev => prev.filter(s => s.id !== id))
    if (!liveMode || !isUuid(id)) return
    try {
      await api.scheduleDeleteShift(id)
    } catch (e) {
      console.warn('deleteShift failed:', e)
      if (prevShift) setShifts(prev => [...prev, prevShift])
      showToast('Could not delete shift')
    }
  }, [liveMode, shifts, showToast])

  const handleSplitShift = useCallback((original: ScheduleShift, firstEnd: string, secondStart: string) => {
    const first: ScheduleShift = {
      ...original,
      endTime: firstEnd,
      breakMinutes: 0,
    }
    const second: ScheduleShift = {
      ...original,
      id: `shift-split-${Date.now()}`,
      startTime: secondStart,
      breakMinutes: 0,
    }
    setShifts(prev => prev.map(s => (s.id === original.id ? first : s)).concat(second))
    showToast('Shift split into two parts')
  }, [showToast])

  const handleShiftMove = useCallback(async (shiftId: string, newDay: number, newStartHour: number) => {
    const prevShifts = shifts
    let moved: ScheduleShift | null = null
    setShifts(prev => prev.map(s => {
      if (s.id !== shiftId) return s
      const dur = parseInt(s.endTime) - parseInt(s.startTime)
      const eH = Math.min(newStartHour + dur, 23)
      const next = { ...s, dayOfWeek: newDay, shiftDate: formatDateISO(addDays(weekStartDate, newDay)),
        startTime: `${pad2(newStartHour)}:00`, endTime: `${pad2(eH)}:00` }
      moved = next
      return next
    }))
    if (!liveMode || !isUuid(shiftId) || !moved) return
    try {
      // dayOfWeek + shiftDate aren't in our PUT schema; emulate via delete+create.
      const portal = portalContext as 'us' | 'ca'
      const created = await api.scheduleCreateShift(
        shiftToApiCreate(moved, merchantId, portal, formatDateISO(weekStartDate)),
      )
      await api.scheduleDeleteShift(shiftId).catch(() => {})
      setShifts(prev => prev.map(s => (s.id === shiftId ? shiftFromApi(created.shift) : s)))
    } catch (e) {
      console.warn('moveShift failed:', e)
      setShifts(prevShifts)
      showToast('Could not move shift')
    }
  }, [liveMode, merchantId, portalContext, weekStartDate, shifts, showToast])

  const handleGenerate = useCallback(async () => {
    setIsGenerating(true)
    const opt = buildOptimalSchedule(staff, peakHours, weekStartDate)
    if (!liveMode) {
      // Demo: cosmetic delay + local set.
      await new Promise(r => setTimeout(r, 1200))
      setShifts(opt); setIsPublished(false); setIsGenerating(false)
      const used = new Set(opt.map(s => s.staffMemberId).filter(Boolean)).size
      showToast(`Schedule generated — ${opt.length} shifts across ${used} staff`)
      return
    }
    // Live: wipe this week's draft shifts, then bulk-create the optimal set.
    const portal = portalContext as 'us' | 'ca'
    const ws = formatDateISO(weekStartDate)
    setShifts(opt); setIsPublished(false)
    try {
      // Drop existing draft shifts for this week.
      await Promise.all(shifts
        .filter(s => isUuid(s.id) && s.status === 'draft')
        .map(s => api.scheduleDeleteShift(s.id).catch(() => {})))
      const results = await Promise.all(opt.map(s =>
        api.scheduleCreateShift(shiftToApiCreate(s, merchantId, portal, ws))
      ))
      const saved = results.map(r => shiftFromApi(r.shift))
      setShifts(saved)
      const used = new Set(saved.map(s => s.staffMemberId).filter(Boolean)).size
      showToast(`Schedule generated — ${saved.length} shifts across ${used} staff`)
    } catch (e) {
      console.warn('generate persist failed:', e)
      const refresh = await api.scheduleShifts(merchantId, ws).catch(() => null)
      if (refresh) setShifts(refresh.shifts.map(shiftFromApi))
      showToast('Some shifts failed to save — refreshed from server')
    } finally {
      setIsGenerating(false)
    }
  }, [liveMode, merchantId, portalContext, staff, peakHours, weekStartDate, shifts, showToast])

  const handlePublish = useCallback(async () => {
    setIsPublished(true)
    setShifts(prev => prev.map(s => ({ ...s, status: 'published' as const })))
    if (!liveMode) {
      showToast(`Schedule published — ${staffScheduled} staff notified`)
      return
    }
    try {
      const portal = portalContext as 'us' | 'ca'
      const res = await api.schedulePublish({
        merchant_id: merchantId,
        portal_context: portal,
        week_start_date: formatDateISO(weekStartDate),
        published_by: org?.business_name || '',
        notify_staff: true,
      })
      showToast(`Schedule published — ${res.notified_count} staff notified`)
    } catch (e) {
      console.warn('publish failed:', e)
      setIsPublished(false)
      showToast('Publish failed — please try again')
    }
  }, [liveMode, merchantId, portalContext, weekStartDate, org, staffScheduled, showToast])

  const handleDownloadPdf = useCallback(async () => {
    const { generateSchedulePdf } = await import('@/lib/generate-schedule-pdf')
    const blob = await generateSchedulePdf({ shifts, staff, weekStartDate, businessName: org?.business_name })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url
    a.download = `schedule-${formatDateISO(weekStartDate)}.pdf`; a.click()
    URL.revokeObjectURL(url)
  }, [shifts, staff, weekStartDate])

  if (!showDemoSchedule && !liveMode) {
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
              aria-label="Add staff member"
              title="Add staff"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors">
              <Plus size={13} /><span className="hidden sm:inline">Staff</span>
            </button>
            <button onClick={handleCopyPrevWeek}
              aria-label="Copy shifts from previous week"
              className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-xs text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
              title="Copy shifts from previous week">
              <Copy size={13} /><span className="hidden sm:inline">Copy Week</span>
            </button>
            <button onClick={handleGenerate} disabled={isGenerating || staff.length === 0}
              aria-label={isGenerating ? 'Generating schedule' : 'Generate schedule'}
              title={isGenerating ? 'Generating...' : 'Generate'}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-white shadow-lg shadow-[#17C5B0]/20 hover:shadow-[#17C5B0]/30 hover:brightness-110 disabled:opacity-40">
              <Sparkles size={14} className={isGenerating ? 'animate-spin' : ''} />
              <span className="hidden sm:inline">{isGenerating ? 'Generating...' : 'Generate'}</span>
            </button>
            <button onClick={handlePublish}
              disabled={realShifts.length === 0 || isPublished}
              aria-label={isPublished ? 'Schedule published' : 'Publish schedule'}
              title={isPublished ? 'Published' : 'Publish'}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all ${isPublished
                ? 'bg-[#17C5B0]/10 text-[#17C5B0] border border-[#17C5B0]/20'
                : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90 disabled:opacity-30'}`}>
              <Send size={13} /><span className="hidden sm:inline">{isPublished ? 'Published' : 'Publish'}</span>
            </button>
            <button onClick={handleDownloadPdf}
              aria-label="Download schedule as PDF"
              title="Download PDF"
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
            {laborPct !== null && totalLaborCents > 0 && (
              <div
                className="flex items-center gap-1.5 px-2 py-0.5 rounded-full border"
                style={{
                  borderColor: laborTone ? `${laborTone.fg}40` : '#1F1F23',
                  backgroundColor: laborTone ? `${laborTone.bg}15` : 'transparent',
                }}
                title={`Labor cost vs ${(effectiveRevenueCents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })} projected weekly revenue. Floor ${laborTarget.floorPct}% • Target ${laborTarget.targetPct}% • Warn ${laborTarget.warningPct}%.`}
              >
                <Percent size={11} style={{ color: laborTone?.fg }} />
                <span className="text-[12px] font-mono font-semibold" style={{ color: laborTone?.fg }}>
                  {laborPct.toFixed(1)}%
                </span>
              </div>
            )}
          </div>
        </div>
      </ScrollReveal>

      {/* Role filter bar */}
      <ScrollReveal variant="fadeUp" delay={0.04}>
        <div
          className="flex items-center gap-1.5 px-1 pr-6 overflow-x-auto pb-1"
          style={{
            maskImage: 'linear-gradient(to right, black calc(100% - 24px), transparent 100%)',
            WebkitMaskImage: 'linear-gradient(to right, black calc(100% - 24px), transparent 100%)',
          }}
        >
          {FILTER_OPTIONS.map(opt => {
            const isActive = roleFilter === opt.key
            const color = 'color' in opt ? opt.color : undefined
            return (
              <button
                key={opt.key}
                onClick={() => setRoleFilter(opt.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[11px] font-medium whitespace-nowrap transition-all ${
                  isActive
                    ? 'bg-[#1A8FD6]/15 text-[#1A8FD6] border border-[#1A8FD6]/30'
                    : 'text-[#A1A1A8]/60 border border-[#1F1F23] hover:text-[#A1A1A8] hover:bg-[#1F1F23]/50'
                }`}
              >
                {color && <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />}
                {opt.label}
              </button>
            )
          })}
        </div>
      </ScrollReveal>

      {/* Generating state */}
      {isGenerating && (
        <div className="flex items-center justify-center gap-3 py-8">
          <span className="relative flex items-center justify-center">
            <span className="absolute h-8 w-8 rounded-full bg-[#17C5B0]/20 animate-ping" />
            <Sparkles size={20} className="text-[#17C5B0] animate-pulse relative" />
          </span>
          <span className="text-sm text-[#A1A1A8]">Analyzing peak hours and staff availability...</span>
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
              roleFilter={roleFilter}
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

      {/* AI Recommendations — surfaces uncovered peak windows */}
      {!isGenerating && (
        <ScrollReveal variant="fadeUp" delay={0.06}>
          <RecommendationsPanel
            merchantId={merchantId}
            weekStart={formatDateISO(weekStartDate)}
            liveMode={liveMode}
            peakHoursFallback={peakHours}
            currentShifts={shifts}
            onAccept={handleAcceptRecommendation}
          />
        </ScrollReveal>
      )}

      <AddStaffModal open={showAddStaff} onClose={() => setShowAddStaff(false)}
        onSave={handleAddStaff} businessType={businessType} />
      <ShiftEditPopover shift={selectedShift} staff={staff} onClose={() => setSelectedShift(null)}
        onSave={handleShiftSave} onDelete={handleShiftDelete} onSplitShift={handleSplitShift} />
    </div>
  )
}
