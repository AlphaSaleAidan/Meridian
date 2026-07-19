/**
 * Multi-Location Hub API client (Command tier).
 *
 * Standalone from the big `api` object so the hub surface can evolve without
 * touching the shared client. Same auth model: the Supabase JWT is attached via
 * getAuthHeaders(); the active hub org is passed as ?org_id= (the backend gate
 * verifies membership + Command tier server-side).
 *
 * Every endpoint is Command-tier gated on the server — a non-Command org gets a
 * 403 here, which the UI surfaces as "requires the Command plan".
 */
import { getAuthHeaders } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

export interface HubOrg {
  org_id: string
  name: string
  plan_tier: string | null
  status: string | null
  role: string
  is_owner: boolean
}

export interface HubLocationStat {
  org_id: string
  name: string
  plan_tier: string | null
  revenue_cents: number
  transaction_count: number
  phone_order_count: number
  phone_call_count: number
}

export interface HubOverview {
  window_days: number
  location_count: number
  totals: {
    revenue_cents: number
    transaction_count: number
    phone_call_count: number
  }
  locations: HubLocationStat[]
}

export interface PushDownResult {
  config_type: string
  results: Array<{ org_id: string; status: string; detail?: string }>
}

export class HubForbiddenError extends Error {}

async function hubFetch<T>(
  path: string,
  hubOrgId: string,
  opts?: { method?: string; body?: Record<string, unknown>; params?: Record<string, string | number> },
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  url.searchParams.set('org_id', hubOrgId)
  if (opts?.params) {
    Object.entries(opts.params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const authHeaders = await getAuthHeaders()
  const init: RequestInit = {
    method: opts?.method || 'GET',
    credentials: 'include',
    headers: { ...authHeaders, Accept: 'application/json' },
  }
  if (opts?.body) {
    init.headers = { ...init.headers, 'Content-Type': 'application/json' }
    init.body = JSON.stringify(opts.body)
  }
  const res = await fetch(url.toString(), init)
  if (res.status === 403) {
    throw new HubForbiddenError(await res.text())
  }
  if (!res.ok) {
    throw new Error(`Hub API ${res.status}: ${await res.text()}`)
  }
  return res.json()
}

export const hubApi = {
  orgs: (hubOrgId: string) =>
    hubFetch<{ orgs: HubOrg[] }>('/api/hub/orgs', hubOrgId),

  overview: (hubOrgId: string, days = 30) =>
    hubFetch<HubOverview>('/api/hub/overview', hubOrgId, { params: { days } }),

  connect: (hubOrgId: string, targetOrgId: string) =>
    hubFetch<{ org_id: string; role: string; is_owner: boolean; linked: boolean }>(
      '/api/hub/connect', hubOrgId, { method: 'POST', body: { target_org_id: targetOrgId } },
    ),

  switchOrg: (hubOrgId: string, targetOrgId: string) =>
    hubFetch<{ active_org_id: string; role: string; is_owner: boolean }>(
      '/api/hub/switch', hubOrgId, { method: 'POST', body: { target_org_id: targetOrgId } },
    ),

  pushDown: (
    hubOrgId: string,
    configType: string,
    payload: Record<string, unknown>,
    targetOrgIds: string[],
  ) =>
    hubFetch<PushDownResult>('/api/hub/push-down', hubOrgId, {
      method: 'POST',
      body: { config_type: configType, payload, target_org_ids: targetOrgIds },
    }),
}
