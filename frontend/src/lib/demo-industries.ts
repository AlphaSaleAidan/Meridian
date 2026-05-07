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

export interface MarginIngredient {
  name: string
  batchCostCents: number
  batchServings: number
  amountUsedOz: number
  wastePct: number
}

export interface MarginItemDef {
  name: string
  category: string
  sellingPriceCents: number
  monthlySales: number
  ingredients: MarginIngredient[]
  externalLeakageCents: number
}

export interface MenuEngItem {
  name: string
  category: string
  monthlySales: number
  marginPct: number
  revenueCents: number
  marginCents: number
}

export interface MenuEngConfig {
  pageTitle: string
  xAxisLabel: string
  yAxisLabel: string
  quadrantLabels: { star: string; plowhorse: string; puzzle: string; dog: string }
  items: MenuEngItem[]
}

export interface AnomalyDef {
  id: string
  type: 'void_spike' | 'refund_surge' | 'revenue_drop' | 'cost_spike' | 'traffic_anomaly' | 'register_shortage'
  severity: 'critical' | 'warning' | 'info'
  title: string
  description: string
  metric: string
  expected: number
  actual: number
  deviationPct: number
  agentSource: string
}

export interface IndustryOverrides {
  businessName: string
  overview: Overview
  products: ProductPerf[]
  hourlyDistribution: number[]
  insights: Insight[]
  topActions: TopAction[]
  peakHourHeatmap: PeakHourCell[]
  recoverableRevenue30d: number
  marginItems: MarginItemDef[]
  menuEngConfig: MenuEngConfig
  anomalies: AnomalyDef[]
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

function coffeeShopMarginItems(): MarginItemDef[] {
  return [
    {
      name: 'Espresso', category: 'drinks', sellingPriceCents: 450, monthlySales: 330,
      ingredients: [
        { name: 'Espresso Beans', batchCostCents: 1800, batchServings: 50, amountUsedOz: 0.7, wastePct: 3 },
        { name: 'Filtered Water', batchCostCents: 200, batchServings: 100, amountUsedOz: 2, wastePct: 1 },
        { name: 'Paper Cup + Lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Cappuccino', category: 'drinks', sellingPriceCents: 525, monthlySales: 450,
      ingredients: [
        { name: 'Espresso Beans', batchCostCents: 1800, batchServings: 50, amountUsedOz: 0.7, wastePct: 3 },
        { name: 'Whole Milk', batchCostCents: 450, batchServings: 20, amountUsedOz: 6, wastePct: 5 },
        { name: 'Paper Cup + Lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Iced Latte', category: 'drinks', sellingPriceCents: 575, monthlySales: 340,
      ingredients: [
        { name: 'Espresso Beans', batchCostCents: 1800, batchServings: 50, amountUsedOz: 0.7, wastePct: 3 },
        { name: 'Whole Milk', batchCostCents: 450, batchServings: 20, amountUsedOz: 8, wastePct: 5 },
        { name: 'Ice', batchCostCents: 300, batchServings: 80, amountUsedOz: 6, wastePct: 10 },
        { name: 'Plastic Cup + Lid', batchCostCents: 1800, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Cold Brew', category: 'drinks', sellingPriceCents: 550, monthlySales: 300,
      ingredients: [
        { name: 'Cold Brew Beans', batchCostCents: 2200, batchServings: 40, amountUsedOz: 1, wastePct: 4 },
        { name: 'Filtered Water', batchCostCents: 200, batchServings: 100, amountUsedOz: 12, wastePct: 1 },
        { name: 'Plastic Cup + Lid', batchCostCents: 1800, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Matcha Latte', category: 'drinks', sellingPriceCents: 625, monthlySales: 190,
      ingredients: [
        { name: 'Matcha Powder', batchCostCents: 3200, batchServings: 30, amountUsedOz: 0.5, wastePct: 3 },
        { name: 'Oat Milk', batchCostCents: 550, batchServings: 12, amountUsedOz: 10, wastePct: 6 },
        { name: 'Paper Cup + Lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 8400,
    },
    {
      name: 'Croissant', category: 'food', sellingPriceCents: 425, monthlySales: 360,
      ingredients: [
        { name: 'Frozen Croissants', batchCostCents: 2400, batchServings: 24, amountUsedOz: 3, wastePct: 8 },
        { name: 'Butter Finish', batchCostCents: 600, batchServings: 48, amountUsedOz: 0.5, wastePct: 3 },
        { name: 'Bakery Bag', batchCostCents: 800, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 6800,
    },
    {
      name: 'Avocado Toast', category: 'food', sellingPriceCents: 895, monthlySales: 140,
      ingredients: [
        { name: 'Sourdough Bread', batchCostCents: 500, batchServings: 12, amountUsedOz: 3, wastePct: 8 },
        { name: 'Avocado', batchCostCents: 250, batchServings: 2, amountUsedOz: 4, wastePct: 12 },
        { name: 'Toppings (egg, radish, seeds)', batchCostCents: 1200, batchServings: 20, amountUsedOz: 2, wastePct: 5 },
        { name: 'Plate + Napkin', batchCostCents: 600, batchServings: 50, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 9200,
    },
    {
      name: 'Breakfast Sandwich', category: 'food', sellingPriceCents: 750, monthlySales: 180,
      ingredients: [
        { name: 'English Muffin', batchCostCents: 400, batchServings: 12, amountUsedOz: 3, wastePct: 4 },
        { name: 'Egg', batchCostCents: 450, batchServings: 12, amountUsedOz: 2, wastePct: 3 },
        { name: 'Cheese & Bacon', batchCostCents: 1400, batchServings: 20, amountUsedOz: 2, wastePct: 5 },
        { name: 'Wrapper', batchCostCents: 600, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 4200,
    },
    {
      name: 'Blueberry Muffin', category: 'food', sellingPriceCents: 395, monthlySales: 270,
      ingredients: [
        { name: 'Muffin Batter Mix', batchCostCents: 1200, batchServings: 24, amountUsedOz: 4, wastePct: 5 },
        { name: 'Blueberries', batchCostCents: 600, batchServings: 12, amountUsedOz: 1.5, wastePct: 8 },
        { name: 'Bakery Bag', batchCostCents: 800, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 3100,
    },
    {
      name: 'Drip Coffee', category: 'drinks', sellingPriceCents: 275, monthlySales: 300,
      ingredients: [
        { name: 'Drip Beans', batchCostCents: 1400, batchServings: 60, amountUsedOz: 0.5, wastePct: 3 },
        { name: 'Filter', batchCostCents: 400, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
        { name: 'Paper Cup + Lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
  ]
}

function coffeeShopMenuEngConfig(): MenuEngConfig {
  return {
    pageTitle: 'Menu Matrix',
    xAxisLabel: 'Popularity',
    yAxisLabel: 'Contribution Margin',
    quadrantLabels: { star: 'Stars', plowhorse: 'Plowhorses', puzzle: 'Puzzles', dog: 'Dogs' },
    items: [
      { name: 'Espresso', category: 'drinks', monthlySales: 330, marginPct: 78, revenueCents: 148500, marginCents: 115830 },
      { name: 'Cappuccino', category: 'drinks', monthlySales: 450, marginPct: 72, revenueCents: 236250, marginCents: 170100 },
      { name: 'Iced Latte', category: 'drinks', monthlySales: 340, marginPct: 70, revenueCents: 195500, marginCents: 136850 },
      { name: 'Cold Brew', category: 'drinks', monthlySales: 300, marginPct: 76, revenueCents: 165000, marginCents: 125400 },
      { name: 'Matcha Latte', category: 'drinks', monthlySales: 190, marginPct: 62, revenueCents: 118750, marginCents: 73625 },
      { name: 'Drip Coffee', category: 'drinks', monthlySales: 300, marginPct: 85, revenueCents: 82500, marginCents: 70125 },
      { name: 'Croissant', category: 'food', monthlySales: 360, marginPct: 65, revenueCents: 153000, marginCents: 99450 },
      { name: 'Avocado Toast', category: 'food', monthlySales: 140, marginPct: 52, revenueCents: 125300, marginCents: 65156 },
      { name: 'Breakfast Sandwich', category: 'food', monthlySales: 180, marginPct: 58, revenueCents: 135000, marginCents: 78300 },
      { name: 'Blueberry Muffin', category: 'food', monthlySales: 270, marginPct: 68, revenueCents: 106650, marginCents: 72522 },
    ],
  }
}

function coffeeShopAnomalies(): AnomalyDef[] {
  return [
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'critical',
      title: 'Morning rush lasted 40 min longer Thursday',
      description: 'Queue past door 8:10am-9:50am, 14 walkouts detected by camera. Normal rush ends by 9:10am. Estimated lost revenue from walkouts: $105.',
      metric: 'queue_duration_min', expected: 60, actual: 100, deviationPct: 67,
      agentSource: 'queue-monitor',
    },
    {
      id: uuid(), type: 'revenue_drop', severity: 'warning',
      title: 'Cold brew sold out by 11am Wed and Thu',
      description: 'Batch exhausted 2 hours before typical demand tails off. Estimated $340 in lost sales across both days. Consider increasing cold brew batch by 40%.',
      metric: 'stockout_lost_revenue_cents', expected: 0, actual: 34000, deviationPct: 100,
      agentSource: 'inventory-tracker',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'warning',
      title: '41 morning regulars not visited in 18+ days',
      description: 'Loyalty data shows 41 customers who previously visited 4+/week have not returned in 18+ days. Potential monthly revenue at risk: $2,300.',
      metric: 'churning_regulars', expected: 5, actual: 41, deviationPct: 720,
      agentSource: 'customer-intelligence',
    },
    {
      id: uuid(), type: 'cost_spike', severity: 'warning',
      title: 'Oat milk usage up 40% without sales increase',
      description: 'Oat milk consumption spiked 40% week-over-week but oat milk drink sales remained flat. Possible over-pouring or waste. Weekly cost impact: ~$85.',
      metric: 'oat_milk_usage_oz', expected: 320, actual: 448, deviationPct: 40,
      agentSource: 'margin-optimizer',
    },
    {
      id: uuid(), type: 'void_spike', severity: 'warning',
      title: 'Void transactions 3x normal Tuesday evenings',
      description: 'Tuesday 4-8pm saw 18 void transactions vs. normal average of 6. Concentrate on Register 2. Review staff procedures and POS error patterns.',
      metric: 'void_count', expected: 6, actual: 18, deviationPct: 200,
      agentSource: 'anomaly-detector',
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

function restaurantMarginItems(): MarginItemDef[] {
  return [
    {
      name: 'Ribeye Steak', category: 'entrees', sellingPriceCents: 4200, monthlySales: 180,
      ingredients: [
        { name: 'Prime Beef Ribeye', batchCostCents: 9600, batchServings: 8, amountUsedOz: 14, wastePct: 6 },
        { name: 'Seasoning & Butter', batchCostCents: 800, batchServings: 40, amountUsedOz: 1, wastePct: 2 },
        { name: 'Side Vegetables', batchCostCents: 1200, batchServings: 10, amountUsedOz: 6, wastePct: 8 },
        { name: 'Plate & Service', batchCostCents: 0, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 18000,
    },
    {
      name: 'Grilled Salmon', category: 'entrees', sellingPriceCents: 2800, monthlySales: 210,
      ingredients: [
        { name: 'Salmon Fillet', batchCostCents: 5400, batchServings: 6, amountUsedOz: 8, wastePct: 5 },
        { name: 'Lemon Butter Sauce', batchCostCents: 600, batchServings: 20, amountUsedOz: 2, wastePct: 3 },
        { name: 'Side Vegetables', batchCostCents: 1200, batchServings: 10, amountUsedOz: 6, wastePct: 8 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Caesar Salad', category: 'starters', sellingPriceCents: 1400, monthlySales: 250,
      ingredients: [
        { name: 'Romaine Lettuce', batchCostCents: 350, batchServings: 8, amountUsedOz: 6, wastePct: 12 },
        { name: 'Caesar Dressing', batchCostCents: 900, batchServings: 20, amountUsedOz: 2, wastePct: 3 },
        { name: 'Croutons', batchCostCents: 400, batchServings: 25, amountUsedOz: 1, wastePct: 2 },
        { name: 'Parmesan', batchCostCents: 1200, batchServings: 30, amountUsedOz: 0.5, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Chicken Parmesan', category: 'entrees', sellingPriceCents: 2200, monthlySales: 200,
      ingredients: [
        { name: 'Chicken Breast', batchCostCents: 2400, batchServings: 8, amountUsedOz: 8, wastePct: 4 },
        { name: 'Marinara Sauce', batchCostCents: 800, batchServings: 16, amountUsedOz: 4, wastePct: 3 },
        { name: 'Mozzarella', batchCostCents: 1000, batchServings: 12, amountUsedOz: 3, wastePct: 3 },
        { name: 'Pasta', batchCostCents: 600, batchServings: 10, amountUsedOz: 6, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Craft Cocktail', category: 'drinks', sellingPriceCents: 1500, monthlySales: 280,
      ingredients: [
        { name: 'Premium Spirits', batchCostCents: 4500, batchServings: 25, amountUsedOz: 2, wastePct: 2 },
        { name: 'Mixers & Syrups', batchCostCents: 800, batchServings: 20, amountUsedOz: 3, wastePct: 5 },
        { name: 'Garnish', batchCostCents: 600, batchServings: 30, amountUsedOz: 0.5, wastePct: 15 },
        { name: 'Glassware (depreciation)', batchCostCents: 200, batchServings: 50, amountUsedOz: 0, wastePct: 3 },
      ],
      externalLeakageCents: 12000,
    },
    {
      name: 'House Wine', category: 'drinks', sellingPriceCents: 1100, monthlySales: 230,
      ingredients: [
        { name: 'Wine (by glass)', batchCostCents: 2400, batchServings: 5, amountUsedOz: 5, wastePct: 4 },
        { name: 'Glassware (depreciation)', batchCostCents: 200, batchServings: 50, amountUsedOz: 0, wastePct: 3 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Lobster Bisque', category: 'starters', sellingPriceCents: 1600, monthlySales: 140,
      ingredients: [
        { name: 'Lobster Base', batchCostCents: 3600, batchServings: 8, amountUsedOz: 6, wastePct: 10 },
        { name: 'Heavy Cream', batchCostCents: 700, batchServings: 12, amountUsedOz: 3, wastePct: 5 },
        { name: 'Mirepoix', batchCostCents: 400, batchServings: 16, amountUsedOz: 2, wastePct: 8 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Tiramisu', category: 'desserts', sellingPriceCents: 1200, monthlySales: 120,
      ingredients: [
        { name: 'Mascarpone', batchCostCents: 900, batchServings: 8, amountUsedOz: 3, wastePct: 4 },
        { name: 'Ladyfingers', batchCostCents: 500, batchServings: 12, amountUsedOz: 2, wastePct: 3 },
        { name: 'Espresso', batchCostCents: 300, batchServings: 15, amountUsedOz: 2, wastePct: 2 },
        { name: 'Cocoa Powder', batchCostCents: 400, batchServings: 40, amountUsedOz: 0.25, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Margherita Pizza', category: 'entrees', sellingPriceCents: 1800, monthlySales: 160,
      ingredients: [
        { name: 'Pizza Dough', batchCostCents: 800, batchServings: 10, amountUsedOz: 10, wastePct: 5 },
        { name: 'Fresh Mozzarella', batchCostCents: 1200, batchServings: 8, amountUsedOz: 5, wastePct: 3 },
        { name: 'San Marzano Tomato', batchCostCents: 600, batchServings: 10, amountUsedOz: 4, wastePct: 4 },
        { name: 'Fresh Basil', batchCostCents: 300, batchServings: 20, amountUsedOz: 0.25, wastePct: 15 },
      ],
      externalLeakageCents: 0,
    },
  ]
}

function restaurantMenuEngConfig(): MenuEngConfig {
  return {
    pageTitle: 'Menu Matrix',
    xAxisLabel: 'Popularity',
    yAxisLabel: 'Contribution Margin',
    quadrantLabels: { star: 'Stars', plowhorse: 'Plowhorses', puzzle: 'Puzzles', dog: 'Dogs' },
    items: [
      { name: 'Ribeye Steak', category: 'entrees', monthlySales: 180, marginPct: 62, revenueCents: 756000, marginCents: 468720 },
      { name: 'Grilled Salmon', category: 'entrees', monthlySales: 210, marginPct: 68, revenueCents: 588000, marginCents: 399840 },
      { name: 'Caesar Salad', category: 'starters', monthlySales: 250, marginPct: 78, revenueCents: 350000, marginCents: 273000 },
      { name: 'Chicken Parmesan', category: 'entrees', monthlySales: 200, marginPct: 66, revenueCents: 440000, marginCents: 290400 },
      { name: 'Craft Cocktail', category: 'drinks', monthlySales: 280, marginPct: 82, revenueCents: 420000, marginCents: 344400 },
      { name: 'House Wine', category: 'drinks', monthlySales: 230, marginPct: 72, revenueCents: 253000, marginCents: 182160 },
      { name: 'Lobster Bisque', category: 'starters', monthlySales: 140, marginPct: 58, revenueCents: 224000, marginCents: 129920 },
      { name: 'Tiramisu', category: 'desserts', monthlySales: 120, marginPct: 74, revenueCents: 144000, marginCents: 106560 },
      { name: 'Margherita Pizza', category: 'entrees', monthlySales: 160, marginPct: 70, revenueCents: 288000, marginCents: 201600 },
      { name: 'Sparkling Water', category: 'drinks', monthlySales: 180, marginPct: 88, revenueCents: 72000, marginCents: 63360 },
    ],
  }
}

function restaurantAnomalies(): AnomalyDef[] {
  return [
    {
      id: uuid(), type: 'revenue_drop', severity: 'critical',
      title: 'Revenue dropped 22% on Tuesday vs prior Tuesday',
      description: 'Conversion fell from 94% to 71% for seated guests. Walk-in traffic was normal but reservation no-shows were 3x average. Estimated revenue gap: $1,680.',
      metric: 'daily_revenue_cents', expected: 756000, actual: 589680, deviationPct: 22,
      agentSource: 'revenue-tracker',
    },
    {
      id: uuid(), type: 'revenue_drop', severity: 'warning',
      title: 'Table 12-16 avg ticket $18 below floor average',
      description: 'Server section covering tables 12-16 averaged $24 per cover vs. floor average of $42. Beverage attachment in this section was 18% vs. 52% floor-wide.',
      metric: 'section_avg_ticket_cents', expected: 4200, actual: 2400, deviationPct: 43,
      agentSource: 'staff-performance',
    },
    {
      id: uuid(), type: 'revenue_drop', severity: 'warning',
      title: 'Dessert attachment rate fell from 31% to 9% this week',
      description: 'Dessert orders dropped dramatically. Correlates with removal of tableside dessert tray on Monday. Estimated weekly revenue impact: $840.',
      metric: 'dessert_attachment_pct', expected: 31, actual: 9, deviationPct: 71,
      agentSource: 'product-intelligence',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'info',
      title: 'Bar revenue up 40% Saturday — nearby event detected',
      description: 'Saturday bar revenue was $2,800 vs. $2,000 typical. Correlates with a music festival 2 blocks away. Consider event-aware staffing for future dates.',
      metric: 'bar_revenue_cents', expected: 200000, actual: 280000, deviationPct: 40,
      agentSource: 'event-correlator',
    },
    {
      id: uuid(), type: 'void_spike', severity: 'warning',
      title: 'Void transactions 2x on Thursday evening',
      description: 'Thursday 6-10pm had 14 void transactions vs. normal average of 7. Most voids were on POS terminal 3. Training or system issue suspected.',
      metric: 'void_count', expected: 7, actual: 14, deviationPct: 100,
      agentSource: 'anomaly-detector',
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

function fastFoodMarginItems(): MarginItemDef[] {
  return [
    {
      name: 'Classic Burger', category: 'burgers', sellingPriceCents: 899, monthlySales: 850,
      ingredients: [
        { name: 'Beef Patty', batchCostCents: 3600, batchServings: 24, amountUsedOz: 4, wastePct: 3 },
        { name: 'Bun', batchCostCents: 600, batchServings: 24, amountUsedOz: 3, wastePct: 4 },
        { name: 'Lettuce & Tomato', batchCostCents: 400, batchServings: 30, amountUsedOz: 2, wastePct: 10 },
        { name: 'Wrapper', batchCostCents: 500, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Double Stack', category: 'burgers', sellingPriceCents: 1149, monthlySales: 520,
      ingredients: [
        { name: 'Beef Patty (x2)', batchCostCents: 3600, batchServings: 12, amountUsedOz: 8, wastePct: 3 },
        { name: 'Bun', batchCostCents: 600, batchServings: 24, amountUsedOz: 3, wastePct: 4 },
        { name: 'Cheese Slices', batchCostCents: 800, batchServings: 48, amountUsedOz: 1, wastePct: 2 },
        { name: 'Wrapper', batchCostCents: 500, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Chicken Tenders', category: 'sides', sellingPriceCents: 799, monthlySales: 480,
      ingredients: [
        { name: 'Chicken Strips', batchCostCents: 2800, batchServings: 20, amountUsedOz: 5, wastePct: 4 },
        { name: 'Breading Mix', batchCostCents: 500, batchServings: 40, amountUsedOz: 1, wastePct: 2 },
        { name: 'Frying Oil', batchCostCents: 1800, batchServings: 100, amountUsedOz: 2, wastePct: 8 },
        { name: 'Box', batchCostCents: 600, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Fries Large', category: 'sides', sellingPriceCents: 449, monthlySales: 780,
      ingredients: [
        { name: 'Frozen Potatoes', batchCostCents: 1200, batchServings: 40, amountUsedOz: 6, wastePct: 3 },
        { name: 'Frying Oil', batchCostCents: 1800, batchServings: 100, amountUsedOz: 2, wastePct: 8 },
        { name: 'Salt', batchCostCents: 100, batchServings: 200, amountUsedOz: 0.1, wastePct: 1 },
        { name: 'Container', batchCostCents: 400, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Soda Fountain', category: 'drinks', sellingPriceCents: 249, monthlySales: 900,
      ingredients: [
        { name: 'Syrup BIB', batchCostCents: 5500, batchServings: 400, amountUsedOz: 3, wastePct: 1 },
        { name: 'CO2 Tank', batchCostCents: 3000, batchServings: 600, amountUsedOz: 0, wastePct: 0 },
        { name: 'Cup + Lid + Straw', batchCostCents: 1200, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Combo Meal', category: 'combos', sellingPriceCents: 1399, monthlySales: 650,
      ingredients: [
        { name: 'Burger Components', batchCostCents: 3600, batchServings: 24, amountUsedOz: 4, wastePct: 3 },
        { name: 'Fries Components', batchCostCents: 1200, batchServings: 40, amountUsedOz: 6, wastePct: 3 },
        { name: 'Drink Components', batchCostCents: 5500, batchServings: 400, amountUsedOz: 3, wastePct: 1 },
        { name: 'Combo Bag', batchCostCents: 800, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Milkshake', category: 'drinks', sellingPriceCents: 599, monthlySales: 220,
      ingredients: [
        { name: 'Ice Cream', batchCostCents: 2400, batchServings: 16, amountUsedOz: 8, wastePct: 4 },
        { name: 'Whole Milk', batchCostCents: 450, batchServings: 20, amountUsedOz: 4, wastePct: 3 },
        { name: 'Cup + Lid', batchCostCents: 1400, batchServings: 100, amountUsedOz: 1, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Kids Meal', category: 'combos', sellingPriceCents: 699, monthlySales: 280,
      ingredients: [
        { name: 'Mini Burger', batchCostCents: 2400, batchServings: 24, amountUsedOz: 2.5, wastePct: 3 },
        { name: 'Small Fries', batchCostCents: 1200, batchServings: 60, amountUsedOz: 3, wastePct: 3 },
        { name: 'Toy', batchCostCents: 4800, batchServings: 100, amountUsedOz: 0, wastePct: 0 },
        { name: 'Bag', batchCostCents: 600, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Onion Rings', category: 'sides', sellingPriceCents: 549, monthlySales: 180,
      ingredients: [
        { name: 'Onion Rings (frozen)', batchCostCents: 1400, batchServings: 20, amountUsedOz: 5, wastePct: 4 },
        { name: 'Breading Mix', batchCostCents: 500, batchServings: 40, amountUsedOz: 1, wastePct: 2 },
        { name: 'Frying Oil', batchCostCents: 1800, batchServings: 100, amountUsedOz: 2, wastePct: 8 },
        { name: 'Container', batchCostCents: 400, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Apple Pie', category: 'desserts', sellingPriceCents: 349, monthlySales: 150,
      ingredients: [
        { name: 'Frozen Apple Pie', batchCostCents: 2400, batchServings: 48, amountUsedOz: 3, wastePct: 3 },
        { name: 'Box', batchCostCents: 400, batchServings: 100, amountUsedOz: 1, wastePct: 1 },
      ],
      externalLeakageCents: 0,
    },
  ]
}

function fastFoodMenuEngConfig(): MenuEngConfig {
  return {
    pageTitle: 'Menu Matrix',
    xAxisLabel: 'Popularity',
    yAxisLabel: 'Contribution Margin',
    quadrantLabels: { star: 'Stars', plowhorse: 'Plowhorses', puzzle: 'Puzzles', dog: 'Dogs' },
    items: [
      { name: 'Classic Burger', category: 'burgers', monthlySales: 850, marginPct: 68, revenueCents: 764150, marginCents: 519622 },
      { name: 'Double Stack', category: 'burgers', monthlySales: 520, marginPct: 64, revenueCents: 597480, marginCents: 382387 },
      { name: 'Chicken Tenders', category: 'sides', monthlySales: 480, marginPct: 66, revenueCents: 383520, marginCents: 253123 },
      { name: 'Fries Large', category: 'sides', monthlySales: 780, marginPct: 82, revenueCents: 350220, marginCents: 287180 },
      { name: 'Soda Fountain', category: 'drinks', monthlySales: 900, marginPct: 85, revenueCents: 224100, marginCents: 190485 },
      { name: 'Combo Meal', category: 'combos', monthlySales: 650, marginPct: 62, revenueCents: 909350, marginCents: 563797 },
      { name: 'Milkshake', category: 'drinks', monthlySales: 220, marginPct: 58, revenueCents: 131780, marginCents: 76432 },
      { name: 'Kids Meal', category: 'combos', monthlySales: 280, marginPct: 55, revenueCents: 195720, marginCents: 107646 },
      { name: 'Onion Rings', category: 'sides', monthlySales: 180, marginPct: 72, revenueCents: 98820, marginCents: 71150 },
      { name: 'Apple Pie', category: 'desserts', monthlySales: 150, marginPct: 78, revenueCents: 52350, marginCents: 40833 },
    ],
  }
}

function fastFoodAnomalies(): AnomalyDef[] {
  return [
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'critical',
      title: 'Drive-through speed spiked to 7.2 min Tuesday 12-1pm',
      description: 'Average drive-through service time hit 7.2 minutes during Tuesday lunch peak, well above 4.5-minute target. 11 vehicles abandoned the lane. Correlates with one fryer being down for maintenance.',
      metric: 'drive_through_time_min', expected: 4.5, actual: 7.2, deviationPct: 60,
      agentSource: 'queue-monitor',
    },
    {
      id: uuid(), type: 'revenue_drop', severity: 'warning',
      title: 'Combo attachment rate dropped to 44% — down from 61%',
      description: 'Combo meal upgrade rate fell 17 percentage points over the past week. POS upsell prompt was disabled after a software update on Monday. Re-enable to recover estimated $420/week.',
      metric: 'combo_attachment_pct', expected: 61, actual: 44, deviationPct: 28,
      agentSource: 'product-intelligence',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'info',
      title: 'Seating area occupancy at 0% from 2-4pm three days',
      description: 'In-store seating area completely empty during 2-4pm on Monday, Wednesday, and Thursday. All orders were drive-through or takeout. Consider converting seating to pickup staging.',
      metric: 'seating_occupancy_pct', expected: 15, actual: 0, deviationPct: 100,
      agentSource: 'heatmap-generator',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'info',
      title: 'Breakfast daypart up 28% since menu change',
      description: 'Breakfast revenue (6-10:30am) increased 28% week-over-week following the new breakfast burrito launch. 340 breakfast transactions this week vs. 265 prior week.',
      metric: 'breakfast_revenue_cents', expected: 291500, actual: 373120, deviationPct: 28,
      agentSource: 'revenue-tracker',
    },
    {
      id: uuid(), type: 'refund_surge', severity: 'warning',
      title: 'Register 3 refund rate 3x other registers',
      description: 'Register 3 processed 24 refunds this week vs. average of 8 on other registers. Review operator training or investigate potential process issues.',
      metric: 'refund_count', expected: 8, actual: 24, deviationPct: 200,
      agentSource: 'anomaly-detector',
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

function autoShopMarginItems(): MarginItemDef[] {
  return [
    {
      name: 'Oil Change', category: 'maintenance', sellingPriceCents: 4999, monthlySales: 420,
      ingredients: [
        { name: 'Motor Oil (5qt)', batchCostCents: 2800, batchServings: 1, amountUsedOz: 160, wastePct: 2 },
        { name: 'Oil Filter', batchCostCents: 450, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Labor (20 min)', batchCostCents: 1200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Oil Disposal Fee', batchCostCents: 150, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Brake Pad Replace', category: 'repair', sellingPriceCents: 24900, monthlySales: 110,
      ingredients: [
        { name: 'Brake Pads (set)', batchCostCents: 4500, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Rotors (pair)', batchCostCents: 6200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Labor (2 hr)', batchCostCents: 7200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Hardware & Clips', batchCostCents: 350, batchServings: 1, amountUsedOz: 0, wastePct: 2 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Tire Rotation', category: 'maintenance', sellingPriceCents: 3999, monthlySales: 280,
      ingredients: [
        { name: 'Labor (30 min)', batchCostCents: 1800, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Equipment Wear', batchCostCents: 200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Full Inspection', category: 'diagnostic', sellingPriceCents: 8999, monthlySales: 190,
      ingredients: [
        { name: 'Labor (45 min)', batchCostCents: 2700, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Inspection Report/Printout', batchCostCents: 50, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Engine Diagnostic', category: 'diagnostic', sellingPriceCents: 12900, monthlySales: 160,
      ingredients: [
        { name: 'Labor (1 hr)', batchCostCents: 3600, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Scanner Usage', batchCostCents: 400, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'AC Recharge', category: 'repair', sellingPriceCents: 14900, monthlySales: 90,
      ingredients: [
        { name: 'Refrigerant (R-134a)', batchCostCents: 3200, batchServings: 1, amountUsedOz: 24, wastePct: 5 },
        { name: 'Labor (1 hr)', batchCostCents: 3600, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'UV Dye', batchCostCents: 250, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Alignment', category: 'maintenance', sellingPriceCents: 9999, monthlySales: 120,
      ingredients: [
        { name: 'Labor (45 min)', batchCostCents: 2700, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Alignment Equipment Wear', batchCostCents: 500, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Battery Replace', category: 'repair', sellingPriceCents: 18900, monthlySales: 85,
      ingredients: [
        { name: 'Battery', batchCostCents: 9500, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Labor (30 min)', batchCostCents: 1800, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Core Disposal', batchCostCents: 300, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Transmission Flush', category: 'maintenance', sellingPriceCents: 17900, monthlySales: 60,
      ingredients: [
        { name: 'Transmission Fluid', batchCostCents: 4800, batchServings: 1, amountUsedOz: 128, wastePct: 3 },
        { name: 'Labor (1.5 hr)', batchCostCents: 5400, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Gasket', batchCostCents: 350, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Wiper Blades', category: 'parts', sellingPriceCents: 3499, monthlySales: 200,
      ingredients: [
        { name: 'Wiper Blade Set', batchCostCents: 1200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Labor (10 min)', batchCostCents: 600, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
  ]
}

function autoShopMenuEngConfig(): MenuEngConfig {
  return {
    pageTitle: 'Service Matrix',
    xAxisLabel: 'Job Frequency',
    yAxisLabel: 'Profit per Job',
    quadrantLabels: { star: 'Core Services', plowhorse: 'High Volume Low Margin', puzzle: 'High Value Low Volume', dog: 'Review' },
    items: [
      { name: 'Oil Change', category: 'maintenance', monthlySales: 420, marginPct: 54, revenueCents: 2099580, marginCents: 1133773 },
      { name: 'Brake Pad Replace', category: 'repair', monthlySales: 110, marginPct: 27, revenueCents: 2739000, marginCents: 739530 },
      { name: 'Tire Rotation', category: 'maintenance', monthlySales: 280, marginPct: 50, revenueCents: 1119720, marginCents: 559860 },
      { name: 'Full Inspection', category: 'diagnostic', monthlySales: 190, marginPct: 69, revenueCents: 1709810, marginCents: 1179769 },
      { name: 'Engine Diagnostic', category: 'diagnostic', monthlySales: 160, marginPct: 69, revenueCents: 2064000, marginCents: 1424160 },
      { name: 'AC Recharge', category: 'repair', monthlySales: 90, marginPct: 53, revenueCents: 1341000, marginCents: 710730 },
      { name: 'Alignment', category: 'maintenance', monthlySales: 120, marginPct: 68, revenueCents: 1199880, marginCents: 815918 },
      { name: 'Battery Replace', category: 'repair', monthlySales: 85, marginPct: 39, revenueCents: 1606500, marginCents: 626535 },
      { name: 'Transmission Flush', category: 'maintenance', monthlySales: 60, marginPct: 41, revenueCents: 1074000, marginCents: 440340 },
    ],
  }
}

function autoShopAnomalies(): AnomalyDef[] {
  return [
    {
      id: uuid(), type: 'revenue_drop', severity: 'critical',
      title: 'Bay utilization dropped to 54% Tue-Wed vs 85% target',
      description: 'Only 3 of 6 bays were active Tuesday and Wednesday. Two technicians called out sick with no backup coverage. Estimated lost capacity: 18 jobs worth $3,330.',
      metric: 'bay_utilization_pct', expected: 85, actual: 54, deviationPct: 36,
      agentSource: 'capacity-monitor',
    },
    {
      id: uuid(), type: 'revenue_drop', severity: 'warning',
      title: 'Avg repair order value fell $67 — advisor upsell dropped',
      description: 'Average repair order value dropped from $185 to $118. Service advisor upsell rate fell from 34% to 12%. Correlates with new advisor starting Monday without completing upsell training.',
      metric: 'avg_order_value_cents', expected: 18500, actual: 11800, deviationPct: 36,
      agentSource: 'staff-performance',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'warning',
      title: 'Customer wait time in lounge exceeded 90 min on 6 visits',
      description: 'Six customers waited over 90 minutes for oil changes and inspections, versus 45-minute target. Two left negative reviews. Root cause: inspection backlog creating bottleneck.',
      metric: 'customer_wait_min', expected: 45, actual: 90, deviationPct: 100,
      agentSource: 'queue-monitor',
    },
    {
      id: uuid(), type: 'cost_spike', severity: 'warning',
      title: 'Parts inventory discrepancy: 12 filters unaccounted for',
      description: 'Monthly inventory count shows 12 oil filters missing from stock. At $4.50 each, $54 in unaccounted inventory. Could indicate recording errors or shrinkage.',
      metric: 'missing_parts_count', expected: 0, actual: 12, deviationPct: 100,
      agentSource: 'inventory-tracker',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'info',
      title: 'Saturday morning bookings up 35% — overflow risk',
      description: 'Saturday 7-11am appointment slots are 35% above last month. Current capacity may overflow by 3 jobs. Consider extending Saturday hours or adding a flex technician.',
      metric: 'saturday_bookings', expected: 20, actual: 27, deviationPct: 35,
      agentSource: 'capacity-monitor',
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

function smokeShopMarginItems(): MarginItemDef[] {
  return [
    {
      name: 'Cigarette Carton', category: 'tobacco', sellingPriceCents: 6500, monthlySales: 340,
      ingredients: [
        { name: 'Wholesale Carton', batchCostCents: 4800, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Tax & Compliance', batchCostCents: 850, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Vape Pod Pack', category: 'vape', sellingPriceCents: 2400, monthlySales: 380,
      ingredients: [
        { name: 'Wholesale Pods', batchCostCents: 1200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Packaging', batchCostCents: 50, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Premium Cigar', category: 'tobacco', sellingPriceCents: 1800, monthlySales: 200,
      ingredients: [
        { name: 'Wholesale Cigar', batchCostCents: 900, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Humidor Maintenance', batchCostCents: 80, batchServings: 1, amountUsedOz: 0, wastePct: 3 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'E-Liquid 60ml', category: 'vape', sellingPriceCents: 2200, monthlySales: 250,
      ingredients: [
        { name: 'Wholesale E-Liquid', batchCostCents: 850, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Shelf Space Allocation', batchCostCents: 30, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Glass Pipe', category: 'glass', sellingPriceCents: 4500, monthlySales: 80,
      ingredients: [
        { name: 'Wholesale Glass', batchCostCents: 1500, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Display & Insurance', batchCostCents: 200, batchServings: 1, amountUsedOz: 0, wastePct: 4 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Rolling Papers', category: 'accessories', sellingPriceCents: 450, monthlySales: 420,
      ingredients: [
        { name: 'Wholesale Papers', batchCostCents: 120, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Display Rack', batchCostCents: 10, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Lighter Collection', category: 'accessories', sellingPriceCents: 800, monthlySales: 350,
      ingredients: [
        { name: 'Wholesale Lighters', batchCostCents: 250, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Display', batchCostCents: 15, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'CBD Gummies', category: 'cbd', sellingPriceCents: 3500, monthlySales: 110,
      ingredients: [
        { name: 'Wholesale CBD Gummies', batchCostCents: 1100, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Compliance & Labeling', batchCostCents: 150, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Hookah Tobacco', category: 'tobacco', sellingPriceCents: 2800, monthlySales: 70,
      ingredients: [
        { name: 'Wholesale Tobacco', batchCostCents: 1400, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Compliance & Tax', batchCostCents: 200, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
    {
      name: 'Grinder', category: 'accessories', sellingPriceCents: 2500, monthlySales: 95,
      ingredients: [
        { name: 'Wholesale Grinder', batchCostCents: 800, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
        { name: 'Display', batchCostCents: 20, batchServings: 1, amountUsedOz: 0, wastePct: 0 },
      ],
      externalLeakageCents: 0,
    },
  ]
}

function smokeShopMenuEngConfig(): MenuEngConfig {
  return {
    pageTitle: 'Product Matrix',
    xAxisLabel: 'Sales Velocity',
    yAxisLabel: 'Gross Margin %',
    quadrantLabels: { star: 'Top Performers', plowhorse: 'High Volume', puzzle: 'Premium', dog: 'Underperformers' },
    items: [
      { name: 'Cigarette Carton', category: 'tobacco', monthlySales: 340, marginPct: 13, revenueCents: 2210000, marginCents: 287300 },
      { name: 'Premium Cigar', category: 'tobacco', monthlySales: 200, marginPct: 46, revenueCents: 360000, marginCents: 165600 },
      { name: 'Rolling Papers', category: 'accessories', monthlySales: 420, marginPct: 71, revenueCents: 189000, marginCents: 134190 },
      { name: 'Glass Pipe', category: 'glass', monthlySales: 80, marginPct: 62, revenueCents: 360000, marginCents: 223200 },
      { name: 'Vape Pod Pack', category: 'vape', monthlySales: 380, marginPct: 48, revenueCents: 912000, marginCents: 437760 },
      { name: 'Lighter Collection', category: 'accessories', monthlySales: 350, marginPct: 67, revenueCents: 280000, marginCents: 187600 },
      { name: 'CBD Gummies', category: 'cbd', monthlySales: 110, marginPct: 64, revenueCents: 385000, marginCents: 246400 },
      { name: 'E-Liquid 60ml', category: 'vape', monthlySales: 250, marginPct: 60, revenueCents: 550000, marginCents: 330000 },
      { name: 'Hookah Tobacco', category: 'tobacco', monthlySales: 70, marginPct: 43, revenueCents: 196000, marginCents: 84280 },
    ],
  }
}

function smokeShopAnomalies(): AnomalyDef[] {
  return [
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'critical',
      title: '7 regular customers (4+ visits/week) not returned in 10+ days',
      description: 'Loyalty data shows 7 high-frequency customers have gone silent. Combined weekly spend was $840. Potential churn to competitor or online ordering. Consider targeted outreach.',
      metric: 'churning_regulars', expected: 1, actual: 7, deviationPct: 600,
      agentSource: 'customer-intelligence',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'warning',
      title: 'Accessory wall dwell time up 34% but conversion stayed at 3%',
      description: 'Camera heatmap shows 34% more browsing time at the accessory display, but purchase conversion remains stuck at 3%. Customers may be interested but facing friction — pricing, product placement, or lack of staff assistance.',
      metric: 'accessory_conversion_pct', expected: 8, actual: 3, deviationPct: 63,
      agentSource: 'heatmap-generator',
    },
    {
      id: uuid(), type: 'revenue_drop', severity: 'warning',
      title: 'Tuesday 4-7pm revenue 41% below prior Tuesday',
      description: 'Prime after-work revenue window saw $680 vs. $1,150 the prior week. Foot traffic was normal but conversion dropped from 72% to 44%. Possibly related to out-of-stock on popular vape pods.',
      metric: 'afternoon_revenue_cents', expected: 115000, actual: 68000, deviationPct: 41,
      agentSource: 'revenue-tracker',
    },
    {
      id: uuid(), type: 'cost_spike', severity: 'warning',
      title: 'CBD inventory approaching expiry date on 14 units',
      description: '14 CBD gummy packs expire within 30 days. At $35 each, $490 at risk. Consider running a BOGO promotion or bundling with other CBD products to clear inventory.',
      metric: 'expiring_units', expected: 2, actual: 14, deviationPct: 600,
      agentSource: 'inventory-tracker',
    },
    {
      id: uuid(), type: 'traffic_anomaly', severity: 'info',
      title: 'Weekend foot traffic up 22% — likely nearby event',
      description: 'Saturday and Sunday foot traffic was 22% above 4-week average. No promotions were running. Nearby street fair likely drove additional walk-in traffic. Plan staffing for similar future events.',
      metric: 'weekend_traffic', expected: 95, actual: 116, deviationPct: 22,
      agentSource: 'event-correlator',
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
  marginItemsFn: () => MarginItemDef[]
  menuEngConfigFn: () => MenuEngConfig
  anomaliesFn: () => AnomalyDef[]
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
    marginItems: params.marginItemsFn(),
    menuEngConfig: params.menuEngConfigFn(),
    anomalies: params.anomaliesFn(),
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
        marginItemsFn: coffeeShopMarginItems,
        menuEngConfigFn: coffeeShopMenuEngConfig,
        anomaliesFn: coffeeShopAnomalies,
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
        marginItemsFn: restaurantMarginItems,
        menuEngConfigFn: restaurantMenuEngConfig,
        anomaliesFn: restaurantAnomalies,
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
        marginItemsFn: fastFoodMarginItems,
        menuEngConfigFn: fastFoodMenuEngConfig,
        anomaliesFn: fastFoodAnomalies,
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
        marginItemsFn: autoShopMarginItems,
        menuEngConfigFn: autoShopMenuEngConfig,
        anomaliesFn: autoShopAnomalies,
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
        marginItemsFn: smokeShopMarginItems,
        menuEngConfigFn: smokeShopMenuEngConfig,
        anomaliesFn: smokeShopAnomalies,
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
