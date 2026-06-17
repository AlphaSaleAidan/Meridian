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

import {
  generateStaffPerformance,
  generateMarginWaterfall,
  generateMenuEngineering,
  generateAnomalies,
  generateRFMSegments,
  generateCustomerRankings,
  generateCohorts,
  generateAgents,
  generateAgentChains,
  generateCalibrationHistory,
  generateTopActions,
} from './agent-data'

import { getActiveBusinessType, getCurrencyMultiplier, isCanadaPath } from './demo-context'
import { getProducts, getRevenueConfig, getHourlyPattern, getBusinessName, getBusinessProfile, type ProductDef } from './business-config'

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

// Seed-based pseudo-random for consistent demo data per business type
let seed = 42
function resetSeed(): void {
  const bt = getActiveBusinessType()
  const SEED_MAP: Record<string, number> = {
    coffee_shop: 42, restaurant: 137, fast_food: 271, auto_shop: 389, smoke_shop: 523,
  }
  seed = SEED_MAP[bt] ?? 42
}
function seededRand(): number {
  seed = (seed * 16807) % 2147483647
  return (seed - 1) / 2147483646
}

function seededRandRange(min: number, max: number): number {
  return Math.floor(seededRand() * (max - min + 1)) + min
}

function cx(cents: number): number {
  return Math.round(cents * getCurrencyMultiplier())
}

// ─── Products ───────────────────────────────────────────

function getActiveProducts(): ProductDef[] {
  return getProducts(getActiveBusinessType())
}

// ─── Business-Aware Text Substitution ──────────────────

function bizSub(text: string): string {
  const p = getActiveProducts()
  const bt = getActiveBusinessType()
  const labels: Record<string, string> = {
    coffee_shop: 'Coffee Shop / Café',
    restaurant: 'Full-Service Restaurant',
    fast_food: 'Quick-Service Restaurant',
    auto_shop: 'Automotive Service',
    smoke_shop: 'Tobacco & Accessories',
  }
  const shortLabels: Record<string, string> = {
    coffee_shop: 'Coffee Shop',
    restaurant: 'Restaurant',
    fast_food: 'Fast Food',
    auto_shop: 'Auto Shop',
    smoke_shop: 'Smoke Shop',
  }
  const replacements: [string, string][] = [
    ['Matcha Latte', p[4]?.name || 'Item E'],
    ['Cold Brew', p[3]?.name || 'Item D'],
    ['Avocado Toast', p[10]?.name || 'Item K'],
    ['Cappuccino', p[1]?.name || 'Item B'],
    ['Iced Latte', p[2]?.name || 'Item C'],
    ['Croissant', p[9]?.name || 'Item J'],
    ['Espresso', p[0]?.name || 'Item A'],
    ['Blueberry Muffin', p[8]?.name || 'Item I'],
    ['Breakfast Sandwich', p[11]?.name || 'Item L'],
    ['Drip Coffee', p[7]?.name || 'Item H'],
    ['Hot Chocolate', p[5]?.name || 'Item F'],
    ['Banana Bread', p[12]?.name || 'Item M'],
    ['Cookie', p[13]?.name || 'Item N'],
    ['Chai Latte', p[6]?.name || 'Item G'],
    ['Sunrise Coffee Co.', getBusinessName(bt)],
    ['Coffee Shop / Café', labels[bt] || bt],
    ['Coffee Shop', shortLabels[bt] || bt],
  ]
  let result = text
  for (const [from, to] of replacements) {
    result = result.split(from).join(to)
  }
  return result
}

// ─── Daily Revenue ──────────────────────────────────────

