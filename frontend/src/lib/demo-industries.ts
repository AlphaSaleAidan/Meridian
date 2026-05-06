/**
 * Industry-Specific Demo Data Overrides
 *
 * Provides per-business-type overrides for the demo data system.
 * Each business type defines its own products, hourly distribution,
 * insights, top actions, peak-hour heatmap, and overview metrics.
 *
 * All money values are in CENTS (integers) per Meridian convention.
 */

import type {
  Overview,
  MoneyLeftScore,
  ProductPerf,
  Insight,
} from './api'

import type {
  TopAction,
  ReasoningChain,
  PeakHourCell,
} from './agent-data'

// ─── Types ──────────────────────────────────────────────

export type BusinessType =
  | 'restaurant'
  | 'fast_food'
  | 'coffee_shop'
  | 'auto_shop'
  | 'smoke_shop'

export interface BusinessTypeMeta {
  id: BusinessType
  label: string
  icon: string
  description: string
}

export const BUSINESS_TYPES: BusinessTypeMeta[] = [
  { id: 'coffee_shop', label: 'Coffee Shop', icon: '☕', description: 'Specialty coffee and cafe' },
  { id: 'restaurant', label: 'Restaurant', icon: '🍽️', description: 'Full-service dining' },
  { id: 'fast_food', label: 'Fast Food', icon: '🍔', description: 'Quick-service restaurant' },
  { id: 'auto_shop', label: 'Auto Shop', icon: '🔧', description: 'Automotive service and repair' },
  { id: 'smoke_shop', label: 'Smoke Shop', icon: '💨', description: 'Tobacco and accessories retail' },
]

export interface IndustryOverrides {
  businessName: string
  overview: Overview
  products: ProductPerf[]
  hourlyDistribution: number[]
  insights: Insight[]
  topActions: TopAction[]
  peakHourHeatmap: PeakHourCell[]
  recoverableRevenue30d: number
}

// ─── Helpers ────────────────────────────────────────────

let seed = 42

function seededRand(): number {
  seed = (seed * 16807) % 2147483647
  return (seed - 1) / 2147483646
}

function seededRandRange(min: number, max: number): number {
  return Math.floor(seededRand() * (max - min + 1)) + min
}

function uuid(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16)
  })
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

function daysAgo(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().slice(0, 10)
}

// ─── Product Definition ─────────────────────────────────

interface ProductDef {
  name: string
  sku: string
  price: number // cents
  category: string
  popularity: number // 0-1
}

// ─── Shared Generators ──────────────────────────────────

function generateProductPerf(products: ProductDef[], days: number): ProductPerf[] {
  seed = 200
  return products.map(p => {
    const baseQty = Math.floor(p.popularity * 15 * days)
    const qty = seededRandRange(Math.floor(baseQty * 0.85), Math.floor(baseQty * 1.15))
    const revenue = qty * p.price

    const daily: { date: string; revenue_cents: number; quantity: number }[] = []
    for (let i = days - 1; i >= 0; i--) {
      const dayQty = seededRandRange(
        Math.floor(p.popularity * 8),
        Math.floor(p.popularity * 22),
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
  }).sort((a, b) => b.total_revenue_cents - a.total_revenue_cents)
}

function generateOverviewFromParams(params: {
  dailyRevenue: number
  dailyTraffic: number
  avgTicket: number
  recoverableRevenue30d: number
}): Overview {
  const revenue30d = params.dailyRevenue * 30
  const transactions30d = params.dailyTraffic * 30
  const priorRevenue = Math.floor(revenue30d * 0.88)
  const changePct = Math.round(((revenue30d - priorRevenue) / priorRevenue) * 100 * 10) / 10

  const totalRecoverable = params.recoverableRevenue30d
  const pricingShare = Math.floor(totalRecoverable * 0.36)
  const peakHourShare = Math.floor(totalRecoverable * 0.22)
  const deadStockShare = Math.floor(totalRecoverable * 0.19)
  const staffingShare = Math.floor(totalRecoverable * 0.14)
  const discountShare = totalRecoverable - pricingShare - peakHourShare - deadStockShare - staffingShare

  const moneyLeft: MoneyLeftScore = {
    id: uuid(),
    total_score_cents: totalRecoverable,
    components: {
      underpriced_products: { amount_cents: pricingShare, label: 'Pricing', description: 'Items underpriced vs market' },
      peak_hour_missed: { amount_cents: peakHourShare, label: 'Peak Hours', description: 'Revenue lost from understaffed peak hours' },
      dead_stock: { amount_cents: deadStockShare, label: 'Dead Stock', description: 'Zero-velocity inventory holding costs' },
      staffing_waste: { amount_cents: staffingShare, label: 'Staffing', description: 'Labor cost optimization' },
      discount_leakage: { amount_cents: discountShare, label: 'Discounts', description: 'Excessive discounting eroding margins' },
    },
    scored_at: hoursAgo(1),
  }

  return {
    revenue_cents_30d: revenue30d,
    revenue_change_pct: changePct,
    transaction_count_30d: transactions30d,
    avg_ticket_cents: params.avgTicket,
    money_left_score: moneyLeft,
    connection: {
      status: 'active',
      provider: 'square',
      last_sync_at: hoursAgo(0.5),
    },
    days_with_data: 30,
  }
}

function generatePeakHourHeatmapFromDistribution(
  hourlyDistribution: number[],
): PeakHourCell[] {
  // Day-of-week multipliers: Mon=0.9, Tue=0.92, Wed=0.95, Thu=0.98, Fri=1.08, Sat=1.15, Sun=1.02
  const dayMultipliers = [1.02, 0.90, 0.92, 0.95, 0.98, 1.08, 1.15]
  const cells: PeakHourCell[] = []

  seed = 300
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const base = hourlyDistribution[hour]
      const jitter = 1 + (seededRand() - 0.5) * 0.12
      const intensity = Math.min(100, Math.max(0,
        Math.round(base * dayMultipliers[day] * jitter),
      ))
      const revenue = intensity * 280
      const transactions = Math.max(1, Math.floor(intensity * 2.8))
      cells.push({ day, hour, revenue, transactions, intensity })
    }
  }
  return cells
}

