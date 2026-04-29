import type { Insight } from './api'

export interface AgentInfo {
  id: string
  name: string
  status: 'active' | 'idle' | 'running' | 'error'
  lastRun: string
  nextRun: string
  findings: number
  confidence: number
  category: 'analysis' | 'forecasting' | 'optimization' | 'strategy' | 'coordination'
  description: string
  latestFinding: string
}

export interface ReasoningChain {
  observation: string
  reasoning: string
  conclusion: string
  impact: string
  confidence: number
  priority: 'Critical' | 'High' | 'Medium' | 'Low'
  rawData: Record<string, number | string>
  agentId: string
  agentName: string
}

export interface TopAction {
  rank: number
  title: string
  description: string
  expectedImpact: string
  impactCents: number
  effort: 'Low' | 'Medium' | 'High'
  confidence: number
  priority: 'Critical' | 'High' | 'Medium' | 'Low'
  agentSource: string
  reasoning: ReasoningChain
}

export interface RFMSegment {
  name: string
  count: number
  percentage: number
  avgSpendCents: number
  avgFrequency: number
  retentionScore: number
  color: string
  description: string
}

export interface RFMCell {
  r: number
  f: number
  count: number
  label: string
  color: string
}

export interface StaffMember {
  id: string
  name: string
  role: string
  avgTicketCents: number
  transactionsPerShift: number
  upsellRate: number
  customerRating: number
  revenuePerHour: number
  trend: 'up' | 'down' | 'stable'
}

export interface PeakHourCell {
  day: number
  hour: number
  revenue: number
  transactions: number
  intensity: number
}

export interface IngredientCost {
  name: string
  batchCostCents: number
  batchServings: number
  amountUsedOz: number
  wastePct: number
}

export interface MarginItem {
  name: string
  revenueCents: number
  costCents: number
  marginCents: number
  marginPct: number
  leakageCents: number
  category: string
  sellingPriceCents: number
  monthlySales: number
  rawCostPerServingCents: number
  wasteAdjustedCostCents: number
  pourCostPct: number
  marginPerUnitCents: number
  wasteFactor: number
  ingredients: IngredientCost[]
}

export interface CustomerProfile {
  id: string
  name: string
  segment: string
  segmentColor: string
  avgOrderCents: number
  totalSpentCents: number
  visitsPerMonth: number
  lastVisit: string
  daysSinceVisit: number
  topItem: string
  retentionRisk: 'low' | 'medium' | 'high'
}

export interface ForecastPeriod {
  label: string
  days: number
  predictedCents: number
  lowerCents: number
  upperCents: number
  confidence: number
  growthPct: number
}

function hoursAgo(h: number): string {
  const d = new Date()
  d.setHours(d.getHours() - h)
  return d.toISOString()
}

function minutesAgo(m: number): string {
  const d = new Date()
  d.setMinutes(d.getMinutes() - m)
  return d.toISOString()
}

function hoursFromNow(h: number): string {
  const d = new Date()
  d.setHours(d.getHours() + h)
  return d.toISOString()
}

