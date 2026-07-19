// Team Management API client (Workstream 1).
// Self-contained fetch wrapper mirroring lib/api.ts's apiFetch (which is module-
// private). All calls carry the Supabase JWT via getAuthHeaders so the backend
// can enforce org-scoped RBAC. org_id is always passed explicitly and re-validated
// server-side against the caller's membership — the client value is never trusted.
import { getAuthHeaders } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

type Method = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

interface Opts {
  params?: Record<string, string | number | boolean | undefined>
  method?: Method
  body?: Record<string, unknown>
}

async function req<T>(path: string, opts?: Opts): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (opts?.params) {
    Object.entries(opts.params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    })
  }
  const authHeaders = await getAuthHeaders()
  const fetchOpts: RequestInit = {
    method: opts?.method || 'GET',
    credentials: 'include',
    headers: { ...authHeaders, Accept: 'application/json' },
  }
  if (opts?.body) {
    fetchOpts.headers = { ...fetchOpts.headers, 'Content-Type': 'application/json' }
    fetchOpts.body = JSON.stringify(opts.body)
  }
  const res = await fetch(url.toString(), fetchOpts)
  if (!res.ok) {
    const text = await res.text()
    const err = new Error(`API ${res.status}: ${text}`) as Error & { status?: number }
    err.status = res.status
    throw err
  }
  return res.json()
}

// ─── Types ────────────────────────────────────────────────
export type Role = 'owner' | 'manager' | 'employee'

export interface Permissions {
  visibility: Record<string, boolean>
  actions: Record<string, boolean>
}

export interface Member {
  id: string
  email: string
  full_name?: string
  role: Role
  permissions: Permissions
  invite_status: string
  user_id?: string
}

export interface PermissionSchema {
  roles: Role[]
  visibility: string[]
  actions: string[]
}

export interface HoursRow {
  employee_id: string
  name: string
  scheduled_hours: number
  actual_hours: number
  variance_hours: number
  variance_flag: boolean
}

export interface Channel { id: string; name: string; description?: string; is_default?: boolean }
export interface TeamMessage { id: string; author_name: string; body: string; created_at: string }

// ─── API ──────────────────────────────────────────────────
export const teamApi = {
  // 1c/1e — member admin
  permissionSchema: () => req<PermissionSchema>('/api/team-admin/permission-schema'),
  members: (orgId: string) =>
    req<{ members: Member[]; total: number }>('/api/team-admin/members', { params: { org_id: orgId } }),
  createMember: (orgId: string, body: {
    email: string; full_name?: string; role: Role; permissions?: Permissions
    portal?: string; send_invite?: boolean
  }) =>
    req<{ member: Member; invite_sent: boolean; temp_password?: string }>(
      '/api/team-admin/members', { method: 'POST', body: { org_id: orgId, ...body } }),
  updateMember: (orgId: string, memberId: string, body: { role?: Role; permissions?: Permissions }) =>
    req<{ member_id: string }>(`/api/team-admin/members/${memberId}`, {
      method: 'PATCH', body: { org_id: orgId, ...body },
    }),
  deactivateMember: (orgId: string, memberId: string) =>
    req<{ member_id: string; active: boolean }>(`/api/team-admin/members/${memberId}`, {
      method: 'DELETE', params: { org_id: orgId },
    }),

  // 1b — time clock
  clockIn: (orgId: string, employeeId: string, source = 'manual') =>
    req<{ punch: any }>('/api/time-clock/clock-in', {
      method: 'POST', body: { org_id: orgId, employee_id: employeeId, source },
    }),
  clockOut: (orgId: string, employeeId: string) =>
    req<{ punch_id: string }>('/api/time-clock/clock-out', {
      method: 'POST', body: { org_id: orgId, employee_id: employeeId },
    }),
  hoursSummary: (orgId: string, weekStart: string) =>
    req<{ week_start: string; rows: HoursRow[] }>('/api/time-clock/summary', {
      params: { org_id: orgId, week_start: weekStart },
    }),
  correctPunch: (orgId: string, punchId: string, body: {
    clock_in_at?: string; clock_out_at?: string; edit_reason: string
  }) =>
    req<{ punch_id: string }>(`/api/time-clock/punches/${punchId}`, {
      method: 'PATCH', body: { org_id: orgId, ...body },
    }),

  // 1d — internal chat
  channels: (orgId: string) =>
    req<{ channels: Channel[] }>('/api/team-chat/channels', { params: { org_id: orgId } }),
  messages: (orgId: string, channelId: string) =>
    req<{ messages: TeamMessage[] }>('/api/team-chat/messages', {
      params: { org_id: orgId, channel_id: channelId },
    }),
  postMessage: (orgId: string, channelId: string, text: string) =>
    req<{ message: TeamMessage }>('/api/team-chat/messages', {
      method: 'POST', body: { org_id: orgId, channel_id: channelId, body: text },
    }),

  // 1d — customer chatbot config
  chatbotConfig: (orgId: string) =>
    req<{ config: any }>('/api/chatbot/config', { params: { org_id: orgId } }),
  saveChatbotConfig: (orgId: string, cfg: Record<string, unknown>) =>
    req<{ config: any }>('/api/chatbot/config', { method: 'PUT', body: { org_id: orgId, ...cfg } }),
}
