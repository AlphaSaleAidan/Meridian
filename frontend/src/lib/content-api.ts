/**
 * Content API Client
 *
 * Mirrors the pattern in @/lib/api.ts:
 * - Demo mode returns mock data via fetchDemoContentData()
 * - Real mode calls apiFetch() against /api/content/* endpoints
 */

import { fetchDemoContentData, type ContentDashboardData } from './content-demo-data'
import { getAuthHeaders } from './supabase'

const API_BASE = import.meta.env.VITE_API_URL || ''

function isDemo(orgId: string): boolean {
  return orgId === 'demo'
}

function delay<T>(data: T, ms = 400): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(data), ms + Math.random() * 200))
}

interface ApiFetchOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: Record<string, unknown>
}

async function apiFetch<T>(path: string, opts?: ApiFetchOptions): Promise<T> {
  const url = `${API_BASE}${path}`
  const authHeaders = await getAuthHeaders()

  const fetchOpts: RequestInit = {
    method: opts?.method || 'GET',
    credentials: 'include',
    headers: { ...authHeaders, Accept: 'application/json' },
  }

  if (opts?.body) {
    fetchOpts.headers = {
      ...fetchOpts.headers,
      'Content-Type': 'application/json',
    }
    fetchOpts.body = JSON.stringify(opts.body)
  }

  const res = await fetch(url, fetchOpts)

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }

  return res.json()
}

export const contentApi = {
  dashboard: (orgId: string): Promise<ContentDashboardData> =>
    isDemo(orgId)
      ? delay(fetchDemoContentData())
      : apiFetch<ContentDashboardData>('/api/content/dashboard/' + orgId),

  approvePost: (postId: string, merchantId: string, scheduledAt?: string) =>
    apiFetch<{ ok: boolean }>('/api/content/posts/' + postId + '/approve', {
      method: 'PATCH',
      body: { merchantId, scheduledAt },
    }),

  rejectPost: (postId: string) =>
    apiFetch<{ ok: boolean }>('/api/content/posts/' + postId + '/reject', {
      method: 'PATCH',
    }),

  regeneratePost: (postId: string, field: string, merchantId: string) =>
    apiFetch<{ ok: boolean }>('/api/content/posts/' + postId + '/regenerate', {
      method: 'POST',
      body: { merchantId, field },
    }),

  generateCalendar: (merchantId: string) =>
    apiFetch<{ ok: boolean; jobIds: string[] }>('/api/content/calendar/generate/' + merchantId, {
      method: 'POST',
    }),
}