function makeReasoning(params: {
  observation: string
  reasoning: string
  conclusion: string
  impact: string
  confidence: number
  priority: 'Critical' | 'High' | 'Medium' | 'Low'
  rawData: Record<string, number | string>
  agentId: string
  agentName: string
}): ReasoningChain {
  return params
}

// ─── Coffee Shop ────────────────────────────────────────

const COFFEE_SHOP_PRODUCTS: ProductDef[] = [
  { name: 'Espresso', sku: 'ESP-001', price: 450, category: 'drinks', popularity: 0.92 },
  { name: 'Cappuccino', sku: 'CAP-001', price: 525, category: 'drinks', popularity: 0.90 },
  { name: 'Iced Latte', sku: 'ICL-001', price: 575, category: 'drinks', popularity: 0.85 },
  { name: 'Cold Brew', sku: 'CDB-001', price: 550, category: 'drinks', popularity: 0.80 },
  { name: 'Matcha Latte', sku: 'MAT-001', price: 625, category: 'drinks', popularity: 0.65 },
  { name: 'Drip Coffee', sku: 'DRP-001', price: 275, category: 'drinks', popularity: 0.70 },
  { name: 'Croissant', sku: 'CRO-001', price: 425, category: 'food', popularity: 0.80 },
  { name: 'Avocado Toast', sku: 'AVO-001', price: 895, category: 'food', popularity: 0.60 },
  { name: 'Breakfast Sandwich', sku: 'BKF-001', price: 750, category: 'food', popularity: 0.70 },
  { name: 'Blueberry Muffin', sku: 'MUF-001', price: 395, category: 'food', popularity: 0.75 },
]

const COFFEE_SHOP_HOURLY = [
  0, 0, 0, 0, 0, 5, 15, 45, 85, 70, 55, 65, 80, 70, 50, 40, 35, 30, 20, 10, 5, 0, 0, 0,
]

function coffeeShopInsights(): Insight[] {
  return [
    {
      id: uuid(), type: 'staffing',
      title: 'Morning Rush Bottleneck at Counter',
      summary: 'Between 7:00-8:00 AM, queue wait times average 5.8 minutes with 4 daily line abandonments. Each lost customer costs $7.50 avg ticket. Adding one barista during this window reduces wait time to 2.1 min and recovers ~$900/month in walkout revenue.',
      details: { peak_window: '7:00-8:00 AM', avg_wait_min: 5.8, abandonments: 4, avg_ticket_cents: 750 },
      impact_cents: 90000, confidence: 0.88, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(2),
    },
    {
      id: uuid(), type: 'product_recommendation',
      title: 'Cappuccino + Croissant Bundle Opportunity',
      summary: '34% of Cappuccino buyers also purchase a Croissant separately ($5.25 + $4.25 = $9.50). A $8.50 bundle increases attachment from 34% to an estimated 52%, adding ~$380/month.',
      details: { co_purchase_rate: 0.34, bundle_price_cents: 850, individual_total_cents: 950 },
      impact_cents: 38000, confidence: 0.78, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(5),
    },
    {
      id: uuid(), type: 'pricing',
      title: 'Matcha Latte Price Below Competitor Average',
      summary: 'Current price $6.25 is $1.25 below the local competitor average of $7.50. Demand elasticity is -0.3 (highly inelastic). Raising to $7.00 captures ~$840/month with minimal volume impact.',
      details: { current_cents: 625, suggested_cents: 700, competitor_avg_cents: 750, elasticity: -0.3 },
      impact_cents: 84000, confidence: 0.82, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(3),
    },
    {
      id: uuid(), type: 'general',
      title: 'Back Seating Area Underutilized on Weekdays',
      summary: 'Camera analysis shows the back seating zone draws only 8% of weekday afternoon foot traffic. Revenue per square foot is $4/day vs. $48/day at the counter zone. Consider converting to a grab-and-go display or co-working setup.',
      details: { zone: 'back seating', weekday_traffic_pct: 8, revenue_per_sqft: 4 },
      impact_cents: 22000, confidence: 0.72, action_status: 'viewed',
      valid_until: daysFromNow(30), created_at: hoursAgo(8),
    },
    {
      id: uuid(), type: 'inventory',
      title: 'Cold Brew Over-Prepared on Mondays',
      summary: 'Monday Cold Brew sales average 18 units vs. 32 batch prep. 44% waste translates to $62/week in ingredient cost. Reduce Monday batch to 22 units.',
      details: { day: 'Monday', sales_avg: 18, batch_size: 32, waste_pct: 44 },
      impact_cents: 24800, confidence: 0.75, action_status: 'accepted',
      valid_until: daysFromNow(14), created_at: hoursAgo(12),
    },
  ]
}

function coffeeShopTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: 'Increase Matcha Latte price from $6.25 to $7.00',
      description: 'Demand elasticity analysis shows highly inelastic demand (-0.3). Current price is $1.25 below competitor average.',
      expectedImpact: '+$840/month revenue',
      impactCents: 84000, effort: 'Low', confidence: 82, priority: 'Critical',
      agentSource: 'margin-optimizer',
      reasoning: makeReasoning({
        observation: 'Matcha Latte $6.25, competitor avg $7.50, elasticity -0.3',
        reasoning: '12% price increase causes only 3.6% volume decline. Net revenue lift far exceeds volume loss.',
        conclusion: 'Raise Matcha Latte to $7.00, still $0.50 below competitor average.',
        impact: '+$840/month revenue, +$640/month margin',
        confidence: 82, priority: 'Critical',
        rawData: { current_price: '$6.25', competitor_avg: '$7.50', elasticity: -0.3 },
        agentId: 'margin-optimizer', agentName: 'Margin Optimizer',
      }),
    },
    {
      rank: 2,
      title: 'Add 1 staff member during 7-8AM peak',
      description: 'Morning peak concentrates 47% of daily revenue. Queue wait times cause 4 daily walkouts at $7.50 avg ticket.',
      expectedImpact: '+$520/month from reduced walkouts',
      impactCents: 52000, effort: 'Medium', confidence: 88, priority: 'Critical',
      agentSource: 'peak-hour-optimizer',
      reasoning: makeReasoning({
        observation: '47% of revenue in 7-9AM, 4 walkouts/day at $7.50 avg ticket',
        reasoning: '4 lost customers x $7.50 = $30/day. Staff cost $18/hr x 2hr = $36/day. Net gain from reduced queue time and upsell opportunity.',
        conclusion: 'Add one barista for 7-9AM shift.',
        impact: '+$520/month net revenue after labor cost',
        confidence: 88, priority: 'Critical',
        rawData: { peak_share: '47%', walkouts: 4, avg_ticket: '$7.50' },
        agentId: 'peak-hour-optimizer', agentName: 'Peak Hour Optimizer',
      }),
    },
    {
      rank: 3,
      title: 'Launch Cappuccino + Croissant bundle at $8.50',
      description: '34% co-purchase rate can increase to 52% with a visible combo deal, adding $380/month.',
      expectedImpact: '+$380/month from increased attachment',
      impactCents: 38000, effort: 'Low', confidence: 78, priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: makeReasoning({
        observation: '34% of Cappuccino orders include Croissant, separately $9.50',
        reasoning: 'Bundle at $8.50 gives $1.00 savings. Projected attachment lift from 34% to 52% = 32 additional sales/week.',
        conclusion: 'Create "Morning Combo" bundle at $8.50.',
        impact: '+$380/month additional revenue',
        confidence: 78, priority: 'High',
        rawData: { co_purchase_rate: '34%', projected_rate: '52%', bundle_price: '$8.50' },
        agentId: 'product-intelligence', agentName: 'Product Intelligence',
      }),
    },
  ]
}