export function generateAgents(): AgentInfo[] {
  return [
    { id: 'transaction-analyst', name: 'Transaction Analyst', status: 'active', lastRun: minutesAgo(12), nextRun: hoursFromNow(1), findings: 8, confidence: 91, category: 'analysis', description: 'Deep dives into every transaction for anomalies and patterns', latestFinding: 'Detected 3x spike in void transactions on Tuesday evenings — possible training gap' },
    { id: 'revenue-forecaster', name: 'Revenue Forecaster', status: 'active', lastRun: minutesAgo(45), nextRun: hoursFromNow(6), findings: 3, confidence: 84, category: 'forecasting', description: 'Predicts 7, 30, and 90 day revenue with seasonal adjustments', latestFinding: '90-day forecast projects $184K revenue with 12% growth trajectory' },
    { id: 'product-intelligence', name: 'Product Intelligence', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 6, confidence: 88, category: 'analysis', description: 'Ranks SKUs by margin, velocity, and cannibalization', latestFinding: 'Cappuccino + Croissant bundle opportunity: 34% co-purchase rate, $2.40 avg uplift' },
    { id: 'customer-segmentor', name: 'Customer Segmentor', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 5, confidence: 86, category: 'analysis', description: 'RFM segmentation identifying VIPs, at-risk, and lapsed customers', latestFinding: '23 VIP customers drive 41% of revenue — 4 showing early churn signals' },
    { id: 'retention-strategist', name: 'Retention Strategist', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 4, confidence: 79, category: 'strategy', description: 'Recommends specific retention plays per customer segment', latestFinding: 'Winback offer for 12 lapsed customers: 15% discount projected to recover $840/mo' },
    { id: 'staff-performance-analyst', name: 'Staff Performance', status: 'active', lastRun: hoursAgo(3), nextRun: hoursFromNow(3), findings: 5, confidence: 82, category: 'analysis', description: 'Correlates staff schedules with revenue and upsell metrics', latestFinding: 'Sarah M. achieves 2.3x avg upsell rate during morning shifts — model for training' },
    { id: 'peak-hour-optimizer', name: 'Peak Hour Optimizer', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 3, confidence: 90, category: 'optimization', description: 'Maps transaction density and recommends staffing levels', latestFinding: '7-9AM generates 47% of daily revenue but is 1 staff member short' },
    { id: 'inventory-intelligence', name: 'Inventory Intelligence', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 4, confidence: 85, category: 'optimization', description: 'Predicts stockout risk and optimal reorder points', latestFinding: 'Espresso beans will stockout in 2 days at current velocity — reorder now' },
    { id: 'competitor-benchmarker', name: 'Competitor Benchmarker', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 3, confidence: 72, category: 'analysis', description: 'Compares metrics against industry benchmarks', latestFinding: 'Average ticket $10.20 is 16% above Coffee Shop industry median of $8.80' },
    { id: 'margin-optimizer', name: 'Margin Optimizer', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 5, confidence: 83, category: 'optimization', description: 'Identifies margin leakage and pricing opportunities', latestFinding: 'Matcha Latte margin at 62% vs 75% category avg — ingredient cost review needed' },
    { id: 'loyalty-architect', name: 'Loyalty Architect', status: 'idle', lastRun: hoursAgo(48), nextRun: hoursFromNow(48), findings: 2, confidence: 71, category: 'strategy', description: 'Monitors loyalty program ROI and reward optimization', latestFinding: 'Points redemption rate 23% — below 35% benchmark. Simplify reward tiers.' },
    { id: 'location-analyst', name: 'Location Analyst', status: 'idle', lastRun: hoursAgo(72), nextRun: hoursFromNow(96), findings: 1, confidence: 68, category: 'analysis', description: 'Compares multi-location performance metrics', latestFinding: 'Single location detected — agent will activate when additional locations are added' },
    { id: 'insight-narrator', name: 'Insight Narrator', status: 'active', lastRun: minutesAgo(30), nextRun: hoursFromNow(2), findings: 10, confidence: 87, category: 'coordination', description: 'Synthesizes all agent findings into plain English narratives', latestFinding: 'Generated executive brief: 3 critical actions, $3,200/mo combined impact potential' },
    { id: 'action-prioritizer', name: 'Action Prioritizer', status: 'active', lastRun: minutesAgo(25), nextRun: hoursFromNow(2), findings: 3, confidence: 85, category: 'coordination', description: 'Ranks all recommendations by ROI and effort', latestFinding: 'Top action: Matcha Latte price increase — $840/mo impact, 15 minutes effort' },
    { id: 'feature-engineer', name: 'Feature Engineer', status: 'idle', lastRun: hoursAgo(72), nextRun: hoursFromNow(96), findings: 2, confidence: 74, category: 'strategy', description: 'Identifies highest-value features from agent findings', latestFinding: 'Priority feature: Automated reorder alerts via SMS when stock hits reorder point' },
  ]
}