function generateDailyRevenue(days: number): DailyRevenue[] {
  resetSeed()
  const rc = getRevenueConfig(getActiveBusinessType())
  const result: DailyRevenue[] = []

  for (let i = days - 1; i >= 0; i--) {
    const date = daysAgo(i)
    const d = new Date(date)
    const dow = d.getDay() // 0=Sun, 6=Sat

    // Base revenue: weekends higher, Mon-Fri varies
    const isWeekend = dow === 0 || dow === 6
    const baseRevenue = isWeekend
      ? seededRandRange(rc.weekendMin, rc.weekendMax)
      : seededRandRange(rc.weekdayMin, rc.weekdayMax)

    // Add slight upward trend over 30 days
    const trendBoost = Math.floor((days - i) * 800)
    const revenue = baseRevenue + trendBoost

    // Transactions based on business avg ticket
    const avgTicket = seededRandRange(rc.avgTicketMin, rc.avgTicketMax)
    const transactions = Math.floor(revenue / avgTicket)
    const customers = Math.floor(transactions * 0.85)
    const refunds = seededRandRange(0, 3) * seededRandRange(300, 800)
    const tax = Math.floor(revenue * 0.085)
    const tip = Math.floor(revenue * seededRand() * 0.12)
    const discount = seededRandRange(0, 5) * seededRandRange(100, 500)

    result.push({
      date,
      revenue_cents: cx(revenue),
      transactions,
      avg_ticket_cents: cx(avgTicket),
      refund_cents: cx(refunds),
      tax_cents: cx(tax),
      tip_cents: cx(tip),
      discount_cents: cx(discount),
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
  const hourlyPattern = getHourlyPattern(getActiveBusinessType())

  return {
    hourly: hourlyPattern.map((pct, hour) => {
      const revenue = Math.floor(pct * 280) // scale
      const sales = Math.max(1, Math.floor(pct * 2.8))
      return {
        hour: `${hour.toString().padStart(2, '0')}:00`,
        revenue_cents: cx(revenue * 100),
        sales,
        refunds: pct > 40 ? rand(0, 1) : 0,
        avg_ticket_cents: cx(pct > 0 ? rand(800, 1200) : 0),
        customers: Math.floor(sales * 0.85),
      }
    }),
  }
}

// ─── Products ───────────────────────────────────────────

function generateProducts(days: number): ProductsData {
  seed = 100

  const products: ProductPerf[] = getActiveProducts().map(p => {
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
        revenue_cents: cx(dayQty * p.price),
        quantity: dayQty,
      })
    }

    return {
      product_id: uuid(),
      name: p.name,
      sku: p.sku,
      price_cents: cx(p.price),
      total_revenue_cents: cx(revenue),
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
  const p = getActiveProducts()
  const bt = getActiveBusinessType()
  const profile = getBusinessProfile(bt)
  const deadItems = profile.deadStockItems
  const peak = profile.peakLabel
  const indLabel = profile.industryLabel

  // Revenue multiplier — scales dollar amounts to match business type
  const scaleMap: Record<string, number> = {
    coffee_shop: 1, restaurant: 3, fast_food: 2, auto_shop: 2.5, smoke_shop: 0.7,
  }
  const m = scaleMap[bt] || 1

  // Dynamic price helpers. cx() applies the currency multiplier (1.38 on the
  // Canada portal, 1.0 elsewhere) so every prose dollar figure matches the
  // CAD-scaled impact_cents badges the cards render. Product prices carry no
  // business-scale (m), only currency; revenue figures carry both.
  const priceFmt = (cents: number) => `$${(cx(cents) / 100).toFixed(2)}`
  const p4price = cx(p[4]?.price || 625) / 100
  const p3price = cx(p[3]?.price || 500) / 100
  const p10price = cx(p[10]?.price || 895) / 100
  const p4suggest = Math.round(p4price * 1.12 * 100) / 100
  const p3suggest = Math.round(p3price * 1.10 * 100) / 100
  const p10suggest = Math.round(p10price * 1.11 * 100) / 100
  const p4name = p[4]?.name || 'Item E'
  const p3name = p[3]?.name || 'Item D'
  const p10name = p[10]?.name || 'Item K'

  const $s = (base: number) => `$${cx(base * m).toLocaleString()}`
  const sm = (cents: number) => Math.round(cents * m) // scale cents
  const txPerDay = bt === 'auto_shop' ? 22 : bt === 'smoke_shop' ? 65 : sm(118)
  const pzM4 = Math.round((p[4]?.price || 625) * 0.45)
  const pzM7 = Math.round((p[7]?.price || 275) * 0.55)
  const pzM11 = Math.round((p[11]?.price || 795) * 0.35)

  const insights: Insight[] = [
    {
      id: uuid(),
      type: 'money_left',
      title: `\u{1F4B8} ${$s(2340)}/Month Left on the Table — Here's How to Capture It`,
      summary: `Meridian's Money Left on Table analysis identifies ${$s(2340)}/month in unrealized revenue across your operations. This score is calculated using five economic dimensions, each benchmarked against industry standards:\n\n*Component breakdown:*\n  • Pricing Optimization: ${$s(840)}/mo\n  • Peak Hour Staffing: ${$s(520)}/mo\n  • Dead Stock Clearance: ${$s(450)}/mo\n  • Discount Leakage: ${$s(310)}/mo\n  • Schedule Gap Recovery: ${$s(220)}/mo\n\nMcKinsey research confirms most SMBs leave 2-7% of revenue on the table through suboptimal pricing, staffing, and inventory management — and that structured optimization yields an average 3.3% revenue lift [McKinsey & Company, 2024].\n\n*Prioritized action plan:*\n1. Increase ${p4name} and ${p3name} prices by ${priceFmt(Math.round((p[4]?.price || 625) * 0.12))}-${priceFmt(Math.round((p[4]?.price || 625) * 0.15))} (est. ${$s(840)}/mo)\n2. Add one staff member during ${peak} peak window (est. ${$s(520)}/mo)\n3. Clear 4 dead-stock items via bundles or markdowns (est. ${$s(450)}/mo)`,
      details: { components: {
        pricing: { amount_cents: cx(sm(84000)), detail: 'Underpriced items with inelastic demand' },
        staffing: { amount_cents: cx(sm(52000)), detail: 'Understaffed peak hours losing throughput' },
        dead_stock: { amount_cents: cx(sm(45000)), detail: 'Zero-velocity inventory holding costs' },
        discounts: { amount_cents: cx(sm(31000)), detail: 'Excessive discounting above 3% benchmark' },
        scheduling: { amount_cents: cx(sm(22000)), detail: 'Revenue gaps in recoverable dayparts' },
      }, citations: ['mckinsey_pricing', 'hbr_pricing_power', 'mit_sloan_scheduling', 'nra_food_waste'] },
      impact_cents: cx(sm(234000)), confidence: 0.65, action_status: 'accepted',
      valid_until: daysFromNow(30),
      created_at: hoursAgo(1),
    },
    {
      id: uuid(),
      type: 'pricing',
      title: `\u{1F4CA} Gross Margin Compression: 58% → 54% Over 8 Weeks`,
      summary: `Your gross margin has eroded 4 points over the past 8 weeks — from 58.2% to 54.1%. At current revenue levels, that 4-point compression represents ${$s(1120)}/month in lost profit.\n\n*Root cause analysis (Meridian AI):*\nCOGS increased 6.3% while prices remained flat. Investopedia's gross margin research notes that ${indLabel} businesses operating below 55% gross margin are in the "danger zone" where one bad month eliminates quarterly profit [Investopedia, 2026]. CFI analysis of 2,400 SMBs found that businesses monitoring margins weekly recover from compression 2.3x faster than those reviewing monthly [Corporate Finance Institute, 2026].\n\n*Recovery plan:*\n1. Audit your top 5 COGS items — identify which suppliers raised prices\n2. Renegotiate or find alternative suppliers for the 2 highest-impact items\n3. Implement a 3-5% selective price increase on items with inelastic demand\n4. Target: Recover to 57%+ within 4 weeks`,
      details: {
        current_margin_pct: 54.1,
        prior_margin_pct: 58.2,
        erosion_pct: 4.1,
        cogs_increase_pct: 6.3,
        citations: ['investopedia_gross_margin', 'cfi_margin_analysis', 'bench_accounting_cogs'],
      },
      impact_cents: cx(sm(112000)), confidence: 0.79, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(6),
    },
    {
      id: uuid(),
      type: 'pricing',
      title: `\u{1F4B0} 3 Data-Backed Pricing Opportunities — ${$s(840)}/Month Potential`,
      summary: `Our analysis identified 3 products where data supports a price adjustment. Top opportunity: *${p4name}* — current price ${priceFmt(p[4]?.price || 625)}, demand elasticity analysis shows highly inelastic demand (elasticity: -0.3), supporting a ${priceFmt(Math.round((p[4]?.price || 625) * 0.12))} increase.\n\n*Economic rationale:*\nHarvard Business Review research demonstrates that a 1% price increase yields an average 11.1% improvement in operating profit — making pricing the single highest-leverage variable in the P&L [Harvard Business Review, 2023]. Businesses using data-driven menu engineering achieve 8-15% higher gross margins vs. cost-plus pricing [Cornell Hospitality Quarterly, 2024].\n\nMeta-analysis data shows items with <5% price increases exhibit near-zero demand reduction (mean elasticity: -1.2 for staples) [Journal of Marketing Research, 2023].\n\n*Implementation:*\n1. ${p4name}: $${p4price.toFixed(2)} → $${p4suggest.toFixed(2)} (+12%, still below competitor avg)\n2. ${p3name}: $${p3price.toFixed(2)} → $${p3suggest.toFixed(2)} (+10%, high demand inelasticity)\n3. ${p10name}: $${p10price.toFixed(2)} → $${p10suggest.toFixed(2)} (+11%, premium positioning supports it)\n4. Total combined potential: ${$s(840)}/month`,
      details: {
        opportunities: [
          { name: p4name, current: cx(p[4]?.price || 625), suggested: cx(Math.floor((p[4]?.price || 625) * 1.12)), elasticity: -0.3 },
          { name: p3name, current: cx(p[3]?.price || 500), suggested: cx(Math.floor((p[3]?.price || 500) * 1.10)), elasticity: -0.4 },
          { name: p10name, current: cx(p[10]?.price || 895), suggested: cx(Math.floor((p[10]?.price || 895) * 1.11)), elasticity: -0.6 },
        ],
        citations: ['hbr_pricing_power', 'cornell_menu_pricing', 'jmr_elasticity', 'mckinsey_pricing'],
      },
      impact_cents: cx(sm(84000)), confidence: 0.82, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(3),
    },
    {
      id: uuid(),
      type: 'seasonal',
      title: `\u{1F327}️ Weather Correlation Detected: Rain Days = -23% Revenue`,
      summary: `Meridian's pattern analysis detected a strong negative correlation between precipitation and your daily revenue. On days with >0.1" rainfall, revenue drops an average of 23% (${$s(387)} below daily mean).\n\n*Intelligence synthesis:*\nNation's Restaurant News reports that weather accounts for $22B in annual U.S. restaurant revenue variability [NRN, 2026]. Deloitte's retail analytics practice found that businesses with weather-responsive operations (adjusting staffing, promotions, and inventory based on forecasts) recover 40-60% of weather-related revenue losses [Deloitte Insights, 2026].\n\n*Weather playbook:*\n1. Monitor 3-day forecasts — reduce prep by 20% on predicted rain days\n2. Launch "rainy day specials" via push notification or social media\n3. Cut one staff member on rain days to protect labor ratio\n4. Promote delivery/pickup options more aggressively when rain is forecast\n5. *Estimated recovery:* 40% of weather losses = ${$s(155)}/rain day`,
      details: {
        rain_impact_pct: -23,
        avg_loss_cents: cx(sm(38700)),
        rain_days_per_month: 6,
        recovery_potential_cents: cx(sm(93000)),
        citations: ['nrn_weather_impact', 'deloitte_retail_analytics', 'bls_seasonal_adjustment'],
      },
      impact_cents: cx(sm(93000)), confidence: 0.64, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(30),
    },
    {
      id: uuid(),
      type: 'staffing',
      title: `\u{1F525} Golden Window: ${peak} — 47% of Revenue`,
      summary: `Your most profitable operating window is ${peak}, concentrating 47% of daily revenue into a focused block. This exceeds the industry benchmark of 45% for ${indLabel} businesses.\n\n*Staffing economics:*\nMIT Sloan research shows each understaffed peak hour costs 8-15% of that hour's potential revenue through lost sales, longer wait times, and reduced upselling capacity [MIT Sloan Management Review, 2024]. Cornell's demand-driven scheduling research found that aligning staff to 15-minute demand blocks (vs. shift-based) improves revenue-per-labor-hour by 18% [Cornell Center for Hospitality Research, 2023].\n\n*Action items:*\n1. Ensure maximum staffing during ${peak} — every position filled\n2. Pre-prep high-volume items 30 min before peak to maximize throughput\n3. Schedule breaks and training during off-peak hours only\n4. Track revenue-per-labor-hour weekly to optimize scheduling`,
      details: {
        golden_window: { label: peak, revenue_share_pct: 47 },
        benchmark_share_pct: 45,
        citations: ['mit_sloan_scheduling', 'cornell_labor_scheduling', 'bls_labor_costs'],
      },
      impact_cents: cx(sm(52000)), confidence: 0.88, action_status: 'completed',
      valid_until: daysFromNow(14), created_at: hoursAgo(2),
    },
    {
      id: uuid(),
      type: 'staffing',
      title: `⏱️ Labor Cost Ratio: 31.2% — 3.2 Points Above Optimal`,
      summary: `Your labor-to-revenue ratio is 31.2%, exceeding the ${indLabel} benchmark of 28%. BLS data shows the median labor cost is 28.0% of revenue [Bureau of Labor Statistics, 2026]. At your revenue level, the 3.2-point gap equals ~${$s(890)}/month in excess labor spend.\n\n*Intelligence from 7shifts and Toast research:*\nBusinesses using demand-driven scheduling (aligning staff counts to 15-minute revenue blocks rather than fixed shifts) reduce labor costs by 4-8% while maintaining or improving service quality [7shifts Blog, 2026]. Toast's 2026 Restaurant Trends report found that 67% of operators who adopted predictive scheduling software saw labor cost reductions within 60 days.\n\n*Action plan:*\n1. Map hourly revenue vs. hourly labor cost for the past 4 weeks\n2. Identify "overstaffed hours" where labor cost exceeds 35% of that hour's revenue\n3. Shift 2-3 hours from overstaffed periods to understaffed ${peak} windows\n4. *Target:* Reduce labor ratio to 28.5% within 6 weeks = ${$s(890)}/mo savings`,
      details: {
        labor_pct: 31.2,
        benchmark_pct: 28.0,
        excess_monthly_cents: cx(sm(89000)),
        citations: ['bls_labor_costs', '7shifts_scheduling', 'toast_trends_2026'],
      },
      impact_cents: cx(sm(89000)), confidence: 0.74, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(10),
    },
    {
      id: uuid(),
      type: 'product_recommendation',
      title: bizSub('⭐ Star Products Identified — Protect & Promote These Revenue Drivers'),
      summary: `Your top performers (${p[1]?.name || 'Item B'}, ${p[2]?.name || 'Item C'}, ${p[9]?.name || 'Item J'}) collectively account for 42% of total revenue. In menu engineering terms, these are your "Stars" — high popularity, high profitability items that form the backbone of your product mix [Cornell Hospitality Quarterly, 2024].\n\n*Strategic recommendations:*\n1. *Never stock out* — Each lost sale of a star product costs your average ticket plus the probability of a walk-away (estimated 15-20% of customers leave rather than substitute)\n2. *Feature prominently* — Position at eye level, prime spots, and as first recommendations from staff\n3. *Test selective premiumization* — Star products tolerate 3-5% price increases with minimal volume impact due to their inelastic demand [Journal of Marketing Research, 2023]\n4. *Build combos around them* — Pair with underperforming items to lift average ticket and move slow inventory`,
      details: {
        stars: [
          { name: p[1]?.name || 'Top Item', revenue_pct: 18, trend: 'growing' as const },
          { name: p[2]?.name || 'Second Item', revenue_pct: 14, trend: 'growing' as const },
          { name: p[9]?.name || 'Side Item', revenue_pct: 10, trend: 'stable' as const },
        ],
        citations: ['cornell_menu_pricing', 'jmr_elasticity'],
      },
      impact_cents: 0, confidence: 0.92, action_status: 'viewed',
      valid_until: daysFromNow(30), created_at: hoursAgo(5),
    },
    {
      id: uuid(),
      type: 'product_recommendation',
      title: `\u{1F9EA} Menu Engineering Matrix: 3 "Puzzles" Identified`,
      summary: `Meridian's menu engineering analysis classified your products into the Boston Consulting Group matrix. Three items are "Puzzles" — high profitability but low popularity: ${p4name} (${priceFmt(pzM4)} margin, 3.1% of orders), ${p[7]?.name || 'Item H'} (${priceFmt(pzM7)} margin, 2.8% of orders), and ${p[11]?.name || 'Item L'} (${priceFmt(pzM11)} margin, 1.9% of orders).\n\n*Research-backed strategy:*\nCornell's menu engineering framework shows that repositioning Puzzles through strategic placement, staff recommendations, and bundling converts 30-50% into Stars within 4-6 weeks [Cornell Hospitality Quarterly, 2024]. McKinsey's consumer research confirms that item visibility drives 22% of customer selection — meaning placement changes alone can shift order patterns [McKinsey Consumer, 2025].\n\n*Conversion playbook:*\n1. Move all 3 Puzzles to the "golden triangle" on your menu board (top-right quadrant)\n2. Train staff to recommend one Puzzle per customer interaction\n3. Create a combo: Puzzle item + Star item at 10% bundle discount\n4. *Expected lift:* Convert 1-2 Puzzles to Stars = ${$s(340)}-${$s(680)}/mo additional margin`,
      details: {
        puzzles: [
          { name: p[4]?.name || 'Item E', margin_cents: cx(pzM4), order_pct: 3.1 },
          { name: p[7]?.name || 'Item H', margin_cents: cx(pzM7), order_pct: 2.8 },
          { name: p[11]?.name || 'Item L', margin_cents: cx(pzM11), order_pct: 1.9 },
        ],
        citations: ['cornell_menu_engineering', 'mckinsey_consumer_choice', 'nra_menu_trends'],
      },
      impact_cents: cx(sm(51000)), confidence: 0.71, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(20),
    },
    {
      id: uuid(),
      type: 'inventory',
      title: `\u{1F6AB} 4 Dead Stock Items — ${$s(450)}/Month Hidden Cost`,
      summary: `4 products have generated zero revenue over the past 30 days: ${deadItems[0] || 'Item 1'}, ${deadItems[1] || 'Item 2'}, ${deadItems[2] || 'Item 3'}, and ${deadItems[3] || 'Item 4'} (seasonal decline).\n\n*The hidden economics of dead stock:*\nAccording to NRF research, dead stock accounts for 25-30% of total inventory shrinkage, which averages 1.6% of annual revenue [National Retail Federation, 2024]. Beyond direct cost, dead stock occupies shelf space that could house your top performers, and perishable items compound losses through spoilage. The National Restaurant Association estimates reducing waste by 20% improves net margin by 1-3 points [National Restaurant Association / ReFED, 2024].\n\n*Action plan:*\n1. Immediate: Mark down remaining inventory 40-60% or bundle with star products\n2. Within 7 days: Remove from active ordering. Redirect budget to top performers\n3. Going forward: Set a 14-day zero-sales trigger for automatic review`,
      details: {
        dead_stock: [
          { name: deadItems[0] || 'Item 1', days_since_sale: 30 },
          { name: deadItems[1] || 'Item 2', days_since_sale: 25 },
          { name: deadItems[2] || 'Item 3', days_since_sale: 22 },
          { name: deadItems[3] || 'Item 4', days_since_sale: 18 },
        ],
        citations: ['nrf_inventory_shrink', 'nra_food_waste', 'ibisworld_retail_efficiency'],
      },
      impact_cents: cx(sm(45000)), confidence: 0.72, action_status: 'accepted',
      valid_until: daysFromNow(7), created_at: hoursAgo(12),
    },
    {
      id: uuid(),
      type: 'general',
      title: `\u{1F504} Cash Flow Velocity: 4.2 Days Average Collection`,
      summary: `Your average cash conversion cycle is 4.2 days — revenue takes 4.2 days from transaction to usable cash in your account. This is within the healthy range for POS-connected businesses (1-5 days), but optimization is possible.\n\n*Key finding from Investopedia and Freshbooks research:*\nCash flow is the #1 reason small businesses fail, with 82% of failures attributed to cash management problems rather than profitability issues [Investopedia, 2026]. Freshbooks' SMB survey found that businesses with same-day or next-day deposit access are 34% less likely to take on short-term debt [Freshbooks Blog, 2026].\n\n*Opportunities:*\n1. Switch to same-day deposit if your POS provider offers it (Square, Toast offer this)\n2. Negotiate net-15 → net-30 with your top 3 suppliers to extend payables\n3. Build a 2-week cash reserve equal to ~${$s(5600)} based on your burn rate\n4. Set up automated low-balance alerts at $${sm(2000).toLocaleString()}`,
      details: {
        avg_collection_days: 4.2,
        target_days: 2.0,
        reserve_target_cents: cx(sm(560000)),
        citations: ['investopedia_cash_flow', 'freshbooks_cash_management', 'quickbooks_cash_reserve'],
      },
      impact_cents: 0, confidence: 0.85, action_status: 'viewed',
      valid_until: daysFromNow(30), created_at: hoursAgo(14),
    },
    {
      id: uuid(),
      type: 'seasonal',
      title: `\u{1F4C5} Monday Revenue Gap: 38% Below Saturday — ${$s(620)}/Mo Recovery Potential`,
      summary: `Saturday averages ${$s(2180)} while Monday generates only ${$s(1350)} — a 38% revenue gap.\n\nNRA daypart research shows businesses capturing 3+ strong dayparts achieve 40% higher revenue per square foot [National Restaurant Association, 2025]. Counter-seasonal promotions can recover 30-50% of the weakest day's revenue gap [National Restaurant Association, 2025].\n\n*Monday recovery playbook:*\n1. Launch a Monday-specific promotion (e.g., "Happy Monday" with a featured item at 15% off)\n2. Test a loyalty multiplier (2x points on Mondays)\n3. Shift marketing spend to drive traffic on slow days\n4. *Target:* Close 25% of the gap = ${$s(620)}/month`,
      details: {
        best_day: { name: 'Saturday', avg_cents: cx(sm(218000)) },
        worst_day: { name: 'Monday', avg_cents: cx(sm(135000)) },
        gap_pct: 38,
        citations: ['nra_daypart_analysis', 'nra_seasonal_trends'],
      },
      impact_cents: cx(sm(62000)), confidence: 0.6, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(8),
    },
    {
      id: uuid(),
      type: 'anomaly',
      title: `\u{1F4C8} Statistical Anomaly: 42% Above Expected (Last Saturday)`,
      summary: `Revenue of ${$s(3180)} last Saturday represents a 42% deviation from the expected ${$s(2240)} (z-score: 2.8σ, confidence: 56%).\n\n*Positive anomaly investigation:*\nIdentify the driver — was it higher traffic, larger tickets, or a specific product? If replicable, this pattern could be worth ~${$s(940)}/occurrence. McKinsey's customer analytics research shows businesses that identify and replicate positive anomalies see 10-30% lift in targeted segments [McKinsey & Company, 2024].\n\nPreliminary analysis suggests the spike correlated with a local event. Consider partnering for recurring cross-promotion.`,
      details: {
        anomaly: { date: daysAgo(2), revenue_cents: cx(sm(318000)), expected_cents: cx(sm(224000)), z_score: 2.8, type: 'spike' },
        citations: ['mckinsey_customer_analytics', 'nra_seasonal_trends'],
      },
      impact_cents: cx(sm(94000)), confidence: 0.56, action_status: 'viewed',
      valid_until: daysFromNow(7), created_at: hoursAgo(26),
    },
    {
      id: uuid(),
      type: 'pricing',
      title: `\u{1F3F7}️ Discount Rate at 4.8% — Margin Erosion Risk`,
      summary: `Your discount rate (4.8%) exceeds the industry benchmark of 3.0%. This costs you an estimated $${cx(sm(310)).toLocaleString()} in unnecessary margin erosion. Shift from blanket discounts to targeted, time-limited promotions — research shows targeted promotions outperform blanket discounts 3:1.\n\nResearch from Harvard Business Review shows that targeted, time-limited promotions outperform blanket discounts by a 3:1 margin in terms of incremental revenue generated [Harvard Business Review, 2023].\n\n*Recommended strategy:*\n1. Audit current discount triggers — identify which are driving new customers vs. subsidizing existing ones\n2. Cap blanket discounts at 3% of revenue\n3. Shift budget to targeted offers: loyalty rewards, slow-day promotions, and new customer incentives`,
      details: {
        actual_rate_pct: 4.8,
        benchmark_rate_pct: 3.0,
        excess_cents: cx(sm(31000)),
        citations: ['hbr_discount_strategy', 'mckinsey_pricing'],
      },
      impact_cents: cx(sm(31000)), confidence: 0.7, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(18),
    },
    {
      id: uuid(),
      type: 'general',
      title: `\u{1F4A1} Tip Rate at 12.4% — Optimization Can Boost Staff Retention`,
      summary: `Your tip rate (12.4%) is 5.6 points below the optimal 18.0%. Research from Cornell shows that POS tip prompts with suggested amounts (18%/20%/25%) increase average tips by 38% vs. open-entry fields. Implementing this alone could add ~$${cx(sm(480)).toLocaleString()}/month to your staff's take-home pay, improving retention [Cornell Hospitality Quarterly, 2023].\n\nHigher tips don't just help your staff — they directly reduce turnover. With labor costs averaging 28% of revenue in ${indLabel} businesses [Bureau of Labor Statistics, 2025], reducing turnover through better tip income is one of the highest-ROI operational changes available.\n\n*Implementation:* Update your POS tip screen to show preset buttons at 18%, 20%, and 25% (plus custom). Cornell research shows this single change increases tip probability by 27%.`,
      details: {
        current_rate_pct: 12.4,
        optimal_rate_pct: 18.0,
        gap_pct: 5.6,
        monthly_potential_cents: cx(sm(48000)),
        citations: ['cornell_tipping', 'bls_labor_costs', 'square_payments_report'],
      },
      impact_cents: cx(sm(48000)), confidence: 0.65, action_status: 'accepted',
      valid_until: daysFromNow(30), created_at: hoursAgo(4),
    },
    {
      id: uuid(),
      type: 'benchmark',
      title: `\u{1F4C8} Strong Revenue Momentum — Compounding Growth Detected`,
      summary: `Week-over-week revenue grew +8.3%, reflecting sustained demand acceleration. Your trailing average of ${$s(1680)}/day across ${txPerDay} daily transactions indicates healthy throughput. Relative to the ${indLabel} industry benchmark, your daily revenue places you in the above median (+16.2% vs. industry median of ${$s(1450)}/day).\n\nAt this trajectory, annualized revenue projects to ~${$s(613200)}, assuming no seasonal adjustment. To sustain this growth curve, ensure staffing scales proportionally — understaffed peak hours cost 8-15% of potential revenue [MIT Sloan Management Review, 2024].\n\n*Recommended actions:*\n1. Lock in supplier agreements at current volume to protect margins\n2. Evaluate whether current ${peak} staffing can support continued growth\n3. Consider modest price increases on top sellers while demand is strong — a 1% price lift yields ~11% operating profit improvement [Harvard Business Review, 2023]`,
      details: {
        wow_growth_pct: 8.3,
        avg_daily_cents: cx(sm(168000)),
        annualized_cents: cx(sm(61320000)),
        benchmark_gap_pct: 16.2,
        citations: ['nra_2025_pricing', 'mit_sloan_scheduling', 'hbr_pricing_power'],
      },
      impact_cents: 0, confidence: 0.88, action_status: 'viewed',
      valid_until: null, created_at: hoursAgo(2),
    },
  ]

  return { insights, total: insights.length }
}
// ─── Forecasts ──────────────────────────────────────────

function generateForecasts(): { forecasts: Forecast[]; total: number } {
  const rc = getRevenueConfig(getActiveBusinessType())
  const forecasts: Forecast[] = []

  // Daily revenue forecasts for next 90 days. Confidence and bounds widen
  // gradually with horizon to match how real forecasters degrade further out.
  for (let i = 1; i <= 90; i++) {
    const date = daysFromNow(i)
    const d = new Date(date)
    const dow = d.getDay()
    const isWeekend = dow === 0 || dow === 6

    const base = isWeekend ? rand(rc.weekendMin, rc.weekendMax) : rand(rc.weekdayMin, rc.weekdayMax)
    // Bound width grows with horizon (8% → 28%) — closer days are tighter.
    const widthPct = 0.08 + Math.min(i / 90, 1) * 0.20
    const lower = Math.floor(base * (1 - widthPct))
    const upper = Math.floor(base * (1 + widthPct))
    // Confidence decays from ~0.88 to ~0.60 across the 90-day horizon.
    const confidence = randFloat(
      Math.max(0.55, 0.92 - i / 120),
      Math.max(0.60, 0.97 - i / 120),
    )
    const horizonDays = i <= 7 ? 7 : i <= 30 ? 30 : 90
    const errorRate = i <= 7 ? 0.10 : i <= 30 ? 0.15 : 0.22

    forecasts.push({
      id: uuid(),
      type: 'daily_revenue',
      period_start: date,
      period_end: date,
      predicted_cents: cx(base),
      lower_bound_cents: cx(lower),
      upper_bound_cents: cx(upper),
      confidence,
      horizon_days: horizonDays,
      error_rate: errorRate,
    })
  }

  // Weekly forecast — computed from business revenue config
  const weeklyAvg = Math.floor(((rc.weekdayMin + rc.weekdayMax) / 2) * 5 + ((rc.weekendMin + rc.weekendMax) / 2) * 2)
  forecasts.push({
    id: uuid(),
    type: 'weekly_revenue',
    period_start: daysFromNow(1),
    period_end: daysFromNow(7),
    predicted_cents: cx(weeklyAvg),
    lower_bound_cents: cx(Math.floor(weeklyAvg * 0.85)),
    upper_bound_cents: cx(Math.floor(weeklyAvg * 1.15)),
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
      body: `A new pricing optimization opportunity was detected for your ${getActiveProducts()[4]?.name || 'top item'}. Review it in the Insights tab.`,
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
      body: `5 ${getActiveProducts()[3]?.name || 'item'} refunds in one day is 3x your normal rate. This may indicate a quality issue.`,
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
      body: `Today's ${getBusinessProfile(getActiveBusinessType()).peakLabel} revenue was 22% above forecast. Consider adding extra staff for tomorrow.`,
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

  // Scale by business type (same multiplier the insight cards use) so the
  // dashboard money-left score matches the money_left insight card, then apply
  // the currency multiplier via cx() — consistent on both US and Canada.
  const mlScale: Record<string, number> = { coffee_shop: 1, restaurant: 3, fast_food: 2, auto_shop: 2.5, smoke_shop: 0.7 }
  const mlm = mlScale[getActiveBusinessType()] || 1
  const mlc = (cents: number) => cx(Math.round(cents * mlm))
  const moneyLeft: MoneyLeftScore = {
    id: uuid(),
    total_score_cents: mlc(234000),
    components: {
      underpriced_products: { amount_cents: mlc(52000), label: 'Pricing', description: 'Items underpriced vs market' },
      peak_hour_missed: { amount_cents: mlc(84000), label: 'Peak Hours', description: 'Revenue lost from understaffed peak hours' },
      dead_stock: { amount_cents: mlc(38000), label: 'Dead Stock', description: 'Zero-velocity inventory holding costs' },
      staffing_waste: { amount_cents: mlc(32000), label: 'Staffing', description: 'Labor cost optimization' },
      discount_leakage: { amount_cents: mlc(28000), label: 'Discounts', description: 'Excessive discounting eroding margins' },
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
  const products = getActiveProducts()
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
        pIdx = lrRange(0, products.length - 1)
      } while (usedProducts.has(pIdx) && usedProducts.size < products.length)
      usedProducts.add(pIdx)

      const p = products[pIdx]
      const qty = lr() < 0.8 ? 1 : 2
      const itemTotal = p.price * qty
      txTotal += itemTotal

      productQtyCounts[p.name] = (productQtyCounts[p.name] || 0) + qty

      items.push({
        id: uuid(),
        product_name: p.name,
        sku: p.sku,
        quantity: qty,
        unit_price_cents: cx(p.price),
        total_cents: cx(itemTotal),
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
      total_cents: cx(txTotal - discountCents + tipCents),
      tip_cents: cx(tipCents),
      discount_cents: cx(discountCents),
      refund_cents: cx(refundCents),
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
  const items: InventoryItem[] = getActiveProducts().map((p, i) => {
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

let _cacheKey: string | null = null
let _daily30: DailyRevenue[] = []
let _daily90: DailyRevenue[] = []

function getDaily(days: 30 | 90): DailyRevenue[] {
  const key = `${getActiveBusinessType()}_${isCanadaPath() ? 'ca' : 'us'}`
  if (_cacheKey !== key) {
    _cacheKey = key
    _daily30 = generateDailyRevenue(30)
    _daily90 = generateDailyRevenue(90)
  }
  return days === 30 ? _daily30 : _daily90
}

export const demoData = {
  overview: () => { resetSeed(); return generateOverview(getDaily(30)) },

  revenue: (days: number): RevenueData => {
    resetSeed()
    const daily = days <= 30 ? getDaily(30) : getDaily(90).slice(-days)
    return {
      daily,
      weekly: generateWeeklyRevenue(daily),
    }
  },

  hourlyRevenue: (): HourlyData => { resetSeed(); return generateHourlyData() },

  products: (days: number): ProductsData => { resetSeed(); return generateProducts(days) },

  insights: (limit: number) => {
    resetSeed()
    const all = generateInsights()
    // Rotate the deck daily so the demo feels fresh on repeat visits, but keep
    // the money_left headline pinned at the top — it's the hero insight.
    const dayOffset = Math.floor(Date.now() / 86_400_000)
    const head = all.insights.filter(i => i.type === 'money_left')
    const rest = all.insights.filter(i => i.type !== 'money_left')
    const o = rest.length ? ((dayOffset % rest.length) + rest.length) % rest.length : 0
    const rotated = [...head, ...rest.slice(o), ...rest.slice(0, o)]
    return { insights: rotated.slice(0, limit), total: all.total }
  },

  forecasts: () => { resetSeed(); return generateForecasts() },

  notifications: (limit: number) => {
    resetSeed()
    const all = generateNotifications()
    return { notifications: all.notifications.slice(0, limit), total: all.total }
  },

  connection: () => { resetSeed(); return generateConnection() },

  dayTransactions: (date: string) => { resetSeed(); return generateDayTransactions(date) },

  inventory: () => { resetSeed(); return generateInventory() },

  weeklyReport: () => {
    resetSeed()
    return {
      report: {
        period: `${daysAgo(7)} to ${daysAgo(1)}`,
        total_revenue_cents: cx(1285000),
        revenue_change_pct: 8.2,
        top_product: getActiveProducts()[1]?.name || 'Top Product',
        insights_generated: 3,
        forecast_accuracy: 0.94,
      },
    }
  },

  staff: () => {
    resetSeed()
    return { staff: generateStaffPerformance() }
  },

  margins: () => {
    resetSeed()
    return { items: generateMarginWaterfall() }
  },

  menuEngineering: () => {
    resetSeed()
    return { items: generateMenuEngineering() }
  },

  anomalies: () => {
    resetSeed()
    return { anomalies: generateAnomalies() }
  },

  customers: () => {
    resetSeed()
    return {
      segments: generateRFMSegments(),
      rankings: generateCustomerRankings(),
      cohorts: generateCohorts(),
    }
  },

  agents: () => {
    resetSeed()
    return {
      agents: generateAgents(),
      chains: generateAgentChains(),
      calibration: generateCalibrationHistory(),
    }
  },

  actions: () => {
    resetSeed()
    return { actions: generateTopActions() }
  },
}
