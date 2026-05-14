import type { Insight } from './api'
import { getActiveBusinessType, getCurrencyMultiplier } from './demo-context'
import { getBusinessProfile, getProducts, getStaff } from './business-config'

function cx(cents: number): number {
  return Math.round(cents * getCurrencyMultiplier())
}

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
  ltvCents?: number
  churnRiskPct?: number
  pAlive?: number
}

export interface ForecastPeriod {
  label: string
  days: number
  predictedCents: number
  lowerCents: number
  upperCents: number
  confidence: number
  growthPct: number
  errorRate?: number
  scenarioOptimisticCents?: number
  scenarioExpectedCents?: number
  scenarioPessimisticCents?: number
  modelMethod?: string
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

function bizSub(text: string): string {
  const p = getProducts(getActiveBusinessType())
  const bp = getBusinessProfile(getActiveBusinessType())
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
    ['Sunrise Coffee Co.', bp.businessName],
    ['Coffee Shop / Café', bp.industryLabel],
    ['Coffee Shop', (() => {
      const labels: Record<string, string> = { coffee_shop: 'Coffee Shop', restaurant: 'Restaurant', fast_food: 'Fast Food', auto_shop: 'Auto Shop', smoke_shop: 'Smoke Shop' }
      return labels[getActiveBusinessType()] || 'Business'
    })()],
    ['coffee shop', (() => {
      const labels: Record<string, string> = { coffee_shop: 'coffee shop', restaurant: 'restaurant', fast_food: 'fast food', auto_shop: 'auto shop', smoke_shop: 'smoke shop' }
      return labels[getActiveBusinessType()] || 'business'
    })()],
  ]
  let result = text
  for (const [from, to] of replacements) {
    result = result.split(from).join(to)
  }
  return result
}

export function generateAgents(): AgentInfo[] {
  return [
    { id: 'transaction-analyst', name: 'Transaction Analyst', status: 'active', lastRun: minutesAgo(12), nextRun: hoursFromNow(1), findings: 8, confidence: 91, category: 'analysis', description: 'Deep dives into every transaction for anomalies and patterns', latestFinding: bizSub('Detected 3x spike in void transactions on Tuesday evenings — possible training gap') },
    { id: 'revenue-forecaster', name: 'Revenue Forecaster', status: 'active', lastRun: minutesAgo(45), nextRun: hoursFromNow(6), findings: 3, confidence: 84, category: 'forecasting', description: 'Predicts 7, 30, and 90 day revenue with seasonal adjustments', latestFinding: bizSub('90-day forecast projects $184K revenue with 12% growth trajectory') },
    { id: 'product-intelligence', name: 'Product Intelligence', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 6, confidence: 88, category: 'analysis', description: 'Ranks SKUs by margin, velocity, and cannibalization', latestFinding: bizSub('Cappuccino + Croissant bundle opportunity: 34% co-purchase rate, $2.40 avg uplift') },
    { id: 'customer-segmentor', name: 'Customer Segmentor', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 5, confidence: 86, category: 'analysis', description: 'RFM segmentation identifying VIPs, at-risk, and lapsed customers', latestFinding: bizSub('23 VIP customers drive 41% of revenue — 4 showing early churn signals') },
    { id: 'retention-strategist', name: 'Retention Strategist', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 4, confidence: 79, category: 'strategy', description: 'Recommends specific retention plays per customer segment', latestFinding: bizSub('Winback offer for 12 lapsed customers: 15% discount projected to recover $840/mo') },
    { id: 'staff-performance-analyst', name: 'Staff Performance', status: 'active', lastRun: hoursAgo(3), nextRun: hoursFromNow(3), findings: 5, confidence: 82, category: 'analysis', description: 'Correlates staff schedules with revenue and upsell metrics', latestFinding: bizSub('Sarah M. achieves 2.3x avg upsell rate during morning shifts — model for training') },
    { id: 'peak-hour-optimizer', name: 'Peak Hour Optimizer', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 3, confidence: 90, category: 'optimization', description: 'Maps transaction density and recommends staffing levels', latestFinding: bizSub('7-9AM generates 47% of daily revenue but is 1 staff member short') },
    { id: 'inventory-intelligence', name: 'Inventory Intelligence', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 4, confidence: 85, category: 'optimization', description: 'Predicts stockout risk and optimal reorder points', latestFinding: bizSub('Espresso beans will stockout in 2 days at current velocity — reorder now') },
    { id: 'competitor-benchmarker', name: 'Competitor Benchmarker', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 3, confidence: 72, category: 'analysis', description: 'Compares metrics against industry benchmarks', latestFinding: bizSub('Average ticket $10.20 is 16% above Coffee Shop industry median of $8.80') },
    { id: 'margin-optimizer', name: 'Margin Optimizer', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 5, confidence: 83, category: 'optimization', description: 'Identifies margin leakage and pricing opportunities', latestFinding: bizSub('Matcha Latte margin at 62% vs 75% category avg — ingredient cost review needed') },
    { id: 'loyalty-architect', name: 'Loyalty Architect', status: 'idle', lastRun: hoursAgo(48), nextRun: hoursFromNow(48), findings: 2, confidence: 71, category: 'strategy', description: 'Monitors loyalty program ROI and reward optimization', latestFinding: bizSub('Points redemption rate 23% — below 35% benchmark. Simplify reward tiers.') },
    { id: 'location-analyst', name: 'Location Analyst', status: 'idle', lastRun: hoursAgo(72), nextRun: hoursFromNow(96), findings: 1, confidence: 68, category: 'analysis', description: 'Compares multi-location performance metrics', latestFinding: bizSub('Single location detected — agent will activate when additional locations are added') },
    { id: 'insight-narrator', name: 'Insight Narrator', status: 'active', lastRun: minutesAgo(30), nextRun: hoursFromNow(2), findings: 10, confidence: 87, category: 'coordination', description: 'Synthesizes all agent findings into plain English narratives', latestFinding: bizSub('Generated executive brief: 3 critical actions, $3,200/mo combined impact potential') },
    { id: 'action-prioritizer', name: 'Action Prioritizer', status: 'active', lastRun: minutesAgo(25), nextRun: hoursFromNow(2), findings: 3, confidence: 85, category: 'coordination', description: 'Ranks all recommendations by ROI and effort', latestFinding: bizSub('Top action: Matcha Latte price increase — $840/mo impact, 15 minutes effort') },
    { id: 'feature-engineer', name: 'Feature Engineer', status: 'idle', lastRun: hoursAgo(72), nextRun: hoursFromNow(96), findings: 2, confidence: 74, category: 'strategy', description: 'Identifies highest-value features from agent findings', latestFinding: bizSub('Priority feature: Automated reorder alerts via SMS when stock hits reorder point') },
    { id: 'basket-analysis', name: 'Basket Analysis', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(4), findings: 5, confidence: 83, category: 'analysis', description: 'Identifies co-purchase pairs and bundle recommendations from transaction line items', latestFinding: bizSub('Espresso + Blueberry Muffin co-purchase rate 28% — potential $6.50 combo bundle') },
    { id: 'cash-flow', name: 'Cash Flow', status: 'active', lastRun: minutesAgo(30), nextRun: hoursFromNow(6), findings: 3, confidence: 80, category: 'forecasting', description: '14-day cash position forecast with processing fee analysis', latestFinding: bizSub('Processing fees averaging 2.8% — switching to flat-rate plan could save $220/mo') },
    { id: 'cashflow-forecast', name: 'Cashflow Forecast', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(6), findings: 2, confidence: 76, category: 'forecasting', description: '30-day cash flow projection with danger zone detection for low-balance periods', latestFinding: bizSub('Cash position dips to danger zone around the 18th — schedule vendor payments after the 20th') },
    { id: 'category-mix', name: 'Category Mix', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 4, confidence: 81, category: 'analysis', description: 'Analyzes category revenue share and identifies mix optimization opportunities', latestFinding: bizSub('Drinks dominate at 68% revenue share — food category underperforming at 32% vs 40% benchmark') },
    { id: 'customer-ltv', name: 'Customer LTV', status: 'active', lastRun: hoursAgo(3), nextRun: hoursFromNow(6), findings: 4, confidence: 78, category: 'analysis', description: 'Predicts customer lifetime value and identifies churn risk by segment', latestFinding: bizSub('Average LTV $1,840 — top decile customers worth $4,200+ over 12 months') },
    { id: 'customer-recognizer', name: 'Customer Recognizer', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 2, confidence: 70, category: 'analysis', description: 'Identifies repeat visitors via anonymized embeddings, tracks new vs returning ratio', latestFinding: bizSub('62% repeat visitor rate — loyalty-without-a-card metric trending up 5% MoM') },
    { id: 'day-of-week', name: 'Day of Week', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(6), findings: 3, confidence: 87, category: 'analysis', description: 'Identifies best and worst performing days with day-specific revenue patterns', latestFinding: bizSub('Saturday revenue 27% above average — Sunday underperforms by 21%, consider shorter hours') },
    { id: 'demographic-profiler', name: 'Demographic Profiler', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 2, confidence: 65, category: 'analysis', description: 'Detects age and gender distribution from camera feeds to inform marketing decisions', latestFinding: bizSub('25-34 age group represents 42% of traffic — tailor social media campaigns accordingly') },
    { id: 'discount-analyzer', name: 'Discount Analyzer', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(4), findings: 4, confidence: 84, category: 'optimization', description: 'Evaluates discount ROI and detects cannibalization from over-discounting', latestFinding: bizSub('Tuesday 20%-off promo cannibalized $180 in full-price sales — net ROI negative') },
    { id: 'dwell-time', name: 'Dwell Time', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 2, confidence: 69, category: 'analysis', description: 'Measures time visitors spend in each zone and builds browse-to-buy funnel metrics', latestFinding: bizSub('Avg dwell time 4.2 min in browse zone — visitors spending 6+ min convert at 2.1x rate') },
    { id: 'growth-score', name: 'Growth Score', status: 'active', lastRun: hoursAgo(4), nextRun: hoursFromNow(8), findings: 1, confidence: 77, category: 'strategy', description: 'Calculates executive growth opportunity score 0-100 with monthly action plan', latestFinding: bizSub('Growth score: 72/100 — pricing optimization and staffing adjustments are top levers') },
    { id: 'money-left', name: 'Money Left on Table', status: 'active', lastRun: hoursAgo(3), nextRun: hoursFromNow(6), findings: 3, confidence: 80, category: 'strategy', description: 'Aggregates all agent outputs into a headline dollar opportunity figure', latestFinding: bizSub('$3,840/mo total opportunity identified across pricing, staffing, and retention plays') },
    { id: 'payment-optimizer', name: 'Payment Optimizer', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(6), findings: 3, confidence: 79, category: 'optimization', description: 'Analyzes payment method mix and identifies fee optimization opportunities', latestFinding: bizSub('Cash transactions at 12% — encouraging cash for orders under $10 could save $160/mo in fees') },
    { id: 'pricing-power', name: 'Pricing Power', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 4, confidence: 82, category: 'optimization', description: 'Measures price elasticity across SKUs and identifies safe price increase candidates', latestFinding: bizSub('4 items have inelastic demand (elasticity < -0.5) — combined price increase potential $1,200/mo') },
    { id: 'product-velocity', name: 'Product Velocity', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(5), findings: 5, confidence: 86, category: 'analysis', description: 'Ranks products by sales velocity, identifies rising stars and dead stock', latestFinding: bizSub('Cold Brew velocity up 18% MoM — rising star. Chai Latte declining 3 consecutive weeks') },
    { id: 'promo-roi', name: 'Promo ROI', status: 'active', lastRun: hoursAgo(4), nextRun: hoursFromNow(8), findings: 2, confidence: 75, category: 'optimization', description: 'Calculates promotion return on investment with diminishing returns detection', latestFinding: bizSub('BOGO promo ROI at 1.4x — but repeat frequency shows diminishing returns after 3rd run') },
    { id: 'revenue-trend', name: 'Revenue Trend', status: 'active', lastRun: minutesAgo(20), nextRun: hoursFromNow(2), findings: 3, confidence: 88, category: 'analysis', description: 'Tracks daily, weekly, and monthly growth rates with trend signals', latestFinding: bizSub('WoW growth +4.2%, MoM +8.3% — consistent uptrend, strongest in morning daypart') },
    { id: 'seasonality', name: 'Seasonality', status: 'active', lastRun: hoursAgo(6), nextRun: hoursFromNow(12), findings: 2, confidence: 73, category: 'forecasting', description: 'Decomposes seasonal patterns and calendar effects on revenue', latestFinding: bizSub('Spring uptick begins mid-March historically — plan inventory ramp-up 2 weeks early') },
    { id: 'staffing', name: 'Staffing', status: 'active', lastRun: hoursAgo(2), nextRun: hoursFromNow(4), findings: 3, confidence: 81, category: 'optimization', description: 'Calculates optimal headcount per hour based on transaction volume and labor efficiency', latestFinding: bizSub('Overstaffed by 1 during 2-4PM lull — reassigning to 7-9AM peak saves $18/day') },
    { id: 'waste-shrinkage', name: 'Waste & Shrinkage', status: 'active', lastRun: hoursAgo(3), nextRun: hoursFromNow(6), findings: 4, confidence: 80, category: 'optimization', description: 'Tracks shrinkage rate, void patterns, and projects annual loss from waste', latestFinding: bizSub('Shrinkage rate 3.1% vs 2% target — void pattern on Register 2 needs investigation') },
    { id: 'foot-traffic', name: 'Foot Traffic', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 3, confidence: 72, category: 'analysis', description: 'Counts entries and exits from camera feeds, calculates visitor-to-transaction conversion', latestFinding: bizSub('Conversion rate 34% — 66% of foot traffic leaves without purchasing, signage test recommended') },
    { id: 'queue-monitor', name: 'Queue Monitor', status: 'idle', lastRun: hoursAgo(24), nextRun: hoursFromNow(24), findings: 2, confidence: 71, category: 'optimization', description: 'Tracks real-time queue length and wait times, estimates walkaway revenue loss', latestFinding: bizSub('Avg wait exceeds 3 min during 8-9AM — estimated $320/mo in walkaway losses') },
  ]
}