export function generateTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: 'Increase Matcha Latte price from $6.25 to $7.00',
      description: 'Demand elasticity analysis shows highly inelastic demand (elasticity: -0.3). Current price is $1.25 below competitor average. This single change captures 36% of total pricing opportunity.',
      expectedImpact: '+$840/month revenue, +$640/month margin',
      impactCents: 84000,
      effort: 'Low',
      confidence: 82,
      priority: 'Critical',
      agentSource: 'margin-optimizer',
      reasoning: {
        observation: 'Matcha Latte priced at $6.25, competitor avg $7.50, demand elasticity -0.3',
        reasoning: 'If demand elasticity is -0.3, a 12% price increase causes only 3.6% volume decline. Net revenue increases by ~$840/mo because price lift far exceeds volume loss.',
        conclusion: 'Raise Matcha Latte to $7.00. Still $0.50 below competitor average, maintaining value perception.',
        impact: '+$840/month revenue, +$640/month margin after accounting for 3.6% volume decline',
        confidence: 82,
        priority: 'Critical',
        rawData: { current_price: '$6.25', competitor_avg: '$7.50', elasticity: -0.3, monthly_units: 420, projected_revenue_lift: '$840' },
        agentId: 'margin-optimizer',
        agentName: 'Margin Optimizer',
      },
    },
    {
      rank: 2,
      title: 'Add 1 staff member during 7-9AM peak window',
      description: 'Morning peak concentrates 47% of daily revenue into 2 hours but is understaffed by 1 position. Each lost sale costs $10.20 avg ticket. MIT research shows understaffing costs 8-15% of peak revenue.',
      expectedImpact: '+$520/month from reduced wait-time walkouts',
      impactCents: 52000,
      effort: 'Medium',
      confidence: 88,
      priority: 'Critical',
      agentSource: 'peak-hour-optimizer',
      reasoning: {
        observation: '47% of revenue in 7-9AM, avg queue time 4.2 min, estimated 6 walkouts/day',
        reasoning: 'If 6 customers walk out daily at $10.20 avg ticket, that is $61.20/day lost. Adding 1 staff member costs ~$18/hr x 2hr = $36/day. Net gain: $25.20/day = $756/mo.',
        conclusion: 'Add 1 staff member for 7-9AM shift. Conservative estimate $520/mo after accounting for variable walkout rates.',
        impact: '+$520/month net revenue after labor cost',
        confidence: 88,
        priority: 'Critical',
        rawData: { peak_revenue_share: '47%', avg_queue_time: '4.2 min', estimated_walkouts: 6, avg_ticket: '$10.20', labor_cost_per_hour: '$18' },
        agentId: 'peak-hour-optimizer',
        agentName: 'Peak Hour Optimizer',
      },
    },
    {
      rank: 3,
      title: 'Launch Cappuccino + Croissant bundle at $8.50',
      description: '34% of Cappuccino buyers also buy a Croissant (separately: $5.25 + $4.25 = $9.50). A $8.50 bundle gives customers $1.00 savings while increasing attachment rate from 34% to projected 52%.',
      expectedImpact: '+$380/month from increased attachment rate',
      impactCents: 38000,
      effort: 'Low',
      confidence: 78,
      priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: {
        observation: 'Cappuccino sold 180x/week, 34% co-purchase with Croissant, separate total $9.50',
        reasoning: 'If bundle at $8.50 increases attachment from 34% to 52%, that is 32 additional Croissant sales/week. At $4.25 cost offset by $1.00 discount: net $3.25 x 32 = $104/week = $450/mo. Conservative: $380/mo.',
        conclusion: 'Create "Morning Combo" bundle at $8.50. Display prominently on menu board and POS screen.',
        impact: '+$380/month additional revenue, improved customer satisfaction from perceived value',
        confidence: 78,
        priority: 'High',
        rawData: { cappuccino_weekly_sales: 180, co_purchase_rate: '34%', projected_rate: '52%', bundle_price: '$8.50', individual_total: '$9.50' },
        agentId: 'product-intelligence',
        agentName: 'Product Intelligence',
      },
    },
  ]
}

