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
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: Record<string, unknown>
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

  const fetchOpts: RequestInit = {
    method: opts?.method || 'GET',
    credentials: 'include',
    headers: { 'Accept': 'application/json' },
  }

  if (opts?.body) {
    fetchOpts.headers = {
      ...fetchOpts.headers,
      'Content-Type': 'application/json',
    }
    fetchOpts.body = JSON.stringify(opts.body)
  }

  const res = await fetch(url.toString(), fetchOpts)

  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }

  return res.json()
}

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
  horizon_days?: number
  error_rate?: number
  scenario_analysis?: {
    optimistic_cents: number
    expected_cents: number
    pessimistic_cents: number
  }
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

// ─── Transaction Drill-Down Types ────────────────────────

export interface TransactionLineItem {
  id: string
  product_name: string
  sku: string | null
  quantity: number
  unit_price_cents: number
  total_cents: number
  category: string | null
}

export interface TransactionDetail {
  id: string
  created_at: string
  total_cents: number
  tip_cents: number
  discount_cents: number
  refund_cents: number
  payment_method: string
  items: TransactionLineItem[]
}

export interface DayTransactions {
  date: string
  transactions: TransactionDetail[]
  summary: {
    total_revenue_cents: number
    transaction_count: number
    unique_products: number
    avg_ticket_cents: number
    top_product: string
    top_product_qty: number
  }
}

// ─── Inventory Types ─────────────────────────────────────

export interface InventoryItem {
  id: string
  product_name: string
  sku: string
  category: string
  current_stock: number
  unit: string
  reorder_point: number
  predicted_daily_usage: number
  days_until_reorder: number | null
  trend: 'rising' | 'falling' | 'stable'
  trend_pct: number
  last_updated: string
}

export interface InventoryData {
  items: InventoryItem[]
  total: number
  alerts: {
    low_stock: number
    overstocked: number
    trending_up: number
  }
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
      : apiFetch<any>(`/api/dashboard/insights/${insightId}/action`, { method: 'PATCH', params: { org_id: orgId, action_status: status } }),

  // Transaction drill-down: get individual SKUs/products sold on a specific day
  dayTransactions: (orgId: string, date: string) =>
    isDemo(orgId)
      ? delay(demoData.dayTransactions(date))
      : apiFetch<DayTransactions>('/api/dashboard/transactions/day', { params: { org_id: orgId, date } }),

  // Inventory management
  inventory: (orgId: string) =>
    isDemo(orgId)
      ? delay(demoData.inventory())
      : apiFetch<InventoryData>('/api/dashboard/inventory', { params: { org_id: orgId } }),

  // OAuth URL for connecting Square
  squareAuthorize: (orgId: string) =>
    `${API_BASE}/api/square/authorize?org_id=${orgId}`,
}
