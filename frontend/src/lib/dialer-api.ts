// SR Auto Dialer API client. Self-contained fetch wrapper mirroring
// lib/team-api.ts (lib/api.ts's apiFetch is module-private). All calls carry
// the Supabase JWT via getAuthHeaders; scoping (rep vs admin-or-better) is
// enforced server-side — nothing here is trusted.
import { getAuthHeaders } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

type Method = 'GET' | 'POST' | 'PATCH' | 'DELETE'

interface Opts {
  params?: Record<string, string | number | boolean | undefined>
  method?: Method
  body?: object   // any JSON-serializable object (typed input models included)
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
export type DialerMarket = 'canada' | 'us'
export type SessionStatus = 'active' | 'paused' | 'ended'
export type CallStatus =
  | 'queued' | 'dialing' | 'ringing' | 'connected' | 'ended' | 'failed' | 'blocked'
export type Disposition =
  | 'meeting_booked' | 'interested' | 'callback' | 'left_voicemail'
  | 'no_answer' | 'busy' | 'bad_number' | 'not_interested' | 'dnc' | 'other'

export interface DialerSession {
  id: string
  rep_id: string
  market: DialerMarket
  status: SessionStatus
  wrap_up_seconds: number
  dials: number
  connects: number
  talk_seconds: number
  started_at: string
  ended_at: string | null
}

export interface DialerCall {
  id: string
  session_id: string | null
  rep_id: string
  rep_name?: string
  lead_id: string | null
  lead_table: string | null
  business_name: string
  contact_name: string
  phone_e164: string
  status: CallStatus
  blocked_reason: string | null
  sim: boolean
  started_at: string
  answered_at: string | null
  ended_at: string | null
  duration_seconds: number | null
  talk_seconds: number | null
  disposition: Disposition | null
  notes: string
  created_at: string
}

/** Compliance annotation attached to every queue entry by the backend. */
export interface GateInfo {
  phone_e164: string
  on_dnc: boolean
  callable_now: boolean
  gate_reason: string
  local_time: string
  window_label: string
  country: string
}

export type PosSystem =
  | 'square' | 'clover' | 'toast' | 'lightspeed' | 'shopify' | 'none' | 'unknown' | string
export type PhoneLeadStatus =
  | 'new' | 'attempting' | 'contacted' | 'callback' | 'booked'
  | 'converted' | 'not_interested' | 'bad_number' | 'dnc' | 'dead'

export interface PhoneLead {
  id: string
  business_name: string
  contact_name: string
  phone_e164: string
  contact_email: string
  city: string
  province: string
  vertical: string
  pos_system: PosSystem
  pos_source: string
  website: string
  est_monthly_value: number   // cents
  notes: string
  status: PhoneLeadStatus
  attempts: number
  last_attempt_at: string | null
  last_disposition: Disposition | null
  next_action_at: string | null
  rep_id: string | null
  source: string
  converted_lead_id: string | null
  created_at: string
}

export interface QueueLead extends GateInfo, PhoneLead {
  kind: 'lead'
}

export interface QueueCallback extends GateInfo {
  kind: 'callback'
  id: string
  lead_id: string | null
  business_name: string
  contact_name: string
  due_at: string
  note: string
}

export interface DialerQueue {
  callbacks: QueueCallback[]
  leads: QueueLead[]
  dev_store: boolean
}

export interface DialGate {
  allowed: boolean
  reason: string
  local_time: string
  window_label: string
}

export interface WebrtcToken {
  mode: 'sim' | 'webrtc'
  token?: string
  caller_id: string
}

export interface DialerCallback {
  id: string
  rep_id: string
  rep_name?: string
  lead_id: string | null
  phone_e164: string
  business_name: string
  contact_name: string
  due_at: string
  timezone: string
  note: string
  status: 'pending' | 'done' | 'cancelled'
}

export interface LiveSession extends DialerSession {
  rep_name: string
  rep_role: string
  current_call: DialerCall | null
}

export interface RepAnalytics {
  rep_id: string
  rep_name: string
  rep_role: string
  dials: number
  connects: number
  connect_rate: number
  talk_seconds: number
  blocked: number
  dispositions: Record<string, number>
}

export interface DialerAnalytics {
  days: number
  reps: RepAnalytics[]
  totals: {
    dials: number; connects: number; connect_rate: number
    talk_seconds: number; blocked: number; dispositions: Record<string, number>
  }
}

export interface DncEntry {
  id: string
  phone_e164: string
  market: DialerMarket
  reason: string
  created_at: string
}

// ─── Rep API ──────────────────────────────────────────────
export const dialerApi = {
  queue: (market: DialerMarket) =>
    req<DialerQueue>('/api/dialer/queue', { params: { market } }),
  currentSession: () =>
    req<{ session: DialerSession | null; dev_store: boolean }>('/api/dialer/sessions/current'),
  startSession: (market: DialerMarket, wrapUpSeconds: number) =>
    req<{ session: DialerSession }>('/api/dialer/sessions', {
      method: 'POST', body: { market, wrap_up_seconds: wrapUpSeconds },
    }),
  patchSession: (id: string, status: SessionStatus) =>
    req<{ session: DialerSession }>(`/api/dialer/sessions/${id}`, {
      method: 'PATCH', body: { status },
    }),
  startCall: (body: {
    session_id: string; market: DialerMarket; phone: string
    lead_id?: string | null; business_name?: string; contact_name?: string; sim?: boolean
  }) =>
    req<{ call: DialerCall; gate: DialGate }>('/api/dialer/calls', { method: 'POST', body }),
  patchCall: (id: string, body: {
    status?: 'dialing' | 'ringing' | 'connected' | 'ended' | 'failed'
    telnyx_call_id?: string; duration_seconds?: number; talk_seconds?: number
  }) =>
    req<{ call: DialerCall }>(`/api/dialer/calls/${id}`, { method: 'PATCH', body }),
  disposition: (callId: string, body: {
    disposition: Disposition; notes?: string
    callback?: { due_at: string; note?: string }
    advance_stage?: string
  }) =>
    req<{ call: DialerCall }>(`/api/dialer/calls/${callId}/disposition`, {
      method: 'POST', body,
    }),
  callbacks: (status: 'pending' | 'done' | 'cancelled' = 'pending') =>
    req<{ callbacks: DialerCallback[] }>('/api/dialer/callbacks', { params: { status } }),
  patchCallback: (id: string, status: 'pending' | 'done' | 'cancelled') =>
    req<{ callback: DialerCallback }>(`/api/dialer/callbacks/${id}`, {
      method: 'PATCH', body: { status },
    }),
  webrtcToken: () => req<WebrtcToken>('/api/dialer/webrtc-token', { method: 'POST', body: {} }),

  // ── Phone-lead pool: capture / recapture / promote ──
  createLead: (body: PhoneLeadInput) =>
    req<{ lead: PhoneLead }>('/api/dialer/phone-leads', { method: 'POST', body }),
  importLeads: (source: string, leads: PhoneLeadInput[]) =>
    req<{ imported: number; skipped_duplicate: number; skipped_invalid: number }>(
      '/api/dialer/phone-leads/import', { method: 'POST', body: { source, leads } }),
  listLeads: (status?: string) =>
    req<{ leads: PhoneLead[] }>('/api/dialer/phone-leads', { params: { status } }),
  warmLeads: () =>
    req<{ leads: PhoneLead[] }>('/api/dialer/phone-leads/warm'),
  updateLead: (id: string, body: Partial<PhoneLeadInput> & { status?: string }) =>
    req<{ lead: PhoneLead }>(`/api/dialer/phone-leads/${id}`, { method: 'PATCH', body }),
  promoteLead: (id: string) =>
    req<{ pipeline_lead: { id: string }; already_converted: boolean }>(
      `/api/dialer/phone-leads/${id}/promote`, { method: 'POST', body: {} }),

  // ── Booking calendar ──
  book: (body: {
    phone_lead_id: string; scheduled_at: string; duration_min?: number
    title?: string; notes?: string
  }) =>
    req<{ appointment: Appointment; pipeline_lead_id: string }>(
      '/api/dialer/appointments', { method: 'POST', body }),
  appointments: (days = 30) =>
    req<{ appointments: Appointment[] }>('/api/dialer/appointments', { params: { days } }),
  patchAppointment: (id: string, status: AppointmentStatus) =>
    req<{ appointment: Appointment }>(`/api/dialer/appointments/${id}`, {
      method: 'PATCH', body: { status },
    }),
}

export interface PhoneLeadInput {
  business_name?: string
  contact_name?: string
  phone: string
  contact_email?: string
  city?: string
  province?: string
  vertical?: string
  pos_system?: PosSystem
  website?: string
  est_monthly_value?: number  // cents
  notes?: string
  source?: string
}

export type AppointmentStatus = 'booked' | 'completed' | 'cancelled' | 'no_show'

export interface Appointment {
  id: string
  phone_lead_id: string | null
  rep_id: string
  rep_name?: string
  lead_id: string | null
  business_name: string
  contact_name: string
  phone_e164: string
  scheduled_at: string
  duration_min: number
  timezone: string
  title: string
  notes: string
  status: AppointmentStatus
}

// ─── Admin API (admin-or-better; 403 otherwise) ───────────
export const dialerAdminApi = {
  live: () => req<{ sessions: LiveSession[]; dev_store: boolean }>('/api/dialer/admin/live'),
  calls: (opts: { rep_id?: string; disposition?: string; days?: number; limit?: number } = {}) =>
    req<{ calls: DialerCall[] }>('/api/dialer/admin/calls', { params: opts }),
  patchCall: (id: string, body: { disposition?: Disposition; notes?: string }) =>
    req<{ call: DialerCall }>(`/api/dialer/admin/calls/${id}`, { method: 'PATCH', body }),
  analytics: (days = 7) =>
    req<DialerAnalytics>('/api/dialer/admin/analytics', { params: { days } }),
  callbacks: (status: 'pending' | 'done' | 'cancelled' = 'pending') =>
    req<{ callbacks: DialerCallback[] }>('/api/dialer/admin/callbacks', { params: { status } }),
  dncList: () => req<{ entries: DncEntry[] }>('/api/dialer/admin/dnc'),
  dncAdd: (phone: string, market: DialerMarket, reason: string) =>
    req<{ ok: boolean; phone_e164: string }>('/api/dialer/admin/dnc', {
      method: 'POST', body: { phone, market, reason },
    }),
  dncRemove: (phone: string) =>
    req<{ ok: boolean }>(`/api/dialer/admin/dnc/${encodeURIComponent(phone)}`, {
      method: 'DELETE',
    }),
  appointments: (days = 30) =>
    req<{ appointments: Appointment[] }>('/api/dialer/admin/appointments', { params: { days } }),
}

// ─── Small shared formatters ──────────────────────────────
export function fmtDuration(totalSeconds: number | null | undefined): string {
  const s = Math.max(0, Math.floor(totalSeconds || 0))
  const m = Math.floor(s / 60)
  const h = Math.floor(m / 60)
  if (h > 0) return `${h}h ${m % 60}m`
  return `${m}:${String(s % 60).padStart(2, '0')}`
}

export function fmtCents(cents: number | null | undefined): string {
  const dollars = Math.round((cents || 0) / 100)
  return dollars > 0 ? `$${dollars.toLocaleString()}/mo` : '—'
}

export const POS_LABELS: Record<string, string> = {
  square: 'Square', clover: 'Clover', toast: 'Toast', lightspeed: 'Lightspeed',
  shopify: 'Shopify', none: 'No POS', unknown: 'POS unknown',
}

export function posLabel(pos: string | null | undefined): string {
  if (!pos) return 'POS unknown'
  return POS_LABELS[pos] ?? pos
}

export const DISPOSITION_LABELS: Record<Disposition, string> = {
  meeting_booked: 'Meeting booked',
  interested: 'Interested',
  callback: 'Callback',
  left_voicemail: 'Left voicemail',
  no_answer: 'No answer',
  busy: 'Busy',
  bad_number: 'Bad number',
  not_interested: 'Not interested',
  dnc: 'Do not call',
  other: 'Other',
}