export function generateRFMSegments(): RFMSegment[] {
  return [
    { name: 'Champions', count: 23, percentage: 8, avgSpendCents: 284000, avgFrequency: 18, retentionScore: 96, color: '#17C5B0', description: 'Best customers. High spend, frequent visits, recent activity.' },
    { name: 'Loyal', count: 45, percentage: 15, avgSpendCents: 178000, avgFrequency: 12, retentionScore: 88, color: '#1A8FD6', description: 'Regular customers with consistent spending patterns.' },
    { name: 'Potential Loyalists', count: 38, percentage: 13, avgSpendCents: 95000, avgFrequency: 6, retentionScore: 74, color: '#7C5CFF', description: 'Recent customers with moderate frequency. High conversion potential.' },
    { name: 'Recent Customers', count: 52, percentage: 18, avgSpendCents: 42000, avgFrequency: 2, retentionScore: 62, color: '#4FE3C1', description: 'New customers. Need nurturing to build habit.' },
    { name: 'Promising', count: 34, percentage: 12, avgSpendCents: 68000, avgFrequency: 4, retentionScore: 58, color: '#60A5FA', description: 'Moderate recency and frequency. Respond well to promotions.' },
    { name: 'Needs Attention', count: 28, percentage: 10, avgSpendCents: 124000, avgFrequency: 3, retentionScore: 42, color: '#FBBF24', description: 'Previously good customers showing declining engagement.' },
    { name: 'At Risk', count: 22, percentage: 8, avgSpendCents: 156000, avgFrequency: 1, retentionScore: 28, color: '#F97316', description: 'High-value customers who stopped visiting. Urgent winback needed.' },
    { name: 'Hibernating', count: 32, percentage: 11, avgSpendCents: 52000, avgFrequency: 1, retentionScore: 15, color: '#EF4444', description: 'Long inactive. Low probability of return without intervention.' },
    { name: 'Lost', count: 16, percentage: 5, avgSpendCents: 38000, avgFrequency: 0, retentionScore: 5, color: '#6B7280', description: 'No activity in 90+ days. Consider removing from active targeting.' },
  ]
}

export function generateRFMMatrix(): RFMCell[] {
  const labels: Record<string, string> = {
    '5,5': 'Champions', '5,4': 'Champions', '4,5': 'Loyal',
    '4,4': 'Loyal', '3,5': 'Loyal', '5,3': 'Potential',
    '4,3': 'Potential', '3,4': 'Potential', '5,2': 'Recent',
    '5,1': 'Recent', '4,2': 'Promising', '3,3': 'Promising',
    '4,1': 'Promising', '3,2': 'Needs Attn', '2,5': 'Needs Attn',
    '2,4': 'Needs Attn', '3,1': 'At Risk', '2,3': 'At Risk',
    '2,2': 'At Risk', '1,5': 'At Risk', '2,1': 'Hibernating',
    '1,4': 'Hibernating', '1,3': 'Hibernating', '1,2': 'Lost',
    '1,1': 'Lost',
  }
  const colors: Record<string, string> = {
    Champions: '#17C5B0', Loyal: '#1A8FD6', Potential: '#7C5CFF',
    Recent: '#4FE3C1', Promising: '#60A5FA', 'Needs Attn': '#FBBF24',
    'At Risk': '#F97316', Hibernating: '#EF4444', Lost: '#6B7280',
  }
  const cells: RFMCell[] = []
  let seed = 42
  for (let r = 5; r >= 1; r--) {
    for (let f = 1; f <= 5; f++) {
      const key = `${r},${f}`
      const label = labels[key] || 'Other'
      seed = (seed * 16807) % 2147483647
      const count = Math.floor(((seed - 1) / 2147483646) * 40) + 2
      cells.push({ r, f, count, label, color: colors[label] || '#6B7280' })
    }
  }
  return cells
}