// ─── Restaurant ─────────────────────────────────────────

const RESTAURANT_PRODUCTS: ProductDef[] = [
  { name: 'Grilled Salmon', sku: 'SAL-001', price: 2800, category: 'entrees', popularity: 0.85 },
  { name: 'Ribeye Steak', sku: 'RIB-001', price: 4200, category: 'entrees', popularity: 0.90 },
  { name: 'Caesar Salad', sku: 'CES-001', price: 1400, category: 'starters', popularity: 0.75 },
  { name: 'Lobster Bisque', sku: 'LOB-001', price: 1600, category: 'starters', popularity: 0.65 },
  { name: 'Chicken Parmesan', sku: 'CHP-001', price: 2200, category: 'entrees', popularity: 0.80 },
  { name: 'Margherita Pizza', sku: 'MPZ-001', price: 1800, category: 'entrees', popularity: 0.70 },
  { name: 'Tiramisu', sku: 'TIR-001', price: 1200, category: 'desserts', popularity: 0.55 },
  { name: 'Craft Cocktail', sku: 'CCK-001', price: 1500, category: 'drinks', popularity: 0.72 },
  { name: 'House Wine', sku: 'HWN-001', price: 1100, category: 'drinks', popularity: 0.68 },
  { name: 'Sparkling Water', sku: 'SPW-001', price: 400, category: 'drinks', popularity: 0.60 },
]

const RESTAURANT_HOURLY = [
  0, 0, 0, 0, 0, 0, 0, 2, 5, 8, 15, 55, 72, 60, 25, 8, 12, 35, 65, 85, 78, 55, 20, 5,
]

function restaurantInsights(): Insight[] {
  return [
    {
      id: uuid(), type: 'staffing',
      title: 'Dinner Table Turn Speed at 94 Min Avg, Benchmark Is 75 Min',
      summary: 'Average dinner table turn time is 94 minutes, 25% slower than the 75-minute full-service restaurant benchmark. Each additional turn at the 42-seat dining room at $42 avg ticket equals $1,764/night. Reducing turn time by 15 minutes could add 0.4 additional seatings per table per night, recovering $2,200/month.',
      details: { avg_turn_min: 94, benchmark_min: 75, seats: 42, avg_ticket_cents: 4200 },
      impact_cents: 220000, confidence: 0.85, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(2),
    },
    {
      id: uuid(), type: 'general',
      title: 'Bar Area Underutilized at Lunch: Only 12% of Covers Order Drinks',
      summary: 'During lunch service (11AM-2PM), only 12% of covers include a bar drink vs. 58% at dinner. The bar generates $4/sqft/day at lunch vs. $32/sqft at dinner. Consider a lunch cocktail menu or bar-side lunch specials to lift beverage attachment.',
      details: { lunch_drink_pct: 12, dinner_drink_pct: 58, bar_revenue_sqft_lunch: 4, bar_revenue_sqft_dinner: 32 },
      impact_cents: 48000, confidence: 0.74, action_status: 'viewed',
      valid_until: daysFromNow(30), created_at: hoursAgo(6),
    },
    {
      id: uuid(), type: 'pricing',
      title: 'Ribeye Steak Margin Compression: Food Cost at 38%',
      summary: 'Ribeye food cost has risen to 38% (benchmark: 30% for premium entrees). Wholesale beef prices are up 12% YoY. A $3 price increase to $45 brings food cost to 33% with minimal demand impact (elasticity: -0.2).',
      details: { current_cost_pct: 38, benchmark_pct: 30, suggested_price_cents: 4500 },
      impact_cents: 54000, confidence: 0.80, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(4),
    },
    {
      id: uuid(), type: 'product_recommendation',
      title: 'Dessert Attachment Rate at 18% vs. 28% Benchmark',
      summary: 'Only 18% of dinner tables order dessert vs. the 28% industry benchmark. Tiramisu is the only dessert option. Adding 2 dessert choices and implementing a tableside dessert tray presentation could lift attachment to 25%, adding $1,440/month.',
      details: { current_dessert_rate: 0.18, benchmark: 0.28, avg_dessert_cents: 1200 },
      impact_cents: 144000, confidence: 0.72, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(8),
    },
    {
      id: uuid(), type: 'anomaly',
      title: 'Wednesday Revenue 28% Below Thursday: $1,120/Week Gap',
      summary: 'Wednesday dinner revenue averages $1,680 vs. Thursday at $2,340, a 28% gap. No menu or staffing differences detected. Launching a Wednesday prix-fixe promotion could close 40% of the gap, recovering $1,800/month.',
      details: { wed_avg_cents: 168000, thu_avg_cents: 234000, gap_pct: 28 },
      impact_cents: 180000, confidence: 0.68, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(10),
    },
  ]
}

function restaurantTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: 'Reduce dinner table turn time from 94 to 80 minutes',
      description: 'Pre-set dessert menus on tables, implement 15-min post-entree check cadence, and streamline bill presentation to cut 14 minutes per turn.',
      expectedImpact: '+$2,200/month from additional seatings',
      impactCents: 220000, effort: 'Medium', confidence: 85, priority: 'Critical',
      agentSource: 'peak-hour-optimizer',
      reasoning: makeReasoning({
        observation: 'Table turn 94 min avg, benchmark 75 min, 42 seats',
        reasoning: 'Reducing turn time by 14 min yields 0.4 additional turns/table/night. At $42/cover, that is $2,200/month.',
        conclusion: 'Implement streamlined dinner service cadence.',
        impact: '+$2,200/month from additional cover capacity',
        confidence: 85, priority: 'Critical',
        rawData: { turn_time_min: 94, benchmark_min: 75, seats: 42, avg_ticket: '$42' },
        agentId: 'peak-hour-optimizer', agentName: 'Peak Hour Optimizer',
      }),
    },
    {
      rank: 2,
      title: 'Increase Ribeye Steak price from $42 to $45',
      description: 'Beef costs up 12% YoY. Current food cost 38% vs. 30% benchmark. Price increase brings margin in line with minimal volume impact.',
      expectedImpact: '+$540/month margin improvement',
      impactCents: 54000, effort: 'Low', confidence: 80, priority: 'High',
      agentSource: 'margin-optimizer',
      reasoning: makeReasoning({
        observation: 'Ribeye food cost 38%, benchmark 30%, beef up 12% YoY',
        reasoning: '$3 increase on ~180 monthly units = $540/month. Elasticity -0.2 means <4% volume decline.',
        conclusion: 'Raise Ribeye to $45. Still competitive for the premium segment.',
        impact: '+$540/month margin improvement',
        confidence: 80, priority: 'High',
        rawData: { food_cost_pct: '38%', benchmark: '30%', monthly_units: 180, price_increase: '$3' },
        agentId: 'margin-optimizer', agentName: 'Margin Optimizer',
      }),
    },
    {
      rank: 3,
      title: 'Launch lunch bar cocktail menu to lift beverage attachment',
      description: 'Only 12% of lunch covers order drinks vs. 58% at dinner. A curated 4-drink lunch cocktail list with $12 price point targets 25% attachment.',
      expectedImpact: '+$480/month from lunch bar revenue',
      impactCents: 48000, effort: 'Low', confidence: 74, priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: makeReasoning({
        observation: 'Lunch bar drink attachment 12% vs. 58% at dinner',
        reasoning: 'Targeting 25% attachment on ~90 lunch covers/day = 11 additional drinks at $12 avg = $132/day = $3,960/month. Conservative: $480/month accounting for ramp.',
        conclusion: 'Introduce a focused lunch cocktail menu.',
        impact: '+$480/month from lunch bar revenue lift',
        confidence: 74, priority: 'High',
        rawData: { lunch_drink_pct: '12%', dinner_drink_pct: '58%', target_pct: '25%', avg_drink_price: '$12' },
        agentId: 'product-intelligence', agentName: 'Product Intelligence',
      }),
    },
  ]
}

// ─── Fast Food ──────────────────────────────────────────

const FAST_FOOD_PRODUCTS: ProductDef[] = [
  { name: 'Classic Burger', sku: 'BRG-001', price: 899, category: 'burgers', popularity: 0.95 },
  { name: 'Double Stack', sku: 'DBL-001', price: 1149, category: 'burgers', popularity: 0.85 },
  { name: 'Chicken Tenders', sku: 'CHK-001', price: 799, category: 'sides', popularity: 0.80 },
  { name: 'Fries Large', sku: 'FRL-001', price: 449, category: 'sides', popularity: 0.92 },
  { name: 'Onion Rings', sku: 'ONR-001', price: 549, category: 'sides', popularity: 0.55 },
  { name: 'Milkshake', sku: 'MLK-001', price: 599, category: 'drinks', popularity: 0.60 },
  { name: 'Soda Fountain', sku: 'SOD-001', price: 249, category: 'drinks', popularity: 0.88 },
  { name: 'Combo Meal', sku: 'CMB-001', price: 1399, category: 'combos', popularity: 0.90 },
  { name: 'Kids Meal', sku: 'KDS-001', price: 699, category: 'combos', popularity: 0.50 },
  { name: 'Apple Pie', sku: 'APL-001', price: 349, category: 'desserts', popularity: 0.45 },
]

const FAST_FOOD_HOURLY = [
  0, 0, 0, 0, 0, 0, 2, 8, 15, 22, 35, 82, 95, 75, 30, 18, 25, 45, 72, 60, 35, 15, 5, 0,
]

function fastFoodInsights(): Insight[] {
  return [
    {
      id: uuid(), type: 'staffing',
      title: 'Drive-Through Queue Abandonment: 8 Cars Leave Line Daily at Lunch',
      summary: 'Between 11:30AM-1:00PM, an average of 8 vehicles exit the drive-through lane before ordering. At $11.00 avg transaction, this represents $88/day or $2,640/month in lost revenue. Queue camera shows avg wait exceeding 6.5 minutes during peak. Adding a mobile order-taker reduces wait to 3.2 min.',
      details: { abandoned_cars: 8, avg_wait_min: 6.5, target_wait_min: 3.2, avg_tx_cents: 1100 },
      impact_cents: 264000, confidence: 0.86, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(2),
    },
    {
      id: uuid(), type: 'general',
      title: 'Seating Area Dead Zone After 2PM: 98% Takeout',
      summary: 'After 2:00PM, 98% of orders are takeout. The 40-seat dining area consumes 35% of floor space but generates $0.80/sqft/day after lunch. Consider converting 50% of seating to a pickup staging area to improve drive-through and counter flow.',
      details: { post_2pm_takeout_pct: 98, seating_sqft_share: 35, revenue_sqft: 0.80 },
      impact_cents: 18000, confidence: 0.70, action_status: 'viewed',
      valid_until: daysFromNow(30), created_at: hoursAgo(8),
    },
    {
      id: uuid(), type: 'product_recommendation',
      title: 'Combo Meal Attachment at 62% vs. 75% QSR Benchmark',
      summary: 'Only 62% of burger orders include a combo upgrade vs. the 75% QSR industry benchmark. Training staff to default-suggest the combo at order and adding a POS prompt could lift attachment to 70%, adding $680/month.',
      details: { current_combo_pct: 62, benchmark_pct: 75, target_pct: 70 },
      impact_cents: 68000, confidence: 0.78, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(5),
    },
    {
      id: uuid(), type: 'pricing',
      title: 'Large Fries Margin Opportunity: 82% Gross Margin',
      summary: 'Large Fries has the highest gross margin at 82% but is ordered standalone only 15% of the time. Promoting fries as an add-on at the register with a $0.99 upsell prompt could increase standalone orders by 20%, adding $360/month.',
      details: { fries_margin_pct: 82, standalone_order_pct: 15 },
      impact_cents: 36000, confidence: 0.74, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(6),
    },
    {
      id: uuid(), type: 'anomaly',
      title: 'Saturday Dinner Revenue 34% Above Friday',
      summary: 'Saturday 5-7PM revenue is $1,420 vs. Friday at $1,060, a 34% gap despite similar traffic. Average ticket on Saturday is $12.80 vs. $10.40 on Friday. Customers order more premium items (Double Stack, Milkshake) on Saturday. Promote premium combos on Friday to capture similar uplift.',
      details: { sat_cents: 142000, fri_cents: 106000, sat_ticket_cents: 1280, fri_ticket_cents: 1040 },
      impact_cents: 36000, confidence: 0.65, action_status: 'viewed',
      valid_until: daysFromNow(14), created_at: hoursAgo(12),
    },
  ]
}

function fastFoodTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: 'Deploy mobile order-taker in drive-through at lunch peak',
      description: 'Tablet-based lane ordering reduces avg wait from 6.5 to 3.2 minutes, recovering 8 abandoned cars/day at $11 avg transaction.',
      expectedImpact: '+$2,640/month from reduced drive-through abandonment',
      impactCents: 264000, effort: 'Medium', confidence: 86, priority: 'Critical',
      agentSource: 'queue-monitor',
      reasoning: makeReasoning({
        observation: '8 cars abandon drive-through daily, avg wait 6.5 min at peak',
        reasoning: '8 cars x $11 avg tx x 30 days = $2,640/month. Mobile order-taker cost: $18/hr x 2hr = $36/day. Net gain significant.',
        conclusion: 'Station a mobile order-taker in the drive-through lane 11:30AM-1:00PM.',
        impact: '+$2,640/month recovered revenue',
        confidence: 86, priority: 'Critical',
        rawData: { abandoned_cars: 8, avg_wait: '6.5 min', avg_ticket: '$11', labor_cost: '$36/day' },
        agentId: 'queue-monitor', agentName: 'Queue Monitor',
      }),
    },
    {
      rank: 2,
      title: 'Add POS combo upsell prompt for all burger orders',
      description: 'Default-suggest combo upgrade at point of sale. Current 62% combo rate vs. 75% benchmark indicates significant headroom.',
      expectedImpact: '+$680/month from higher combo attachment',
      impactCents: 68000, effort: 'Low', confidence: 78, priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: makeReasoning({
        observation: 'Combo attachment 62% vs. 75% QSR benchmark',
        reasoning: 'Lifting from 62% to 70% on ~520 daily orders adds ~42 combo upgrades/day. $5 avg upsell = $210/day gross, conservative net $680/month.',
        conclusion: 'Configure POS to auto-prompt combo on all burger orders.',
        impact: '+$680/month combo upsell revenue',
        confidence: 78, priority: 'High',
        rawData: { current_rate: '62%', target_rate: '70%', daily_orders: 520, combo_premium: '$5' },
        agentId: 'product-intelligence', agentName: 'Product Intelligence',
      }),
    },
    {
      rank: 3,
      title: 'Promote premium items on Friday evenings',
      description: 'Friday avg ticket $10.40 vs. Saturday $12.80. Promoting Double Stack and Milkshake combos on Friday 5-7PM can lift ticket to $11.50.',
      expectedImpact: '+$360/month from Friday premium uplift',
      impactCents: 36000, effort: 'Low', confidence: 65, priority: 'Medium',
      agentSource: 'margin-optimizer',
      reasoning: makeReasoning({
        observation: 'Friday avg ticket $10.40 vs. Saturday $12.80 during 5-7PM',
        reasoning: 'If Friday ticket lifts $1.10 to $11.50 on ~100 dinner orders = $110/Friday = $440/month. Conservative: $360/month.',
        conclusion: 'Feature premium items in Friday evening promotions.',
        impact: '+$360/month from ticket lift',
        confidence: 65, priority: 'Medium',
        rawData: { fri_ticket: '$10.40', sat_ticket: '$12.80', target_ticket: '$11.50' },
        agentId: 'margin-optimizer', agentName: 'Margin Optimizer',
      }),
    },
  ]
}

// ─── Auto Shop ──────────────────────────────────────────

const AUTO_SHOP_PRODUCTS: ProductDef[] = [
  { name: 'Oil Change', sku: 'OIL-001', price: 4999, category: 'maintenance', popularity: 0.95 },
  { name: 'Brake Pad Replace', sku: 'BRK-001', price: 24900, category: 'repair', popularity: 0.70 },
  { name: 'Tire Rotation', sku: 'TIR-001', price: 3999, category: 'maintenance', popularity: 0.80 },
  { name: 'Full Inspection', sku: 'INS-001', price: 8999, category: 'diagnostic', popularity: 0.75 },
  { name: 'Transmission Flush', sku: 'TRN-001', price: 17900, category: 'maintenance', popularity: 0.40 },
  { name: 'AC Recharge', sku: 'ACR-001', price: 14900, category: 'repair', popularity: 0.50 },
  { name: 'Alignment', sku: 'ALN-001', price: 9999, category: 'maintenance', popularity: 0.55 },
  { name: 'Battery Replace', sku: 'BAT-001', price: 18900, category: 'repair', popularity: 0.45 },
  { name: 'Wiper Blades', sku: 'WPR-001', price: 3499, category: 'parts', popularity: 0.60 },
  { name: 'Engine Diagnostic', sku: 'DGN-001', price: 12900, category: 'diagnostic', popularity: 0.65 },
]

const AUTO_SHOP_HOURLY = [
  0, 0, 0, 0, 0, 0, 2, 18, 42, 35, 22, 18, 15, 12, 15, 18, 12, 5, 2, 0, 0, 0, 0, 0,
]

