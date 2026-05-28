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
