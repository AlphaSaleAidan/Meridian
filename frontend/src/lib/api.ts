/**
 * Meridian API Client
 * 
 * Calls the FastAPI backend for dashboard data.
 * In demo mode (org_id='demo'): returns realistic mock data client-side.
 * In dev: proxied via Vite to localhost:8000
 * In prod: uses VITE_API_URL env var
 */

import { demoData } from './demo-data'

const API_BASE = import.meta.env.VITE_API_URL || ''

interface ApiOptions {
  params?: Record<string, string | number | boolean>
}

async function apiFetch<T>(path: string, opts?: ApiOptions): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  
  if (opts?.params) {
    Object.entries(opts.params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) {
        url.searchParams.set(k, String(v))
      }
    })
  }

  const res = await fetch(url.toString(), {
    credentials: 'include',
    headers: { 'Accept': 'application/json' },
  })

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }

  return res.json()
}

// Simulate network delay for realism
function delay<T>(data: T, ms = 400): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(data), ms + Math.random() * 200))
}

// ─── Type Definitions ────────────────────────────────────

export interface Overview {
  revenue_cents_30d: number
  revenue_change_pct: number
  transaction_count_30d: number
  avg_ticket_cents: number
  money_left_score: MoneyLeftScore | null
  connection: { status: string; provider: string | null; last_sync_at: string | null }
  days_with_data: number
}

export interface MoneyLeftScore {
  id: string
  total_score_cents: number
  components: Record<string, { amount_cents: number; [key: string]: any }>
  scored_at: string
}

export interface DailyRevenue {
  date: string
  revenue_cents: number
  transactions: number
  avg_ticket_cents: number
  refund_cents: number
  tax_cents: number
  tip_cents: number
  discount_cents: number
  customers: number
}

export interface WeeklyRevenue {
  week: string
  revenue_cents: number
  transactions: number
  avg_ticket_cents: number
}

export interface RevenueData {
  daily: DailyRevenue[]
  weekly: WeeklyRevenue[]
}

export interface HourlyData {
  hourly: {
    hour: string
    revenue_cents: number
    sales: number
    refunds: number
    avg_ticket_cents: number
    customers: number
  }[]
}

export interface ProductPerf {
  product_id: string
  name: string
  sku: string | null
  price_cents: number | null
  total_revenue_cents: number
  total_quantity: number
  times_sold: number
  daily: { date: string; revenue_cents: number; quantity: number }[]
}

export interface ProductsData {
  products: ProductPerf[]
  total_products: number
  period_days: number
}

export interface Insight {
  id: string
  type: string
  title: string
  summary: string
  details: Record<string, any>
  impact_cents: number | null
  confidence: number | null
  action_status: string
  valid_until: string | null
  created_at: string
}

export interface Forecast {
  id: string
  type: string
  period_start: string
  period_end: string
  predicted_cents: number
  lower_bound_cents: number | null
  upper_bound_cents: number | null
  confidence: number | null
}

export interface Notification {
  id: string
  title: string
  body: string
  priority: string
  source_type: string | null
  status: string
  created_at: string
  acknowledged_at: string | null
}

export interface ConnectionInfo {
  id: string
  provider: string
  status: string
  merchant_id: string | null
  last_sync_at: string | null
  historical_import_complete: boolean | null
  last_error: string | null
  created_at: string
}

// ─── API Functions ───────────────────────────────────────

function isDemo(orgId: string): boolean {
  return orgId === 'demo'
}

export const api = {
  overview: (orgId: string) =>
    isDemo(orgId)
      ? delay(demoData.overview())
      : apiFetch<Overview>('/api/dashboard/overview', { params: { org_id: orgId } }),

  revenue: (orgId: string, days = 30) =>
    isDemo(orgId)
      ? delay(demoData.revenue(days))
      : apiFetch<RevenueData>('/api/dashboard/revenue', { params: { org_id: orgId, days } }),

  hourlyRevenue: (orgId: string, days = 30) =>
    isDemo(orgId)
      ? delay(demoData.hourlyRevenue())
      : apiFetch<HourlyData>('/api/dashboard/revenue/hourly', { params: { org_id: orgId, days } }),

  products: (orgId: string, days = 30) =>
    isDemo(orgId)
      ? delay(demoData.products(days))
      : apiFetch<ProductsData>('/api/dashboard/products', { params: { org_id: orgId, days } }),

  insights: (orgId: string, limit = 20) =>
    isDemo(orgId)
      ? delay(demoData.insights(limit))
      : apiFetch<{ insights: Insight[]; total: number }>('/api/dashboard/insights', { params: { org_id: orgId, limit } }),

  forecasts: (orgId: string) =>
    isDemo(orgId)
      ? delay(demoData.forecasts())
      : apiFetch<{ forecasts: Forecast[]; total: number }>('/api/dashboard/forecasts', { params: { org_id: orgId } }),

  notifications: (orgId: string, limit = 20) =>
    isDemo(orgId)
      ? delay(demoData.notifications(limit))
      : apiFetch<{ notifications: Notification[]; total: number }>('/api/dashboard/notifications', { params: { org_id: orgId, limit } }),

  connection: (orgId: string) =>
    isDemo(orgId)
      ? delay(demoData.connection())
      : apiFetch<{ connections: ConnectionInfo[] }>('/api/dashboard/connection', { params: { org_id: orgId } }),

  weeklyReport: (orgId: string) =>
    isDemo(orgId)
      ? delay(demoData.weeklyReport())
      : apiFetch<{ report: any }>('/api/dashboard/weekly-report', { params: { org_id: orgId } }),

  updateInsightAction: (insightId: string, orgId: string, status: string) =>
    isDemo(orgId)
      ? delay({ success: true })
      : apiFetch<any>(`/api/dashboard/insights/${insightId}/action`, { params: { org_id: orgId, action_status: status } }),

  // OAuth URL for connecting Square
  squareAuthorize: (orgId: string) =>
    `${API_BASE}/api/square/authorize?org_id=${orgId}`,
}