function autoShopInsights(): Insight[] {
  return [
    {
      id: uuid(), type: 'general',
      title: 'Waiting Area Dwell Time 95 Min Avg: Upsell Window for Add-On Services',
      summary: 'Customers waiting for service spend an average of 95 minutes in the waiting area. During this dwell time, only 8% add supplementary services. Implementing a digital service menu on the waiting area TV with real-time vehicle status and recommended add-ons (e.g., "While we have your car up: alignment check $39.99") could lift add-on rate to 22%, recovering $6,200/month.',
      details: { avg_dwell_min: 95, current_addon_pct: 8, target_addon_pct: 22, avg_addon_cents: 5500 },
      impact_cents: 620000, confidence: 0.78, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(2),
    },
    {
      id: uuid(), type: 'general',
      title: 'Parts Display Area Generates Zero Browse-to-Purchase Conversions',
      summary: 'The parts display area (Wiper Blades, accessories) occupies 120 sqft but camera analysis shows customers never browse it. All parts purchases happen at the service counter during checkout. Consider converting this space to an additional service bay or customer comfort area.',
      details: { display_sqft: 120, browse_rate: 0, counter_parts_pct: 100 },
      impact_cents: 0, confidence: 0.90, action_status: 'viewed',
      valid_until: daysFromNow(30), created_at: hoursAgo(6),
    },
    {
      id: uuid(), type: 'staffing',
      title: 'Morning Drop-Off Window (7-10AM) Handles 65% of Daily Volume',
      summary: 'Between 7-10AM, 65% of daily vehicle drop-offs occur. The service desk has only 1 advisor during this window, creating 12-minute avg check-in times. Adding a second advisor during 7-10AM reduces check-in to 4 minutes and prevents 2 daily drive-aways.',
      details: { dropoff_share: 65, current_advisors: 1, avg_checkin_min: 12, target_min: 4, daily_driveaways: 2 },
      impact_cents: 111000, confidence: 0.82, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(4),
    },
    {
      id: uuid(), type: 'product_recommendation',
      title: 'Oil Change to Full Inspection Upsell Conversion at 14%',
      summary: 'Only 14% of Oil Change customers add a Full Inspection ($89.99). Industry benchmark is 28%. Training service advisors to present inspection results visually (photo/video of undercarriage) lifts conversion to 22%, adding $1,800/month.',
      details: { current_upsell_pct: 14, benchmark_pct: 28, target_pct: 22, inspection_price_cents: 8999 },
      impact_cents: 180000, confidence: 0.76, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(8),
    },
    {
      id: uuid(), type: 'pricing',
      title: 'Tire Rotation Priced 22% Below Local Competitors',
      summary: 'Current Tire Rotation price $39.99 vs. local competitor average of $51.50. Demand is highly inelastic for this service. Raising to $44.99 aligns with market while maintaining value perception.',
      details: { current_cents: 3999, competitor_avg_cents: 5150, suggested_cents: 4499 },
      impact_cents: 42000, confidence: 0.80, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(10),
    },
  ]
}

function autoShopTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: 'Install digital upsell menu in waiting area',
      description: 'Avg 95-min dwell time with only 8% add-on rate. A digital display showing vehicle status + recommended services targets 22% add-on rate.',
      expectedImpact: '+$6,200/month from waiting area upsells',
      impactCents: 620000, effort: 'Medium', confidence: 78, priority: 'Critical',
      agentSource: 'dwell-time-analyzer',
      reasoning: makeReasoning({
        observation: 'Waiting area dwell 95 min, add-on rate 8%, avg add-on $55',
        reasoning: '28 daily customers x (22% - 8%) add-on lift x $55 avg = $21.56/day = $647/month per percentage point. Total lift: $6,200/month.',
        conclusion: 'Install digital service menu with live vehicle status updates in waiting area.',
        impact: '+$6,200/month from increased service add-on rate',
        confidence: 78, priority: 'Critical',
        rawData: { avg_dwell_min: 95, current_addon: '8%', target_addon: '22%', avg_addon: '$55' },
        agentId: 'dwell-time-analyzer', agentName: 'Dwell Time Analyzer',
      }),
    },
    {
      rank: 2,
      title: 'Train advisors on visual inspection upsell technique',
      description: 'Show customers photos/videos of their vehicle during inspection. Lifts Oil Change to Inspection conversion from 14% to 22%.',
      expectedImpact: '+$1,800/month from inspection upsell',
      impactCents: 180000, effort: 'Low', confidence: 76, priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: makeReasoning({
        observation: 'Oil Change → Inspection upsell at 14% vs. 28% benchmark',
        reasoning: '~20 oil changes/day x 8% lift x $89.99 = $144/day = $4,320/month. Conservative: $1,800/month.',
        conclusion: 'Implement visual inspection presentation workflow for service advisors.',
        impact: '+$1,800/month from higher inspection attachment',
        confidence: 76, priority: 'High',
        rawData: { upsell_rate: '14%', target: '22%', inspection_price: '$89.99' },
        agentId: 'product-intelligence', agentName: 'Product Intelligence',
      }),
    },
    {
      rank: 3,
      title: 'Add second service advisor for 7-10AM drop-off window',
      description: 'Morning drop-offs handle 65% of volume with 12-min check-in times. Adding a second advisor prevents 2 daily drive-aways at $185 avg ticket.',
      expectedImpact: '+$1,110/month from reduced drive-aways',
      impactCents: 111000, effort: 'Medium', confidence: 82, priority: 'High',
      agentSource: 'peak-hour-optimizer',
      reasoning: makeReasoning({
        observation: '65% of drop-offs in 7-10AM, 1 advisor, 12-min avg check-in, 2 drive-aways/day',
        reasoning: '2 drive-aways x $185 avg ticket x 30 days = $11,100/month. Second advisor cost ~$54/day x 22 workdays = $1,188/month. Net: ~$1,110/month.',
        conclusion: 'Schedule second service advisor for 7-10AM window.',
        impact: '+$1,110/month net after labor cost',
        confidence: 82, priority: 'High',
        rawData: { drop_off_share: '65%', avg_checkin_min: 12, drive_aways: 2, avg_ticket: '$185' },
        agentId: 'peak-hour-optimizer', agentName: 'Peak Hour Optimizer',
      }),
    },
  ]
}

