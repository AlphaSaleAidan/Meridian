import { useState, useMemo, useCallback } from 'react'
import { Calendar } from 'lucide-react'
import {
  generateScheduleStaff,
  generateScheduleShifts,
  generateRecommendedShifts,
  generatePeakHourHeatmap,
  getHolidaysForWeek,
  type ScheduleShift,
  type ScheduleStaffMember,
} from '@/lib/agent-data'
import { getActiveBusinessType, isCanadaPath } from '@/lib/demo-context'
import ScrollReveal from '@/components/ScrollReveal'
import AnalyzingDataState from '@/components/AnalyzingDataState'
import { useIsDemo } from '@/hooks/useOrg'
import WeeklyCalendarGrid from '@/components/schedule/WeeklyCalendarGrid'
import StaffRosterPanel from '@/components/schedule/StaffRosterPanel'
import WeekSummaryPanel from '@/components/schedule/WeekSummaryPanel'
import AddStaffModal from '@/components/schedule/AddStaffModal'
import ShiftEditPopover from '@/components/schedule/ShiftEditPopover'

/** Return the Monday of the week containing the given date. */
function getMonday(d: Date): Date {
  const date = new Date(d)
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  date.setHours(0, 0, 0, 0)
  return date
}

function addWeeks(d: Date, weeks: number): Date {
  const date = new Date(d)
  date.setDate(date.getDate() + weeks * 7)
  return date
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

function formatDateISO(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

export default function SchedulePage() {
  const isDemo = useIsDemo()
  const businessType = getActiveBusinessType()
  const portalContext = isCanadaPath() ? 'ca' : 'us'
  const country = portalContext === 'ca' ? 'CA' : 'US'

  const [weekStartDate, setWeekStartDate] = useState(() => getMonday(new Date()))
  const [showAddStaff, setShowAddStaff] = useState(false)
  const [selectedShift, setSelectedShift] = useState<ScheduleShift | null>(null)
  const [isPublished, setIsPublished] = useState(false)

  // Demo staff roster — mutable so user can add
  const [staff, setStaff] = useState<ScheduleStaffMember[]>(() =>
    isDemo ? generateScheduleStaff() : []
  )

  // Demo shifts — mutable so user can edit/add/delete
  const [shifts, setShifts] = useState<ScheduleShift[]>(() =>
    isDemo ? generateScheduleShifts(weekStartDate) : []
  )

  // Recommendations
  const recommendations = useMemo(() => {
    if (!isDemo) return []
    return generateRecommendedShifts(weekStartDate)
  }, [isDemo, weekStartDate])

  // Peak hours for calendar background
  const peakHours = useMemo(() => generatePeakHourHeatmap(), [])

  // Holidays for current week
  const holidays = useMemo(
    () => getHolidaysForWeek(weekStartDate, country as 'US' | 'CA'),
    [weekStartDate, country]
  )

  // All shifts including recommendations (for display)
  const allShifts = useMemo(() => {
    return [...shifts, ...recommendations.filter(r => !shifts.some(s => s.id === r.id))]
  }, [shifts, recommendations])

  // Recommendations mapped for the panel
  const panelRecommendations = useMemo(() => {
    return recommendations.map(r => ({
      id: r.id,
      reason: r.recommendationReason || '',
      priority: r.priority || ('recommended' as const),
      dayOfWeek: r.dayOfWeek,
      startTime: r.startTime,
      endTime: r.endTime,
    }))
  }, [recommendations])

  const handlePrevWeek = useCallback(() => {
    const prev = addWeeks(weekStartDate, -1)
    setWeekStartDate(prev)
    setIsPublished(false)
    if (isDemo) setShifts(generateScheduleShifts(prev))
  }, [weekStartDate, isDemo])

  const handleNextWeek = useCallback(() => {
    const next = addWeeks(weekStartDate, 1)
    setWeekStartDate(next)
    setIsPublished(false)
    if (isDemo) setShifts(generateScheduleShifts(next))
  }, [weekStartDate, isDemo])

  const handleAddStaff = useCallback((member: Omit<ScheduleStaffMember, 'id'>) => {
    const newMember: ScheduleStaffMember = {
      ...member,
      id: `staff-${Date.now()}`,
    }
    setStaff(prev => [...prev, newMember])
  }, [])

  const handleShiftClick = useCallback((shift: ScheduleShift) => {
    setSelectedShift(shift)
  }, [])

  const handleSlotClick = useCallback((day: number, hour: number) => {
    const shiftDate = addDays(weekStartDate, day)
    const newShift: ScheduleShift = {
      id: `shift-new-${Date.now()}`,
      staffMemberId: null,
      dayOfWeek: day,
      shiftDate: formatDateISO(shiftDate),
      startTime: `${pad2(hour)}:00`,
      endTime: `${pad2(Math.min(hour + 4, 23))}:00`,
      role: 'any',
      breakMinutes: 0,
      notes: '',
      status: 'draft',
      isRecommended: false,
    }
    setShifts(prev => [...prev, newShift])
    setSelectedShift(newShift)
  }, [weekStartDate])

  const handleShiftSave = useCallback((updated: ScheduleShift) => {
    setShifts(prev => prev.map(s => s.id === updated.id ? updated : s))
  }, [])

  const handleShiftDelete = useCallback((shiftId: string) => {
    setShifts(prev => prev.filter(s => s.id !== shiftId))
  }, [])

  const handleApplyRecommendation = useCallback((rec: { id: string; dayOfWeek: number; startTime: string; endTime: string }) => {
    const recShift = recommendations.find(r => r.id === rec.id)
    if (!recShift) return
    const newShift: ScheduleShift = {
      ...recShift,
      id: `shift-rec-${Date.now()}`,
      isRecommended: false,
      status: 'draft',
    }
    setShifts(prev => [...prev, newShift])
  }, [recommendations])

  const handlePublish = useCallback(() => {
    setIsPublished(true)
    setShifts(prev => prev.map(s => ({ ...s, status: 'published' as const })))
  }, [])

  // Non-demo: show analyzing state
  if (!isDemo) {
    return (
      <div className="space-y-6">
        <ScrollReveal variant="fadeUp">
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Schedule</h1>
            <p className="text-sm text-[#A1A1A8] mt-1">
              AI-powered staff scheduling with peak hour optimization
            </p>
          </div>
        </ScrollReveal>
        <AnalyzingDataState
          title="Setting up your schedule"
          description="Connect your POS to import staff data and generate AI-optimized schedules based on your transaction patterns."
        />
      </div>
    )
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <ScrollReveal variant="fadeUp">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center">
            <Calendar size={20} className="text-[#1A8FD6]" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-[#F5F5F7]">Schedule</h1>
            <p className="text-sm text-[#A1A1A8] mt-0.5">
              AI-powered staff scheduling with peak hour optimization
            </p>
          </div>
        </div>
      </ScrollReveal>

      {/* 3-column layout */}
      <ScrollReveal variant="fadeUp" delay={0.05}>
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Left: Staff roster — hidden on mobile, shown as row below on small */}
          <div className="hidden lg:block w-[260px] flex-shrink-0">
            <StaffRosterPanel
              staff={staff}
              onAddStaff={() => setShowAddStaff(true)}
              recommendations={panelRecommendations}
              onApplyRecommendation={handleApplyRecommendation}
            />
          </div>

          {/* Center: Calendar grid */}
          <div className="flex-1 min-w-0">
            <WeeklyCalendarGrid
              shifts={allShifts}
              staff={staff}
              peakHours={peakHours}
              holidays={holidays}
              onShiftClick={handleShiftClick}
              onSlotClick={handleSlotClick}
              weekStartDate={weekStartDate}
              businessType={businessType}
            />
          </div>

          {/* Right: Summary panel */}
          <div className="w-full lg:w-[260px] flex-shrink-0">
            <WeekSummaryPanel
              shifts={shifts}
              staff={staff}
              holidays={holidays}
              weekStartDate={weekStartDate}
              peakHours={peakHours}
              onPublish={handlePublish}
              isPublished={isPublished}
              portalContext={portalContext as 'us' | 'ca'}
              onPrevWeek={handlePrevWeek}
              onNextWeek={handleNextWeek}
            />
          </div>

          {/* Mobile: Staff roster below */}
          <div className="lg:hidden">
            <StaffRosterPanel
              staff={staff}
              onAddStaff={() => setShowAddStaff(true)}
              recommendations={panelRecommendations}
              onApplyRecommendation={handleApplyRecommendation}
            />
          </div>
        </div>
      </ScrollReveal>

      {/* Modals */}
      <AddStaffModal
        open={showAddStaff}
        onClose={() => setShowAddStaff(false)}
        onSave={handleAddStaff}
        businessType={businessType}
      />

      <ShiftEditPopover
        shift={selectedShift}
        staff={staff}
        onClose={() => setSelectedShift(null)}
        onSave={handleShiftSave}
        onDelete={handleShiftDelete}
      />
    </div>
  )
}