export function generateStaffPerformance(): StaffMember[] {
  return [
    { id: '1', name: 'Sarah M.', role: 'Barista Lead', avgTicketCents: 1280, transactionsPerShift: 48, upsellRate: 34, customerRating: 4.9, revenuePerHour: 6800, trend: 'up' },
    { id: '2', name: 'James K.', role: 'Barista', avgTicketCents: 1150, transactionsPerShift: 42, upsellRate: 28, customerRating: 4.7, revenuePerHour: 5600, trend: 'up' },
    { id: '3', name: 'Maria L.', role: 'Barista', avgTicketCents: 1080, transactionsPerShift: 45, upsellRate: 22, customerRating: 4.8, revenuePerHour: 5400, trend: 'stable' },
    { id: '4', name: 'Alex T.', role: 'Barista', avgTicketCents: 980, transactionsPerShift: 38, upsellRate: 18, customerRating: 4.5, revenuePerHour: 4200, trend: 'down' },
    { id: '5', name: 'Priya S.', role: 'Cashier', avgTicketCents: 920, transactionsPerShift: 52, upsellRate: 12, customerRating: 4.6, revenuePerHour: 4800, trend: 'stable' },
    { id: '6', name: 'Tom B.', role: 'Barista (New)', avgTicketCents: 860, transactionsPerShift: 32, upsellRate: 8, customerRating: 4.3, revenuePerHour: 3200, trend: 'up' },
  ]
}

export function generatePeakHourHeatmap(): PeakHourCell[] {
  const basePattern = [
    [0,0,0,0,0,3,12,42,78,65,48,58,72,62,45,35,28,22,15,8,4,0,0,0],
    [0,0,0,0,0,5,15,45,85,70,55,65,80,70,50,40,35,30,20,10,5,0,0,0],
    [0,0,0,0,0,5,18,48,88,72,58,68,82,72,52,42,38,32,22,12,5,0,0,0],
    [0,0,0,0,0,4,14,44,82,68,52,62,78,68,48,38,32,28,18,10,4,0,0,0],
    [0,0,0,0,0,6,16,46,90,75,60,70,85,75,55,45,40,35,25,14,6,0,0,0],
    [0,0,0,0,0,8,20,55,95,82,68,78,92,80,62,48,42,36,28,16,8,0,0,0],
    [0,0,0,0,0,6,18,50,88,78,62,72,88,76,58,44,38,30,22,12,5,0,0,0],
  ]
  const cells: PeakHourCell[] = []
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const base = basePattern[day][hour]
      const revenue = base * 280
      const transactions = Math.max(1, Math.floor(base * 2.8))
      cells.push({ day, hour, revenue, transactions, intensity: base })
    }
  }
  return cells
}

