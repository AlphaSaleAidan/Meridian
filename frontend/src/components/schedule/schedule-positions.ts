import type { ScheduleShift, ScheduleStaffMember } from '@/lib/agent-data'
import { getRoleColor, timeToMinutes, isStaffAvailable } from './schedule-helpers'

/**
 * Positions = named, category-based shift slots (not random hours).
 * A position slot IS a shift (role + time block); an *open* position is just an
 * unassigned shift. This lets the whole positions model reuse shift CRUD.
 *
 * `base`  = slots needed on a normal day.
 * `flex`  = a coverage position that scales UP on busy days, using sales history
 *           (peak-hour intensity derived from revenue/transactions).
 */
export interface PositionDef {
  key: string
  label: string
  role: string
  start: string
  end: string
  base: number
  flex?: boolean
}

export const POSITIONS_BY_TYPE: Record<string, PositionDef[]> = {
  restaurant: [
    { key: 'manager', label: 'Manager', role: 'manager', start: '09:00', end: '17:00', base: 1 },
    { key: 'open', label: 'Opening', role: 'server', start: '08:00', end: '16:00', base: 1 },
    { key: 'float', label: 'Midday Float', role: 'server', start: '11:00', end: '19:00', base: 1, flex: true },
    { key: 'close', label: 'Close', role: 'server', start: '16:00', end: '23:00', base: 1 },
    { key: 'cook', label: 'Line Cook', role: 'kitchen', start: '10:00', end: '22:00', base: 1, flex: true },
    { key: 'bar', label: 'Bar', role: 'bartender', start: '16:00', end: '23:00', base: 1 },
  ],
  fast_food: [
    { key: 'manager', label: 'Shift Lead', role: 'shift_lead', start: '09:00', end: '17:00', base: 1 },
    { key: 'open', label: 'Opening', role: 'cashier', start: '07:00', end: '15:00', base: 1 },
    { key: 'float', label: 'Counter Float', role: 'cashier', start: '11:00', end: '19:00', base: 1, flex: true },
    { key: 'drive', label: 'Drive-Thru', role: 'drive_through', start: '11:00', end: '20:00', base: 1, flex: true },
    { key: 'close', label: 'Close', role: 'cashier', start: '15:00', end: '23:00', base: 1 },
    { key: 'cook', label: 'Grill', role: 'kitchen', start: '10:00', end: '21:00', base: 1, flex: true },
  ],
  coffee_shop: [
    { key: 'manager', label: 'Manager', role: 'manager', start: '07:00', end: '15:00', base: 1 },
    { key: 'open', label: 'Opening Barista', role: 'barista', start: '06:00', end: '13:00', base: 1 },
    { key: 'float', label: 'Rush Float', role: 'barista', start: '07:00', end: '12:00', base: 1, flex: true },
    { key: 'mid', label: 'Midday', role: 'barista', start: '11:00', end: '17:00', base: 1, flex: true },
    { key: 'close', label: 'Close', role: 'barista', start: '13:00', end: '19:00', base: 1 },
  ],
  auto_shop: [
    { key: 'manager', label: 'Service Manager', role: 'manager', start: '08:00', end: '16:00', base: 1 },
    { key: 'advisor', label: 'Service Advisor', role: 'advisor', start: '08:00', end: '17:00', base: 1, flex: true },
    { key: 'tech', label: 'Technician', role: 'technician', start: '08:00', end: '17:00', base: 2, flex: true },
    { key: 'parts', label: 'Parts Counter', role: 'parts_counter', start: '09:00', end: '17:00', base: 1 },
  ],
  smoke_shop: [
    { key: 'manager', label: 'Manager', role: 'manager', start: '10:00', end: '18:00', base: 1 },
    { key: 'open', label: 'Opening', role: 'associate', start: '09:00', end: '17:00', base: 1 },
    { key: 'close', label: 'Close', role: 'associate', start: '15:00', end: '23:00', base: 1, flex: true },
  ],
}

export function positionsForType(businessType: string): PositionDef[] {
  return POSITIONS_BY_TYPE[businessType] || POSITIONS_BY_TYPE.coffee_shop
}

