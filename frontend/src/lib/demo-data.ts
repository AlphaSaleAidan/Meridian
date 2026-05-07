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
  DayTransactions, TransactionDetail, TransactionLineItem,
  InventoryData, InventoryItem,
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
      title: '💸 $2,340/Month Left on the Table — Here\'s How to Capture It',
      summary: 'Meridian\'s Money Left on Table analysis identifies $2,340/month in unrealized revenue across your operations. This score is calculated using five economic dimensions, each benchmarked against industry standards:\n\n*Component breakdown:*\n  • Pricing Optimization: $840/mo\n  • Peak Hour Staffing: $520/mo\n  • Dead Stock Clearance: $450/mo\n  • Discount Leakage: $310/mo\n  • Schedule Gap Recovery: $220/mo\n\nMcKinsey research confirms most SMBs leave 2-7% of revenue on the table through suboptimal pricing, staffing, and inventory management — and that structured optimization yields an average 3.3% revenue lift [McKinsey & Company, 2024].\n\n*Prioritized action plan:*\n1. Increase Matcha Latte and Cold Brew prices by $0.50-$0.75 (est. $840/mo)\n2. Add one staff member during 7-9am peak window (est. $520/mo)\n3. Clear 4 dead-stock items via bundles or markdowns (est. $450/mo)',
      details: {
        components: {
          pricing: { amount_cents: 84000, detail: 'Underpriced items with inelastic demand' },
          staffing: { amount_cents: 52000, detail: 'Understaffed peak hours losing throughput' },
          dead_stock: { amount_cents: 45000, detail: 'Zero-velocity inventory holding costs' },
          discounts: { amount_cents: 31000, detail: 'Excessive discounting above 3% benchmark' },
          scheduling: { amount_cents: 22000, detail: 'Revenue gaps in recoverable dayparts' },
        },
        citations: ['mckinsey_pricing', 'hbr_pricing_power', 'mit_sloan_scheduling', 'nra_food_waste'],
      },
      impact_cents: 234000,
      confidence: 0.65,
      action_status: 'accepted',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(1),
    },
    {
      id: uuid(),
      type: 'pricing',
      title: '💰 3 Data-Backed Pricing Opportunities — $840/Month Potential',
      summary: 'Our analysis identified 3 products where data supports a price adjustment. Top opportunity: *Matcha Latte* — current price $6.25, demand elasticity analysis shows highly inelastic demand (elasticity: -0.3), supporting a $0.75 increase.\n\n*Economic rationale:*\nHarvard Business Review research demonstrates that a 1% price increase yields an average 11.1% improvement in operating profit — making pricing the single highest-leverage variable in the P&L [Harvard Business Review, 2023]. Restaurants using data-driven menu engineering achieve 8-15% higher gross margins vs. cost-plus pricing [Cornell Hospitality Quarterly, 2024].\n\nMeta-analysis data shows food service items with <5% price increases exhibit near-zero demand reduction (mean elasticity: -1.2 for staples) [Journal of Marketing Research, 2023].\n\n*Implementation:*\n1. Matcha Latte: $6.25 → $7.00 (+12%, still below competitor avg of $7.50)\n2. Cold Brew: $5.00 → $5.50 (+10%, high demand inelasticity)\n3. Avocado Toast: $8.95 → $9.95 (+11%, premium positioning supports it)\n4. Total combined potential: $840/month',
      details: {
        opportunities: [
          { name: 'Matcha Latte', current: 625, suggested: 700, elasticity: -0.3 },
          { name: 'Cold Brew', current: 500, suggested: 550, elasticity: -0.4 },
          { name: 'Avocado Toast', current: 895, suggested: 995, elasticity: -0.6 },
        ],
        citations: ['hbr_pricing_power', 'cornell_menu_pricing', 'jmr_elasticity', 'mckinsey_pricing'],
      },
      impact_cents: 84000,
      confidence: 0.82,
      action_status: 'pending',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(3),
    },
    {
      id: uuid(),
      type: 'staffing',
      title: '🔥 Golden Window: 7:00–10:00 AM — 47% of Revenue in 3 Hours',
      summary: 'Your most profitable operating window is 7:00-10:00 AM, concentrating 47% of daily revenue into roughly 3 hours. This exceeds the industry benchmark of 45% for Coffee Shop / Café businesses.\n\n*Staffing economics:*\nMIT Sloan research shows each understaffed peak hour costs 8-15% of that hour\'s potential revenue through lost sales, longer wait times, and reduced upselling capacity [MIT Sloan Management Review, 2024]. Cornell\'s demand-driven scheduling research found that aligning staff to 15-minute demand blocks (vs. shift-based) improves revenue-per-labor-hour by 18% [Cornell Center for Hospitality Research, 2023].\n\n*Action items:*\n1. Ensure maximum staffing during 7:00-10:00 AM — every position filled\n2. Pre-prep high-volume items 30 min before peak to maximize throughput\n3. Schedule breaks and training during off-peak hours only\n4. Track revenue-per-labor-hour weekly to optimize scheduling',
      details: {
        golden_window: { label: '7:00-10:00 AM', revenue_share_pct: 47 },
        benchmark_share_pct: 45,
        citations: ['mit_sloan_scheduling', 'cornell_labor_scheduling', 'bls_labor_costs'],
      },
      impact_cents: 52000,
      confidence: 0.88,
      action_status: 'completed',
      valid_until: daysFromNow(14),
      created_at: hoursAgo(2),
    },
    {
      id: uuid(),
      type: 'product_recommendation',
      title: '⭐ Star Products Identified — Protect & Promote These Revenue Drivers',
      summary: 'Your top performers (Cappuccino, Iced Latte, Croissant) collectively account for 42% of total revenue. In menu engineering terms, these are your "Stars" — high popularity, high profitability items that form the backbone of your product mix [Cornell Hospitality Quarterly, 2024].\n\n*Strategic recommendations:*\n1. *Never stock out* — Each lost sale of a star product costs your average ticket plus the probability of a walk-away (estimated 15-20% of customers leave rather than substitute)\n2. *Feature prominently* — Position at eye level, menu board prime spots, and as first recommendations from staff\n3. *Test selective premiumization* — Star products tolerate 3-5% price increases with minimal volume impact due to their inelastic demand [Journal of Marketing Research, 2023]\n4. *Build combos around them* — Pair with underperforming items to lift average ticket and move slow inventory',
      details: {
        stars: [
          { name: 'Cappuccino', revenue_pct: 18, trend: 'growing' },
          { name: 'Iced Latte', revenue_pct: 14, trend: 'growing' },
          { name: 'Croissant', revenue_pct: 10, trend: 'stable' },
        ],
        citations: ['cornell_menu_pricing', 'jmr_elasticity'],
      },
      impact_cents: 0,
      confidence: 0.92,
      action_status: 'viewed',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(5),
    },
    {
      id: uuid(),
      type: 'inventory',
      title: '🚫 4 Dead Stock Items — $450/Month Hidden Cost',
      summary: '4 products have generated zero revenue over the past 30 days: Hot Chocolate, Banana Bread, Cookie, and Chai Latte (seasonal decline).\n\n*The hidden economics of dead stock:*\nAccording to NRF research, dead stock accounts for 25-30% of total inventory shrinkage, which averages 1.6% of annual revenue [National Retail Federation, 2024]. Beyond direct cost, dead stock occupies shelf space that could house your top performers, and perishable items compound losses through spoilage. The National Restaurant Association estimates reducing food waste by 20% improves net margin by 1-3 points [National Restaurant Association / ReFED, 2024].\n\n*Action plan:*\n1. Immediate: Mark down remaining inventory 40-60% or bundle with star products\n2. Within 7 days: Remove from active ordering. Redirect budget to top performers\n3. Going forward: Set a 14-day zero-sales trigger for automatic review',
      details: {
        dead_stock: [
          { name: 'Hot Chocolate', days_since_sale: 30 },
          { name: 'Banana Bread', days_since_sale: 25 },
          { name: 'Cookie', days_since_sale: 22 },
          { name: 'Chai Latte', days_since_sale: 18 },
        ],
        citations: ['nrf_inventory_shrink', 'nra_food_waste', 'ibisworld_retail_efficiency'],
      },
      impact_cents: 45000,
      confidence: 0.72,
      action_status: 'accepted',
      valid_until: daysFromNow(7),
      created_at: hoursAgo(12),
    },
    {
      id: uuid(),
      type: 'staffing',
      title: '📅 Monday Revenue Gap: 38% Below Saturday — $620/Mo Recovery Potential',
      summary: 'Saturday averages $2,180 while Monday generates only $1,350 — a 38% revenue gap.\n\nNRA daypart research shows businesses capturing 3+ strong dayparts achieve 40% higher revenue per square foot [National Restaurant Association, 2025]. Counter-seasonal promotions can recover 30-50% of the weakest day\'s revenue gap [National Restaurant Association, 2025].\n\n*Monday recovery playbook:*\n1. Launch a Monday-specific promotion (e.g., "Happy Monday" with a featured item at 15% off)\n2. Test a loyalty multiplier (2x points on Mondays)\n3. Shift marketing spend to drive traffic on slow days\n4. *Target:* Close 25% of the gap = $620/month',
      details: {
        best_day: { name: 'Saturday', avg_cents: 218000 },
        worst_day: { name: 'Monday', avg_cents: 135000 },
        gap_pct: 38,
        citations: ['nra_daypart_analysis', 'nra_seasonal_trends'],
      },
      impact_cents: 62000,
      confidence: 0.6,
      action_status: 'pending',
      valid_until: daysFromNow(21),
      created_at: hoursAgo(8),
    },
    {
      id: uuid(),
      type: 'anomaly',
      title: '📈 Statistical Anomaly: 42% Above Expected (Last Saturday)',
      summary: 'Revenue of $3,180 last Saturday represents a 42% deviation from the expected $2,240 (z-score: 2.8σ, confidence: 56%).\n\n*Positive anomaly investigation:*\nIdentify the driver — was it higher traffic, larger tickets, or a specific product? If replicable, this pattern could be worth ~$940/occurrence. McKinsey\'s customer analytics research shows businesses that identify and replicate positive anomalies see 10-30% lift in targeted segments [McKinsey & Company, 2024].\n\nPreliminary analysis suggests the spike correlated with a local farmers market event. Consider partnering with the market for recurring cross-promotion.',
      details: {
        anomaly: { date: daysAgo(2), revenue_cents: 318000, expected_cents: 224000, z_score: 2.8, type: 'spike' },
        citations: ['mckinsey_customer_analytics', 'nra_seasonal_trends'],
      },
      impact_cents: 94000,
      confidence: 0.56,
      action_status: 'viewed',
      valid_until: daysFromNow(7),
      created_at: hoursAgo(26),
    },
    {
      id: uuid(),
      type: 'pricing',
      title: '🏷️ Discount Rate at 4.8% — Margin Erosion Risk',
      summary: 'Your discount rate (4.8%) exceeds the industry benchmark of 3.0%. This costs you an estimated $310 in unnecessary margin erosion. Shift from blanket discounts to targeted, time-limited promotions — research shows targeted promotions outperform blanket discounts 3:1.\n\nResearch from Harvard Business Review shows that targeted, time-limited promotions outperform blanket discounts by a 3:1 margin in terms of incremental revenue generated [Harvard Business Review, 2023].\n\n*Recommended strategy:*\n1. Audit current discount triggers — identify which are driving new customers vs. subsidizing existing ones\n2. Cap blanket discounts at 3% of revenue\n3. Shift budget to targeted offers: loyalty rewards, slow-day promotions, and new customer incentives',
      details: {
        actual_rate_pct: 4.8,
        benchmark_rate_pct: 3.0,
        excess_cents: 31000,
        citations: ['hbr_discount_strategy', 'mckinsey_pricing'],
      },
      impact_cents: 31000,
      confidence: 0.7,
      action_status: 'pending',
      valid_until: daysFromNow(14),
      created_at: hoursAgo(18),
    },
    {
      id: uuid(),
      type: 'general',
      title: '💡 Tip Rate at 12.4% — Optimization Can Boost Staff Retention',
      summary: 'Your tip rate (12.4%) is 5.6 points below the optimal 18.0%. Research from Cornell shows that POS tip prompts with suggested amounts (18%/20%/25%) increase average tips by 38% vs. open-entry fields. Implementing this alone could add ~$480/month to your staff\'s take-home pay, improving retention [Cornell Hospitality Quarterly, 2023].\n\nHigher tips don\'t just help your staff — they directly reduce turnover. With labor costs averaging 28% of revenue in Coffee Shop / Café businesses [Bureau of Labor Statistics, 2025], reducing turnover through better tip income is one of the highest-ROI operational changes available.\n\n*Implementation:* Update your POS tip screen to show preset buttons at 18%, 20%, and 25% (plus custom). Cornell research shows this single change increases tip probability by 27%.',
      details: {
        current_rate_pct: 12.4,
        optimal_rate_pct: 18.0,
        gap_pct: 5.6,
        monthly_potential_cents: 48000,
        citations: ['cornell_tipping', 'bls_labor_costs', 'square_payments_report'],
      },
      impact_cents: 48000,
      confidence: 0.65,
      action_status: 'accepted',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(4),
    },
    {
      id: uuid(),
      type: 'general',
      title: '📈 Strong Revenue Momentum — Compounding Growth Detected',
      summary: 'Week-over-week revenue grew +8.3%, reflecting sustained demand acceleration. Your trailing average of $1,680/day across 118 daily transactions indicates healthy throughput. Relative to the Coffee Shop / Café industry benchmark, your daily revenue places you in the above median (+16.2% vs. industry median of $1,450/day).\n\nAt this trajectory, annualized revenue projects to ~$613,200, assuming no seasonal adjustment. To sustain this growth curve, ensure staffing scales proportionally — understaffed peak hours cost 8-15% of potential revenue [MIT Sloan Management Review, 2024].\n\n*Recommended actions:*\n1. Lock in supplier agreements at current volume to protect margins\n2. Evaluate whether current peak-hour staffing can support continued growth\n3. Consider modest price increases on top sellers while demand is strong — a 1% price lift yields ~11% operating profit improvement [Harvard Business Review, 2023]',
      details: {
        wow_growth_pct: 8.3,
        avg_daily_cents: 168000,
        annualized_cents: 61320000,
        benchmark_gap_pct: 16.2,
        citations: ['nra_2025_pricing', 'mit_sloan_scheduling', 'hbr_pricing_power'],
      },
      impact_cents: 0,
      confidence: 0.88,
      action_status: 'viewed',
      valid_until: null,
      created_at: hoursAgo(2),
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
      underpriced_products: { amount_cents: 52000, label: 'Pricing', description: 'Items underpriced vs market' },
      peak_hour_missed: { amount_cents: 84000, label: 'Peak Hours', description: 'Revenue lost from understaffed peak hours' },
      dead_stock: { amount_cents: 38000, label: 'Dead Stock', description: 'Zero-velocity inventory holding costs' },
      staffing_waste: { amount_cents: 32000, label: 'Staffing', description: 'Labor cost optimization' },
      discount_leakage: { amount_cents: 28000, label: 'Discounts', description: 'Excessive discounting eroding margins' },
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

// ─── Transaction Drill-Down ─────────────────────────────

function generateDayTransactions(date: string): DayTransactions {
  // Seed from date for consistency
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
  const txCount = lrRange(80, 160)
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
        pIdx = lrRange(0, PRODUCTS.length - 1)
      } while (usedProducts.has(pIdx) && usedProducts.size < PRODUCTS.length)
      usedProducts.add(pIdx)

      const p = PRODUCTS[pIdx]
      const qty = lr() < 0.8 ? 1 : 2
      const itemTotal = p.price * qty
      txTotal += itemTotal

      productQtyCounts[p.name] = (productQtyCounts[p.name] || 0) + qty

      items.push({
        id: uuid(),
        product_name: p.name,
        sku: p.sku,
        quantity: qty,
        unit_price_cents: p.price,
        total_cents: itemTotal,
        category: p.category,
      })
    }

    const hasTip = lr() < 0.35
    const tipCents = hasTip ? lrRange(50, 300) : 0
    const hasDiscount = lr() < 0.08
    const discountCents = hasDiscount ? lrRange(100, 400) : 0
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

  // Sort by time
  transactions.sort((a, b) => a.created_at.localeCompare(b.created_at))

  const totalRev = transactions.reduce((s, t) => s + t.total_cents, 0)
  const uniqueProducts = new Set(transactions.flatMap(t => t.items.map(i => i.product_name))).size

  // Top product
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
  const items: InventoryItem[] = PRODUCTS.map((p, i) => {
    seed = 100 + i * 7
    const dailyUsage = Math.floor(p.popularity * seededRandRange(8, 35))
    const currentStock = seededRandRange(dailyUsage * 2, dailyUsage * 14)
    const reorderPoint = Math.ceil(dailyUsage * 3) // 3 day buffer
    const daysUntil = dailyUsage > 0 ? Math.max(0, Math.floor((currentStock - reorderPoint) / dailyUsage)) : null
    const trendRoll = seededRand()
    const trend = trendRoll < 0.3 ? 'rising' as const : trendRoll < 0.6 ? 'falling' as const : 'stable' as const
    const trendPct = trend === 'rising' ? seededRandRange(5, 25) : trend === 'falling' ? -seededRandRange(5, 20) : seededRandRange(-3, 3)
    const unit = p.category === 'drinks' ? 'servings' : 'units'

    return {
      id: uuid(),
      product_name: p.name,
      sku: p.sku,
      category: p.category,
      current_stock: currentStock,
      unit,
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

  dayTransactions: (date: string) => generateDayTransactions(date),

  inventory: () => generateInventory(),

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
