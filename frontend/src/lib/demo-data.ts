/**
 * Demo Data Provider
 * 
 * Generates realistic POS analytics data for a fictional "Sunrise Coffee Co."
 * Used when org_id is 'demo' — no backend needed.
 */

import type {
  Overview, MoneyLeftScore, DailyRevenue, WeeklyRevenue, RevenueData,
  HourlyData, ProductPerf, ProductsData, Insight, Forecast,
  Notification, ConnectionInfo,
} from './api'

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

const PRODUCTS = [
  { name: 'Espresso', sku: 'ESP-001', price: 350, category: 'drinks', popularity: 0.95 },
  { name: 'Cappuccino', sku: 'CAP-001', price: 525, category: 'drinks', popularity: 0.90 },
  { name: 'Iced Latte', sku: 'ICL-001', price: 575, category: 'drinks', popularity: 0.85 },
  { name: 'Cold Brew', sku: 'CDB-001', price: 500, category: 'drinks', popularity: 0.80 },
  { name: 'Matcha Latte', sku: 'MAT-001', price: 625, category: 'drinks', popularity: 0.65 },
  { name: 'Hot Chocolate', sku: 'HOT-001', price: 475, category: 'drinks', popularity: 0.50 },
  { name: 'Chai Latte', sku: 'CHA-001', price: 550, category: 'drinks', popularity: 0.55 },
  { name: 'Drip Coffee', sku: 'DRP-001', price: 275, category: 'drinks', popularity: 0.70 },
  { name: 'Blueberry Muffin', sku: 'MUF-001', price: 395, category: 'food', popularity: 0.75 },
  { name: 'Croissant', sku: 'CRO-001', price: 425, category: 'food', popularity: 0.80 },
  { name: 'Avocado Toast', sku: 'AVO-001', price: 895, category: 'food', popularity: 0.60 },
  { name: 'Breakfast Sandwich', sku: 'BKF-001', price: 795, category: 'food', popularity: 0.70 },
  { name: 'Banana Bread', sku: 'BAN-001', price: 375, category: 'food', popularity: 0.55 },
  { name: 'Cookie', sku: 'COK-001', price: 295, category: 'food', popularity: 0.45 },
]

// ─── Daily Revenue ──────────────────────────────────────