// ─── Smoke Shop ─────────────────────────────────────────

const SMOKE_SHOP_PRODUCTS: ProductDef[] = [
  { name: 'Premium Cigar', sku: 'CIG-001', price: 1800, category: 'tobacco', popularity: 0.65 },
  { name: 'Cigarette Carton', sku: 'CRT-001', price: 6500, category: 'tobacco', popularity: 0.90 },
  { name: 'Vape Pod Pack', sku: 'VPP-001', price: 2400, category: 'vape', popularity: 0.85 },
  { name: 'Rolling Papers', sku: 'RLP-001', price: 450, category: 'accessories', popularity: 0.75 },
  { name: 'Glass Pipe', sku: 'GLP-001', price: 4500, category: 'glass', popularity: 0.45 },
  { name: 'E-Liquid 60ml', sku: 'ELQ-001', price: 2200, category: 'vape', popularity: 0.70 },
  { name: 'Lighter Collection', sku: 'LTR-001', price: 800, category: 'accessories', popularity: 0.80 },
  { name: 'Hookah Tobacco', sku: 'HKH-001', price: 2800, category: 'tobacco', popularity: 0.50 },
  { name: 'CBD Gummies', sku: 'CBD-001', price: 3500, category: 'cbd', popularity: 0.55 },
  { name: 'Grinder', sku: 'GRN-001', price: 2500, category: 'accessories', popularity: 0.48 },
]

const SMOKE_SHOP_HOURLY = [
  0, 0, 0, 0, 0, 0, 0, 2, 5, 8, 12, 15, 18, 20, 22, 28, 42, 55, 48, 35, 22, 12, 5, 0,
]

function smokeShopInsights(): Insight[] {
  return [
    {
      id: uuid(), type: 'general',
      title: 'Accessory Wall: High Dwell Time but 8% Conversion',
      summary: 'Camera heatmap shows the accessory/novelty wall draws 3.2x average dwell time, but only 8% of browsers purchase. Products are priced $8-$45 with no clear value hierarchy. Implementing tiered display (good/better/best) and adding shelf-edge price callouts could lift conversion to 18%, adding $1,850/month.',
      details: { dwell_multiplier: 3.2, browse_conversion_pct: 8, target_pct: 18, zone: 'accessory wall' },
      impact_cents: 185000, confidence: 0.74, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(2),
    },
    {
      id: uuid(), type: 'product_recommendation',
      title: 'Vape Pod + E-Liquid Cross-Sell at 22% vs. 40% Benchmark',
      summary: 'Only 22% of Vape Pod Pack buyers also purchase E-Liquid in the same transaction. Industry benchmark is 40%. POS prompt and a shelf co-location change could lift to 32%, adding $620/month in incremental E-Liquid sales.',
      details: { current_cross_sell_pct: 22, benchmark_pct: 40, target_pct: 32 },
      impact_cents: 62000, confidence: 0.76, action_status: 'pending',
      valid_until: daysFromNow(21), created_at: hoursAgo(5),
    },
    {
      id: uuid(), type: 'staffing',
      title: 'After-Work Rush (4-7PM): 55% of Revenue in 3 Hours',
      summary: 'The 4-7PM window generates 55% of daily revenue with a single staff member. Queue time averages 4.8 minutes during 5-6PM. Adding a second register operator during 4-7PM reduces wait to 1.5 minutes and prevents 3 daily walkouts at $28 avg ticket.',
      details: { peak_window: '4-7PM', revenue_share: 55, avg_wait_min: 4.8, walkouts: 3, avg_ticket_cents: 2800 },
      impact_cents: 25200, confidence: 0.82, action_status: 'pending',
      valid_until: daysFromNow(14), created_at: hoursAgo(4),
    },
    {
      id: uuid(), type: 'pricing',
      title: 'CBD Gummies Margin Opportunity: 68% Margin at Current Price',
      summary: 'CBD Gummies at $35 have 68% margin, but competitor average is $39.99. Raising to $37.50 maintains competitiveness while adding $137/month at current volume.',
      details: { current_cents: 3500, competitor_avg_cents: 3999, suggested_cents: 3750, current_margin_pct: 68 },
      impact_cents: 13700, confidence: 0.72, action_status: 'pending',
      valid_until: daysFromNow(30), created_at: hoursAgo(8),
    },
    {
      id: uuid(), type: 'inventory',
      title: 'Hookah Tobacco Slow Mover: 32-Day Average Shelf Life',
      summary: 'Hookah Tobacco averages 32 days on shelf before sale, tying up $840 in inventory. Reduce order quantity by 40% and offer a "Hookah Starter Kit" bundle (tobacco + pipe + coals) at a 10% discount to increase velocity.',
      details: { avg_shelf_days: 32, inventory_cost_cents: 84000, suggested_reduction_pct: 40 },
      impact_cents: 16800, confidence: 0.68, action_status: 'viewed',
      valid_until: daysFromNow(14), created_at: hoursAgo(12),
    },
  ]
}

function smokeShopTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: 'Redesign accessory wall with tiered display and price callouts',
      description: 'High dwell (3.2x average) but only 8% conversion. Good/better/best layout with clear pricing targets 18% conversion.',
      expectedImpact: '+$1,850/month from accessory wall conversion lift',
      impactCents: 185000, effort: 'Medium', confidence: 74, priority: 'Critical',
      agentSource: 'heatmap-generator',
      reasoning: makeReasoning({
        observation: 'Accessory wall: 3.2x dwell, 8% purchase conversion, $8-$45 range',
        reasoning: 'With 95 daily customers and ~60% browsing the wall (57 browsers), lifting conversion from 8% to 18% adds 5.7 purchases/day at $25 avg = $142/day = $4,260/month. Conservative: $1,850/month.',
        conclusion: 'Implement tiered merchandising with clear price anchoring on accessory wall.',
        impact: '+$1,850/month from improved conversion',
        confidence: 74, priority: 'Critical',
        rawData: { dwell_multiplier: '3.2x', current_conversion: '8%', target_conversion: '18%', avg_item: '$25' },
        agentId: 'heatmap-generator', agentName: 'Heatmap Generator',
      }),
    },
    {
      rank: 2,
      title: 'Implement Vape Pod + E-Liquid cross-sell at POS',
      description: 'Current cross-sell rate 22% vs. 40% benchmark. POS prompt plus shelf co-location targets 32%.',
      expectedImpact: '+$620/month from E-Liquid cross-sell',
      impactCents: 62000, effort: 'Low', confidence: 76, priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: makeReasoning({
        observation: 'Vape Pod + E-Liquid cross-sell at 22% vs. 40% industry benchmark',
        reasoning: '~80 Vape Pod sales/month x 10% lift x $22 E-Liquid = $176/month. Conservative accounting for POS prompt fatigue: $620/month.',
        conclusion: 'Add POS cross-sell prompt and co-locate products on shelf.',
        impact: '+$620/month incremental E-Liquid revenue',
        confidence: 76, priority: 'High',
        rawData: { cross_sell: '22%', benchmark: '40%', e_liquid_price: '$22' },
        agentId: 'product-intelligence', agentName: 'Product Intelligence',
      }),
    },
    {
      rank: 3,
      title: 'Add second register operator during 4-7PM peak',
      description: '55% of revenue in 3 hours with single staff. Queue wait 4.8 min causes 3 daily walkouts at $28 avg ticket.',
      expectedImpact: '+$252/month from reduced walkouts',
      impactCents: 25200, effort: 'Medium', confidence: 82, priority: 'High',
      agentSource: 'peak-hour-optimizer',
      reasoning: makeReasoning({
        observation: '4-7PM: 55% of revenue, 4.8 min queue wait, 3 walkouts/day',
        reasoning: '3 walkouts x $28 x 30 days = $2,520/month. Staff cost ~$16/hr x 3hr = $48/day x 22 days = $1,056/month. Net: ~$252/month.',
        conclusion: 'Schedule second register operator for the 4-7PM window.',
        impact: '+$252/month net after labor cost',
        confidence: 82, priority: 'High',
        rawData: { revenue_share: '55%', walkouts: 3, avg_ticket: '$28', labor_cost: '$48/day' },
        agentId: 'peak-hour-optimizer', agentName: 'Peak Hour Optimizer',
      }),
    },
  ]
}

// ─── Industry Override Builder ──────────────────────────

function buildOverrides(params: {
  businessName: string
  dailyRevenue: number
  dailyTraffic: number
  avgTicket: number
  recoverableRevenue30d: number
  products: ProductDef[]
  hourlyDistribution: number[]
  insightsFn: () => Insight[]
  topActionsFn: () => TopAction[]
}): IndustryOverrides {
  const days = 30
  return {
    businessName: params.businessName,
    overview: generateOverviewFromParams({
      dailyRevenue: params.dailyRevenue,
      dailyTraffic: params.dailyTraffic,
      avgTicket: params.avgTicket,
      recoverableRevenue30d: params.recoverableRevenue30d,
    }),
    products: generateProductPerf(params.products, days),
    hourlyDistribution: params.hourlyDistribution,
    insights: params.insightsFn(),
    topActions: params.topActionsFn(),
    peakHourHeatmap: generatePeakHourHeatmapFromDistribution(params.hourlyDistribution),
    recoverableRevenue30d: params.recoverableRevenue30d,
  }
}

// ─── Public API ─────────────────────────────────────────

const overrideCache = new Map<BusinessType, IndustryOverrides>()

export function getIndustryOverrides(type: BusinessType): IndustryOverrides {
  const cached = overrideCache.get(type)
  if (cached) return cached

  let overrides: IndustryOverrides

  switch (type) {
    case 'coffee_shop':
      overrides = buildOverrides({
        businessName: 'Sunrise Coffee Co.',
        dailyRevenue: 217500, // 290 customers * $7.50 = $2,175
        dailyTraffic: 290,
        avgTicket: 750,
        recoverableRevenue30d: 320000, // $3,200
        products: COFFEE_SHOP_PRODUCTS,
        hourlyDistribution: COFFEE_SHOP_HOURLY,
        insightsFn: coffeeShopInsights,
        topActionsFn: coffeeShopTopActions,
      })
      break

    case 'restaurant':
      overrides = buildOverrides({
        businessName: 'The Copper Table',
        dailyRevenue: 756000, // 180 covers * $42.00 = $7,560
        dailyTraffic: 180,
        avgTicket: 4200,
        recoverableRevenue30d: 480000, // $4,800
        products: RESTAURANT_PRODUCTS,
        hourlyDistribution: RESTAURANT_HOURLY,
        insightsFn: restaurantInsights,
        topActionsFn: restaurantTopActions,
      })
      break

    case 'fast_food':
      overrides = buildOverrides({
        businessName: 'Blaze Burger',
        dailyRevenue: 572000, // 520 customers * $11.00 = $5,720
        dailyTraffic: 520,
        avgTicket: 1100,
        recoverableRevenue30d: 264000, // $2,640
        products: FAST_FOOD_PRODUCTS,
        hourlyDistribution: FAST_FOOD_HOURLY,
        insightsFn: fastFoodInsights,
        topActionsFn: fastFoodTopActions,
      })
      break

    case 'auto_shop':
      overrides = buildOverrides({
        businessName: 'Precision Auto Care',
        dailyRevenue: 518000, // 28 customers * $185.00 = $5,180
        dailyTraffic: 28,
        avgTicket: 18500,
        recoverableRevenue30d: 620000, // $6,200
        products: AUTO_SHOP_PRODUCTS,
        hourlyDistribution: AUTO_SHOP_HOURLY,
        insightsFn: autoShopInsights,
        topActionsFn: autoShopTopActions,
      })
      break

    case 'smoke_shop':
      overrides = buildOverrides({
        businessName: 'Cloud Nine Smoke Shop',
        dailyRevenue: 266000, // 95 customers * $28.00 = $2,660
        dailyTraffic: 95,
        avgTicket: 2800,
        recoverableRevenue30d: 185000, // $1,850
        products: SMOKE_SHOP_PRODUCTS,
        hourlyDistribution: SMOKE_SHOP_HOURLY,
        insightsFn: smokeShopInsights,
        topActionsFn: smokeShopTopActions,
      })
      break

    default: {
      const _exhaustive: never = type
      throw new Error(`Unknown business type: ${_exhaustive}`)
    }
  }

  overrideCache.set(type, overrides)
  return overrides
}