function calcMarginItem(
  name: string,
  category: string,
  sellingPriceCents: number,
  monthlySales: number,
  ingredients: IngredientCost[],
  externalLeakageCents: number,
): MarginItem {
  // Raw Cost Per Serving = sum of (batch cost / batch servings) for each ingredient
  const rawCostPerServingCents = ingredients.reduce((sum, ing) => {
    return sum + Math.round(ing.batchCostCents / ing.batchServings)
  }, 0)

  // Waste Factor = weighted average of ingredient waste percentages
  const totalIngredientCost = ingredients.reduce((s, ing) => s + ing.batchCostCents, 0)
  const wasteFactor = totalIngredientCost > 0
    ? ingredients.reduce((s, ing) => s + (ing.wastePct / 100) * ing.batchCostCents, 0) / totalIngredientCost
    : 0

  // Waste-Adjusted Cost = Raw Cost / (1 - Waste Factor)
  const wasteAdjustedCostCents = wasteFactor < 1
    ? Math.round(rawCostPerServingCents / (1 - wasteFactor))
    : rawCostPerServingCents

  // Pour Cost % = COGS / Revenue
  const pourCostPct = sellingPriceCents > 0
    ? Math.round((wasteAdjustedCostCents / sellingPriceCents) * 100)
    : 0

  // Margin Per Unit = Selling Price - Waste-Adjusted Cost
  const marginPerUnitCents = sellingPriceCents - wasteAdjustedCostCents

  // Monthly aggregates
  const revenueCents = sellingPriceCents * monthlySales
  const costCents = wasteAdjustedCostCents * monthlySales
  const marginCents = marginPerUnitCents * monthlySales
  const marginPct = revenueCents > 0 ? Math.round((marginCents / revenueCents) * 100) : 0

  // Leakage = waste cost delta + external leakage (discounts, comps, spoilage)
  const wasteCostDelta = (wasteAdjustedCostCents - rawCostPerServingCents) * monthlySales
  const leakageCents = wasteCostDelta + externalLeakageCents

  return {
    name, category, sellingPriceCents, monthlySales,
    revenueCents, costCents, marginCents, marginPct, leakageCents,
    rawCostPerServingCents, wasteAdjustedCostCents, pourCostPct,
    marginPerUnitCents, wasteFactor, ingredients,
  }
}