export function generateTopActions(): TopAction[] {
  return [
    {
      rank: 1,
      title: bizSub('Increase Matcha Latte price from $6.25 to $7.00'),
      description: bizSub('Demand elasticity analysis shows highly inelastic demand (elasticity: -0.3). Current price is $1.25 below competitor average. This single change captures 36% of total pricing opportunity.'),
      expectedImpact: bizSub('+$840/month revenue, +$640/month margin'),
      impactCents: cx(84000),
      effort: 'Low',
      confidence: 82,
      priority: 'Critical',
      agentSource: 'margin-optimizer',
      reasoning: {
        observation: bizSub('Matcha Latte priced at $6.25, competitor avg $7.50, demand elasticity -0.3'),
        reasoning: bizSub('Pricing-power agent ran price-elasticity regression on 90 days of transaction data. Elasticity coefficient -0.3 means a 12% price increase causes only 3.6% volume decline. Net revenue lift = (420 units x $0.75 increase) - (420 x 3.6% lost x $7.00) = $315 - $108.86 = $206.14/wk = $840/mo.'),
        conclusion: bizSub('Raise Matcha Latte to $7.00. Still $0.50 below competitor average, maintaining value perception.'),
        impact: bizSub('+$840/month revenue, +$640/month margin after accounting for 3.6% volume decline'),
        confidence: 82,
        priority: 'Critical',
        rawData: { current_price: '$6.25', competitor_avg: '$7.50', elasticity: -0.3, monthly_units: 420, projected_revenue_lift: '$840', model: 'log-log OLS regression (R²=0.91)' },
        agentId: 'margin-optimizer',
        agentName: 'Margin Optimizer',
      },
    },
    {
      rank: 2,
      title: bizSub('Add 1 staff member during 7-9AM peak window'),
      description: bizSub('Morning peak concentrates 47% of daily revenue into 2 hours but is understaffed by 1 position. Each lost sale costs $10.20 avg ticket. Queue-monitor estimates 6 walkouts/day during this window.'),
      expectedImpact: bizSub('+$520/month from reduced wait-time walkouts'),
      impactCents: cx(52000),
      effort: 'Medium',
      confidence: 88,
      priority: 'Critical',
      agentSource: 'peak-hour-optimizer',
      reasoning: {
        observation: bizSub('47% of revenue in 7-9AM, avg queue time 4.2 min, queue-monitor counted 6 walkouts/day via camera feed exit events'),
        reasoning: bizSub('Peak-hour-optimizer correlated staffing levels with queue-monitor walkout data. 6 lost customers/day x $10.20 avg ticket = $61.20/day. Adding 1 staff member costs $18/hr x 2hr = $36/day. Net gain $25.20/day x 26 weekdays = $655/mo. Conservative: $520/mo accounting for weekends at lower volume.'),
        conclusion: bizSub('Add 1 staff member for 7-9AM shift. Queue-monitor will validate reduction in walkouts within 2 weeks.'),
        impact: bizSub('+$520/month net revenue after labor cost'),
        confidence: 88,
        priority: 'Critical',
        rawData: { peak_revenue_share: '47%', avg_queue_time: '4.2 min', estimated_walkouts: 6, avg_ticket: '$10.20', labor_cost_per_hour: '$18', data_source: 'queue-monitor camera feed' },
        agentId: 'peak-hour-optimizer',
        agentName: 'Peak Hour Optimizer',
      },
    },
    {
      rank: 3,
      title: bizSub('Launch Cappuccino + Croissant bundle at $8.50'),
      description: bizSub('Basket-analysis agent found 34% co-purchase rate between Cappuccino and Croissant (separately: $5.25 + $4.25 = $9.50). A $8.50 bundle gives customers $1.00 savings while increasing attachment rate.'),
      expectedImpact: bizSub('+$380/month from increased attachment rate'),
      impactCents: cx(38000),
      effort: 'Low',
      confidence: 78,
      priority: 'High',
      agentSource: 'product-intelligence',
      reasoning: {
        observation: bizSub('Basket-analysis found Cappuccino + Croissant co-purchase rate 34% (support: 0.12, confidence: 0.34, lift: 1.8) from Apriori association rules on 12K transactions'),
        reasoning: bizSub('Product-intelligence ran what-if simulation: at $8.50 bundle (10.5% discount), projected attachment rate rises from 34% to 52% based on price-sensitivity curves. 180 Cappuccino sales/wk x 18% incremental attachment = 32 additional Croissant sales/wk. Net margin: $3.25 x 32 = $104/wk = $450/mo. Conservative: $380/mo.'),
        conclusion: bizSub('Create "Morning Combo" bundle at $8.50. Display prominently on menu board and POS screen. Basket-analysis will track lift weekly.'),
        impact: bizSub('+$380/month additional revenue, improved customer satisfaction from perceived value'),
        confidence: 78,
        priority: 'High',
        rawData: { cappuccino_weekly_sales: 180, co_purchase_rate: '34%', apriori_lift: 1.8, projected_rate: '52%', bundle_price: '$8.50', individual_total: '$9.50' },
        agentId: 'product-intelligence',
        agentName: 'Product Intelligence',
      },
    },
    {
      rank: 4,
      title: bizSub('Investigate Register 2 void spike — ensemble anomaly detected'),
      description: bizSub('Transaction-analyst flagged 14 voids on Tuesday 6-9PM vs 4-5 average. PyOD ensemble (IForest + LOF + KNN) confirmed 3/3 majority vote. Luminol time-series score 142 (threshold: 80). Possible training gap or policy abuse.'),
      expectedImpact: bizSub('+$460/month from void reduction to baseline'),
      impactCents: cx(46000),
      effort: 'Low',
      confidence: 91,
      priority: 'Critical',
      agentSource: 'transaction-analyst',
      reasoning: {
        observation: bizSub('14 void transactions Tuesday 6-9PM on Register 2 vs 4.6 trailing average. Z-score: -3.8 (>3σ threshold).'),
        reasoning: bizSub('Transaction-analyst ran 3-model ensemble: IsolationForest anomaly score 0.82 (threshold 0.65), LocalOutlierFactor score 0.91 (threshold 0.70), KNN distance score 0.78 (threshold 0.60). All 3 models flagged → majority vote = confirmed anomaly. Luminol time-series detector scored 142 vs 80 threshold, confirming temporal anomaly. Void $ value: $460/mo if pattern continues weekly.'),
        conclusion: bizSub('Review Register 2 operator logs for Tuesday PM shifts. Cross-reference with staff-performance-analyst for that shift. Likely training gap — not fraud (no cash drawer discrepancy).'),
        impact: bizSub('+$460/month if void rate returns to baseline 2% from current 5.8%'),
        confidence: 91,
        priority: 'Critical',
        rawData: { void_count: 14, expected_count: 4.6, z_score: -3.8, iforest_score: 0.82, lof_score: 0.91, knn_score: 0.78, luminol_score: 142, ensemble_vote: '3/3', register: 'Register 2' },
        agentId: 'transaction-analyst',
        agentName: 'Transaction Analyst',
      },
    },
    {
      rank: 5,
      title: bizSub('Winback campaign for 12 lapsed high-value customers'),
      description: bizSub('Customer-segmentor identified 12 customers in "At Risk" RFM segment with LTV >$2,000. BG/NBD model shows p(alive) between 0.25-0.40 — still recoverable. Retention-strategist recommends 15% targeted discount.'),
      expectedImpact: bizSub('+$840/month if 50% reactivation rate achieved'),
      impactCents: cx(84000),
      effort: 'Medium',
      confidence: 79,
      priority: 'High',
      agentSource: 'retention-strategist',
      reasoning: {
        observation: bizSub('12 At-Risk customers: avg LTV $2,840, avg 28 days since last visit, avg historical spend $156/mo. BG/NBD p(alive) range: 0.25-0.40.'),
        reasoning: bizSub('Retention-strategist consumed customer-segmentor RFM output + customer-ltv BG/NBD scores. BG/NBD model (lifetimes library: beta-geometric/negative-binomial distribution) estimates these customers have 25-40% probability of still being active — the winback window. Gamma-Gamma sub-model predicts expected monetary value per transaction. A 15% discount offer costs ~$23/reactivated visit but recovers $140 avg spend. Expected: 6 of 12 reactivate (50% response rate) x $140/mo = $840/mo.'),
        conclusion: bizSub('Send personalized SMS/email with 15% off next visit. Time-limit 7 days to create urgency. Customer-recognizer will track return visits.'),
        impact: bizSub('+$840/month revenue recovery, reduced churn in high-value segment'),
        confidence: 79,
        priority: 'High',
        rawData: { at_risk_count: 12, avg_ltv: '$2,840', avg_days_lapsed: 28, bg_nbd_p_alive_range: '0.25-0.40', projected_reactivation: '50%', discount_offered: '15%', model: 'BG/NBD + Gamma-Gamma (lifetimes)' },
        agentId: 'retention-strategist',
        agentName: 'Retention Strategist',
      },
    },
    {
      rank: 6,
      title: bizSub('Reorder Espresso beans now — stockout in 2 days'),
      description: bizSub('Inventory-intelligence velocity model predicts stockout in 48 hours at current consumption rate. Lead time is 3 days. Revenue at risk: $1,800/week from espresso-based drinks (62% of menu).'),
      expectedImpact: bizSub('Avoid $620/month in lost sales from stockouts'),
      impactCents: cx(62000),
      effort: 'Low',
      confidence: 85,
      priority: 'Critical',
      agentSource: 'inventory-intelligence',
      reasoning: {
        observation: bizSub('Espresso bean stock: 4.2 lbs remaining. 7-day avg consumption: 2.1 lbs/day. Supplier lead time: 3 business days. Reorder point: 6.3 lbs.'),
        reasoning: bizSub('Inventory-intelligence calculated: current_stock (4.2 lbs) / daily_consumption (2.1 lbs) = 2.0 days until stockout. Reorder point = lead_time (3 days) x daily_consumption (2.1) x safety_factor (1.0) = 6.3 lbs. Stock is 33% below reorder point. Espresso beans supply 8 of 14 menu items (Espresso, Cappuccino, Iced Latte, Cold Brew, etc). Historical stockout cost: avg $155/day in lost sales.'),
        conclusion: bizSub('Place emergency order immediately. Set auto-reorder trigger at 6.3 lbs to prevent future stockouts. Margin-optimizer flagged that supplier B offers 8% lower cost — consider switching.'),
        impact: bizSub('Avoid $620/month in stockout losses (avg 4 stockout days/month historically)'),
        confidence: 85,
        priority: 'Critical',
        rawData: { current_stock_lbs: 4.2, daily_consumption_lbs: 2.1, days_until_stockout: 2.0, lead_time_days: 3, reorder_point_lbs: 6.3, affected_menu_items: 8, daily_stockout_cost: '$155' },
        agentId: 'inventory-intelligence',
        agentName: 'Inventory Intelligence',
      },
    },
    {
      rank: 7,
      title: bizSub('Cancel Tuesday 20%-off promo — negative ROI detected'),
      description: bizSub('Discount-analyzer found the recurring Tuesday promotion cannibalized $180 in full-price sales while generating only $120 in incremental revenue. Promo-roi confirmed diminishing returns after 3rd consecutive run.'),
      expectedImpact: bizSub('+$240/month from ending negative-ROI promotion'),
      impactCents: cx(24000),
      effort: 'Low',
      confidence: 84,
      priority: 'High',
      agentSource: 'discount-analyzer',
      reasoning: {
        observation: bizSub('Tuesday 20%-off promo: $680 in promo sales, but Tuesday baseline without promo was $560. Incremental revenue: $120. Discount cost: $136 (20% of $680). Net: -$16/week.'),
        reasoning: bizSub('Discount-analyzer decomposed Tuesday sales into baseline + incremental using diff-in-diff method (comparing to non-promo Tuesdays). Only 17.6% of promo revenue was truly incremental — 82.4% would have happened at full price. Promo-roi agent confirmed: ROI was 1.4x on first run but declined to 0.88x by run #5 (diminishing returns curve fitted R²=0.94). Cannibalization rate accelerating as regular customers time purchases to Tuesdays.'),
        conclusion: bizSub('Discontinue the Tuesday blanket discount. Replace with targeted offers to "Needs Attention" segment only (via retention-strategist) to limit cannibalization.'),
        impact: bizSub('+$240/month net margin recovery from eliminating promo cannibalization'),
        confidence: 84,
        priority: 'High',
        rawData: { promo_revenue: '$680', baseline_revenue: '$560', incremental_pct: '17.6%', cannibalization_pct: '82.4%', promo_roi_run5: 0.88, discount_cost_weekly: '$136', method: 'diff-in-diff + diminishing returns fit' },
        agentId: 'discount-analyzer',
        agentName: 'Discount Analyzer',
      },
    },
    {
      rank: 8,
      title: bizSub('Shrinkage investigation — Register 2 waste rate 3.1% vs 2% target'),
      description: bizSub('Waste-shrinkage agent detected 3.1% shrinkage rate, 55% above the 2% target. Void pattern on Register 2 correlates with transaction-analyst anomaly finding. Combined waste + void leakage estimated at $380/month.'),
      expectedImpact: bizSub('+$380/month from shrinkage reduction'),
      impactCents: cx(38000),
      effort: 'Medium',
      confidence: 80,
      priority: 'High',
      agentSource: 'waste-shrinkage',
      reasoning: {
        observation: bizSub('Shrinkage rate 3.1% (target 2.0%). Register 2 accounts for 68% of all voids. Inventory-intelligence reports oat milk usage 40% above expected without matching sales increase.'),
        reasoning: bizSub('Waste-shrinkage agent correlated three data streams: (1) transaction-analyst void spike data, (2) inventory-intelligence usage anomaly on oat milk, (3) daily cash reconciliation reports. Register 2 void-to-sale ratio is 2.4x other registers. Oat milk over-consumption maps to same Tuesday PM shift — likely over-portioning, not theft. Total monthly leakage: $220 void-related + $160 over-portioning = $380.'),
        conclusion: bizSub('Schedule retraining for Tuesday PM shift operator on portioning and void procedures. Install pour-cost tracking on oat milk. Re-measure in 30 days.'),
        impact: bizSub('+$380/month from reducing shrinkage rate from 3.1% to target 2.0%'),
        confidence: 80,
        priority: 'High',
        rawData: { shrinkage_rate: '3.1%', target_rate: '2.0%', register_2_void_share: '68%', oat_milk_overuse_pct: '40%', void_leakage_monthly: '$220', portion_leakage_monthly: '$160', correlated_agents: 'transaction-analyst, inventory-intelligence' },
        agentId: 'waste-shrinkage',
        agentName: 'Waste & Shrinkage',
      },
    },
    {
      rank: 9,
      title: bizSub('Forecast confidence boost — switch to AutoARIMA+AutoETS+AutoTheta ensemble'),
      description: bizSub('Revenue-forecaster backtested 5 model combinations. The 3-model adaptive ensemble (statsforecast) reduced MAPE from 14.2% to 8.7% vs single-model AutoETS. 90-day forecast tightens from ±14% to ±9% confidence interval.'),
      expectedImpact: bizSub('Better planning accuracy — avoid $340/month in over/under-ordering'),
      impactCents: cx(34000),
      effort: 'Low',
      confidence: 84,
      priority: 'Medium',
      agentSource: 'revenue-forecaster',
      reasoning: {
        observation: bizSub('Current 90-day forecast uses single AutoETS model. Backtest MAPE: 14.2%. Confidence interval: ±14%. Inventory-intelligence over-ordered twice last month based on wide forecast bands.'),
        reasoning: bizSub('Revenue-forecaster ran statsforecast adaptive ensemble selection: AutoARIMA (MAPE 11.3%), AutoETS (MAPE 14.2%), AutoTheta (MAPE 12.8%), CES (MAPE 16.1%), MSTL (MAPE 13.5%). Top-3 ensemble weighted by inverse MAPE: AutoARIMA 0.38, AutoTheta 0.33, AutoETS 0.29. Ensemble MAPE: 8.7%. Cross-validation on 12 rolling windows confirmed improvement is statistically significant (p < 0.05, Diebold-Mariano test).'),
        conclusion: bizSub('Activate 3-model ensemble as default. Seasonality agent provides seasonal decomposition as input feature. Forecast periods feed into inventory-intelligence reorder calculations.'),
        impact: bizSub('Tighter forecasts reduce over-ordering by $220/mo and under-stocking losses by $120/mo = $340/mo total'),
        confidence: 84,
        priority: 'Medium',
        rawData: { autoarima_mape: '11.3%', autoets_mape: '14.2%', autotheta_mape: '12.8%', ensemble_mape: '8.7%', ci_improvement: '±14% → ±9%', cross_val_windows: 12, dm_test_p: '<0.05', model: 'statsforecast adaptive ensemble' },
        agentId: 'revenue-forecaster',
        agentName: 'Revenue Forecaster',
      },
    },
    {
      rank: 10,
      title: bizSub('Target 23 Champions with exclusive early access to new Iced Latte flavor'),
      description: bizSub('Customer-segmentor identified 23 Champions (top 8% by RFM score) driving 41% of revenue. Customer-ltv BG/NBD model confirms p(alive) >0.95 for this cohort. Loyalty-architect recommends exclusive preview to deepen engagement.'),
      expectedImpact: bizSub('+$280/month from increased Champion visit frequency'),
      impactCents: cx(28000),
      effort: 'Low',
      confidence: 76,
      priority: 'Medium',
      agentSource: 'customer-segmentor',
      reasoning: {
        observation: bizSub('23 Champion customers: RFM score 5/5/5, avg 18 visits/mo, avg spend $15.80/visit, LTV $4,200+. BG/NBD p(alive): 0.95-0.98. 4 of 23 showing early frequency decline (18 → 14 visits/mo).'),
        reasoning: bizSub('Customer-segmentor RFM analysis assigned segment via recency (days since last visit), frequency (visits/90d), monetary (avg order value). Customer-ltv ran BG/NBD model (lifetimes library) for p(alive) and Gamma-Gamma for expected monetary value. 4 Champions showing 22% frequency decline — early churn signal. Loyalty-architect recommends exclusive preview (cost: ~$0/marginal cost for existing inventory) to arrest decline. If it recovers 2 of 4 declining Champions: 2 x 4 extra visits/mo x $15.80 = $126/mo. Plus word-of-mouth from 23 Champions driving 1 new referral/mo at $140 LTV = $280/mo total.'),
        conclusion: bizSub('Send personalized invite to Champions for exclusive early tasting of new Iced Latte seasonal flavor. Track with customer-recognizer for visit frequency changes over 30 days.'),
        impact: bizSub('+$280/month from retained Champion frequency + referral revenue'),
        confidence: 76,
        priority: 'Medium',
        rawData: { champion_count: 23, revenue_share: '41%', avg_visits_month: 18, avg_spend: '$15.80', declining_count: 4, bg_nbd_p_alive: '0.95-0.98', gamma_gamma_emv: '$15.80', rfm_score: '5/5/5', model: 'BG/NBD + Gamma-Gamma + RFM' },
        agentId: 'customer-segmentor',
        agentName: 'Customer Segmentor',
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
  ].map(s => ({ ...s, avgSpendCents: cx(s.avgSpendCents) }))
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
  const staff = getStaff(getActiveBusinessType())
  const baseData = [
    { avgTicketCents: 1280, transactionsPerShift: 48, upsellRate: 34, customerRating: 4.9, revenuePerHour: 6800, trend: 'up' as const },
    { avgTicketCents: 1150, transactionsPerShift: 42, upsellRate: 28, customerRating: 4.7, revenuePerHour: 5600, trend: 'up' as const },
    { avgTicketCents: 1080, transactionsPerShift: 45, upsellRate: 22, customerRating: 4.8, revenuePerHour: 5400, trend: 'stable' as const },
    { avgTicketCents: 980, transactionsPerShift: 38, upsellRate: 18, customerRating: 4.5, revenuePerHour: 4200, trend: 'down' as const },
    { avgTicketCents: 920, transactionsPerShift: 52, upsellRate: 12, customerRating: 4.6, revenuePerHour: 4800, trend: 'stable' as const },
    { avgTicketCents: 860, transactionsPerShift: 32, upsellRate: 8, customerRating: 4.3, revenuePerHour: 3200, trend: 'up' as const },
  ]
  const rc = getBusinessProfile(getActiveBusinessType()).revenue
  const coffeeAvgTicket = 1050
  const bizAvgTicket = (rc.avgTicketMin + rc.avgTicketMax) / 2
  const scale = bizAvgTicket / coffeeAvgTicket

  return staff.map((s, i) => ({
    id: String(i + 1),
    name: s.name,
    role: s.role,
    avgTicketCents: Math.round(baseData[i].avgTicketCents * scale),
    transactionsPerShift: baseData[i].transactionsPerShift,
    upsellRate: baseData[i].upsellRate,
    customerRating: baseData[i].customerRating,
    revenuePerHour: Math.round(baseData[i].revenuePerHour * scale),
    trend: baseData[i].trend,
  }))
}

export function generatePeakHourHeatmap(): PeakHourCell[] {
  const hourly = getBusinessProfile(getActiveBusinessType()).hourlyPattern
  const dayFactors = [0.92, 1.0, 1.02, 0.98, 1.04, 1.08, 0.96]
  const cells: PeakHourCell[] = []
  for (let day = 0; day < 7; day++) {
    for (let hour = 0; hour < 24; hour++) {
      const base = Math.round(hourly[hour] * dayFactors[day])
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
  const bt = getActiveBusinessType()
  if (bt === 'coffee_shop') {
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
  // For other business types, generate from product catalog
  const products = getProducts(bt)
  const primaryName = bt === 'auto_shop' ? 'Parts & materials'
    : bt === 'smoke_shop' ? 'Wholesale cost'
    : bt === 'restaurant' ? 'Ingredients'
    : bt === 'fast_food' ? 'Food cost'
    : 'Ingredients'
  const wastePctBase = bt === 'auto_shop' ? 2 : 5
  let ms = 200
  return products.slice(0, 10).map(p => {
    ms = (ms * 16807) % 2147483647
    const r = (ms - 1) / 2147483646
    const marginBias = p.popularity > 0.7 ? 0.72 : 0.62
    const marginPct = marginBias + r * 0.12
    const monthlySales = Math.floor(p.popularity * 350 + 50)
    const rawCost = Math.round(p.price * (1 - marginPct))
    return calcMarginItem(p.name, p.category, p.price, monthlySales, [
      { name: primaryName, batchCostCents: rawCost * 20, batchServings: 20, amountUsedOz: 1, wastePct: wastePctBase },
      { name: 'Packaging/overhead', batchCostCents: 1500, batchServings: 100, amountUsedOz: 0, wastePct: 1 },
    ], Math.floor(r * 9000))
  })
}

export function generateCustomerRankings(): CustomerProfile[] {
  const p = getProducts(getActiveBusinessType())
  const daysAgo = (d: number) => {
    const dt = new Date()
    dt.setDate(dt.getDate() - d)
    return dt.toISOString()
  }
  return [
    { id: 'c1', name: 'Rachel M.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1580, totalSpentCents: 284400, visitsPerMonth: 18, lastVisit: daysAgo(1), daysSinceVisit: 1, topItem: p[2].name + ' + ' + p[10].name, retentionRisk: 'low', ltvCents: 420000, churnRiskPct: 3, pAlive: 0.97 },
    { id: 'c2', name: 'David K.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1420, totalSpentCents: 255600, visitsPerMonth: 16, lastVisit: daysAgo(1), daysSinceVisit: 1, topItem: p[3].name + ' + ' + p[9].name, retentionRisk: 'low', ltvCents: 384000, churnRiskPct: 5, pAlive: 0.95 },
    { id: 'c3', name: 'Sarah T.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1250, totalSpentCents: 150000, visitsPerMonth: 12, lastVisit: daysAgo(2), daysSinceVisit: 2, topItem: p[1].name + ' + ' + p[8].name, retentionRisk: 'low', ltvCents: 264000, churnRiskPct: 8, pAlive: 0.92 },
    { id: 'c4', name: 'Michael B.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1680, totalSpentCents: 302400, visitsPerMonth: 20, lastVisit: daysAgo(0), daysSinceVisit: 0, topItem: p[4].name + ' + ' + p[11].name, retentionRisk: 'low', ltvCents: 480000, churnRiskPct: 2, pAlive: 0.98 },
    { id: 'c5', name: 'Lisa W.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1180, totalSpentCents: 141600, visitsPerMonth: 10, lastVisit: daysAgo(3), daysSinceVisit: 3, topItem: p[0].name + ' + ' + p[9].name, retentionRisk: 'low', ltvCents: 216000, churnRiskPct: 10, pAlive: 0.90 },
    { id: 'c6', name: 'James P.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 980, totalSpentCents: 117600, visitsPerMonth: 8, lastVisit: daysAgo(4), daysSinceVisit: 4, topItem: p[7].name + ' x2', retentionRisk: 'low', ltvCents: 168000, churnRiskPct: 12, pAlive: 0.88 },
    { id: 'c7', name: 'Amanda R.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 1340, totalSpentCents: 80400, visitsPerMonth: 6, lastVisit: daysAgo(5), daysSinceVisit: 5, topItem: p[2].name + ' + ' + p[10].name, retentionRisk: 'low', ltvCents: 144000, churnRiskPct: 18, pAlive: 0.82 },
    { id: 'c8', name: 'Chris H.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 890, totalSpentCents: 53400, visitsPerMonth: 5, lastVisit: daysAgo(6), daysSinceVisit: 6, topItem: p[1].name, retentionRisk: 'medium', ltvCents: 96000, churnRiskPct: 25, pAlive: 0.75 },
    { id: 'c9', name: 'Nicole F.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 1560, totalSpentCents: 46800, visitsPerMonth: 3, lastVisit: daysAgo(14), daysSinceVisit: 14, topItem: p[4].name + ' + ' + p[10].name, retentionRisk: 'medium', ltvCents: 72000, churnRiskPct: 42, pAlive: 0.58 },
    { id: 'c10', name: 'Robert G.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 1450, totalSpentCents: 174000, visitsPerMonth: 1, lastVisit: daysAgo(28), daysSinceVisit: 28, topItem: p[3].name + ' + ' + p[11].name, retentionRisk: 'high', ltvCents: 48000, churnRiskPct: 68, pAlive: 0.32 },
    { id: 'c11', name: 'Emily S.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 720, totalSpentCents: 28800, visitsPerMonth: 4, lastVisit: daysAgo(7), daysSinceVisit: 7, topItem: p[7].name + ' + ' + p[8].name, retentionRisk: 'low', ltvCents: 60000, churnRiskPct: 15, pAlive: 0.85 },
    { id: 'c12', name: 'Tom L.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 1320, totalSpentCents: 158400, visitsPerMonth: 1, lastVisit: daysAgo(35), daysSinceVisit: 35, topItem: p[2].name + ' + ' + p[9].name, retentionRisk: 'high', ltvCents: 36000, churnRiskPct: 75, pAlive: 0.25 },
    { id: 'c13', name: 'Jennifer C.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 650, totalSpentCents: 13000, visitsPerMonth: 2, lastVisit: daysAgo(3), daysSinceVisit: 3, topItem: p[1].name, retentionRisk: 'medium', ltvCents: 24000, churnRiskPct: 30, pAlive: 0.70 },
    { id: 'c14', name: 'Brian N.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 980, totalSpentCents: 58800, visitsPerMonth: 0, lastVisit: daysAgo(62), daysSinceVisit: 62, topItem: p[0].name + ' + ' + p[9].name, retentionRisk: 'high', ltvCents: 12000, churnRiskPct: 88, pAlive: 0.12 },
    { id: 'c15', name: 'Karen A.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 480, totalSpentCents: 9600, visitsPerMonth: 2, lastVisit: daysAgo(5), daysSinceVisit: 5, topItem: p[7].name, retentionRisk: 'medium', ltvCents: 18000, churnRiskPct: 35, pAlive: 0.65 },
  ].map(c => ({ ...c, avgOrderCents: cx(c.avgOrderCents), totalSpentCents: cx(c.totalSpentCents), ltvCents: cx(c.ltvCents!) } as CustomerProfile))
}

export function generateForecastPeriods(): ForecastPeriod[] {
  const rc = getBusinessProfile(getActiveBusinessType()).revenue
  const avgDaily = (rc.weekdayMin + rc.weekdayMax) / 2
  const weeklyBase = Math.floor(avgDaily * 5 + ((rc.weekendMin + rc.weekendMax) / 2) * 2)
  const monthlyBase = Math.floor(weeklyBase * 4.3)
  const quarterlyBase = monthlyBase * 3

  return [
    { label: '7-Day', days: 7, predictedCents: cx(weeklyBase), lowerCents: cx(Math.floor(weeklyBase * 0.85)), upperCents: cx(Math.floor(weeklyBase * 1.15)), confidence: 89, growthPct: 4.2, errorRate: 0.10, scenarioOptimisticCents: cx(Math.floor(weeklyBase * 1.15)), scenarioExpectedCents: cx(weeklyBase), scenarioPessimisticCents: cx(Math.floor(weeklyBase * 0.85)), modelMethod: 'AutoETS + AutoARIMA ensemble' },
    { label: '30-Day', days: 30, predictedCents: cx(monthlyBase), lowerCents: cx(Math.floor(monthlyBase * 0.88)), upperCents: cx(Math.floor(monthlyBase * 1.12)), confidence: 82, growthPct: 8.3, errorRate: 0.13, scenarioOptimisticCents: cx(Math.floor(monthlyBase * 1.15)), scenarioExpectedCents: cx(monthlyBase), scenarioPessimisticCents: cx(Math.floor(monthlyBase * 0.85)), modelMethod: 'AutoARIMA + AutoETS + AutoTheta ensemble' },
    { label: '90-Day', days: 90, predictedCents: cx(quarterlyBase), lowerCents: cx(Math.floor(quarterlyBase * 0.86)), upperCents: cx(Math.floor(quarterlyBase * 1.14)), confidence: 71, growthPct: 12.1, errorRate: 0.18, scenarioOptimisticCents: cx(Math.floor(quarterlyBase * 1.15)), scenarioExpectedCents: cx(quarterlyBase), scenarioPessimisticCents: cx(Math.floor(quarterlyBase * 0.85)), modelMethod: 'AutoARIMA + AutoETS + AutoTheta ensemble' },
  ]
}

// ─── #1 Menu Engineering BCG Matrix ─────────────────────────

export type MenuQuadrant = 'star' | 'puzzle' | 'plowhorse' | 'dog'

export interface MenuEngItem {
  name: string
  category: string
  monthlySales: number
  marginPct: number
  popularityIndex: number
  profitabilityIndex: number
  quadrant: MenuQuadrant
  recommendation: string
  revenueCents: number
  marginCents: number
}

export function generateMenuEngineering(): MenuEngItem[] {
  const products = getProducts(getActiveBusinessType())
  const items = products.slice(0, 10)
  const avgSales = 290
  const avgMargin = 68

  function classify(sales: number, margin: number): MenuQuadrant {
    if (sales >= avgSales && margin >= avgMargin) return 'star'
    if (sales < avgSales && margin >= avgMargin) return 'puzzle'
    if (sales >= avgSales && margin < avgMargin) return 'plowhorse'
    return 'dog'
  }

  const recommendations: Record<MenuQuadrant, string> = {
    star: 'Protect and promote — premium menu placement, never discount',
    puzzle: 'High profit but low sales — increase visibility, add to combos, train staff to upsell',
    plowhorse: 'Popular but low margin — raise price incrementally or reduce portion cost',
    dog: 'Low profit, low popularity — consider removing or completely reinventing',
  }

  let ms = 300
  return items.map(p => {
    ms = (ms * 16807) % 2147483647
    const r = (ms - 1) / 2147483646
    const monthlySales = Math.floor(p.popularity * 350 + r * 150)
    const marginPct = Math.floor(55 + p.popularity * 25 + r * 8)
    const revenueCents = monthlySales * p.price
    const marginCents = Math.floor(revenueCents * marginPct / 100)
    const q = classify(monthlySales, marginPct)
    return {
      name: p.name,
      category: p.category,
      monthlySales,
      marginPct,
      popularityIndex: Math.round((monthlySales / avgSales) * 100),
      profitabilityIndex: Math.round((marginPct / avgMargin) * 100),
      quadrant: q,
      recommendation: recommendations[q],
      revenueCents,
      marginCents,
    }
  })
}

// ─── #2 Anomaly Detection ───────────────────────────────────

export interface Anomaly {
  id: string
  type: 'void_spike' | 'refund_surge' | 'revenue_drop' | 'cost_spike' | 'traffic_anomaly' | 'register_shortage'
  severity: 'critical' | 'warning' | 'info'
  title: string
  description: string
  detectedAt: string
  metric: string
  expected: number
  actual: number
  deviationPct: number
  agentSource: string
  acknowledged: boolean
  zScore?: number
  luminolScore?: number
  detectionMethod?: 'zscore' | 'luminol' | 'ensemble'
}

export function generateAnomalies(): Anomaly[] {
  return [
    { id: 'a1', type: 'void_spike', severity: 'critical', title: bizSub('Void transactions 3x normal'), description: bizSub('Tuesday 6-9PM saw 14 void transactions vs. 4-5 average. Concentrated on Register 2. Possible training issue or policy abuse.'), detectedAt: minutesAgo(45), metric: 'void_count', expected: 5, actual: 14, deviationPct: 180, agentSource: 'transaction-analyst', acknowledged: false, zScore: -3.8, luminolScore: 142, detectionMethod: 'ensemble' },
    { id: 'a2', type: 'revenue_drop', severity: 'warning', title: bizSub('Morning revenue down 22%'), description: bizSub('Revenue between 7-9AM dropped 22% vs. prior 4-week average. Weather was clear, no holidays. Possible competitor event or staffing issue.'), detectedAt: hoursAgo(3), metric: 'peak_revenue', expected: 48000, actual: 37440, deviationPct: -22, agentSource: 'peak-hour-optimizer', acknowledged: false, zScore: -2.4, luminolScore: 87, detectionMethod: 'ensemble' },
    { id: 'a3', type: 'cost_spike', severity: 'warning', title: bizSub('Oat milk usage up 40%'), description: bizSub('Oat milk consumption jumped 40% without corresponding sales increase. Possible over-portioning or waste issue.'), detectedAt: hoursAgo(8), metric: 'ingredient_usage_oz', expected: 320, actual: 448, deviationPct: 40, agentSource: 'inventory-intelligence', acknowledged: true, zScore: 2.1, detectionMethod: 'zscore' },
    { id: 'a4', type: 'traffic_anomaly', severity: 'info', title: bizSub('Unusual Saturday surge'), description: bizSub('Transactions 35% above Saturday average. Nearby event (farmers market) likely driving foot traffic. Consider staffing up for recurring events.'), detectedAt: hoursAgo(26), metric: 'transaction_count', expected: 180, actual: 243, deviationPct: 35, agentSource: 'peak-hour-optimizer', acknowledged: true, zScore: 1.8, luminolScore: 64, detectionMethod: 'luminol' },
    { id: 'a5', type: 'refund_surge', severity: 'warning', title: bizSub('Refund rate doubled this week'), description: bizSub('Refund rate hit 4.2% vs. 2.1% trailing average. 6 of 8 refunds were on Breakfast Sandwich — possible quality issue with current batch.'), detectedAt: hoursAgo(5), metric: 'refund_rate_pct', expected: 2.1, actual: 4.2, deviationPct: 100, agentSource: 'transaction-analyst', acknowledged: false, zScore: -2.8, luminolScore: 95, detectionMethod: 'ensemble' },
  ]
}

// ─── #3 Cohort Analysis ─────────────────────────────────────

export interface CohortRow {
  cohort: string
  totalCustomers: number
  retentionByMonth: number[]
}

export function generateCohorts(): CohortRow[] {
  return [
    { cohort: 'Jan 2026', totalCustomers: 42, retentionByMonth: [100, 74, 62, 55] },
    { cohort: 'Feb 2026', totalCustomers: 38, retentionByMonth: [100, 71, 58] },
    { cohort: 'Mar 2026', totalCustomers: 51, retentionByMonth: [100, 78] },
    { cohort: 'Apr 2026', totalCustomers: 47, retentionByMonth: [100] },
  ]
}

// ─── #4 Agent Chaining ──────���───────────────────────────────

export interface AgentChainLink {
  from: string
  to: string
  trigger: string
  dataPassed: string
}

export function generateAgentChains(): AgentChainLink[] {
  return [
    // ── Transaction Pipeline ──
    { from: 'transaction-analyst', to: 'product-intelligence', trigger: 'new_transactions_batch', dataPassed: 'Transaction line items + timestamps + register IDs' },
    { from: 'transaction-analyst', to: 'customer-segmentor', trigger: 'new_transactions_batch', dataPassed: 'Customer IDs + spend amounts + visit timestamps' },
    { from: 'transaction-analyst', to: 'basket-analysis', trigger: 'new_transactions_batch', dataPassed: 'Basket contents per transaction for Apriori association rules' },
    { from: 'transaction-analyst', to: 'payment-optimizer', trigger: 'new_transactions_batch', dataPassed: 'Payment method + amount per transaction' },
    { from: 'transaction-analyst', to: 'waste-shrinkage', trigger: 'void_or_refund_detected', dataPassed: 'Void/refund records + register ID + operator ID' },
    { from: 'transaction-analyst', to: 'revenue-trend', trigger: 'daily_close', dataPassed: 'Daily revenue total + transaction count + avg ticket' },

    // ── Product & Pricing Pipeline ──
    { from: 'product-intelligence', to: 'margin-optimizer', trigger: 'sku_velocity_updated', dataPassed: 'SKU rankings + co-purchase rates + cannibalization matrix' },
    { from: 'product-intelligence', to: 'category-mix', trigger: 'sku_velocity_updated', dataPassed: 'Category-level revenue shares + velocity trends' },
    { from: 'basket-analysis', to: 'product-intelligence', trigger: 'association_rules_updated', dataPassed: 'Support/confidence/lift for top item pairs (Apriori output)' },
    { from: 'pricing-power', to: 'margin-optimizer', trigger: 'elasticity_computed', dataPassed: 'Per-SKU price elasticity coefficients + safe-increase candidates' },
    { from: 'margin-optimizer', to: 'revenue-forecaster', trigger: 'pricing_opportunity_found', dataPassed: 'Price change proposals + projected volume impact + elasticity data' },
    { from: 'product-velocity', to: 'inventory-intelligence', trigger: 'velocity_change_detected', dataPassed: 'Rising/declining SKU velocity + reorder implications' },
    { from: 'product-velocity', to: 'product-intelligence', trigger: 'velocity_change_detected', dataPassed: 'Rising stars + dead stock flags for menu engineering' },

    // ── Customer Pipeline (BG/NBD + RFM) ──
    { from: 'customer-segmentor', to: 'retention-strategist', trigger: 'segments_updated', dataPassed: 'RFM segments + churn risk scores + segment migration' },
    { from: 'customer-segmentor', to: 'customer-ltv', trigger: 'segments_updated', dataPassed: 'Customer purchase histories for BG/NBD + Gamma-Gamma modeling' },
    { from: 'customer-ltv', to: 'retention-strategist', trigger: 'ltv_scores_updated', dataPassed: 'p(alive) scores + expected monetary value + LTV estimates' },
    { from: 'customer-ltv', to: 'loyalty-architect', trigger: 'ltv_scores_updated', dataPassed: 'High-LTV customer list for reward tier optimization' },
    { from: 'customer-recognizer', to: 'customer-segmentor', trigger: 'visitor_identified', dataPassed: 'Anonymized visitor embeddings + new vs returning classification' },
    { from: 'retention-strategist', to: 'discount-analyzer', trigger: 'winback_offer_proposed', dataPassed: 'Proposed discount offers for ROI pre-validation' },
    { from: 'demographic-profiler', to: 'customer-segmentor', trigger: 'demographics_updated', dataPassed: 'Age/gender distribution for enriching customer segments' },

    // ── Anomaly Detection Pipeline (PyOD ensemble + Luminol) ──
    { from: 'transaction-analyst', to: 'waste-shrinkage', trigger: 'anomaly_ensemble_alert', dataPassed: 'PyOD scores (IForest + LOF + KNN) + Luminol time-series score + z-score' },
    { from: 'waste-shrinkage', to: 'staff-performance-analyst', trigger: 'shrinkage_operator_flagged', dataPassed: 'Operator ID + void/waste pattern + shift correlation' },
    { from: 'inventory-intelligence', to: 'waste-shrinkage', trigger: 'usage_anomaly_detected', dataPassed: 'Ingredient over-consumption rates vs expected from sales mix' },

    // ── Forecasting Pipeline (statsforecast ensemble) ──
    { from: 'revenue-trend', to: 'revenue-forecaster', trigger: 'trend_signal_updated', dataPassed: 'WoW/MoM growth rates + trend direction + daypart breakdown' },
    { from: 'seasonality', to: 'revenue-forecaster', trigger: 'seasonal_decomposition_ready', dataPassed: 'Seasonal indices + calendar effects + holiday flags' },
    { from: 'revenue-forecaster', to: 'cashflow-forecast', trigger: 'forecast_updated', dataPassed: 'Revenue projections (7/30/90 day) + confidence intervals from ensemble' },
    { from: 'revenue-forecaster', to: 'inventory-intelligence', trigger: 'forecast_updated', dataPassed: 'Predicted demand for reorder point calculations' },

    // ── Operations Pipeline ──
    { from: 'peak-hour-optimizer', to: 'staffing', trigger: 'peak_hours_computed', dataPassed: 'Optimal headcount per hour from transaction density analysis' },
    { from: 'peak-hour-optimizer', to: 'staff-performance-analyst', trigger: 'staffing_gap_detected', dataPassed: 'Understaffed hours + current schedule + queue-monitor data' },
    { from: 'staffing', to: 'cash-flow', trigger: 'labor_cost_projected', dataPassed: 'Projected labor cost per day for cash flow modeling' },
    { from: 'queue-monitor', to: 'peak-hour-optimizer', trigger: 'queue_length_alert', dataPassed: 'Real-time queue length + wait times + walkout count' },
    { from: 'foot-traffic', to: 'peak-hour-optimizer', trigger: 'traffic_count_updated', dataPassed: 'Entry/exit counts + visitor-to-transaction conversion rate' },
    { from: 'dwell-time', to: 'foot-traffic', trigger: 'dwell_analysis_complete', dataPassed: 'Zone dwell times + browse-to-buy funnel conversion' },

    // ── Inventory & Cost Pipeline ──
    { from: 'inventory-intelligence', to: 'margin-optimizer', trigger: 'cost_anomaly_detected', dataPassed: 'Ingredient cost changes + supplier price movements' },
    { from: 'inventory-intelligence', to: 'cash-flow', trigger: 'reorder_triggered', dataPassed: 'Purchase order amounts for cash outflow projection' },
    { from: 'cashflow-forecast', to: 'payment-optimizer', trigger: 'cash_position_forecast', dataPassed: '14-day cash position + danger zone dates' },

    // ── Financial & Growth Pipeline ──
    { from: 'discount-analyzer', to: 'promo-roi', trigger: 'discount_event_analyzed', dataPassed: 'Incremental vs cannibalized revenue per promo event' },
    { from: 'promo-roi', to: 'margin-optimizer', trigger: 'promo_roi_computed', dataPassed: 'Promo ROI trajectory + diminishing returns curve' },
    { from: 'competitor-benchmarker', to: 'pricing-power', trigger: 'benchmark_updated', dataPassed: 'Competitor price points + market positioning gaps' },
    { from: 'growth-score', to: 'feature-engineer', trigger: 'growth_levers_ranked', dataPassed: 'Top growth opportunity areas + lever impact estimates' },

    // ── Coordination Layer ──
    { from: 'day-of-week', to: 'peak-hour-optimizer', trigger: 'daily_patterns_updated', dataPassed: 'Best/worst day performance + day-specific revenue coefficients' },
    { from: 'money-left', to: 'insight-narrator', trigger: 'opportunity_aggregated', dataPassed: 'Total $/mo opportunity figure from all agent recommendations' },
    { from: 'insight-narrator', to: 'action-prioritizer', trigger: 'all_agents_complete', dataPassed: 'Synthesized findings from all 37 agents as narrative brief' },
    { from: 'action-prioritizer', to: 'revenue-forecaster', trigger: 'action_ranked', dataPassed: 'Top actions for impact projection into forecast scenarios' },
    { from: 'revenue-forecaster', to: 'insight-narrator', trigger: 'forecast_updated', dataPassed: 'Updated projections + scenario analysis for executive brief' },
    { from: 'location-analyst', to: 'competitor-benchmarker', trigger: 'location_data_refreshed', dataPassed: 'Multi-location performance deltas for cross-store benchmarking' },
  ]
}

// ─── #5 Confidence Calibration ──────────────────────────────

export interface CalibrationPoint {
  agentId: string
  agentName: string
  predictionDate: string
  predictedValue: number
  actualValue: number | null
  confidenceScore: number
  accuracyPct: number | null
  category: string
}

export function generateCalibrationHistory(): CalibrationPoint[] {
  return [
    { agentId: 'revenue-forecaster', agentName: 'Revenue Forecaster', predictionDate: '2026-03-01', predictedValue: 52000, actualValue: 54200, confidenceScore: 82, accuracyPct: 96, category: '30-day revenue' },
    { agentId: 'revenue-forecaster', agentName: 'Revenue Forecaster', predictionDate: '2026-02-01', predictedValue: 48000, actualValue: 47100, confidenceScore: 79, accuracyPct: 98, category: '30-day revenue' },
    { agentId: 'margin-optimizer', agentName: 'Margin Optimizer', predictionDate: '2026-03-15', predictedValue: 840, actualValue: 720, confidenceScore: 82, accuracyPct: 86, category: 'price change impact' },
    { agentId: 'peak-hour-optimizer', agentName: 'Peak Hour Optimizer', predictionDate: '2026-03-10', predictedValue: 520, actualValue: 580, confidenceScore: 88, accuracyPct: 90, category: 'staffing ROI' },
    { agentId: 'customer-segmentor', agentName: 'Customer Segmentor', predictionDate: '2026-03-01', predictedValue: 4, actualValue: 3, confidenceScore: 79, accuracyPct: 75, category: 'churn prediction' },
    { agentId: 'product-intelligence', agentName: 'Product Intelligence', predictionDate: '2026-03-20', predictedValue: 380, actualValue: 410, confidenceScore: 78, accuracyPct: 92, category: 'bundle uplift' },
    { agentId: 'inventory-intelligence', agentName: 'Inventory Intelligence', predictionDate: '2026-04-01', predictedValue: 2, actualValue: 2, confidenceScore: 85, accuracyPct: 100, category: 'stockout prediction' },
    { agentId: 'retention-strategist', agentName: 'Retention Strategist', predictionDate: '2026-04-10', predictedValue: 840, actualValue: null, confidenceScore: 79, accuracyPct: null, category: 'winback revenue' },
  ]
}

// ─── #6 Business Type Profiles ──────────────────────────────

export interface BusinessTypeProfile {
  type: string
  label: string
  benchmarks: {
    avgTicketCents: number
    marginPct: number
    peakHours: string
    topCategory: string
    wastePct: number
    staffingRatio: string
  }
  agentThresholds: {
    voidAlertPct: number
    refundAlertPct: number
    revenueDropAlertPct: number
    lowMarginPct: number
    highMarginPct: number
    peakStaffingMin: number
  }
}

export function generateBusinessProfiles(): BusinessTypeProfile[] {
  return [
    {
      type: 'coffee_shop', label: 'Coffee Shop',
      benchmarks: { avgTicketCents: 880, marginPct: 72, peakHours: '7-9AM', topCategory: 'Hot drinks', wastePct: 6, staffingRatio: '1 per $400/hr' },
      agentThresholds: { voidAlertPct: 2, refundAlertPct: 3, revenueDropAlertPct: 15, lowMarginPct: 60, highMarginPct: 80, peakStaffingMin: 3 },
    },
    {
      type: 'restaurant', label: 'Full-Service Restaurant',
      benchmarks: { avgTicketCents: 3200, marginPct: 62, peakHours: '6-9PM', topCategory: 'Entrees', wastePct: 10, staffingRatio: '1 per $600/hr' },
      agentThresholds: { voidAlertPct: 1.5, refundAlertPct: 2, revenueDropAlertPct: 20, lowMarginPct: 55, highMarginPct: 70, peakStaffingMin: 5 },
    },
    {
      type: 'fast_food', label: 'Fast Food',
      benchmarks: { avgTicketCents: 1300, marginPct: 65, peakHours: '11:30AM-1:30PM', topCategory: 'Burgers', wastePct: 8, staffingRatio: '1 per $500/hr' },
      agentThresholds: { voidAlertPct: 1.5, refundAlertPct: 2.5, revenueDropAlertPct: 18, lowMarginPct: 58, highMarginPct: 75, peakStaffingMin: 4 },
    },
    {
      type: 'auto_shop', label: 'Auto Shop',
      benchmarks: { avgTicketCents: 16500, marginPct: 55, peakHours: '10AM-2PM', topCategory: 'Maintenance', wastePct: 3, staffingRatio: '1 per $800/hr' },
      agentThresholds: { voidAlertPct: 1, refundAlertPct: 2, revenueDropAlertPct: 20, lowMarginPct: 40, highMarginPct: 60, peakStaffingMin: 3 },
    },
    {
      type: 'smoke_shop', label: 'Smoke Shop',
      benchmarks: { avgTicketCents: 2200, marginPct: 48, peakHours: '2-6PM', topCategory: 'Vapes', wastePct: 2, staffingRatio: '1 per $600/hr' },
      agentThresholds: { voidAlertPct: 1.5, refundAlertPct: 3, revenueDropAlertPct: 15, lowMarginPct: 35, highMarginPct: 55, peakStaffingMin: 2 },
    },
  ]
}

// ─── Schedule Builder Types & Generators ──────────────────────

export interface ScheduleStaffMember {
  id: string
  name: string
  role: string
  color: string
  hourlyRate: number  // cents
  availability: Record<string, { available: boolean; start: string; end: string }>
}

export interface ScheduleShift {
  id: string
  staffMemberId: string | null
  dayOfWeek: number  // 0=Mon, 6=Sun
  shiftDate: string
  startTime: string  // "07:00"
  endTime: string    // "15:00"
  role: string
  breakMinutes: number
  notes: string
  status: 'draft' | 'published' | 'confirmed'
  isRecommended: boolean
  recommendationReason?: string
  priority?: 'critical' | 'recommended' | 'optional'
}

export interface Holiday {
  date: string
  name: string
  type: 'federal' | 'provincial' | 'observance' | 'retail_peak'
  trafficMultiplier: number
  notes: string
}

const STAFF_COLORS = [
  '#17C5B0', '#1A8FD6', '#E06B5E', '#D4A843', '#9B7FD4', '#4CAF50',
  '#FF7043', '#26C6DA', '#AB47BC', '#78909C', '#EC407A', '#8D6E63',
]

const SCHEDULE_STAFF_BY_TYPE: Record<string, { name: string; role: string }[]> = {
  coffee_shop: [
    { name: 'Alex', role: 'barista' },
    { name: 'Sam', role: 'barista' },
    { name: 'Jordan', role: 'bar_lead' },
    { name: 'Chris', role: 'cashier' },
    { name: 'Taylor', role: 'supervisor' },
  ],
  restaurant: [
    { name: 'Maria', role: 'server' },
    { name: 'James', role: 'server' },
    { name: 'Lin', role: 'bartender' },
    { name: 'Sarah', role: 'host' },
    { name: 'Mike', role: 'kitchen' },
    { name: 'Pat', role: 'runner' },
    { name: 'Dave', role: 'manager' },
  ],
  fast_food: [
    { name: 'Emma', role: 'counter' },
    { name: 'Ryan', role: 'drive_through' },
    { name: 'Kai', role: 'kitchen' },
    { name: 'Lisa', role: 'kitchen' },
    { name: 'Tom', role: 'manager' },
  ],
  auto_shop: [
    { name: 'Mark', role: 'technician' },
    { name: 'Steve', role: 'technician' },
    { name: 'Ana', role: 'technician' },
    { name: 'Bob', role: 'advisor' },
    { name: 'Jenny', role: 'advisor' },
    { name: 'Carl', role: 'parts_counter' },
  ],
  smoke_shop: [
    { name: 'Jesse', role: 'associate' },
    { name: 'Mo', role: 'associate' },
    { name: 'Priya', role: 'shift_lead' },
  ],
}

const BIZ_HOURS: Record<string, { open: number; close: number }> = {
  coffee_shop: { open: 5, close: 21 },
  restaurant: { open: 10, close: 23 },
  fast_food: { open: 5, close: 23 },
  auto_shop: { open: 7, close: 19 },
  smoke_shop: { open: 10, close: 22 },
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : `${n}`
}

function addDays(date: Date, days: number): Date {
  const d = new Date(date)
  d.setDate(d.getDate() + days)
  return d
}

function formatDateISO(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`
}

export function generateScheduleStaff(): ScheduleStaffMember[] {
  const bizType = getActiveBusinessType()
  const roster = SCHEDULE_STAFF_BY_TYPE[bizType] || SCHEDULE_STAFF_BY_TYPE.coffee_shop
  const dayNames = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
  const hours = BIZ_HOURS[bizType] || BIZ_HOURS.coffee_shop

  return roster.map((s, i) => {
    const availability: Record<string, { available: boolean; start: string; end: string }> = {}
    dayNames.forEach((day, di) => {
      // Weekend availability varies; some staff off on weekends
      const available = di < 5 || i % 3 !== 0
      availability[day] = {
        available,
        start: `${pad2(hours.open)}:00`,
        end: `${pad2(hours.close)}:00`,
      }
    })

    const baseRate = bizType === 'auto_shop' ? 2800
      : bizType === 'restaurant' ? 1800
      : bizType === 'coffee_shop' ? 1600
      : bizType === 'fast_food' ? 1400
      : 1500
    // Leads/supervisors/managers get higher rate
    const roleBonus = s.role.includes('lead') || s.role.includes('supervisor') || s.role.includes('manager') ? 400 : 0

    return {
      id: `staff-${i + 1}`,
      name: s.name,
      role: s.role,
      color: STAFF_COLORS[i % STAFF_COLORS.length],
      hourlyRate: baseRate + roleBonus + (i * 50),
      availability,
    }
  })
}

export function generateScheduleShifts(weekStartDate: Date): ScheduleShift[] {
  const bizType = getActiveBusinessType()
  const staff = generateScheduleStaff()
  const hours = BIZ_HOURS[bizType] || BIZ_HOURS.coffee_shop
  const shifts: ScheduleShift[] = []
  let shiftId = 1

  for (let day = 0; day < 7; day++) {
    const shiftDate = addDays(weekStartDate, day)
    const dateStr = formatDateISO(shiftDate)
    const isWeekend = day >= 5

    // Determine staffing: fewer staff on weekends for some biz types
    const staffForDay = isWeekend
      ? staff.filter((_, i) => i % 3 !== 0).slice(0, Math.max(2, staff.length - 1))
      : staff

    staffForDay.forEach((member) => {
      // Create realistic shift patterns: openers and closers
      const staffIdx = staff.indexOf(member)
      const isOpener = staffIdx % 2 === 0
      const openH = hours.open
      const closeH = hours.close
      const midPoint = Math.floor((openH + closeH) / 2)

      const startH = isOpener ? openH : midPoint
      const endH = isOpener ? midPoint + 1 : closeH
      const breakMins = (endH - startH) >= 6 ? 30 : 0

      shifts.push({
        id: `shift-${shiftId++}`,
        staffMemberId: member.id,
        dayOfWeek: day,
        shiftDate: dateStr,
        startTime: `${pad2(startH)}:00`,
        endTime: `${pad2(endH)}:00`,
        role: member.role,
        breakMinutes: breakMins,
        notes: '',
        status: 'draft',
        isRecommended: false,
      })
    })
  }

  return shifts
}

export function generateRecommendedShifts(weekStartDate: Date): ScheduleShift[] {
  const bizType = getActiveBusinessType()
  const hours = BIZ_HOURS[bizType] || BIZ_HOURS.coffee_shop
  const profile = getBusinessProfile(bizType)
  const recommendations: ScheduleShift[] = []

  // Find the peak hour from the hourly pattern
  const peakHour = profile.hourlyPattern.indexOf(Math.max(...profile.hourlyPattern))

  // Recommend extra coverage during peak hours on weekdays
  const peakStart = Math.max(hours.open, peakHour - 1)
  const peakEnd = Math.min(hours.close, peakHour + 2)

  for (let day = 0; day < 5; day++) {
    const shiftDate = addDays(weekStartDate, day)
    recommendations.push({
      id: `rec-${day + 1}`,
      staffMemberId: null,
      dayOfWeek: day,
      shiftDate: formatDateISO(shiftDate),
      startTime: `${pad2(peakStart)}:00`,
      endTime: `${pad2(peakEnd)}:00`,
      role: 'any',
      breakMinutes: 0,
      notes: '',
      status: 'draft',
      isRecommended: true,
      recommendationReason: `Peak hour coverage — ${profile.peakLabel} sees highest transaction volume. Add 1 staff to reduce wait times.`,
      priority: day < 2 ? 'critical' : 'recommended',
    })
  }

  // Weekend recommendation
  const satDate = addDays(weekStartDate, 5)
  recommendations.push({
    id: 'rec-sat',
    staffMemberId: null,
    dayOfWeek: 5,
    shiftDate: formatDateISO(satDate),
    startTime: `${pad2(hours.open + 1)}:00`,
    endTime: `${pad2(hours.open + 5)}:00`,
    role: 'any',
    breakMinutes: 0,
    notes: '',
    status: 'draft',
    isRecommended: true,
    recommendationReason: 'Saturday morning coverage gap detected — current staffing is 1 below optimal based on last 4 weeks of transaction data.',
    priority: 'optional',
  })

  return recommendations
}

export function getHolidaysForWeek(weekStart: Date, country: 'US' | 'CA'): Holiday[] {
  const allHolidays: { date: string; name: string; type: Holiday['type']; mult: number; notes: string; country: string }[] = [
    // US Federal
    { date: '2025-01-01', name: 'New Year\'s Day', type: 'federal', mult: 0.6, notes: '', country: 'US' },
    { date: '2025-01-20', name: 'MLK Day', type: 'federal', mult: 0.8, notes: '', country: 'US' },
    { date: '2025-02-17', name: 'Presidents\' Day', type: 'federal', mult: 0.9, notes: '', country: 'US' },
    { date: '2025-05-26', name: 'Memorial Day', type: 'federal', mult: 0.7, notes: '', country: 'US' },
    { date: '2025-07-04', name: 'Independence Day', type: 'federal', mult: 0.5, notes: '', country: 'US' },
    { date: '2025-09-01', name: 'Labor Day', type: 'federal', mult: 0.7, notes: '', country: 'US' },
    { date: '2025-11-27', name: 'Thanksgiving', type: 'federal', mult: 0.3, notes: '', country: 'US' },
    { date: '2025-12-25', name: 'Christmas Day', type: 'federal', mult: 0.2, notes: '', country: 'US' },
    { date: '2026-01-01', name: 'New Year\'s Day', type: 'federal', mult: 0.6, notes: '', country: 'US' },
    { date: '2026-05-25', name: 'Memorial Day', type: 'federal', mult: 0.7, notes: '', country: 'US' },
    { date: '2026-07-04', name: 'Independence Day', type: 'federal', mult: 0.5, notes: '', country: 'US' },
    { date: '2026-11-26', name: 'Thanksgiving', type: 'federal', mult: 0.3, notes: '', country: 'US' },
    { date: '2026-12-25', name: 'Christmas Day', type: 'federal', mult: 0.2, notes: '', country: 'US' },
    // US Retail Peaks
    { date: '2025-02-14', name: 'Valentine\'s Day', type: 'retail_peak', mult: 1.5, notes: 'Gift & dining surge', country: 'US' },
    { date: '2025-05-11', name: 'Mother\'s Day', type: 'retail_peak', mult: 2.5, notes: 'Highest brunch day', country: 'US' },
    { date: '2025-11-28', name: 'Black Friday', type: 'retail_peak', mult: 2.5, notes: '', country: 'US' },
    { date: '2025-12-24', name: 'Christmas Eve', type: 'retail_peak', mult: 1.8, notes: '', country: 'US' },
    { date: '2025-12-31', name: 'New Year\'s Eve', type: 'retail_peak', mult: 1.8, notes: '', country: 'US' },
    { date: '2026-02-14', name: 'Valentine\'s Day', type: 'retail_peak', mult: 1.5, notes: '', country: 'US' },
    { date: '2026-05-10', name: 'Mother\'s Day', type: 'retail_peak', mult: 2.5, notes: '', country: 'US' },
    { date: '2026-11-27', name: 'Black Friday', type: 'retail_peak', mult: 2.5, notes: '', country: 'US' },
    { date: '2026-12-24', name: 'Christmas Eve', type: 'retail_peak', mult: 1.8, notes: '', country: 'US' },
    { date: '2026-12-31', name: 'New Year\'s Eve', type: 'retail_peak', mult: 1.8, notes: '', country: 'US' },
    // CA Federal
    { date: '2025-01-01', name: 'New Year\'s Day', type: 'federal', mult: 0.6, notes: '', country: 'CA' },
    { date: '2025-04-18', name: 'Good Friday', type: 'federal', mult: 0.5, notes: '', country: 'CA' },
    { date: '2025-05-19', name: 'Victoria Day', type: 'federal', mult: 0.7, notes: '', country: 'CA' },
    { date: '2025-07-01', name: 'Canada Day', type: 'federal', mult: 0.5, notes: '', country: 'CA' },
    { date: '2025-09-01', name: 'Labour Day', type: 'federal', mult: 0.7, notes: '', country: 'CA' },
    { date: '2025-10-13', name: 'Thanksgiving', type: 'federal', mult: 0.4, notes: '2nd Monday Oct', country: 'CA' },
    { date: '2025-12-25', name: 'Christmas Day', type: 'federal', mult: 0.2, notes: '', country: 'CA' },
    { date: '2025-12-26', name: 'Boxing Day', type: 'federal', mult: 2.0, notes: 'Major retail day', country: 'CA' },
    { date: '2026-01-01', name: 'New Year\'s Day', type: 'federal', mult: 0.6, notes: '', country: 'CA' },
    { date: '2026-04-03', name: 'Good Friday', type: 'federal', mult: 0.5, notes: '', country: 'CA' },
    { date: '2026-07-01', name: 'Canada Day', type: 'federal', mult: 0.5, notes: '', country: 'CA' },
    { date: '2026-10-12', name: 'Thanksgiving', type: 'federal', mult: 0.4, notes: '', country: 'CA' },
    { date: '2026-12-25', name: 'Christmas Day', type: 'federal', mult: 0.2, notes: '', country: 'CA' },
    { date: '2026-12-26', name: 'Boxing Day', type: 'federal', mult: 2.0, notes: '', country: 'CA' },
    // CA Provincial
    { date: '2025-02-17', name: 'Family Day', type: 'provincial', mult: 0.8, notes: 'ON/BC/AB/SK', country: 'CA' },
    { date: '2025-06-24', name: 'St-Jean-Baptiste Day', type: 'provincial', mult: 0.6, notes: 'Quebec', country: 'CA' },
    { date: '2025-08-04', name: 'Civic Holiday', type: 'provincial', mult: 0.8, notes: 'ON/BC/AB', country: 'CA' },
    { date: '2026-02-16', name: 'Family Day', type: 'provincial', mult: 0.8, notes: 'ON/BC/AB/SK', country: 'CA' },
    { date: '2026-06-24', name: 'St-Jean-Baptiste Day', type: 'provincial', mult: 0.6, notes: 'Quebec', country: 'CA' },
    { date: '2026-08-03', name: 'Civic Holiday', type: 'provincial', mult: 0.8, notes: 'ON/BC/AB', country: 'CA' },
  ]

  const weekEnd = addDays(weekStart, 6)
  const startStr = formatDateISO(weekStart)
  const endStr = formatDateISO(weekEnd)

  return allHolidays
    .filter(h => h.country === country && h.date >= startStr && h.date <= endStr)
    .map(h => ({
      date: h.date,
      name: h.name,
      type: h.type,
      trafficMultiplier: h.mult,
      notes: h.notes,
    }))
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