function generateDailyRevenue(days: number): DailyRevenue[] {
  seed = 42 // Reset seed for consistency
  const result: DailyRevenue[] = []

  for (let i = days - 1; i >= 0; i--) {
    const date = daysAgo(i)
    const d = new Date(date)
    const dow = d.getDay() // 0=Sun, 6=Sat

    // Base revenue: weekends higher, Mon-Fri varies
    const isWeekend = dow === 0 || dow === 6
    const baseRevenue = isWeekend
      ? seededRandRange(180000, 260000)  // $1800-$2600
      : seededRandRange(120000, 200000)  // $1200-$2000

    // Add slight upward trend over 30 days
    const trendBoost = Math.floor((days - i) * 800)
    const revenue = baseRevenue + trendBoost

    // Transactions: ~$8-12 avg ticket
    const avgTicket = seededRandRange(850, 1200)
    const transactions = Math.floor(revenue / avgTicket)
    const customers = Math.floor(transactions * 0.85)
    const refunds = seededRandRange(0, 3) * seededRandRange(300, 800)
    const tax = Math.floor(revenue * 0.085)
    const tip = Math.floor(revenue * seededRand() * 0.12)
    const discount = seededRandRange(0, 5) * seededRandRange(100, 500)

    result.push({
      date,
      revenue_cents: revenue,
      transactions,
      avg_ticket_cents: avgTicket,
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
  // Typical coffee shop hourly pattern
  const hourlyPattern = [
    0, 0, 0, 0, 0, 5,       // 12am-5am
    15, 45, 85, 70, 55, 65,  // 6am-11am (morning rush)
    80, 70, 50, 40, 35, 30,  // 12pm-5pm (lunch + afternoon)
    20, 10, 5, 0, 0, 0,      // 6pm-11pm
  ]

  return {
    hourly: hourlyPattern.map((pct, hour) => {
      const revenue = Math.floor(pct * 280) // scale
      const sales = Math.max(1, Math.floor(pct * 2.8))
      return {
        hour: `${hour.toString().padStart(2, '0')}:00`,
        revenue_cents: revenue * 100,
        sales,
        refunds: pct > 40 ? rand(0, 1) : 0,
        avg_ticket_cents: pct > 0 ? rand(800, 1200) : 0,
        customers: Math.floor(sales * 0.85),
      }
    }),
  }
}

// ─── Products ───────────────────────────────────────────

function generateProducts(days: number): ProductsData {
  seed = 100

  const products: ProductPerf[] = PRODUCTS.map(p => {
    const baseQty = Math.floor(p.popularity * 15 * days)
    const qty = seededRandRange(Math.floor(baseQty * 0.8), Math.floor(baseQty * 1.2))
    const revenue = qty * p.price

    const daily = []
    for (let i = days - 1; i >= 0; i--) {
      const dayQty = seededRandRange(
        Math.floor(p.popularity * 8),
        Math.floor(p.popularity * 22)
      )
      daily.push({
        date: daysAgo(i),
        revenue_cents: dayQty * p.price,
        quantity: dayQty,
      })
    }

    return {
      product_id: uuid(),
      name: p.name,
      sku: p.sku,
      price_cents: p.price,
      total_revenue_cents: revenue,
      total_quantity: qty,
      times_sold: Math.floor(qty * 0.9),
      daily,
    }
  })

  // Sort by revenue descending
  products.sort((a, b) => b.total_revenue_cents - a.total_revenue_cents)

  return {
    products,
    total_products: products.length,
    period_days: days,
  }
}

// ─── Insights ───────────────────────────────────────────

function generateInsights(): { insights: Insight[]; total: number } {
  const insights: Insight[] = [
    {
      id: uuid(),
      type: 'money_left',
      title: 'Weekend upselling opportunity',
      summary: 'Your Saturday customers spend 35% more when offered a pastry with their drink. Implementing a simple "add a pastry for $2?" prompt could capture an estimated $840/month in additional revenue.',
      details: { avg_weekend_ticket: 1245, avg_weekday_ticket: 920 },
      impact_cents: 84000,
      confidence: 0.87,
      action_status: 'pending',
      valid_until: daysFromNow(14),
      created_at: hoursAgo(2),
    },
    {
      id: uuid(),
      type: 'pricing',
      title: 'Matcha Latte underpriced by $0.75',
      summary: 'Competitor analysis and demand elasticity suggest your Matcha Latte at $6.25 is underpriced. Similar cafes in your area charge $7.00-$7.50. A $0.75 increase would likely retain 95% of volume.',
      details: { current_price: 625, suggested_price: 700, competitors_avg: 725 },
      impact_cents: 52000,
      confidence: 0.82,
      action_status: 'pending',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(5),
    },
    {
      id: uuid(),
      type: 'product_recommendation',
      title: 'Croissant + Cappuccino bundle potential',
      summary: '68% of croissant buyers also purchase a cappuccino. A $8.50 combo (vs $9.50 separate) could increase combo purchases by 40% and boost morning ticket averages.',
      details: { combo_rate: 0.68, suggested_bundle_price: 850 },
      impact_cents: 38000,
      confidence: 0.91,
      action_status: 'viewed',
      valid_until: daysFromNow(21),
      created_at: hoursAgo(12),
    },
    {
      id: uuid(),
      type: 'staffing',
      title: 'Overstaffed Tuesday afternoons',
      summary: 'Tuesday 2-5pm has the lowest revenue per labor hour ($32/hr vs $68/hr average). Consider reducing to 2 staff from 3 during this window to save ~$520/month.',
      details: { revenue_per_labor_hour: 3200, avg_revenue_per_labor_hour: 6800 },
      impact_cents: 52000,
      confidence: 0.78,
      action_status: 'pending',
      valid_until: daysFromNow(14),
      created_at: hoursAgo(24),
    },
    {
      id: uuid(),
      type: 'anomaly',
      title: 'Unusual refund spike detected',
      summary: 'Refunds were 3x higher than normal last Wednesday. 5 of 8 refunds were for Cold Brew — possible quality issue or new barista training needed.',
      details: { refund_count: 8, normal_avg: 2.5, product: 'Cold Brew' },
      impact_cents: -24000,
      confidence: 0.94,
      action_status: 'viewed',
      valid_until: daysFromNow(7),
      created_at: hoursAgo(48),
    },
    {
      id: uuid(),
      type: 'seasonal',
      title: 'Cold Brew demand rising — stock up',
      summary: 'Cold Brew sales have increased 45% over the past 2 weeks as temperatures rise. Based on last year\'s data, expect another 30% increase in the next month. Consider increasing cold brew prep by 2 batches/day.',
      details: { growth_2w: 0.45, predicted_growth_4w: 0.30 },
      impact_cents: 28000,
      confidence: 0.85,
      action_status: 'pending',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(6),
    },
    {
      id: uuid(),
      type: 'money_left',
      title: 'Happy hour could fill 4-6pm gap',
      summary: 'Revenue drops 62% between 4-6pm. A "Happy Hour" discount on pastries (50% off day-old items) could recover $15-25/day while reducing food waste.',
      details: { gap_revenue_pct: 0.38, estimated_recovery: 2000 },
      impact_cents: 60000,
      confidence: 0.73,
      action_status: 'pending',
      valid_until: daysFromNow(21),
      created_at: hoursAgo(36),
    },
    {
      id: uuid(),
      type: 'benchmark',
      title: 'Your avg ticket beats local average',
      summary: 'At $10.42 avg ticket, you\'re 18% above the local coffee shop average of $8.82. Your food attach rate (42%) is the key driver — most competitors are under 30%.',
      details: { your_avg: 1042, local_avg: 882, food_attach: 0.42 },
      impact_cents: null,
      confidence: 0.88,
      action_status: 'viewed',
      valid_until: null,
      created_at: hoursAgo(72),
    },
  ]

  return { insights, total: insights.length }
}

// ─── Forecasts ──────────────────────────────────────────

function generateForecasts(): { forecasts: Forecast[]; total: number } {
  const forecasts: Forecast[] = []

  // Daily revenue forecasts for next 14 days
  for (let i = 1; i <= 14; i++) {
    const date = daysFromNow(i)
    const d = new Date(date)
    const dow = d.getDay()
    const isWeekend = dow === 0 || dow === 6

    const base = isWeekend ? rand(210000, 280000) : rand(150000, 220000)
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

  // Weekly forecast
  forecasts.push({
    id: uuid(),
    type: 'weekly_revenue',
    period_start: daysFromNow(1),
    period_end: daysFromNow(7),
    predicted_cents: 1350000,
    lower_bound_cents: 1150000,
    upper_bound_cents: 1550000,
    confidence: 0.84,
  })

  // Monthly forecast
  forecasts.push({
    id: uuid(),
    type: 'monthly_revenue',
    period_start: daysFromNow(1),
    period_end: daysFromNow(30),
    predicted_cents: 5600000,
    lower_bound_cents: 4800000,
    upper_bound_cents: 6400000,
    confidence: 0.76,
  })

  return { forecasts, total: forecasts.length }
}

// ─── Notifications ──────────────────────────────────────

function generateNotifications(): { notifications: Notification[]; total: number } {
  const notifications: Notification[] = [
    {
      id: uuid(),
      title: 'Revenue milestone reached!',
      body: 'Congratulations! You hit $50,000 in monthly revenue for the first time. That\'s a 12% increase over last month.',
      priority: 'normal',
      source_type: 'event',
      status: 'unread',
      created_at: hoursAgo(1),
      acknowledged_at: null,
    },
    {
      id: uuid(),
      title: 'New AI insight available',
      body: 'A new pricing optimization opportunity was detected for your Matcha Latte. Review it in the Insights tab.',
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
      body: '5 Cold Brew refunds in one day is 3x your normal rate. This may indicate a quality issue.',
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
      title: 'Peak hour alert: Morning rush exceeded forecast',
      body: 'Today\'s 7-9am revenue was 22% above forecast. Consider adding extra staff for tomorrow morning.',
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

function generateOverview(daily: DailyRevenue[]): Overview {
  const totalRevenue = daily.reduce((s, d) => s + d.revenue_cents, 0)
  const totalTx = daily.reduce((s, d) => s + d.transactions, 0)
  const avgTicket = Math.floor(totalRevenue / totalTx)

  // Compare to "prior 30 days" (simulated)
  const priorRevenue = Math.floor(totalRevenue * 0.88) // 12% growth
  const changePct = ((totalRevenue - priorRevenue) / priorRevenue) * 100

  const moneyLeft: MoneyLeftScore = {
    id: uuid(),
    total_score_cents: 234000,
    components: {
      pricing_opportunity: { amount_cents: 52000, label: 'Pricing', description: 'Items underpriced vs market' },
      upsell_potential: { amount_cents: 84000, label: 'Upselling', description: 'Cross-sell & upsell potential' },
      waste_reduction: { amount_cents: 38000, label: 'Waste', description: 'Food waste & overstock savings' },
      staffing_optimization: { amount_cents: 32000, label: 'Staffing', description: 'Labor cost optimization' },
      gap_filling: { amount_cents: 28000, label: 'Gap Filling', description: 'Revenue during slow periods' },
    },
    scored_at: hoursAgo(1),
  }

  return {
    revenue_cents_30d: totalRevenue,
    revenue_change_pct: Math.round(changePct * 10) / 10,
    transaction_count_30d: totalTx,
    avg_ticket_cents: avgTicket,
    money_left_score: moneyLeft,
    connection: {
      status: 'active',
      provider: 'square',
      last_sync_at: hoursAgo(0.5),
    },
    days_with_data: 30,
  }
}

// ─── Public API ─────────────────────────────────────────

const daily30 = generateDailyRevenue(30)
const daily90 = generateDailyRevenue(90)

export const demoData = {
  overview: () => generateOverview(daily30),

  revenue: (days: number): RevenueData => {
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

  weeklyReport: () => ({
    report: {
      period: `${daysAgo(7)} to ${daysAgo(1)}`,
      total_revenue_cents: 1285000,
      revenue_change_pct: 8.2,
      top_product: 'Cappuccino',
      insights_generated: 3,
      forecast_accuracy: 0.94,
    },
  }),
}
