import type { ScheduleStaffMember, ScheduleShift } from '@/lib/agent-data'

/** Role group definitions with display names and colors */
export const ROLE_GROUPS: { key: string; label: string; color: string; roles: string[] }[] = [
  { key: 'management', label: 'Management', color: '#17C5B0', roles: ['manager', 'supervisor', 'shift_lead'] },
  { key: 'kitchen', label: 'Kitchen', color: '#FF7043', roles: ['kitchen', 'runner'] },
  { key: 'foh', label: 'Front of House', color: '#1A8FD6', roles: ['server', 'host', 'cashier', 'counter', 'associate', 'advisor', 'parts_counter'] },
  { key: 'bar', label: 'Bar', color: '#9B7FD4', roles: ['bartender', 'barista', 'bar_lead'] },
  { key: 'other', label: 'Other', color: '#78909C', roles: ['drive_through', 'technician', 'any'] },
]

export const DAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'] as const

/** Determine which group a role belongs to */
export function getRoleGroup(role: string): typeof ROLE_GROUPS[number] {
  return ROLE_GROUPS.find(g => g.roles.includes(role)) || ROLE_GROUPS[ROLE_GROUPS.length - 1]
}

/** Get the color for a role group */
export function getRoleColor(role: string): string {
  return getRoleGroup(role).color
}

/** Group staff by role group, sorted by group order */
export function groupStaffByRole(
  staff: ScheduleStaffMember[],
  filterRole?: string,
): { group: typeof ROLE_GROUPS[number]; members: ScheduleStaffMember[] }[] {
  const result: { group: typeof ROLE_GROUPS[number]; members: ScheduleStaffMember[] }[] = []
  for (const group of ROLE_GROUPS) {
    const members = staff.filter(s => {
      const inGroup = group.roles.includes(s.role)
      if (filterRole && filterRole !== 'all') {
        return inGroup && group.key === filterRole
      }
      return inGroup
    })
    if (members.length > 0) {
      result.push({ group, members })
    }
  }
  // Catch ungrouped staff
  const allGroupedIds = new Set(result.flatMap(r => r.members.map(m => m.id)))
  const ungrouped = staff.filter(s => !allGroupedIds.has(s.id))
  if (ungrouped.length > 0) {
    const otherGroup = ROLE_GROUPS[ROLE_GROUPS.length - 1]
    const existing = result.find(r => r.group.key === otherGroup.key)
    if (existing) {
      existing.members.push(...ungrouped)
    } else {
      result.push({ group: otherGroup, members: ungrouped })
    }
  }
  return result
}

/** Calculate weekly hours for a staff member */
export function getStaffWeeklyHours(staffId: string, shifts: ScheduleShift[]): number {
  const mins = shifts
    .filter(s => s.staffMemberId === staffId && !s.isRecommended)
    .reduce((sum, s) => {
      const dur = timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes
      return sum + Math.max(0, dur)
    }, 0)
  return mins / 60
}

/** Check if staff is available on a given day */
export function isStaffAvailable(member: ScheduleStaffMember, dayIndex: number): boolean {
  const dayKey = DAY_KEYS[dayIndex]
  const av = member.availability[dayKey]
  return av?.available ?? false
}

export function timeToMinutes(t: string): number {
  const [h, m] = t.split(':').map(Number)
  return h * 60 + (m || 0)
}

export function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

export function addDays(d: Date, n: number): Date {
  const r = new Date(d)
  r.setDate(r.getDate() + n)
  return r
}

export function dateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function fmtTime(t: string): string {
  const h = parseInt(t)
  if (h === 0 || h === 12) return `12${h === 0 ? 'a' : 'p'}`
  return h < 12 ? `${h}a` : `${h - 12}p`
}

/**
 * Industry labor cost targets as % of revenue. Healthy is a BAND:
 *   pct < floorPct  → understaffed (yellow)
 *   floor ≤ pct ≤ target → on-target (green)
 *   target < pct ≤ warning → watch (yellow)
 *   pct > warning → over (red)
 * Numbers drawn from standard industry rule-of-thumb ranges.
 */
export const LABOR_TARGETS: Record<string, { floorPct: number; targetPct: number; warningPct: number }> = {
  coffee_shop: { floorPct: 15, targetPct: 25, warningPct: 32 },
  restaurant:  { floorPct: 22, targetPct: 30, warningPct: 38 },
  fast_food:   { floorPct: 20, targetPct: 28, warningPct: 35 },
  auto_shop:   { floorPct: 25, targetPct: 35, warningPct: 45 },
  smoke_shop:  { floorPct: 8,  targetPct: 15, warningPct: 22 },
}

export function getLaborTarget(businessType: string): { floorPct: number; targetPct: number; warningPct: number } {
  return LABOR_TARGETS[businessType] || LABOR_TARGETS.coffee_shop
}

export function laborPctTone(pct: number, targetPct: number, warningPct: number, floorPct = 0): {
  fg: string; bg: string; label: 'understaffed' | 'on-target' | 'watch' | 'over'
} {
  if (pct < floorPct)    return { fg: '#D4A843', bg: '#D4A843',  label: 'understaffed' }
  if (pct <= targetPct)  return { fg: '#17C5B0', bg: '#17C5B0',  label: 'on-target' }
  if (pct <= warningPct) return { fg: '#D4A843', bg: '#D4A843',  label: 'watch' }
  return                      { fg: '#E06B5E', bg: '#E06B5E',  label: 'over' }
}

/**
 * Demo weekly revenue per business type, calibrated against the actual
 * labor cost produced by generateScheduleShifts for each type so labor%
 * lands mid-band on the demo dashboard.
 */
