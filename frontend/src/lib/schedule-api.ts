/**
 * Schedule API DTOs + mappers.
 *
 * Backend uses snake_case + UUID ids + Postgres time strings ("07:00:00").
 * Frontend uses camelCase + "07:00" time strings.
 */
import type { ScheduleShift, ScheduleStaffMember } from './agent-data'

// ── DTOs (wire format) ─────────────────────────────────

export interface StaffMemberDto {
  id: string
  merchant_id: string
  portal_context: string
  name: string
  role: string
  color: string
  hourly_rate: number
  availability: Record<string, { available: boolean; start: string; end: string }>
  phone?: string | null
  active: boolean
}

export interface PeakHourPoint {
  day: number
  hour: number
  intensity: number
  txn_count: number
  revenue_cents: number
}

export interface ShiftDto {
  id: string
  merchant_id: string
  portal_context: string
  staff_member_id: string | null
  week_start_date: string
  day_of_week: number
  shift_date: string
  start_time: string
  end_time: string
  role: string
  break_minutes: number
  notes: string
  status: 'draft' | 'published' | 'cancelled'
  is_recommended: boolean
  recommendation_reason?: string | null
  priority?: 'critical' | 'recommended' | 'optional' | null
}

// ── Mappers ────────────────────────────────────────────

const trimTime = (t: string) => (t.length >= 5 ? t.slice(0, 5) : t)

export function staffFromApi(dto: StaffMemberDto): ScheduleStaffMember {
  return {
    id: dto.id,
    name: dto.name,
    role: dto.role,
    color: dto.color,
    hourlyRate: dto.hourly_rate,
    availability: dto.availability || {},
    phone: dto.phone || undefined,
  }
}

export function staffToApiCreate(
  s: Omit<ScheduleStaffMember, 'id'>,
  merchantId: string,
  portalContext: 'us' | 'ca',
) {
  return {
    merchant_id: merchantId,
    portal_context: portalContext,
    name: s.name,
    role: s.role,
    color: s.color,
    hourly_rate: s.hourlyRate,
    availability: s.availability,
    phone: s.phone || null,
  }
}

export function shiftFromApi(dto: ShiftDto): ScheduleShift {
  return {
    id: dto.id,
    staffMemberId: dto.staff_member_id,
    dayOfWeek: dto.day_of_week,
    shiftDate: dto.shift_date,
    startTime: trimTime(dto.start_time),
    endTime: trimTime(dto.end_time),
    role: dto.role,
    breakMinutes: dto.break_minutes,
    notes: dto.notes || '',
    status: dto.status === 'cancelled' ? 'draft' : (dto.status as 'draft' | 'published'),
    isRecommended: dto.is_recommended,
    recommendationReason: dto.recommendation_reason || undefined,
    priority: dto.priority || undefined,
  }
}

export function shiftToApiCreate(
  s: ScheduleShift,
  merchantId: string,
  portalContext: 'us' | 'ca',
  weekStartDate: string,
) {
  return {
    merchant_id: merchantId,
    portal_context: portalContext,
    staff_member_id: s.staffMemberId,
    week_start_date: weekStartDate,
    day_of_week: s.dayOfWeek,
    shift_date: s.shiftDate,
    start_time: s.startTime,
    end_time: s.endTime,
    role: s.role,
    break_minutes: s.breakMinutes,
    notes: s.notes,
    status: s.status,
    is_recommended: s.isRecommended,
  }
}

export function shiftToApiUpdate(s: Partial<ScheduleShift>) {
  const out: Record<string, unknown> = {}
  if (s.staffMemberId !== undefined) out.staff_member_id = s.staffMemberId
  if (s.startTime !== undefined) out.start_time = s.startTime
  if (s.endTime !== undefined) out.end_time = s.endTime
  if (s.role !== undefined) out.role = s.role
  if (s.breakMinutes !== undefined) out.break_minutes = s.breakMinutes
  if (s.notes !== undefined) out.notes = s.notes
  if (s.status !== undefined) out.status = s.status
  return out
}

// UUID v4-ish check — backend rejects non-UUID merchant_ids with 400.
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export const isUuid = (s: string) => UUID_RE.test(s)