/** Default staff roles per business type (the AddStaffModal picker list). */
export const ROLES_BY_TYPE: Record<string, string[]> = {
  coffee_shop: ['barista', 'bar_lead', 'cashier', 'supervisor'],
  restaurant: ['server', 'bartender', 'host', 'kitchen', 'runner', 'manager'],
  fast_food: ['counter', 'drive_through', 'kitchen', 'manager'],
  auto_shop: ['technician', 'advisor', 'parts_counter'],
  smoke_shop: ['associate', 'shift_lead'],
}

/** Union of the staff-role picker defaults and the position-slot roles, so the
 *  Manage-positions wizard lists everything the schedule can actually use. */
export function defaultRolesForType(businessType: string): string[] {
  const set = new Set(ROLES_BY_TYPE[businessType] || ROLES_BY_TYPE.coffee_shop)
  for (const def of positionsForType(businessType)) set.add(def.role)
  return [...set]
}

/* ------------------------------------------------------------------ *
 * Custom positions — merchant-editable role list (Manage positions).
 *
 * Roles are plain strings on staff + shift rows (no positions table), so the
 * laziest persistence that survives reload is:
 *   - the edited list itself      → localStorage, keyed per merchant
 *   - renames of rows in use      → PUT /schedule/staff + /schedule/shifts
 *     (so renamed roles live in the DB and show up on any device)
 * ------------------------------------------------------------------ */

export interface PositionsOverride {
  /** The merchant's current position list (role strings). */
  positions: string[]
  /** original default role -> current name, so POSITIONS_BY_TYPE slot defs
   *  keep matching staff after a rename. */
  renames: Record<string, string>
}

const POSITIONS_STORE_PREFIX = 'meridian-positions-v1:'

export function positionsStorageKey(merchantId: string, businessType: string): string {
  return `${POSITIONS_STORE_PREFIX}${merchantId || `demo-${businessType}`}`
}

export function loadPositionsOverride(key: string): PositionsOverride | null {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed?.positions)) return null
    return {
      positions: parsed.positions.filter((p: unknown) => typeof p === 'string'),
      renames: parsed.renames && typeof parsed.renames === 'object' ? parsed.renames : {},
    }
  } catch {
    return null
  }
}

export function savePositionsOverride(key: string, override: PositionsOverride): void {
  try { localStorage.setItem(key, JSON.stringify(override)) } catch { /* quota/private mode — non-fatal */ }
}

/** Slot defs with merchant renames applied, so Auto-fill + the board keep
 *  matching staff whose roles were renamed. */
export function applyPositionRenames(defs: PositionDef[], renames: Record<string, string>): PositionDef[] {
  return defs.map(d => (renames[d.role] ? { ...d, role: renames[d.role] } : d))
}

/** Expected traffic for a day, 0..1, scaled ACROSS the week (min-max) so the
 *  forecast spreads red→green instead of clustering — a day's mean sales
 *  intensity relative to the slowest/busiest day. */
export function dayDemand(day: number, peaks: { day: number; hour: number; intensity: number }[]): number {
  if (peaks.length === 0) return 0.5
  const avgFor = (d: number) => {
    const dp = peaks.filter(p => p.day === d)
    return dp.length ? dp.reduce((s, p) => s + p.intensity, 0) / dp.length : 0
  }
  const avgs = [0, 1, 2, 3, 4, 5, 6].map(avgFor)
  const mn = Math.min(...avgs), mx = Math.max(...avgs)
  return mx > mn ? (avgFor(day) - mn) / (mx - mn) : 0.5
}

/** How many extra flex slots a demand level warrants (sales-history driven). */
function flexBonus(demand: number): number {
  if (demand > 0.7) return 2
  if (demand > 0.45) return 1
  return 0
}

export interface PositionSlot {
  positionKey: string
  def: PositionDef
  index: number       // 0..count-1 within the position for this day
  color: string
}