export function generateMarginWaterfall(): MarginItem[] {
  return [
    calcMarginItem('Espresso', 'drinks', 450, 330, [
      { name: 'Coffee beans', batchCostCents: 1800, batchServings: 60, amountUsedOz: 0.5, wastePct: 3 },
      { name: 'Water/filtration', batchCostCents: 200, batchServings: 100, amountUsedOz: 2, wastePct: 0 },
      { name: 'Cup/lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], 0),
    calcMarginItem('Cappuccino', 'drinks', 525, 450, [
      { name: 'Coffee beans', batchCostCents: 1800, batchServings: 60, amountUsedOz: 0.5, wastePct: 3 },
      { name: 'Whole milk', batchCostCents: 450, batchServings: 16, amountUsedOz: 6, wastePct: 8 },
      { name: 'Cup/lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], 0),
    calcMarginItem('Iced Latte', 'drinks', 575, 340, [
      { name: 'Coffee beans', batchCostCents: 1800, batchServings: 60, amountUsedOz: 0.5, wastePct: 3 },
      { name: 'Whole milk', batchCostCents: 450, batchServings: 16, amountUsedOz: 8, wastePct: 8 },
      { name: 'Ice', batchCostCents: 800, batchServings: 100, amountUsedOz: 8, wastePct: 5 },
      { name: 'Cup/lid/straw', batchCostCents: 2000, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], 0),
    calcMarginItem('Cold Brew', 'drinks', 550, 300, [
      { name: 'Coffee beans (coarse)', batchCostCents: 2200, batchServings: 40, amountUsedOz: 1.0, wastePct: 5 },
      { name: 'Filtration/water', batchCostCents: 200, batchServings: 100, amountUsedOz: 12, wastePct: 0 },
      { name: 'Cup/lid/straw', batchCostCents: 2000, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], 0),
    calcMarginItem('Matcha Latte', 'drinks', 625, 190, [
      { name: 'Matcha powder', batchCostCents: 3200, batchServings: 30, amountUsedOz: 0.14, wastePct: 6 },
      { name: 'Oat milk', batchCostCents: 650, batchServings: 12, amountUsedOz: 8, wastePct: 12 },
      { name: 'Cup/lid', batchCostCents: 1500, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], 8400),
    calcMarginItem('Croissant', 'food', 425, 360, [
      { name: 'Frozen croissants (case)', batchCostCents: 4800, batchServings: 48, amountUsedOz: 3, wastePct: 5 },
      { name: 'Butter glaze', batchCostCents: 600, batchServings: 48, amountUsedOz: 0.25, wastePct: 3 },
      { name: 'Bag/tissue', batchCostCents: 800, batchServings: 100, amountUsedOz: 0, wastePct: 0 },
    ], 6800),
    calcMarginItem('Avocado Toast', 'food', 895, 140, [
      { name: 'Sourdough loaf', batchCostCents: 550, batchServings: 12, amountUsedOz: 2.5, wastePct: 8 },
      { name: 'Avocado', batchCostCents: 200, batchServings: 2, amountUsedOz: 4, wastePct: 15 },
      { name: 'Toppings (egg, seasoning)', batchCostCents: 1200, batchServings: 20, amountUsedOz: 2, wastePct: 5 },
      { name: 'Plate/napkin', batchCostCents: 1000, batchServings: 100, amountUsedOz: 0, wastePct: 0 },
    ], 9200),
    calcMarginItem('Breakfast Sandwich', 'food', 750, 180, [
      { name: 'English muffin (case)', batchCostCents: 1200, batchServings: 24, amountUsedOz: 2, wastePct: 4 },
      { name: 'Egg', batchCostCents: 500, batchServings: 12, amountUsedOz: 2, wastePct: 6 },
      { name: 'Cheese/bacon', batchCostCents: 2400, batchServings: 20, amountUsedOz: 2, wastePct: 8 },
      { name: 'Wrapper', batchCostCents: 600, batchServings: 100, amountUsedOz: 0, wastePct: 0 },
    ], 4200),
    calcMarginItem('Blueberry Muffin', 'food', 395, 270, [
      { name: 'Muffin batter (batch)', batchCostCents: 1800, batchServings: 24, amountUsedOz: 4, wastePct: 4 },
      { name: 'Blueberries', batchCostCents: 600, batchServings: 24, amountUsedOz: 0.75, wastePct: 6 },
      { name: 'Bag/tissue', batchCostCents: 800, batchServings: 100, amountUsedOz: 0, wastePct: 0 },
    ], 3100),
    calcMarginItem('Drip Coffee', 'drinks', 275, 300, [
      { name: 'Coffee beans', batchCostCents: 1800, batchServings: 80, amountUsedOz: 0.35, wastePct: 2 },
      { name: 'Filter/water', batchCostCents: 300, batchServings: 100, amountUsedOz: 10, wastePct: 0 },
      { name: 'Cup/lid', batchCostCents: 1200, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], 0),
  ]
}

export function generateCustomerRankings(): CustomerProfile[] {
  const daysAgo = (d: number) => {
    const dt = new Date()
    dt.setDate(dt.getDate() - d)
    return dt.toISOString()
  }
  return [
    { id: 'c1', name: 'Rachel M.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1580, totalSpentCents: 284400, visitsPerMonth: 18, lastVisit: daysAgo(1), daysSinceVisit: 1, topItem: 'Iced Latte + Avocado Toast', retentionRisk: 'low' },
    { id: 'c2', name: 'David K.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1420, totalSpentCents: 255600, visitsPerMonth: 16, lastVisit: daysAgo(1), daysSinceVisit: 1, topItem: 'Cold Brew + Croissant', retentionRisk: 'low' },
    { id: 'c3', name: 'Sarah T.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1250, totalSpentCents: 150000, visitsPerMonth: 12, lastVisit: daysAgo(2), daysSinceVisit: 2, topItem: 'Cappuccino + Blueberry Muffin', retentionRisk: 'low' },
    { id: 'c4', name: 'Michael B.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1680, totalSpentCents: 302400, visitsPerMonth: 20, lastVisit: daysAgo(0), daysSinceVisit: 0, topItem: 'Matcha Latte + Breakfast Sandwich', retentionRisk: 'low' },
    { id: 'c5', name: 'Lisa W.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1180, totalSpentCents: 141600, visitsPerMonth: 10, lastVisit: daysAgo(3), daysSinceVisit: 3, topItem: 'Espresso + Croissant', retentionRisk: 'low' },
    { id: 'c6', name: 'James P.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 980, totalSpentCents: 117600, visitsPerMonth: 8, lastVisit: daysAgo(4), daysSinceVisit: 4, topItem: 'Drip Coffee x2', retentionRisk: 'low' },
    { id: 'c7', name: 'Amanda R.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 1340, totalSpentCents: 80400, visitsPerMonth: 6, lastVisit: daysAgo(5), daysSinceVisit: 5, topItem: 'Iced Latte + Avocado Toast', retentionRisk: 'low' },
    { id: 'c8', name: 'Chris H.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 890, totalSpentCents: 53400, visitsPerMonth: 5, lastVisit: daysAgo(6), daysSinceVisit: 6, topItem: 'Cappuccino', retentionRisk: 'medium' },
    { id: 'c9', name: 'Nicole F.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 1560, totalSpentCents: 46800, visitsPerMonth: 3, lastVisit: daysAgo(14), daysSinceVisit: 14, topItem: 'Matcha Latte + Avocado Toast', retentionRisk: 'medium' },
    { id: 'c10', name: 'Robert G.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 1450, totalSpentCents: 174000, visitsPerMonth: 1, lastVisit: daysAgo(28), daysSinceVisit: 28, topItem: 'Cold Brew + Breakfast Sandwich', retentionRisk: 'high' },
    { id: 'c11', name: 'Emily S.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 720, totalSpentCents: 28800, visitsPerMonth: 4, lastVisit: daysAgo(7), daysSinceVisit: 7, topItem: 'Drip Coffee + Muffin', retentionRisk: 'low' },
    { id: 'c12', name: 'Tom L.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 1320, totalSpentCents: 158400, visitsPerMonth: 1, lastVisit: daysAgo(35), daysSinceVisit: 35, topItem: 'Iced Latte + Croissant', retentionRisk: 'high' },
    { id: 'c13', name: 'Jennifer C.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 650, totalSpentCents: 13000, visitsPerMonth: 2, lastVisit: daysAgo(3), daysSinceVisit: 3, topItem: 'Cappuccino', retentionRisk: 'medium' },
    { id: 'c14', name: 'Brian N.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 980, totalSpentCents: 58800, visitsPerMonth: 0, lastVisit: daysAgo(62), daysSinceVisit: 62, topItem: 'Espresso + Croissant', retentionRisk: 'high' },
    { id: 'c15', name: 'Karen A.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 480, totalSpentCents: 9600, visitsPerMonth: 2, lastVisit: daysAgo(5), daysSinceVisit: 5, topItem: 'Drip Coffee', retentionRisk: 'medium' },
  ]
}

export function generateForecastPeriods(): ForecastPeriod[] {
  return [
    { label: '7-Day', days: 7, predictedCents: 1350000, lowerCents: 1150000, upperCents: 1550000, confidence: 89, growthPct: 4.2 },
    { label: '30-Day', days: 30, predictedCents: 5480000, lowerCents: 4850000, upperCents: 6110000, confidence: 82, growthPct: 8.3 },
    { label: '90-Day', days: 90, predictedCents: 18400000, lowerCents: 15800000, upperCents: 21000000, confidence: 71, growthPct: 12.1 },
  ]
}

export function generateInsightsWithReasoning(): (Insight & { reasoning: ReasoningChain })[] {
  return generateTopActions().map((action, i) => ({
    id: `agent-insight-${i}`,
    type: action.agentSource,
    title: action.title,
    summary: action.description,
    details: { reasoning: action.reasoning },
    impact_cents: action.impactCents,
    confidence: action.confidence / 100,
    action_status: 'pending' as const,
    valid_until: null,
    created_at: hoursAgo(i + 1),
    reasoning: action.reasoning,
  }))
}