export const DEMO_WEEKLY_REVENUE_CENTS: Record<string, number> = {
  coffee_shop: 31_000_00,
  restaurant:  23_000_00,
  fast_food:   22_000_00,
  auto_shop:   22_000_00,
  smoke_shop:  15_000_00,
}

/* ------------------------------------------------------------------ *
 * Coverage: does scheduled staffing actually meet predicted demand?
 * This is the owner's real question — "am I covered for the rush?"
 * ------------------------------------------------------------------ */

export interface DayCoverage {
  day: number
  demandHours: number   // hours that need at least one person
  coveredHours: number  // demanded hours where scheduled heads >= needed
  score: number         // coveredHours / demandHours (1 when no demand)
  busiestHour: number | null
  scheduledStaff: number
  worstGap: { hour: number; need: number; have: number } | null
}

/** Translate a normalized demand ratio (0..1) into a needed headcount. */
function demandHeads(ratio: number): number {
  if (ratio > 0.75) return 3
  if (ratio > 0.5) return 2
  if (ratio > 0.25) return 1
  return 0
}

/**
 * Compare predicted hourly demand (from peak-hour intensity) against the
 * number of staff actually scheduled that hour. `peaks` is the FULL week so
 * the demand scale is consistent across days.
 */
export function computeDayCoverage(
  day: number,
  shifts: ScheduleShift[],
  peaks: { day: number; hour: number; intensity: number }[],
): DayCoverage {
  const maxI = Math.max(...peaks.map(p => p.intensity), 1)
  const dayPeaks = peaks.filter(p => p.day === day)
  const dayShifts = shifts.filter(s => s.dayOfWeek === day && !s.isRecommended)

  let demandHours = 0, coveredHours = 0
  let busiestHour: number | null = null, busiestI = -1
  let worstGap: DayCoverage['worstGap'] = null

  for (const p of dayPeaks) {
    if (p.intensity > busiestI) { busiestI = p.intensity; busiestHour = p.hour }
    const need = demandHeads(p.intensity / maxI)
    if (need === 0) continue
    demandHours++
    const have = dayShifts.filter(s =>
      timeToMinutes(s.startTime) <= p.hour * 60 && timeToMinutes(s.endTime) > p.hour * 60,
    ).length
    if (have >= need) coveredHours++
    else if (!worstGap || need - have > worstGap.need - worstGap.have) {
      worstGap = { hour: p.hour, need, have }
    }
  }

  const scheduledStaff = new Set(dayShifts.map(s => s.staffMemberId).filter(Boolean)).size
  const score = demandHours > 0 ? coveredHours / demandHours : 1
  return { day, demandHours, coveredHours, score, busiestHour, scheduledStaff, worstGap }
}

export function coverageTone(c: DayCoverage): {
  fg: string; label: 'covered' | 'light' | 'gaps' | 'empty'
} {
  if (c.demandHours === 0 && c.scheduledStaff === 0) return { fg: '#3A3A42', label: 'empty' }
  if (c.score >= 0.9) return { fg: '#17C5B0', label: 'covered' }
  if (c.score >= 0.6) return { fg: '#D4A843', label: 'light' }
  return { fg: '#E06B5E', label: 'gaps' }
}

/* ------------------------------------------------------------------ *
 * "Right now" — who's on the clock and who's up next (mobile glance).
 * ------------------------------------------------------------------ */

export interface NowNext {
  onNow: { shift: ScheduleShift; member: ScheduleStaffMember | null }[]
  next: { shift: ScheduleShift; member: ScheduleStaffMember | null } | null
}

export function getNowNext(
  shifts: ScheduleShift[],
  staffMap: Map<string, ScheduleStaffMember>,
  dayIndex: number,
  nowMinutes: number,
): NowNext {
  const todays = shifts
    .filter(s => s.dayOfWeek === dayIndex && !s.isRecommended)
    .sort((a, b) => a.startTime.localeCompare(b.startTime))
  const onNow = todays
    .filter(s => timeToMinutes(s.startTime) <= nowMinutes && timeToMinutes(s.endTime) > nowMinutes)
    .map(s => ({ shift: s, member: s.staffMemberId ? staffMap.get(s.staffMemberId) ?? null : null }))
  const upcoming = todays.find(s => timeToMinutes(s.startTime) > nowMinutes)
  const next = upcoming
    ? { shift: upcoming, member: upcoming.staffMemberId ? staffMap.get(upcoming.staffMemberId) ?? null : null }
    : null
  return { onNow, next }
}

/** Weekly overtime watch tone for a staff member's total hours. */
export function overtimeTone(hours: number): { fg: string; label: 'over' | 'near' | 'ok' } | null {
  if (hours >= 40) return { fg: '#E06B5E', label: 'over' }
  if (hours >= 36) return { fg: '#D4A843', label: 'near' }
  return null
}

/** Sum labor cost (cents) over real (non-recommended) shifts. */
export function computeWeeklyLaborCents(
  shifts: ScheduleShift[],
  staff: ScheduleStaffMember[],
): number {
  const staffMap = new Map(staff.map(s => [s.id, s]))
  return shifts
    .filter(s => !s.isRecommended)
    .reduce((sum, s) => {
      const m = staffMap.get(s.staffMemberId || '')
      if (!m) return sum
      const hrs = Math.max(0, (timeToMinutes(s.endTime) - timeToMinutes(s.startTime) - s.breakMinutes) / 60)
      return sum + Math.round(m.hourlyRate * hrs)
    }, 0)
}
