/**
 * Meridian API Client
 * 
 * Calls the FastAPI backend for dashboard data.
 * In demo mode (org_id='demo'): returns realistic mock data client-side.
 * In dev: proxied via Vite to localhost:8000
 * In prod: uses VITE_API_URL env var
 */

import { demoData } from './demo-data'
import { getAuthHeaders } from './supabase'
import type { StaffMemberDto, ShiftDto, PeakHourPoint } from './schedule-api'

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

  const authHeaders = await getAuthHeaders()

  const fetchOpts: RequestInit = {
    method: opts?.method || 'GET',
    credentials: 'include',
    headers: { ...authHeaders, 'Accept': 'application/json' },
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
  // All-time figures (within a ~13mo window) — used as a fallback so backfilled
  // history is shown when the trailing 30 days has no sales.
  lifetime_revenue_cents?: number
  lifetime_transaction_count?: number
  lifetime_avg_ticket_cents?: number
  first_activity_at?: string | null
  last_activity_at?: string | null
  lifetime_days_with_data?: number
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
  cost_cents?: number | null
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

const EMPTY = {
  overview: { revenue_cents_30d: 0, revenue_change_pct: 0, transaction_count_30d: 0, avg_ticket_cents: 0, money_left_score: null, connection: { status: 'not_connected', provider: null, last_sync_at: null }, days_with_data: 0 } as Overview,
  revenue: { daily: [], weekly: [] } as RevenueData,
  hourly: { hourly: [] } as HourlyData,
  products: { products: [], total_products: 0, period_days: 0 } as ProductsData,
  insights: { insights: [], total: 0 },
  forecasts: { forecasts: [], total: 0 },
  notifications: { notifications: [], total: 0 },
  connection: { connections: [] },
  report: { report: null },
  transactions: { date: '', transactions: [], summary: { total_revenue_cents: 0, transaction_count: 0, avg_ticket_cents: 0 } } as unknown as DayTransactions,
  inventory: { items: [], total: 0, alerts: { low_stock: 0, overstocked: 0, expiring_soon: 0 }, low_stock: [], reorder_suggestions: [] } as unknown as InventoryData,
  empty: {} as any,
}

export const api = {
  overview: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.overview())
    : !orgId ? delay(EMPTY.overview)
    : apiFetch<Overview>('/api/dashboard/overview', { params: { org_id: orgId } }),

  revenue: (orgId: string, days = 30) =>
    isDemo(orgId) ? delay(demoData.revenue(days))
    : !orgId ? delay(EMPTY.revenue)
    : apiFetch<RevenueData>('/api/dashboard/revenue', { params: { org_id: orgId, days } }),

  hourlyRevenue: (orgId: string, days = 30) =>
    isDemo(orgId) ? delay(demoData.hourlyRevenue())
    : !orgId ? delay(EMPTY.hourly)
    : apiFetch<HourlyData>('/api/dashboard/revenue/hourly', { params: { org_id: orgId, days } }),

  products: (orgId: string, days = 30) =>
    isDemo(orgId) ? delay(demoData.products(days))
    : !orgId ? delay(EMPTY.products)
    : apiFetch<ProductsData>('/api/dashboard/products', { params: { org_id: orgId, days } }),

  insights: (orgId: string, limit = 20) =>
    isDemo(orgId) ? delay(demoData.insights(limit))
    : !orgId ? delay(EMPTY.insights)
    : apiFetch<{ insights: Insight[]; total: number }>('/api/dashboard/insights', { params: { org_id: orgId, limit } }),

  forecasts: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.forecasts())
    : !orgId ? delay(EMPTY.forecasts)
    : apiFetch<{ forecasts: Forecast[]; total: number }>('/api/dashboard/forecasts', { params: { org_id: orgId } }),

  notifications: (orgId: string, limit = 20) =>
    isDemo(orgId) ? delay(demoData.notifications(limit))
    : !orgId ? delay(EMPTY.notifications)
    : apiFetch<{ notifications: Notification[]; total: number }>('/api/dashboard/notifications', { params: { org_id: orgId, limit } }),

  acknowledgeNotification: (orgId: string, notificationId: string) =>
    isDemo(orgId) ? delay({ ok: true })
    : apiFetch<{ ok: boolean }>('/api/dashboard/notifications/acknowledge', { method: 'POST', params: { org_id: orgId, notification_id: notificationId } }),

  acknowledgeAllNotifications: (orgId: string) =>
    isDemo(orgId) ? delay({ ok: true })
    : apiFetch<{ ok: boolean }>('/api/dashboard/notifications/acknowledge-all', { method: 'POST', params: { org_id: orgId } }),

  connection: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.connection())
    : !orgId ? delay(EMPTY.connection)
    : apiFetch<{ connections: ConnectionInfo[] }>('/api/dashboard/connection', { params: { org_id: orgId } }),

  weeklyReport: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.weeklyReport())
    : !orgId ? delay(EMPTY.report)
    : apiFetch<{ report: any }>('/api/dashboard/weekly-report', { params: { org_id: orgId } }),

  updateInsightAction: (insightId: string, orgId: string, status: string) =>
    isDemo(orgId) ? delay({ success: true })
    : !orgId ? delay({ success: false })
    : apiFetch<any>(`/api/dashboard/insights/${insightId}/action`, { method: 'PATCH', params: { org_id: orgId, action_status: status } }),

  dayTransactions: (orgId: string, date: string) =>
    isDemo(orgId) ? delay(demoData.dayTransactions(date))
    : !orgId ? delay(EMPTY.transactions)
    : apiFetch<DayTransactions>('/api/dashboard/transactions/day', { params: { org_id: orgId, date } }),

  inventory: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.inventory())
    : !orgId ? delay(EMPTY.inventory)
    : apiFetch<InventoryData>('/api/dashboard/inventory', { params: { org_id: orgId } }),

  staff: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.staff())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/staff', { params: { org_id: orgId } }),

  margins: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.margins())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/margins', { params: { org_id: orgId, days: 365 } })
        .then((r: any) => ({
          summary: r.summary ?? {},
          // Backend returns snake_case `products`; the page renders MarginItem[]
          // under `items`. Map the real fields and default the demo-only
          // embellishments (waste/leakage/ingredients) so real margins render.
          items: (r.products ?? []).map((p: any) => {
            const revenueCents = p.revenue_cents ?? 0
            const costCents = p.cost_cents ?? 0
            const qty = p.quantity_sold ?? 0
            return {
              name: p.name ?? 'Unknown',
              revenueCents,
              costCents,
              marginCents: p.profit_cents ?? (revenueCents - costCents),
              marginPct: p.margin_pct ?? 0,
              leakageCents: 0,
              category: '',
              sellingPriceCents: qty ? Math.round(revenueCents / qty) : 0,
              monthlySales: qty,
              rawCostPerServingCents: qty ? Math.round(costCents / qty) : 0,
              wasteAdjustedCostCents: costCents,
              pourCostPct: revenueCents ? Math.round((costCents / revenueCents) * 100) : 0,
              marginPerUnitCents: qty ? Math.round((revenueCents - costCents) / qty) : 0,
              wasteFactor: 0,
              ingredients: [],
              isEstimated: p.is_estimated ?? false,
            }
          }),
        })),

  // Inline cost entry — set a product's unit cost (and optionally price) so
  // margins compute. Cost-of-goods isn't in the POS feed.
  updateProductCost: (orgId: string, productId: string, body: { cost_cents?: number; price_cents?: number }) =>
    apiFetch<{ ok: boolean; product_id: string; cost_cents: number | null; price_cents: number | null }>(
      `/api/dashboard/products/${productId}`, { method: 'PATCH', params: { org_id: orgId }, body },
    ),

  // Inventory cost-sheet processing (upload happens via supabase storage in the
  // component; these trigger AI extraction + poll status).
  processInventoryDoc: (orgId: string, docId: string) =>
    apiFetch<{ status: string; message?: string }>(
      `/api/inventory-docs/${orgId}/process/${docId}`, { method: 'POST', params: { org_id: orgId } },
    ),

  inventoryDocStatus: (orgId: string, docId: string) =>
    apiFetch<{ status: string; extracted_data?: any; error_message?: string }>(
      `/api/inventory-docs/${orgId}/status/${docId}`, { params: { org_id: orgId } },
    ),

  menuEngineering: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.menuEngineering())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/menu-engineering', { params: { org_id: orgId } }),

  anomalies: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.anomalies())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/anomalies', { params: { org_id: orgId } }),

  customers: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.customers())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/customers', { params: { org_id: orgId } }),

  agents: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.agents())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/agents', { params: { org_id: orgId } }),

  actions: (orgId: string) =>
    isDemo(orgId) ? delay(demoData.actions())
    : !orgId ? delay(EMPTY.empty)
    : apiFetch<any>('/api/dashboard/actions', { params: { org_id: orgId } }),

  squareAuthorize: (orgId: string) =>
    `${API_BASE}/api/square/authorize?org_id=${orgId}`,

  cameras: (orgId: string) =>
    isDemo(orgId) ? delay({ org_id: orgId, cameras: [], total: 0 })
    : !orgId ? delay({ org_id: '', cameras: [], total: 0 })
    : apiFetch<{ org_id: string; cameras: any[]; total: number }>(`/api/vision/cameras/${orgId}`),

  // ── Credit metering ──
  creditBalance: (merchantId: string) =>
    isDemo(merchantId) ? delay({ merchant_id: merchantId, balance: 1000, low_balance_threshold: 200, is_low: false, costs: {} })
    : !merchantId ? delay({ merchant_id: '', balance: 0, low_balance_threshold: 200, is_low: false, costs: {} })
    : apiFetch<{
        merchant_id: string
        balance: number
        low_balance_threshold: number
        is_low: boolean
        costs: Record<string, { credits: number; description: string }>
      }>(`/api/credits/balance/${merchantId}`),

  creditLedger: (merchantId: string, limit = 50) =>
    isDemo(merchantId) ? delay({ entries: [] })
    : !merchantId ? delay({ entries: [] })
    : apiFetch<{
        entries: Array<{
          id: string
          delta: number
          action_type: string
          action_id: string | null
          balance_after: number
          metadata: Record<string, unknown>
          created_at: string
        }>
      }>(`/api/credits/ledger/${merchantId}`, { params: { limit } }),

  creditPurchase: (body: {
    merchant_id: string
    pack_id: string
    customer_email: string
    customer_name?: string
    currency?: 'USD' | 'CAD'
  }) =>
    apiFetch<{
      purchase_id: string
      invoice_url: string
      invoice_id: string
      credit_amount: number
      price_cents: number
      currency: string
    }>('/api/credits/purchase', { method: 'POST', body }),

  // ── Schedule ──
  scheduleStaff: (merchantId: string) =>
    apiFetch<{ staff: StaffMemberDto[]; total: number }>(
      `/api/schedule/staff/${merchantId}`,
    ),

  scheduleCreateStaff: (body: Record<string, unknown>) =>
    apiFetch<{ staff_member: StaffMemberDto }>('/api/schedule/staff', {
      method: 'POST',
      body,
    }),

  scheduleUpdateStaff: (staffId: string, body: Record<string, unknown>) =>
    apiFetch<{ staff_id: string; updated: Record<string, unknown> }>(
      `/api/schedule/staff/${staffId}`,
      { method: 'PUT', body },
    ),

  scheduleDeleteStaff: (staffId: string) =>
    apiFetch<{ staff_id: string; active: boolean }>(
      `/api/schedule/staff/${staffId}`,
      { method: 'DELETE' },
    ),

  scheduleShifts: (merchantId: string, weekStart: string) =>
    apiFetch<{ shifts: ShiftDto[]; total: number }>(
      `/api/schedule/shifts/${merchantId}`,
      { params: { week_start: weekStart } },
    ),

  scheduleCreateShift: (body: Record<string, unknown>) =>
    apiFetch<{ shift: ShiftDto }>('/api/schedule/shifts', {
      method: 'POST',
      body,
    }),

  scheduleUpdateShift: (shiftId: string, body: Record<string, unknown>) =>
    apiFetch<{ shift_id: string; updated: Record<string, unknown> }>(
      `/api/schedule/shifts/${shiftId}`,
      { method: 'PUT', body },
    ),

  scheduleDeleteShift: (shiftId: string) =>
    apiFetch<{ shift_id: string; deleted: boolean }>(
      `/api/schedule/shifts/${shiftId}`,
      { method: 'DELETE' },
    ),

  schedulePublish: (body: {
    merchant_id: string
    portal_context: 'us' | 'ca'
    week_start_date: string
    published_by?: string
    notify_staff?: boolean
  }) =>
    apiFetch<{
      merchant_id: string
      week_start_date: string
      status: string
      published_at: string
      notified_count: number
    }>('/api/schedule/publish', { method: 'POST', body }),

  schedulePeakHours: (merchantId: string, weeks = 8) =>
    apiFetch<{
      merchant_id: string
      weeks: number
      peaks: PeakHourPoint[]
    }>(`/api/schedule/peak-hours/${merchantId}`, { params: { weeks } }),

  scheduleProjectedRevenue: (merchantId: string, weeks = 8) =>
    apiFetch<{
      merchant_id: string
      projected_weekly_cents: number
      weeks_analyzed: number
    }>(`/api/schedule/projected-revenue/${merchantId}`, { params: { weeks } }),

  scheduleRecommend: (
    merchantId: string,
    weekStart: string,
    weeksBack = 8,
    opts: { country?: string; lat?: number; lon?: number } = {},
  ) =>
    apiFetch<{
      recommendations: Array<{
        id: string
        day_of_week: number
        start_time: string
        end_time: string
        role: string
        reason: string
        priority: 'critical' | 'recommended' | 'optional'
        peak_intensity?: number
        factors?: Array<{ kind: 'peak' | 'holiday' | 'weather'; label: string }>
      }>
      signals?: Array<{ kind: 'holiday' | 'weather'; label: string }>
      merchant_id: string
      weeks_analyzed?: number
    }>(`/api/schedule/recommend/${merchantId}`, {
      method: 'POST',
      params: {
        week_start: weekStart,
        weeks_back: weeksBack,
        ...(opts.country ? { country: opts.country } : {}),
        ...(opts.lat != null ? { lat: opts.lat } : {}),
        ...(opts.lon != null ? { lon: opts.lon } : {}),
      },
    }),
}
