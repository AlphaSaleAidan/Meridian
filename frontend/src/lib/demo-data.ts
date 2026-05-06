/**
 * Demo Data Provider
 *
 * Generates realistic POS analytics data for the selected business type.
 * Used when org_id is 'demo' — no backend needed.
 */

import type {
  Overview, DailyRevenue, WeeklyRevenue, RevenueData,
  HourlyData, ProductsData, Insight, Forecast,
  Notification, ConnectionInfo,
  DayTransactions, TransactionDetail, TransactionLineItem,
  InventoryData, InventoryItem,
} from './api'

import { getActiveBusinessType } from './demo-context'
import { getIndustryOverrides } from './demo-industries'

// ─── Helpers ────────────────────────────────────────────

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
}

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

function hoursAgo(h: number): string {
  const d = new Date()
  d.setHours(d.getHours() - h)
  return d.toISOString()
}

function daysFromNow(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

function rand(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

function randFloat(min: number, max: number): number {
  return min + Math.random() * (max - min)
}

// Seed-based pseudo-random for consistent demo data per session
let seed = 42
function seededRand(): number {
  seed = (seed * 16807) % 2147483647
  return (seed - 1) / 2147483646
}

function seededRandRange(min: number, max: number): number {
  return Math.floor(seededRand() * (max - min + 1)) + min
}

// ─── Products ───────────────────────────────────────────
// Industry-specific products are now sourced from demo-industries.ts via getIndustryOverrides()

// ─── Daily Revenue ──────────────────────────────────────

function generateDailyRevenue(days: number): DailyRevenue[] {
  seed = 42
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const dailyBase = overrides.overview.revenue_cents_30d / 30
  const avgTicket = overrides.overview.avg_ticket_cents
  const result: DailyRevenue[] = []

  for (let i = days - 1; i >= 0; i--) {
    const date = daysAgo(i)
    const d = new Date(date)
    const dow = d.getDay()

    const isWeekend = dow === 0 || dow === 6
    const dayMult = isWeekend ? seededRand() * 0.3 + 1.0 : seededRand() * 0.4 + 0.7
    const trendBoost = Math.floor((days - i) * (dailyBase * 0.004))
    const revenue = Math.floor(dailyBase * dayMult) + trendBoost

    const ticketJitter = seededRandRange(Math.floor(avgTicket * 0.85), Math.floor(avgTicket * 1.15))
    const transactions = Math.max(1, Math.floor(revenue / ticketJitter))
    const customers = Math.floor(transactions * 0.85)
    const refunds = seededRandRange(0, 3) * seededRandRange(Math.floor(avgTicket * 0.3), Math.floor(avgTicket * 0.8))
    const tax = Math.floor(revenue * 0.085)
    const tip = Math.floor(revenue * seededRand() * 0.12)
    const discount = seededRandRange(0, 5) * seededRandRange(Math.floor(avgTicket * 0.1), Math.floor(avgTicket * 0.4))

    result.push({
      date,
      revenue_cents: revenue,
      transactions,
      avg_ticket_cents: ticketJitter,
      refund_cents: refunds,
      tax_cents: tax,
      tip_cents: tip,
      discount_cents: discount,
      customers,
    })
  }

  return result
}

function generateWeeklyRevenue(daily: DailyRevenue[]): WeeklyRevenue[] {
  const weeks: Record<string, { revenue: number; tx: number; ticket: number[] }> = {}
  
  daily.forEach(d => {
    const date = new Date(d.date)
    const weekStart = new Date(date)
    weekStart.setDate(date.getDate() - date.getDay())
    const key = weekStart.toISOString().slice(0, 10)
    
    if (!weeks[key]) weeks[key] = { revenue: 0, tx: 0, ticket: [] }
    weeks[key].revenue += d.revenue_cents
    weeks[key].tx += d.transactions
    weeks[key].ticket.push(d.avg_ticket_cents)
  })

  return Object.entries(weeks).map(([week, w]) => ({
    week,
    revenue_cents: w.revenue,
    transactions: w.tx,
    avg_ticket_cents: Math.floor(w.ticket.reduce((a, b) => a + b, 0) / w.ticket.length),
  })).sort((a, b) => a.week.localeCompare(b.week))
}

// ─── Hourly Revenue ─────────────────────────────────────

function generateHourlyData(): HourlyData {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const hourlyPattern = overrides.hourlyDistribution
  const avgTicket = overrides.overview.avg_ticket_cents
  const ticketLow = Math.floor(avgTicket * 0.8)
  const ticketHigh = Math.floor(avgTicket * 1.2)

  return {
    hourly: hourlyPattern.map((pct, hour) => {
      const revenue = Math.floor(pct * 280)
      const sales = Math.max(1, Math.floor(pct * 2.8))
      return {
        hour: `${hour.toString().padStart(2, '0')}:00`,
        revenue_cents: revenue * 100,
        sales,
        refunds: pct > 40 ? rand(0, 1) : 0,
        avg_ticket_cents: pct > 0 ? rand(ticketLow, ticketHigh) : 0,
        customers: Math.floor(sales * 0.85),
      }
    }),
  }
}

// ─── Products ───────────────────────────────────────────

function generateProducts(days: number): ProductsData {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const products = overrides.products

  return {
    products,
    total_products: products.length,
    period_days: days,
  }
}

// ─── Insights ───────────────────────────────────────────

function generateInsights(): { insights: Insight[]; total: number } {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const insights = overrides.insights
  return { insights, total: insights.length }
}
// ─── Forecasts ──────────────────────────────────────────

function generateForecasts(): { forecasts: Forecast[]; total: number } {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const dailyBase = overrides.overview.revenue_cents_30d / 30
  const forecasts: Forecast[] = []

  for (let i = 1; i <= 14; i++) {
    const date = daysFromNow(i)
    const d = new Date(date)
    const dow = d.getDay()
    const isWeekend = dow === 0 || dow === 6

    const mult = isWeekend ? randFloat(1.0, 1.3) : randFloat(0.7, 1.05)
    const base = Math.floor(dailyBase * mult)
    const lower = Math.floor(base * 0.82)
    const upper = Math.floor(base * 1.18)
    const confidence = randFloat(0.72, 0.92)

    forecasts.push({
      id: uuid(),
      type: 'daily_revenue',
      period_start: date,
      period_end: date,
      predicted_cents: base,
      lower_bound_cents: lower,
      upper_bound_cents: upper,
      confidence,
    })
  }

  const weeklyBase = Math.floor(dailyBase * 7)
  forecasts.push({
    id: uuid(),
    type: 'weekly_revenue',
    period_start: daysFromNow(1),
    period_end: daysFromNow(7),
    predicted_cents: weeklyBase,
    lower_bound_cents: Math.floor(weeklyBase * 0.85),
    upper_bound_cents: Math.floor(weeklyBase * 1.15),
    confidence: 0.84,
  })

  return { forecasts, total: forecasts.length }
}

// ─── Notifications ──────────────────────────────────────

function generateNotifications(): { notifications: Notification[]; total: number } {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const topProduct = overrides.products[0]?.name || 'Top Product'
  const secondProduct = overrides.products[1]?.name || 'Product'

  const notifications: Notification[] = [
    {
      id: uuid(),
      title: 'Revenue milestone reached!',
      body: 'Congratulations! You hit a new monthly revenue milestone. That\'s a 12% increase over last month.',
      priority: 'normal',
      source_type: 'event',
      status: 'unread',
      created_at: hoursAgo(1),
      acknowledged_at: null,
    },
    {
      id: uuid(),
      title: 'New AI insight available',
      body: `A new pricing optimization opportunity was detected for your ${secondProduct}. Review it in the Insights tab.`,
      priority: 'normal',
      source_type: 'insight',
      status: 'unread',
      created_at: hoursAgo(5),
      acknowledged_at: null,
    },
    {
      id: uuid(),
      title: 'Weekly report ready',
      body: 'Your weekly performance report for April 7-13 is ready. Revenue was up 8% vs the previous week.',
      priority: 'normal',
      source_type: 'report',
      status: 'read',
      created_at: hoursAgo(24),
      acknowledged_at: hoursAgo(20),
    },
    {
      id: uuid(),
      title: 'Unusual refund activity detected',
      body: `5 ${topProduct} refunds in one day is 3x your normal rate. This may indicate a quality issue.`,
      priority: 'high',
      source_type: 'alert',
      status: 'read',
      created_at: hoursAgo(48),
      acknowledged_at: hoursAgo(46),
    },
    {
      id: uuid(),
      title: 'Square data sync complete',
      body: 'Successfully synced 847 transactions from the past 30 days. All data is up to date.',
      priority: 'low',
      source_type: 'event',
      status: 'read',
      created_at: hoursAgo(72),
      acknowledged_at: hoursAgo(70),
    },
    {
      id: uuid(),
      title: 'Forecast accuracy update',
      body: 'Last week\'s revenue forecast was 94% accurate ($1,320 predicted vs $1,285 actual). Model confidence is improving.',
      priority: 'low',
      source_type: 'report',
      status: 'read',
      created_at: hoursAgo(96),
      acknowledged_at: hoursAgo(90),
    },
    {
      id: uuid(),
      title: 'Peak hour alert: Rush exceeded forecast',
      body: 'Today\'s peak hour revenue was 22% above forecast. Consider adding extra staff for tomorrow.',
      priority: 'normal',
      source_type: 'alert',
      status: 'unread',
      created_at: hoursAgo(3),
      acknowledged_at: null,
    },
  ]

  return { notifications, total: notifications.length }
}

// ─── Connection ─────────────────────────────────────────

function generateConnection(): { connections: ConnectionInfo[] } {
  return {
    connections: [
      {
        id: uuid(),
        provider: 'square',
        status: 'active',
        merchant_id: 'MLQ1F2Z...',
        last_sync_at: hoursAgo(0.5),
        historical_import_complete: true,
        last_error: null,
        created_at: daysAgo(30) + 'T10:00:00Z',
      },
    ],
  }
}

// ─── Overview ───────────────────────────────────────────

function generateOverview(_daily: DailyRevenue[]): Overview {
  return getIndustryOverrides(getActiveBusinessType()).overview
}

// ─── Transaction Drill-Down ─────────────────────────────

function generateDayTransactions(date: string): DayTransactions {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const industryProducts = overrides.products
  const dailyTraffic = overrides.overview.transaction_count_30d / 30

  const dateSeed = date.split('-').reduce((a, b) => a + parseInt(b), 0)
  let localSeed = dateSeed * 16807

  function lr() {
    localSeed = (localSeed * 16807) % 2147483647
    return (localSeed - 1) / 2147483646
  }

  function lrRange(min: number, max: number) {
    return Math.floor(lr() * (max - min + 1)) + min
  }

  const paymentMethods = ['card', 'card', 'card', 'cash', 'apple_pay', 'google_pay']
  const txCount = lrRange(Math.floor(dailyTraffic * 0.7), Math.floor(dailyTraffic * 1.3))
  const transactions: TransactionDetail[] = []
  const productQtyCounts: Record<string, number> = {}

  for (let t = 0; t < txCount; t++) {
    const hour = lrRange(6, 19)
    const minute = lrRange(0, 59)
    const second = lrRange(0, 59)
    const timestamp = `${date}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}:${String(second).padStart(2, '0')}Z`

    const itemCount = lr() < 0.4 ? 1 : lr() < 0.75 ? 2 : 3
    const items: TransactionLineItem[] = []
    let txTotal = 0

    const usedProducts = new Set<number>()
    for (let j = 0; j < itemCount; j++) {
      let pIdx: number
      do {
        pIdx = lrRange(0, industryProducts.length - 1)
      } while (usedProducts.has(pIdx) && usedProducts.size < industryProducts.length)
      usedProducts.add(pIdx)

      const p = industryProducts[pIdx]
      const qty = lr() < 0.8 ? 1 : 2
      const unitPrice = p.price_cents ?? 0
      const itemTotal = unitPrice * qty
      txTotal += itemTotal

      productQtyCounts[p.name] = (productQtyCounts[p.name] || 0) + qty

      items.push({
        id: uuid(),
        product_name: p.name,
        sku: p.sku ?? '',
        quantity: qty,
        unit_price_cents: unitPrice,
        total_cents: itemTotal,
        category: 'general',
      })
    }

    const hasTip = lr() < 0.35
    const tipCents = hasTip ? lrRange(50, Math.floor(txTotal * 0.2)) : 0
    const hasDiscount = lr() < 0.08
    const discountCents = hasDiscount ? lrRange(100, Math.floor(txTotal * 0.15)) : 0
    const hasRefund = lr() < 0.02
    const refundCents = hasRefund ? txTotal : 0

    transactions.push({
      id: uuid(),
      created_at: timestamp,
      total_cents: txTotal - discountCents + tipCents,
      tip_cents: tipCents,
      discount_cents: discountCents,
      refund_cents: refundCents,
      payment_method: paymentMethods[lrRange(0, paymentMethods.length - 1)],
      items,
    })
  }

  transactions.sort((a, b) => a.created_at.localeCompare(b.created_at))

  const totalRev = transactions.reduce((s, t) => s + t.total_cents, 0)
  const uniqueProducts = new Set(transactions.flatMap(t => t.items.map(i => i.product_name))).size

  let topProduct = ''
  let topQty = 0
  for (const [name, qty] of Object.entries(productQtyCounts)) {
    if (qty > topQty) {
      topProduct = name
      topQty = qty
    }
  }

  return {
    date,
    transactions,
    summary: {
      total_revenue_cents: totalRev,
      transaction_count: txCount,
      unique_products: uniqueProducts,
      avg_ticket_cents: Math.floor(totalRev / txCount),
      top_product: topProduct,
      top_product_qty: topQty,
    },
  }
}

// ─── Inventory ──────────────────────────────────────────

function generateInventory(): InventoryData {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const industryProducts = overrides.products

  const items: InventoryItem[] = industryProducts.map((p, i) => {
    seed = 100 + i * 7
    const dailyUsage = Math.max(1, Math.floor(p.total_quantity / 30))
    const currentStock = seededRandRange(dailyUsage * 2, dailyUsage * 14)
    const reorderPoint = Math.ceil(dailyUsage * 3)
    const daysUntil = dailyUsage > 0 ? Math.max(0, Math.floor((currentStock - reorderPoint) / dailyUsage)) : null
    const trendRoll = seededRand()
    const trend = trendRoll < 0.3 ? 'rising' as const : trendRoll < 0.6 ? 'falling' as const : 'stable' as const
    const trendPct = trend === 'rising' ? seededRandRange(5, 25) : trend === 'falling' ? -seededRandRange(5, 20) : seededRandRange(-3, 3)

    return {
      id: uuid(),
      product_name: p.name,
      sku: p.sku ?? '',
      category: 'general',
      current_stock: currentStock,
      unit: 'units',
      reorder_point: reorderPoint,
      predicted_daily_usage: dailyUsage,
      days_until_reorder: daysUntil,
      trend,
      trend_pct: trendPct,
      last_updated: hoursAgo(seededRandRange(1, 12)),
    }
  })

  const lowStock = items.filter(i => i.days_until_reorder !== null && i.days_until_reorder <= 2).length
  const overstocked = items.filter(i => i.current_stock > i.predicted_daily_usage * 12).length
  const trendingUp = items.filter(i => i.trend === 'rising').length

  return { items, total: items.length, alerts: { low_stock: lowStock, overstocked, trending_up: trendingUp } }
}

// ─── Public API ─────────────────────────────────────────

let _cachedType: string | null = null
let _daily30: DailyRevenue[] = []
let _daily90: DailyRevenue[] = []

function getDailyCache() {
  const bt = getActiveBusinessType()
  if (_cachedType !== bt) {
    _cachedType = bt
    _daily30 = generateDailyRevenue(30)
    _daily90 = generateDailyRevenue(90)
  }
  return { daily30: _daily30, daily90: _daily90 }
}

export const demoData = {
  overview: () => {
    const { daily30 } = getDailyCache()
    return generateOverview(daily30)
  },

  revenue: (days: number): RevenueData => {
    const { daily30, daily90 } = getDailyCache()
    const daily = days <= 30 ? daily30 : daily90.slice(-days)
    return {
      daily,
      weekly: generateWeeklyRevenue(daily),
    }
  },

  hourlyRevenue: (): HourlyData => generateHourlyData(),

  products: (days: number): ProductsData => generateProducts(days),

  insights: (limit: number) => {
    const all = generateInsights()
    return { insights: all.insights.slice(0, limit), total: all.total }
  },

  forecasts: () => generateForecasts(),

  notifications: (limit: number) => {
    const all = generateNotifications()
    return { notifications: all.notifications.slice(0, limit), total: all.total }
  },

  connection: () => generateConnection(),

  dayTransactions: (date: string) => generateDayTransactions(date),

  inventory: () => generateInventory(),

  weeklyReport: () => {
    const overrides = getIndustryOverrides(getActiveBusinessType())
    const topProduct = overrides.products[0]?.name || 'Top Product'
    const weeklyRev = Math.floor(overrides.overview.revenue_cents_30d / 4.3)
    return {
      report: {
        period: `${daysAgo(7)} to ${daysAgo(1)}`,
        total_revenue_cents: weeklyRev,
        revenue_change_pct: 8.2,
        top_product: topProduct,
        insights_generated: 3,
        forecast_accuracy: 0.94,
      },
    }
  },
}