/** The required position slots for a day, scaled by that day's sales history. */
export function requiredSlotsForDay(
  defs: PositionDef[],
  day: number,
  peaks: { day: number; hour: number; intensity: number }[],
): PositionSlot[] {
  const demand = dayDemand(day, peaks)
  const slots: PositionSlot[] = []
  for (const def of defs) {
    const count = def.base + (def.flex ? flexBonus(demand) : 0)
    for (let i = 0; i < count; i++) {
      slots.push({ positionKey: def.key, def, index: i, color: getRoleColor(def.role) })
    }
  }
  return slots
}

/** Match an existing shift to a position def (by role + start hour). */
export function positionKeyForShift(shift: ScheduleShift, defs: PositionDef[]): string | null {
  const sh = parseInt(shift.startTime)
  const match = defs.find(d => d.role === shift.role && Math.abs(parseInt(d.start) - sh) <= 1)
  return match?.key ?? null
}

const OT_LIMIT_MIN = 40 * 60

/**
 * Build a position-based week: ensure every required position (scaled by sales
 * history) exists, and assign the best available staff to each — covering the
 * busiest days first, balancing hours, and respecting availability + OT.
 * Returns the full set of position shifts (assigned where possible, else open).
 */
export function buildPositionSchedule(
  staff: ScheduleStaffMember[],
  defs: PositionDef[],
  peaks: { day: number; hour: number; intensity: number }[],
  weekStart: Date,
): ScheduleShift[] {
  const pad2 = (n: number) => (n < 10 ? `0${n}` : `${n}`)
  const isoFor = (day: number) => {
    const d = new Date(weekStart); d.setDate(d.getDate() + day)
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
  }
  const minutesAssigned = new Map<string, number>()
  staff.forEach(s => minutesAssigned.set(s.id, 0))
  // booked[staffId] = list of [startMin,endMin] per day to avoid overlaps
  const booked = new Map<string, Record<number, [number, number][]>>()
  staff.forEach(s => booked.set(s.id, {}))

  const shifts: ScheduleShift[] = []
  let sid = 1

  // Busiest days first so peak coverage wins the best staff.
  const dayOrder = [0, 1, 2, 3, 4, 5, 6].sort((a, b) => dayDemand(b, peaks) - dayDemand(a, peaks))

  for (const day of dayOrder) {
    const slots = requiredSlotsForDay(defs, day, peaks)
    for (const slot of slots) {
      const sMin = timeToMinutes(slot.def.start), eMin = timeToMinutes(slot.def.end)
      const durMin = eMin - sMin
      // Candidate staff: role matches, available, not overlapping, under OT.
      const candidates = staff
        .filter(m => m.role === slot.def.role || getRoleColor(m.role) === slot.color)
        .filter(m => isStaffAvailable(m, day))
        .filter(m => {
          const av = m.availability[['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'][day]]
          if (!av) return false
          return sMin >= timeToMinutes(av.start) && eMin <= timeToMinutes(av.end) + 0
        })
        .filter(m => {
          const days = booked.get(m.id)![day] || []
          return !days.some(([bs, be]) => sMin < be && eMin > bs)
        })
        .filter(m => (minutesAssigned.get(m.id) ?? 0) + durMin <= OT_LIMIT_MIN)
        .sort((a, b) => (minutesAssigned.get(a.id) ?? 0) - (minutesAssigned.get(b.id) ?? 0) || a.hourlyRate - b.hourlyRate)

      const chosen = candidates[0] ?? null
      if (chosen) {
        minutesAssigned.set(chosen.id, (minutesAssigned.get(chosen.id) ?? 0) + durMin)
        const days = booked.get(chosen.id)!
        days[day] = [...(days[day] || []), [sMin, eMin]]
      }
      shifts.push({
        id: `shift-pos-${sid++}`,
        staffMemberId: chosen?.id ?? null,
        dayOfWeek: day,
        shiftDate: isoFor(day),
        startTime: slot.def.start,
        endTime: slot.def.end,
        role: slot.def.role,
        breakMinutes: durMin > 5 * 60 ? 30 : 0,
        notes: '',
        status: 'draft',
        isRecommended: false,
      })
    }
  }
  return shifts
}
