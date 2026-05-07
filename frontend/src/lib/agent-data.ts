import type { Insight } from './api'
import { getActiveBusinessType } from './demo-context'
import { getIndustryOverrides } from './demo-industries'
import { currencyMultiplier } from './format'

function scaleCents(cents: number): number {
  return Math.round(cents * currencyMultiplier())
}

export interface AgentInfo {
  id: string
  name: string
  status: 'active' | 'idle' | 'running' | 'error'
  lastRun: string
  nextRun: string
  findings: number
  confidence: number
  category: 'analysis' | 'forecasting' | 'optimization' | 'strategy' | 'coordination' | 'vision'
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
    // ─── Camera Intelligence Agents ────────────────────────────
    { id: 'foot-traffic-analyst', name: 'Foot Traffic Analyst', status: 'active', lastRun: minutesAgo(5), nextRun: hoursFromNow(1), findings: 7, confidence: 92, category: 'vision', description: 'Counts entries/exits via YOLO edge detection, correlates with POS transactions for walk-in conversion rates', latestFinding: '312 walk-ins today vs. 118 transactions — 37.8% conversion rate, down 4% from last Tuesday' },
    { id: 'queue-monitor', name: 'Queue Monitor', status: 'active', lastRun: minutesAgo(2), nextRun: minutesAgo(-15), findings: 4, confidence: 89, category: 'vision', description: 'Real-time queue length and wait time estimation using ByteTrack person tracking', latestFinding: 'Avg queue wait hit 6.1 min at 8:15AM — 3 customers abandoned line before ordering' },
    { id: 'heatmap-generator', name: 'Heatmap Generator', status: 'active', lastRun: minutesAgo(10), nextRun: hoursFromNow(1), findings: 3, confidence: 87, category: 'vision', description: 'Builds spatial density heatmaps from camera zones showing customer dwell concentration', latestFinding: 'Front-left zone near pastry case draws 2.4x more dwell than back seating — merchandising opportunity' },
    { id: 'dwell-time-analyzer', name: 'Dwell Time Analyzer', status: 'active', lastRun: minutesAgo(8), nextRun: hoursFromNow(1), findings: 5, confidence: 84, category: 'vision', description: 'Measures how long customers spend in each defined zone, flags lingering and rapid exits', latestFinding: 'Avg dwell in ordering zone: 2.8 min (normal). Menu board zone: 4.1 min — menu complexity causing hesitation' },
    { id: 'demographic-profiler', name: 'Demographic Profiler', status: 'active', lastRun: minutesAgo(15), nextRun: hoursFromNow(2), findings: 3, confidence: 76, category: 'vision', description: 'Anonymous age/gender estimation for audience insights — no PII stored, embeddings auto-purge at 90 days', latestFinding: '68% of morning peak is 25-40 age bracket, weekend shifts younger (18-25). Tailor promos accordingly.' },
    { id: 'conversion-tracker', name: 'Conversion Tracker', status: 'active', lastRun: minutesAgo(5), nextRun: hoursFromNow(1), findings: 6, confidence: 90, category: 'vision', description: 'Correlates foot traffic counts with POS transactions to measure walk-in-to-purchase funnel', latestFinding: 'Conversion rate 41% weekdays vs. 28% weekends — weekend browsers need stronger in-store CTAs' },
    { id: 'zone-performance', name: 'Zone Performance', status: 'active', lastRun: hoursAgo(1), nextRun: hoursFromNow(4), findings: 4, confidence: 83, category: 'vision', description: 'Maps revenue per square foot by zone using LiDAR spatial data and POS attribution', latestFinding: 'Counter zone: $48/sqft/day. Seating zone: $12/sqft/day. Patio: $6/sqft — consider seasonal pop-up at patio' },
    { id: 'occupancy-optimizer', name: 'Occupancy Optimizer', status: 'active', lastRun: minutesAgo(3), nextRun: minutesAgo(-30), findings: 2, confidence: 91, category: 'vision', description: 'Tracks real-time occupancy against max capacity, alerts for fire code compliance and crowding', latestFinding: 'Peak occupancy 87% of capacity at 8:30AM Saturday. Within limits but approaching threshold.' },
    { id: 'customer-flow-mapper', name: 'Customer Flow Mapper', status: 'active', lastRun: minutesAgo(20), nextRun: hoursFromNow(2), findings: 3, confidence: 81, category: 'vision', description: 'Traces anonymized movement paths through store to identify common routes and bottlenecks', latestFinding: 'Door → counter is 73% of paths. Only 18% browse pastry case first — relocate case near entrance?' },
    { id: 'security-sentinel', name: 'Security Sentinel', status: 'active', lastRun: minutesAgo(1), nextRun: minutesAgo(-5), findings: 1, confidence: 88, category: 'vision', description: 'Detects unusual behavior patterns — loitering, after-hours motion, register area anomalies', latestFinding: 'All clear — no anomalous behavior detected in last 24 hours. 2 after-hours motion events were cleaning crew.' },
    { id: 'camera-health-monitor', name: 'Camera Health Monitor', status: 'active', lastRun: minutesAgo(1), nextRun: minutesAgo(-5), findings: 1, confidence: 95, category: 'vision', description: 'Monitors camera uptime, feed quality, edge agent CPU/memory, and network latency', latestFinding: '3/3 cameras online. Edge agent CPU 42%, 1.2GB RAM. Avg inference: 28ms. All feeds nominal.' },
  ]
}

export function generateTopActions(): TopAction[] {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const m = currencyMultiplier()
  if (overrides.topActions.length > 0) {
    return m === 1 ? overrides.topActions : overrides.topActions.map(a => ({ ...a, impactCents: scaleCents(a.impactCents) }))
  }
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
    {
      rank: 4,
      title: 'Relocate pastry case near entrance to capture 2.4x more foot traffic',
      description: 'Camera flow analysis shows only 18% of customers browse the pastry case in its current location. The front-left zone near the case draws 2.4x more dwell time than other zones. Moving the case into the high-traffic path could increase impulse food attachment by 15-20%.',
      expectedImpact: '+$460/month from increased food attach rate',
      impactCents: 46000,
      effort: 'Medium',
      confidence: 81,
      priority: 'High',
      agentSource: 'customer-flow-mapper',
      reasoning: {
        observation: '18% of customers browse pastry case, front-left zone has 2.4x dwell density, food attach rate 22%',
        reasoning: 'If relocating the case into the primary traffic path increases browse rate from 18% to 40%, and 30% of browsers purchase (current rate), that adds ~26 food sales/day at $4.25 avg = $110/day = $3,300/mo. Conservative estimate: $460/mo accounting for cannibalization and adjustment period.',
        conclusion: 'Move pastry display case to front-left zone near entrance. This puts impulse items in the natural customer flow path before they reach the counter.',
        impact: '+$460/month from higher food attachment, improved customer experience with visible fresh items',
        confidence: 81,
        priority: 'High',
        rawData: { current_browse_rate: '18%', target_browse_rate: '40%', dwell_multiplier: '2.4x', avg_food_ticket: '$4.25', daily_foot_traffic: 312 },
        agentId: 'customer-flow-mapper',
        agentName: 'Customer Flow Mapper',
      },
    },
    {
      rank: 5,
      title: 'Add dedicated queue staff during 8-9AM to reduce 6.1 min wait times',
      description: 'Queue Monitor detected avg wait time of 6.1 minutes at 8:15AM peak with 3 line abandonments. Industry benchmark for coffee is under 3 minutes. Each abandonment costs $10.20 avg ticket.',
      expectedImpact: '+$310/month from reduced queue abandonment',
      impactCents: 31000,
      effort: 'Low',
      confidence: 89,
      priority: 'High',
      agentSource: 'queue-monitor',
      reasoning: {
        observation: 'Queue wait 6.1 min at peak, 3 daily abandonments, industry benchmark 3 min',
        reasoning: 'If 3 customers abandon the queue daily at $10.20 avg ticket = $30.60/day lost. Adding an expediter for 1 hour at $18/hr reduces abandonment to ~1. Net gain: $20.40/day x 22 workdays = $449/mo. Conservative: $310/mo.',
        conclusion: 'Station a dedicated queue expediter (order-taker with tablet) during 8-9AM to pre-take orders and reduce perceived wait time.',
        impact: '+$310/month net revenue after labor cost, plus improved customer satisfaction scores',
        confidence: 89,
        priority: 'High',
        rawData: { avg_wait_min: 6.1, daily_abandonments: 3, avg_ticket: '$10.20', labor_cost: '$18/hr', benchmark_wait: '3 min' },
        agentId: 'queue-monitor',
        agentName: 'Queue Monitor',
      },
    },
  ]
}

const RFM_SEGMENTS_BY_TYPE: Record<string, RFMSegment[]> = {
  coffee_shop: [
    { name: 'Champions', count: 23, percentage: 8, avgSpendCents: 284000, avgFrequency: 18, retentionScore: 96, color: '#17C5B0', description: 'Best customers. High spend, frequent visits, recent activity.' },
    { name: 'Loyal', count: 45, percentage: 15, avgSpendCents: 178000, avgFrequency: 12, retentionScore: 88, color: '#1A8FD6', description: 'Regular customers with consistent spending patterns.' },
    { name: 'Potential Loyalists', count: 38, percentage: 13, avgSpendCents: 95000, avgFrequency: 6, retentionScore: 74, color: '#7C5CFF', description: 'Recent customers with moderate frequency. High conversion potential.' },
    { name: 'Recent Customers', count: 52, percentage: 18, avgSpendCents: 42000, avgFrequency: 2, retentionScore: 62, color: '#4FE3C1', description: 'New customers. Need nurturing to build habit.' },
    { name: 'Promising', count: 34, percentage: 12, avgSpendCents: 68000, avgFrequency: 4, retentionScore: 58, color: '#60A5FA', description: 'Moderate recency and frequency. Respond well to promotions.' },
    { name: 'Needs Attention', count: 28, percentage: 10, avgSpendCents: 124000, avgFrequency: 3, retentionScore: 42, color: '#FBBF24', description: 'Previously good customers showing declining engagement.' },
    { name: 'At Risk', count: 22, percentage: 8, avgSpendCents: 156000, avgFrequency: 1, retentionScore: 28, color: '#F97316', description: 'High-value customers who stopped visiting. Urgent winback needed.' },
    { name: 'Hibernating', count: 32, percentage: 11, avgSpendCents: 52000, avgFrequency: 1, retentionScore: 15, color: '#EF4444', description: 'Long inactive. Low probability of return without intervention.' },
    { name: 'Lost', count: 16, percentage: 5, avgSpendCents: 38000, avgFrequency: 0, retentionScore: 5, color: '#6B7280', description: 'No activity in 90+ days. Consider removing from active targeting.' },
  ],
  restaurant: [
    { name: 'Champions', count: 18, percentage: 7, avgSpendCents: 1024000, avgFrequency: 6, retentionScore: 94, color: '#17C5B0', description: 'Top diners. High spend per cover, frequent reservations.' },
    { name: 'Loyal', count: 35, percentage: 14, avgSpendCents: 480000, avgFrequency: 4, retentionScore: 86, color: '#1A8FD6', description: 'Regular guests with consistent reservation patterns.' },
    { name: 'Potential Loyalists', count: 30, percentage: 12, avgSpendCents: 220000, avgFrequency: 2, retentionScore: 72, color: '#7C5CFF', description: 'Recent diners who could become regulars with engagement.' },
    { name: 'Recent Customers', count: 48, percentage: 19, avgSpendCents: 85000, avgFrequency: 1, retentionScore: 60, color: '#4FE3C1', description: 'First-time or second-time guests. Follow-up opportunity.' },
    { name: 'Promising', count: 28, percentage: 11, avgSpendCents: 145000, avgFrequency: 2, retentionScore: 55, color: '#60A5FA', description: 'Moderate engagement. Respond well to event invitations.' },
    { name: 'Needs Attention', count: 25, percentage: 10, avgSpendCents: 380000, avgFrequency: 1, retentionScore: 40, color: '#FBBF24', description: 'Previously regular diners showing declining visit frequency.' },
    { name: 'At Risk', count: 20, percentage: 8, avgSpendCents: 520000, avgFrequency: 0, retentionScore: 25, color: '#F97316', description: 'High-value guests who have not returned. Personal outreach needed.' },
    { name: 'Hibernating', count: 28, percentage: 11, avgSpendCents: 195000, avgFrequency: 0, retentionScore: 12, color: '#EF4444', description: 'Long inactive. Low probability of return without a compelling offer.' },
    { name: 'Lost', count: 18, percentage: 7, avgSpendCents: 310000, avgFrequency: 0, retentionScore: 4, color: '#6B7280', description: 'No reservation or visit in 120+ days.' },
  ],
  fast_food: [
    { name: 'Champions', count: 28, percentage: 9, avgSpendCents: 88000, avgFrequency: 18, retentionScore: 95, color: '#17C5B0', description: 'Daily regulars. Highest visit frequency and consistent orders.' },
    { name: 'Loyal', count: 52, percentage: 17, avgSpendCents: 55000, avgFrequency: 10, retentionScore: 87, color: '#1A8FD6', description: 'Frequent visitors with predictable order patterns.' },
    { name: 'Potential Loyalists', count: 42, percentage: 14, avgSpendCents: 30000, avgFrequency: 5, retentionScore: 72, color: '#7C5CFF', description: 'Growing visit frequency. App engagement opportunity.' },
    { name: 'Recent Customers', count: 58, percentage: 19, avgSpendCents: 12000, avgFrequency: 2, retentionScore: 60, color: '#4FE3C1', description: 'New visitors. Coupon-driven first visits.' },
    { name: 'Promising', count: 36, percentage: 12, avgSpendCents: 24000, avgFrequency: 4, retentionScore: 56, color: '#60A5FA', description: 'Moderate frequency. Combo deal responsive.' },
    { name: 'Needs Attention', count: 24, percentage: 8, avgSpendCents: 42000, avgFrequency: 2, retentionScore: 38, color: '#FBBF24', description: 'Visit frequency declining. Previously came weekly.' },
    { name: 'At Risk', count: 20, percentage: 7, avgSpendCents: 65000, avgFrequency: 1, retentionScore: 24, color: '#F97316', description: 'Was a regular, now visiting rarely. Competitor risk.' },
    { name: 'Hibernating', count: 26, percentage: 9, avgSpendCents: 28000, avgFrequency: 0, retentionScore: 12, color: '#EF4444', description: 'No visit in 30+ days. App push notification candidate.' },
    { name: 'Lost', count: 14, percentage: 5, avgSpendCents: 22000, avgFrequency: 0, retentionScore: 4, color: '#6B7280', description: 'No activity in 60+ days. Low reactivation probability.' },
  ],
  auto_shop: [
    { name: 'Champions', count: 15, percentage: 8, avgSpendCents: 684000, avgFrequency: 2, retentionScore: 94, color: '#17C5B0', description: 'Top accounts. Multiple vehicles, full-service loyalty.' },
    { name: 'Loyal', count: 28, percentage: 15, avgSpendCents: 280000, avgFrequency: 1, retentionScore: 86, color: '#1A8FD6', description: 'Regular maintenance customers on predictable schedules.' },
    { name: 'Potential Loyalists', count: 22, percentage: 12, avgSpendCents: 120000, avgFrequency: 0.5, retentionScore: 70, color: '#7C5CFF', description: 'Came for one service, could become regulars with follow-up.' },
    { name: 'Recent Customers', count: 35, percentage: 19, avgSpendCents: 45000, avgFrequency: 0.3, retentionScore: 58, color: '#4FE3C1', description: 'First-time visitors. Service reminder follow-up needed.' },
    { name: 'Promising', count: 20, percentage: 11, avgSpendCents: 85000, avgFrequency: 0.5, retentionScore: 52, color: '#60A5FA', description: 'Have returned once. Maintenance reminder opportunity.' },
    { name: 'Needs Attention', count: 18, percentage: 10, avgSpendCents: 210000, avgFrequency: 0.3, retentionScore: 38, color: '#FBBF24', description: 'Overdue for service. Were previously on schedule.' },
    { name: 'At Risk', count: 14, percentage: 8, avgSpendCents: 340000, avgFrequency: 0, retentionScore: 22, color: '#F97316', description: 'High-value accounts that missed their service interval.' },
    { name: 'Hibernating', count: 18, percentage: 10, avgSpendCents: 140000, avgFrequency: 0, retentionScore: 10, color: '#EF4444', description: 'No visit in 6+ months. May have switched shops.' },
    { name: 'Lost', count: 12, percentage: 7, avgSpendCents: 210000, avgFrequency: 0, retentionScore: 3, color: '#6B7280', description: 'No activity in 12+ months. Likely moved or found another shop.' },
  ],
  smoke_shop: [
    { name: 'Champions', count: 20, percentage: 8, avgSpendCents: 374000, avgFrequency: 12, retentionScore: 95, color: '#17C5B0', description: 'Top spenders. Weekly carton buyers and premium product collectors.' },
    { name: 'Loyal', count: 42, percentage: 16, avgSpendCents: 172000, avgFrequency: 8, retentionScore: 88, color: '#1A8FD6', description: 'Regular replenishment customers with predictable cycles.' },
    { name: 'Potential Loyalists', count: 32, percentage: 12, avgSpendCents: 54000, avgFrequency: 4, retentionScore: 72, color: '#7C5CFF', description: 'Recent customers building a purchase pattern.' },
    { name: 'Recent Customers', count: 48, percentage: 18, avgSpendCents: 18000, avgFrequency: 2, retentionScore: 60, color: '#4FE3C1', description: 'New walk-ins. Loyalty program enrollment opportunity.' },
    { name: 'Promising', count: 30, percentage: 12, avgSpendCents: 42000, avgFrequency: 3, retentionScore: 55, color: '#60A5FA', description: 'Moderate buyers. Respond to new product introductions.' },
    { name: 'Needs Attention', count: 24, percentage: 9, avgSpendCents: 95000, avgFrequency: 2, retentionScore: 40, color: '#FBBF24', description: 'Previously regular buyers whose visit frequency dropped.' },
    { name: 'At Risk', count: 18, percentage: 7, avgSpendCents: 128000, avgFrequency: 0, retentionScore: 25, color: '#F97316', description: 'Was a weekly buyer, now lapsed 2+ weeks. Competitor or online risk.' },
    { name: 'Hibernating', count: 26, percentage: 10, avgSpendCents: 68000, avgFrequency: 0, retentionScore: 12, color: '#EF4444', description: 'No visit in 30+ days. May have switched brands or stores.' },
    { name: 'Lost', count: 20, percentage: 8, avgSpendCents: 32000, avgFrequency: 0, retentionScore: 4, color: '#6B7280', description: 'No activity in 60+ days. Low reactivation probability.' },
  ],
}

export function generateRFMSegments(): RFMSegment[] {
  const bt = getActiveBusinessType()
  const segments = RFM_SEGMENTS_BY_TYPE[bt] || RFM_SEGMENTS_BY_TYPE.coffee_shop
  const m = currencyMultiplier()
  if (m === 1) return segments
  return segments.map(s => ({ ...s, avgSpendCents: scaleCents(s.avgSpendCents) }))
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

const STAFF_BY_TYPE: Record<string, StaffMember[]> = {
  coffee_shop: [
    { id: '1', name: 'Sarah M.', role: 'Barista Lead', avgTicketCents: 1280, transactionsPerShift: 48, upsellRate: 34, customerRating: 4.9, revenuePerHour: 6800, trend: 'up' },
    { id: '2', name: 'James K.', role: 'Barista', avgTicketCents: 1150, transactionsPerShift: 42, upsellRate: 28, customerRating: 4.7, revenuePerHour: 5600, trend: 'up' },
    { id: '3', name: 'Maria L.', role: 'Barista', avgTicketCents: 1080, transactionsPerShift: 45, upsellRate: 22, customerRating: 4.8, revenuePerHour: 5400, trend: 'stable' },
    { id: '4', name: 'Alex T.', role: 'Barista', avgTicketCents: 980, transactionsPerShift: 38, upsellRate: 18, customerRating: 4.5, revenuePerHour: 4200, trend: 'down' },
    { id: '5', name: 'Priya S.', role: 'Cashier', avgTicketCents: 920, transactionsPerShift: 52, upsellRate: 12, customerRating: 4.6, revenuePerHour: 4800, trend: 'stable' },
    { id: '6', name: 'Tom B.', role: 'Barista (New)', avgTicketCents: 860, transactionsPerShift: 32, upsellRate: 8, customerRating: 4.3, revenuePerHour: 3200, trend: 'up' },
  ],
  restaurant: [
    { id: '1', name: 'Marcus R.', role: 'Server Lead', avgTicketCents: 5200, transactionsPerShift: 24, upsellRate: 38, customerRating: 4.9, revenuePerHour: 14800, trend: 'up' },
    { id: '2', name: 'Jennifer W.', role: 'Server', avgTicketCents: 4800, transactionsPerShift: 22, upsellRate: 32, customerRating: 4.8, revenuePerHour: 12800, trend: 'up' },
    { id: '3', name: 'David H.', role: 'Server', avgTicketCents: 4400, transactionsPerShift: 20, upsellRate: 26, customerRating: 4.7, revenuePerHour: 11000, trend: 'stable' },
    { id: '4', name: 'Lisa M.', role: 'Server', avgTicketCents: 4100, transactionsPerShift: 18, upsellRate: 20, customerRating: 4.5, revenuePerHour: 9200, trend: 'down' },
    { id: '5', name: 'Chris P.', role: 'Bartender', avgTicketCents: 3800, transactionsPerShift: 32, upsellRate: 42, customerRating: 4.8, revenuePerHour: 16500, trend: 'up' },
    { id: '6', name: 'Ana G.', role: 'Host', avgTicketCents: 0, transactionsPerShift: 45, upsellRate: 0, customerRating: 4.6, revenuePerHour: 0, trend: 'stable' },
  ],
  fast_food: [
    { id: '1', name: 'Mike T.', role: 'Shift Manager', avgTicketCents: 1150, transactionsPerShift: 85, upsellRate: 28, customerRating: 4.7, revenuePerHour: 12200, trend: 'up' },
    { id: '2', name: 'Jessica R.', role: 'Front Counter', avgTicketCents: 1080, transactionsPerShift: 78, upsellRate: 24, customerRating: 4.5, revenuePerHour: 10500, trend: 'stable' },
    { id: '3', name: 'Carlos M.', role: 'Drive-Through', avgTicketCents: 1120, transactionsPerShift: 92, upsellRate: 22, customerRating: 4.4, revenuePerHour: 12800, trend: 'up' },
    { id: '4', name: 'Brandon K.', role: 'Kitchen Lead', avgTicketCents: 0, transactionsPerShift: 90, upsellRate: 0, customerRating: 4.6, revenuePerHour: 0, trend: 'stable' },
    { id: '5', name: 'Aisha N.', role: 'Front Counter', avgTicketCents: 1020, transactionsPerShift: 72, upsellRate: 18, customerRating: 4.3, revenuePerHour: 9200, trend: 'down' },
    { id: '6', name: 'Tyler H.', role: 'Drive-Through (New)', avgTicketCents: 1000, transactionsPerShift: 65, upsellRate: 14, customerRating: 4.2, revenuePerHour: 8100, trend: 'up' },
  ],
  auto_shop: [
    { id: '1', name: 'Mike C.', role: 'Senior Technician', avgTicketCents: 24500, transactionsPerShift: 6, upsellRate: 38, customerRating: 4.9, revenuePerHour: 18400, trend: 'up' },
    { id: '2', name: 'Sarah K.', role: 'Service Advisor', avgTicketCents: 19800, transactionsPerShift: 14, upsellRate: 34, customerRating: 4.7, revenuePerHour: 16500, trend: 'up' },
    { id: '3', name: 'James W.', role: 'Technician', avgTicketCents: 18500, transactionsPerShift: 5, upsellRate: 28, customerRating: 4.6, revenuePerHour: 14200, trend: 'stable' },
    { id: '4', name: 'David R.', role: 'Technician', avgTicketCents: 17200, transactionsPerShift: 4, upsellRate: 22, customerRating: 4.5, revenuePerHour: 10800, trend: 'down' },
    { id: '5', name: 'Lisa P.', role: 'Parts Counter', avgTicketCents: 8500, transactionsPerShift: 28, upsellRate: 18, customerRating: 4.4, revenuePerHour: 7800, trend: 'stable' },
    { id: '6', name: 'Tom M.', role: 'Technician (New)', avgTicketCents: 15600, transactionsPerShift: 3, upsellRate: 12, customerRating: 4.3, revenuePerHour: 6500, trend: 'up' },
  ],
  smoke_shop: [
    { id: '1', name: 'Daniel K.', role: 'Store Manager', avgTicketCents: 3400, transactionsPerShift: 42, upsellRate: 32, customerRating: 4.8, revenuePerHour: 8900, trend: 'up' },
    { id: '2', name: 'Maria V.', role: 'Shift Lead', avgTicketCents: 3000, transactionsPerShift: 40, upsellRate: 28, customerRating: 4.7, revenuePerHour: 7800, trend: 'stable' },
    { id: '3', name: 'Samantha R.', role: 'Sales Associate', avgTicketCents: 2800, transactionsPerShift: 38, upsellRate: 26, customerRating: 4.6, revenuePerHour: 7200, trend: 'stable' },
    { id: '4', name: 'Jason T.', role: 'Sales Associate', avgTicketCents: 2600, transactionsPerShift: 35, upsellRate: 22, customerRating: 4.5, revenuePerHour: 6400, trend: 'up' },
    { id: '5', name: 'Kim L.', role: 'Sales Associate', avgTicketCents: 2500, transactionsPerShift: 33, upsellRate: 18, customerRating: 4.4, revenuePerHour: 5600, trend: 'down' },
    { id: '6', name: 'Alex P.', role: 'Sales Associate (New)', avgTicketCents: 2400, transactionsPerShift: 30, upsellRate: 14, customerRating: 4.3, revenuePerHour: 4800, trend: 'up' },
  ],
}

export function generateStaffPerformance(): StaffMember[] {
  const bt = getActiveBusinessType()
  const staff = STAFF_BY_TYPE[bt] || STAFF_BY_TYPE.coffee_shop
  const m = currencyMultiplier()
  if (m === 1) return staff
  return staff.map(s => ({ ...s, avgTicketCents: scaleCents(s.avgTicketCents), revenuePerHour: Math.round(s.revenuePerHour * m) }))
}

export function generatePeakHourHeatmap(): PeakHourCell[] {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const m = currencyMultiplier()
  if (overrides.peakHourHeatmap.length > 0) {
    return m === 1 ? overrides.peakHourHeatmap : overrides.peakHourHeatmap.map(c => ({ ...c, revenue: Math.round(c.revenue * m) }))
  }
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
  const bt = getActiveBusinessType()
  const overrides = getIndustryOverrides(bt)
  return overrides.marginItems.map(m =>
    calcMarginItem(m.name, m.category, scaleCents(m.sellingPriceCents), m.monthlySales,
      m.ingredients.map(i => ({ ...i, batchCostCents: scaleCents(i.batchCostCents) })),
      scaleCents(m.externalLeakageCents))
  )
}

function _daysAgo(d: number): string {
  const dt = new Date()
  dt.setDate(dt.getDate() - d)
  return dt.toISOString()
}

const CUSTOMERS_BY_TYPE: Record<string, CustomerProfile[]> = {
  coffee_shop: [
    { id: 'c1', name: 'Rachel M.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1580, totalSpentCents: 284400, visitsPerMonth: 18, lastVisit: _daysAgo(1), daysSinceVisit: 1, topItem: 'Iced Latte + Avocado Toast', retentionRisk: 'low' },
    { id: 'c2', name: 'David K.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1420, totalSpentCents: 255600, visitsPerMonth: 16, lastVisit: _daysAgo(1), daysSinceVisit: 1, topItem: 'Cold Brew + Croissant', retentionRisk: 'low' },
    { id: 'c3', name: 'Michael B.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1680, totalSpentCents: 302400, visitsPerMonth: 20, lastVisit: _daysAgo(0), daysSinceVisit: 0, topItem: 'Matcha Latte + Breakfast Sandwich', retentionRisk: 'low' },
    { id: 'c4', name: 'Sarah T.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1250, totalSpentCents: 150000, visitsPerMonth: 12, lastVisit: _daysAgo(2), daysSinceVisit: 2, topItem: 'Cappuccino + Blueberry Muffin', retentionRisk: 'low' },
    { id: 'c5', name: 'Lisa W.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1180, totalSpentCents: 141600, visitsPerMonth: 10, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: 'Espresso + Croissant', retentionRisk: 'low' },
    { id: 'c6', name: 'James P.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 980, totalSpentCents: 117600, visitsPerMonth: 8, lastVisit: _daysAgo(4), daysSinceVisit: 4, topItem: 'Drip Coffee x2', retentionRisk: 'low' },
    { id: 'c7', name: 'Amanda R.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 1340, totalSpentCents: 80400, visitsPerMonth: 6, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Iced Latte + Avocado Toast', retentionRisk: 'low' },
    { id: 'c8', name: 'Chris H.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 890, totalSpentCents: 53400, visitsPerMonth: 5, lastVisit: _daysAgo(6), daysSinceVisit: 6, topItem: 'Cappuccino', retentionRisk: 'medium' },
    { id: 'c9', name: 'Jennifer C.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 650, totalSpentCents: 13000, visitsPerMonth: 2, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: 'Cappuccino', retentionRisk: 'medium' },
    { id: 'c10', name: 'Karen A.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 480, totalSpentCents: 9600, visitsPerMonth: 2, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Drip Coffee', retentionRisk: 'medium' },
    { id: 'c11', name: 'Emily S.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 720, totalSpentCents: 28800, visitsPerMonth: 4, lastVisit: _daysAgo(7), daysSinceVisit: 7, topItem: 'Drip Coffee + Muffin', retentionRisk: 'low' },
    { id: 'c12', name: 'Nicole F.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 1560, totalSpentCents: 46800, visitsPerMonth: 3, lastVisit: _daysAgo(14), daysSinceVisit: 14, topItem: 'Matcha Latte + Avocado Toast', retentionRisk: 'medium' },
    { id: 'c13', name: 'Robert G.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 1450, totalSpentCents: 174000, visitsPerMonth: 1, lastVisit: _daysAgo(28), daysSinceVisit: 28, topItem: 'Cold Brew + Breakfast Sandwich', retentionRisk: 'high' },
    { id: 'c14', name: 'Brian N.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 980, totalSpentCents: 58800, visitsPerMonth: 0, lastVisit: _daysAgo(62), daysSinceVisit: 62, topItem: 'Espresso + Croissant', retentionRisk: 'high' },
    { id: 'c15', name: 'Tom L.', segment: 'Lost', segmentColor: '#6B7280', avgOrderCents: 1320, totalSpentCents: 158400, visitsPerMonth: 0, lastVisit: _daysAgo(95), daysSinceVisit: 95, topItem: 'Iced Latte + Croissant', retentionRisk: 'high' },
  ],
  restaurant: [
    { id: 'c1', name: 'Richard & Claire W.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 12800, totalSpentCents: 1024000, visitsPerMonth: 8, lastVisit: _daysAgo(1), daysSinceVisit: 1, topItem: 'Ribeye + House Wine', retentionRisk: 'low' },
    { id: 'c2', name: 'The Morrison Party', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 18500, totalSpentCents: 740000, visitsPerMonth: 4, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: 'Grilled Salmon + Cocktails', retentionRisk: 'low' },
    { id: 'c3', name: 'Katherine D.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 8400, totalSpentCents: 504000, visitsPerMonth: 6, lastVisit: _daysAgo(2), daysSinceVisit: 2, topItem: 'Caesar + Chicken Parm + Wine', retentionRisk: 'low' },
    { id: 'c4', name: 'James & Ellen P.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 9200, totalSpentCents: 368000, visitsPerMonth: 4, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Lobster Bisque + Salmon', retentionRisk: 'low' },
    { id: 'c5', name: 'Tony M.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 6800, totalSpentCents: 272000, visitsPerMonth: 4, lastVisit: _daysAgo(4), daysSinceVisit: 4, topItem: 'Margherita Pizza + Cocktail', retentionRisk: 'low' },
    { id: 'c6', name: 'Susan R.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 7500, totalSpentCents: 225000, visitsPerMonth: 3, lastVisit: _daysAgo(7), daysSinceVisit: 7, topItem: 'Grilled Salmon + Tiramisu', retentionRisk: 'low' },
    { id: 'c7', name: 'Mark & Lisa H.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 10200, totalSpentCents: 122400, visitsPerMonth: 2, lastVisit: _daysAgo(8), daysSinceVisit: 8, topItem: 'Ribeye + Cocktails', retentionRisk: 'low' },
    { id: 'c8', name: 'Diana C.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 5400, totalSpentCents: 64800, visitsPerMonth: 2, lastVisit: _daysAgo(10), daysSinceVisit: 10, topItem: 'Caesar + House Wine', retentionRisk: 'medium' },
    { id: 'c9', name: 'Paul N.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 7200, totalSpentCents: 14400, visitsPerMonth: 1, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Chicken Parm + Beer', retentionRisk: 'medium' },
    { id: 'c10', name: 'The Garcia Table', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 22000, totalSpentCents: 22000, visitsPerMonth: 1, lastVisit: _daysAgo(6), daysSinceVisit: 6, topItem: 'Party of 6 — mixed entrees', retentionRisk: 'medium' },
    { id: 'c11', name: 'Andrea B.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 4800, totalSpentCents: 48000, visitsPerMonth: 2, lastVisit: _daysAgo(12), daysSinceVisit: 12, topItem: 'Pizza + Sparkling Water', retentionRisk: 'low' },
    { id: 'c12', name: 'Robert & May K.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 14200, totalSpentCents: 284000, visitsPerMonth: 1, lastVisit: _daysAgo(21), daysSinceVisit: 21, topItem: 'Ribeye + Lobster Bisque + Wine', retentionRisk: 'medium' },
    { id: 'c13', name: 'Christine T.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 8800, totalSpentCents: 352000, visitsPerMonth: 0, lastVisit: _daysAgo(42), daysSinceVisit: 42, topItem: 'Salmon + Cocktails', retentionRisk: 'high' },
    { id: 'c14', name: 'David L.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 6200, totalSpentCents: 186000, visitsPerMonth: 0, lastVisit: _daysAgo(68), daysSinceVisit: 68, topItem: 'Pizza + Beer', retentionRisk: 'high' },
    { id: 'c15', name: 'The Johnson Party', segment: 'Lost', segmentColor: '#6B7280', avgOrderCents: 15800, totalSpentCents: 316000, visitsPerMonth: 0, lastVisit: _daysAgo(110), daysSinceVisit: 110, topItem: 'Regular birthday party group', retentionRisk: 'high' },
  ],
  fast_food: [
    { id: 'c1', name: 'Tyler R.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1480, totalSpentCents: 88800, visitsPerMonth: 18, lastVisit: _daysAgo(0), daysSinceVisit: 0, topItem: 'Double Stack Combo', retentionRisk: 'low' },
    { id: 'c2', name: 'Brandon M.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1250, totalSpentCents: 75000, visitsPerMonth: 16, lastVisit: _daysAgo(1), daysSinceVisit: 1, topItem: 'Combo Meal + Milkshake', retentionRisk: 'low' },
    { id: 'c3', name: 'Jessica L.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 1680, totalSpentCents: 100800, visitsPerMonth: 20, lastVisit: _daysAgo(0), daysSinceVisit: 0, topItem: 'Classic Burger + Fries + Shake', retentionRisk: 'low' },
    { id: 'c4', name: 'Amanda K.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1100, totalSpentCents: 52800, visitsPerMonth: 10, lastVisit: _daysAgo(2), daysSinceVisit: 2, topItem: 'Chicken Tenders + Fries', retentionRisk: 'low' },
    { id: 'c5', name: 'Chris W.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1380, totalSpentCents: 55200, visitsPerMonth: 8, lastVisit: _daysAgo(2), daysSinceVisit: 2, topItem: 'Double Stack + Onion Rings', retentionRisk: 'low' },
    { id: 'c6', name: 'Maria G.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 1850, totalSpentCents: 74000, visitsPerMonth: 8, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: '2x Kids Meal + Combo (family)', retentionRisk: 'low' },
    { id: 'c7', name: 'Derek P.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 1200, totalSpentCents: 36000, visitsPerMonth: 5, lastVisit: _daysAgo(4), daysSinceVisit: 4, topItem: 'Classic Burger + Soda', retentionRisk: 'low' },
    { id: 'c8', name: 'Nicole T.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 980, totalSpentCents: 23520, visitsPerMonth: 4, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Chicken Tenders', retentionRisk: 'medium' },
    { id: 'c9', name: 'Kevin H.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 1100, totalSpentCents: 6600, visitsPerMonth: 2, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: 'Combo Meal', retentionRisk: 'medium' },
    { id: 'c10', name: 'Sarah B.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 750, totalSpentCents: 4500, visitsPerMonth: 2, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Kids Meal', retentionRisk: 'medium' },
    { id: 'c11', name: 'Jason F.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 1050, totalSpentCents: 21000, visitsPerMonth: 4, lastVisit: _daysAgo(4), daysSinceVisit: 4, topItem: 'Classic Burger + Fries', retentionRisk: 'low' },
    { id: 'c12', name: 'Laura D.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 1420, totalSpentCents: 34080, visitsPerMonth: 2, lastVisit: _daysAgo(10), daysSinceVisit: 10, topItem: 'Double Stack Combo', retentionRisk: 'medium' },
    { id: 'c13', name: 'Mike S.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 1280, totalSpentCents: 61440, visitsPerMonth: 1, lastVisit: _daysAgo(18), daysSinceVisit: 18, topItem: 'Combo Meal + Apple Pie', retentionRisk: 'high' },
    { id: 'c14', name: 'Tina R.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 1100, totalSpentCents: 26400, visitsPerMonth: 0, lastVisit: _daysAgo(32), daysSinceVisit: 32, topItem: 'Chicken Tenders + Shake', retentionRisk: 'high' },
    { id: 'c15', name: 'Ryan C.', segment: 'Lost', segmentColor: '#6B7280', avgOrderCents: 900, totalSpentCents: 21600, visitsPerMonth: 0, lastVisit: _daysAgo(55), daysSinceVisit: 55, topItem: 'Classic Burger', retentionRisk: 'high' },
  ],
  auto_shop: [
    { id: 'c1', name: 'Robert M.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 28500, totalSpentCents: 684000, visitsPerMonth: 2, lastVisit: _daysAgo(8), daysSinceVisit: 8, topItem: 'Full service — oil, brakes, tires', retentionRisk: 'low' },
    { id: 'c2', name: 'Jennifer & Paul K.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 18500, totalSpentCents: 444000, visitsPerMonth: 2, lastVisit: _daysAgo(12), daysSinceVisit: 12, topItem: '2 vehicles — regular maintenance', retentionRisk: 'low' },
    { id: 'c3', name: 'David T.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 24200, totalSpentCents: 580800, visitsPerMonth: 2, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Fleet account — 3 trucks', retentionRisk: 'low' },
    { id: 'c4', name: 'Susan L.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 12800, totalSpentCents: 153600, visitsPerMonth: 1, lastVisit: _daysAgo(18), daysSinceVisit: 18, topItem: 'Oil change + tire rotation', retentionRisk: 'low' },
    { id: 'c5', name: 'Mark H.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 15600, totalSpentCents: 187200, visitsPerMonth: 1, lastVisit: _daysAgo(22), daysSinceVisit: 22, topItem: 'Brake service + alignment', retentionRisk: 'low' },
    { id: 'c6', name: 'Lisa & Tom W.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 9800, totalSpentCents: 117600, visitsPerMonth: 1, lastVisit: _daysAgo(28), daysSinceVisit: 28, topItem: 'Regular oil changes — 2 cars', retentionRisk: 'low' },
    { id: 'c7', name: 'Chris B.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 18900, totalSpentCents: 37800, visitsPerMonth: 0.5, lastVisit: _daysAgo(35), daysSinceVisit: 35, topItem: 'AC recharge + diagnostic', retentionRisk: 'low' },
    { id: 'c8', name: 'Amanda G.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 8500, totalSpentCents: 17000, visitsPerMonth: 0.5, lastVisit: _daysAgo(40), daysSinceVisit: 40, topItem: 'Oil change + inspection', retentionRisk: 'medium' },
    { id: 'c9', name: 'Jason R.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 24900, totalSpentCents: 24900, visitsPerMonth: 0.3, lastVisit: _daysAgo(15), daysSinceVisit: 15, topItem: 'Brake pad replacement', retentionRisk: 'medium' },
    { id: 'c10', name: 'Karen P.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 4999, totalSpentCents: 4999, visitsPerMonth: 0.3, lastVisit: _daysAgo(20), daysSinceVisit: 20, topItem: 'First oil change', retentionRisk: 'medium' },
    { id: 'c11', name: 'Brian D.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 14200, totalSpentCents: 56800, visitsPerMonth: 0.5, lastVisit: _daysAgo(45), daysSinceVisit: 45, topItem: 'Transmission + battery service', retentionRisk: 'low' },
    { id: 'c12', name: 'Maria S.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 9200, totalSpentCents: 110400, visitsPerMonth: 0.3, lastVisit: _daysAgo(75), daysSinceVisit: 75, topItem: 'Regular oil changes (overdue)', retentionRisk: 'medium' },
    { id: 'c13', name: 'William F.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 22000, totalSpentCents: 264000, visitsPerMonth: 0, lastVisit: _daysAgo(95), daysSinceVisit: 95, topItem: 'Full service (lapsed)', retentionRisk: 'high' },
    { id: 'c14', name: 'Nancy C.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 8500, totalSpentCents: 102000, visitsPerMonth: 0, lastVisit: _daysAgo(135), daysSinceVisit: 135, topItem: 'Oil + tire rotation (long overdue)', retentionRisk: 'high' },
    { id: 'c15', name: 'Eric J.', segment: 'Lost', segmentColor: '#6B7280', avgOrderCents: 17500, totalSpentCents: 210000, visitsPerMonth: 0, lastVisit: _daysAgo(180), daysSinceVisit: 180, topItem: 'Was regular — may have moved', retentionRisk: 'high' },
  ],
  smoke_shop: [
    { id: 'c1', name: 'Marcus T.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 7800, totalSpentCents: 374400, visitsPerMonth: 12, lastVisit: _daysAgo(1), daysSinceVisit: 1, topItem: 'Carton + Rolling Papers + Lighter', retentionRisk: 'low' },
    { id: 'c2', name: 'Jake W.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 4800, totalSpentCents: 230400, visitsPerMonth: 12, lastVisit: _daysAgo(0), daysSinceVisit: 0, topItem: 'Vape Pods + E-Liquid', retentionRisk: 'low' },
    { id: 'c3', name: 'Ray M.', segment: 'Champion', segmentColor: '#17C5B0', avgOrderCents: 5200, totalSpentCents: 249600, visitsPerMonth: 10, lastVisit: _daysAgo(2), daysSinceVisit: 2, topItem: 'Premium Cigars + Cutter', retentionRisk: 'low' },
    { id: 'c4', name: 'Ashley K.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 3400, totalSpentCents: 108800, visitsPerMonth: 8, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: 'Vape Pods', retentionRisk: 'low' },
    { id: 'c5', name: 'Tony G.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 7200, totalSpentCents: 172800, visitsPerMonth: 6, lastVisit: _daysAgo(4), daysSinceVisit: 4, topItem: 'Carton + CBD Gummies', retentionRisk: 'low' },
    { id: 'c6', name: 'Steve R.', segment: 'Loyal', segmentColor: '#1A8FD6', avgOrderCents: 2800, totalSpentCents: 89600, visitsPerMonth: 8, lastVisit: _daysAgo(3), daysSinceVisit: 3, topItem: 'Rolling Papers + Lighter', retentionRisk: 'low' },
    { id: 'c7', name: 'Megan P.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 4500, totalSpentCents: 54000, visitsPerMonth: 4, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'Glass Pipe + Grinder', retentionRisk: 'low' },
    { id: 'c8', name: 'Derek H.', segment: 'Potential', segmentColor: '#7C5CFF', avgOrderCents: 2600, totalSpentCents: 31200, visitsPerMonth: 4, lastVisit: _daysAgo(6), daysSinceVisit: 6, topItem: 'E-Liquid + Accessories', retentionRisk: 'medium' },
    { id: 'c9', name: 'Chris N.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 3500, totalSpentCents: 7000, visitsPerMonth: 2, lastVisit: _daysAgo(4), daysSinceVisit: 4, topItem: 'Hookah Tobacco + Coals', retentionRisk: 'medium' },
    { id: 'c10', name: 'Alicia B.', segment: 'Recent', segmentColor: '#4FE3C1', avgOrderCents: 1800, totalSpentCents: 3600, visitsPerMonth: 2, lastVisit: _daysAgo(5), daysSinceVisit: 5, topItem: 'CBD Gummies', retentionRisk: 'medium' },
    { id: 'c11', name: 'Juan M.', segment: 'Promising', segmentColor: '#60A5FA', avgOrderCents: 6500, totalSpentCents: 39000, visitsPerMonth: 3, lastVisit: _daysAgo(7), daysSinceVisit: 7, topItem: 'Cigarettes + Vape Pods', retentionRisk: 'low' },
    { id: 'c12', name: 'Linda F.', segment: 'Needs Attention', segmentColor: '#FBBF24', avgOrderCents: 4200, totalSpentCents: 50400, visitsPerMonth: 2, lastVisit: _daysAgo(15), daysSinceVisit: 15, topItem: 'Carton + Lighter Collection', retentionRisk: 'medium' },
    { id: 'c13', name: 'Ryan D.', segment: 'At Risk', segmentColor: '#F97316', avgOrderCents: 3800, totalSpentCents: 91200, visitsPerMonth: 0, lastVisit: _daysAgo(22), daysSinceVisit: 22, topItem: 'Vape Pods (was weekly buyer)', retentionRisk: 'high' },
    { id: 'c14', name: 'Kevin S.', segment: 'Hibernating', segmentColor: '#EF4444', avgOrderCents: 6800, totalSpentCents: 81600, visitsPerMonth: 0, lastVisit: _daysAgo(45), daysSinceVisit: 45, topItem: 'Carton + Papers', retentionRisk: 'high' },
    { id: 'c15', name: 'Tim J.', segment: 'Lost', segmentColor: '#6B7280', avgOrderCents: 2400, totalSpentCents: 28800, visitsPerMonth: 0, lastVisit: _daysAgo(72), daysSinceVisit: 72, topItem: 'Cigarettes', retentionRisk: 'high' },
  ],
}

export function generateCustomerRankings(): CustomerProfile[] {
  const bt = getActiveBusinessType()
  const customers = CUSTOMERS_BY_TYPE[bt] || CUSTOMERS_BY_TYPE.coffee_shop
  const m = currencyMultiplier()
  if (m === 1) return customers
  return customers.map(c => ({ ...c, avgOrderCents: scaleCents(c.avgOrderCents), totalSpentCents: scaleCents(c.totalSpentCents) }))
}

export function generateForecastPeriods(): ForecastPeriod[] {
  const overrides = getIndustryOverrides(getActiveBusinessType())
  const dailyRev = overrides.overview.revenue_cents_30d / 30

  const week = Math.round(dailyRev * 7 * 1.04)
  const month = Math.round(dailyRev * 30 * 1.08)
  const quarter = Math.round(dailyRev * 90 * 1.12)

  return [
    { label: '7-Day', days: 7, predictedCents: scaleCents(week), lowerCents: scaleCents(Math.round(week * 0.85)), upperCents: scaleCents(Math.round(week * 1.15)), confidence: 89, growthPct: 4.2 },
    { label: '30-Day', days: 30, predictedCents: scaleCents(month), lowerCents: scaleCents(Math.round(month * 0.88)), upperCents: scaleCents(Math.round(month * 1.12)), confidence: 82, growthPct: 8.3 },
    { label: '90-Day', days: 90, predictedCents: scaleCents(quarter), lowerCents: scaleCents(Math.round(quarter * 0.86)), upperCents: scaleCents(Math.round(quarter * 1.14)), confidence: 71, growthPct: 12.1 },
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

export interface MenuEngConfig {
  pageTitle: string
  xAxisLabel: string
  yAxisLabel: string
  quadrantLabels: Record<MenuQuadrant, string>
}

const MENU_ENG_CONFIGS: Record<string, MenuEngConfig> = {
  coffee_shop: { pageTitle: 'Menu Matrix', xAxisLabel: 'Popularity', yAxisLabel: 'Contribution Margin', quadrantLabels: { star: 'Stars', plowhorse: 'Plowhorses', puzzle: 'Puzzles', dog: 'Dogs' } },
  restaurant:  { pageTitle: 'Menu Matrix', xAxisLabel: 'Popularity', yAxisLabel: 'Contribution Margin', quadrantLabels: { star: 'Stars', plowhorse: 'Plowhorses', puzzle: 'Puzzles', dog: 'Dogs' } },
  fast_food:   { pageTitle: 'Menu Matrix', xAxisLabel: 'Popularity', yAxisLabel: 'Contribution Margin', quadrantLabels: { star: 'Stars', plowhorse: 'Plowhorses', puzzle: 'Puzzles', dog: 'Dogs' } },
  auto_shop:   { pageTitle: 'Service Matrix', xAxisLabel: 'Job Frequency', yAxisLabel: 'Profit per Job', quadrantLabels: { star: 'Core Services', plowhorse: 'High Volume Low Margin', puzzle: 'High Value Low Volume', dog: 'Review' } },
  smoke_shop:  { pageTitle: 'Product Matrix', xAxisLabel: 'Sales Velocity', yAxisLabel: 'Gross Margin %', quadrantLabels: { star: 'Top Performers', plowhorse: 'High Volume', puzzle: 'Premium', dog: 'Underperformers' } },
}

export function getMenuEngConfig(): MenuEngConfig {
  const bt = getActiveBusinessType()
  return MENU_ENG_CONFIGS[bt] || MENU_ENG_CONFIGS.coffee_shop
}

type MenuEngItemRaw = Omit<MenuEngItem, 'quadrant' | 'popularityIndex' | 'profitabilityIndex' | 'recommendation'>

const MENU_ENG_ITEMS: Record<string, MenuEngItemRaw[]> = {
  coffee_shop: [
    { name: 'Espresso', category: 'drinks', monthlySales: 330, marginPct: 80, revenueCents: 148500, marginCents: 118800 },
    { name: 'Cappuccino', category: 'drinks', monthlySales: 450, marginPct: 75, revenueCents: 236250, marginCents: 177190 },
    { name: 'Iced Latte', category: 'drinks', monthlySales: 340, marginPct: 72, revenueCents: 195500, marginCents: 140760 },
    { name: 'Cold Brew', category: 'drinks', monthlySales: 300, marginPct: 70, revenueCents: 165000, marginCents: 115500 },
    { name: 'Matcha Latte', category: 'drinks', monthlySales: 190, marginPct: 62, revenueCents: 118750, marginCents: 73625 },
    { name: 'Drip Coffee', category: 'drinks', monthlySales: 300, marginPct: 82, revenueCents: 82500, marginCents: 67650 },
    { name: 'Croissant', category: 'food', monthlySales: 360, marginPct: 65, revenueCents: 153000, marginCents: 99450 },
    { name: 'Avocado Toast', category: 'food', monthlySales: 140, marginPct: 55, revenueCents: 125300, marginCents: 68915 },
    { name: 'Breakfast Sandwich', category: 'food', monthlySales: 180, marginPct: 60, revenueCents: 135150, marginCents: 81090 },
    { name: 'Blueberry Muffin', category: 'food', monthlySales: 270, marginPct: 65, revenueCents: 106650, marginCents: 69322 },
  ],
  restaurant: [
    { name: 'Ribeye Steak', category: 'entrees', monthlySales: 180, marginPct: 58, revenueCents: 756000, marginCents: 438480 },
    { name: 'Grilled Salmon', category: 'entrees', monthlySales: 210, marginPct: 64, revenueCents: 588000, marginCents: 376320 },
    { name: 'Caesar Salad', category: 'starters', monthlySales: 250, marginPct: 78, revenueCents: 350000, marginCents: 273000 },
    { name: 'Chicken Parmesan', category: 'entrees', monthlySales: 200, marginPct: 66, revenueCents: 440000, marginCents: 290400 },
    { name: 'Craft Cocktail', category: 'drinks', monthlySales: 280, marginPct: 82, revenueCents: 420000, marginCents: 344400 },
    { name: 'House Wine', category: 'drinks', monthlySales: 230, marginPct: 76, revenueCents: 253000, marginCents: 192280 },
    { name: 'Lobster Bisque', category: 'starters', monthlySales: 140, marginPct: 62, revenueCents: 224000, marginCents: 138880 },
    { name: 'Tiramisu', category: 'desserts', monthlySales: 120, marginPct: 72, revenueCents: 144000, marginCents: 103680 },
    { name: 'Margherita Pizza', category: 'entrees', monthlySales: 160, marginPct: 70, revenueCents: 288000, marginCents: 201600 },
  ],
  fast_food: [
    { name: 'Classic Burger', category: 'burgers', monthlySales: 850, marginPct: 62, revenueCents: 764150, marginCents: 473773 },
    { name: 'Combo Meal', category: 'combos', monthlySales: 650, marginPct: 58, revenueCents: 909350, marginCents: 527423 },
    { name: 'Fries Large', category: 'sides', monthlySales: 780, marginPct: 84, revenueCents: 350220, marginCents: 294185 },
    { name: 'Soda Fountain', category: 'drinks', monthlySales: 900, marginPct: 88, revenueCents: 224100, marginCents: 197208 },
    { name: 'Double Stack', category: 'burgers', monthlySales: 520, marginPct: 60, revenueCents: 597480, marginCents: 358488 },
    { name: 'Chicken Tenders', category: 'sides', monthlySales: 480, marginPct: 65, revenueCents: 383520, marginCents: 249288 },
    { name: 'Milkshake', category: 'drinks', monthlySales: 220, marginPct: 72, revenueCents: 131780, marginCents: 94882 },
    { name: 'Kids Meal', category: 'combos', monthlySales: 280, marginPct: 55, revenueCents: 195720, marginCents: 107646 },
    { name: 'Onion Rings', category: 'sides', monthlySales: 180, marginPct: 78, revenueCents: 98820, marginCents: 77080 },
    { name: 'Apple Pie', category: 'desserts', monthlySales: 150, marginPct: 74, revenueCents: 52350, marginCents: 38739 },
  ],
  auto_shop: [
    { name: 'Oil Change', category: 'maintenance', monthlySales: 420, marginPct: 68, revenueCents: 2099580, marginCents: 1427714 },
    { name: 'Brake Pad Replace', category: 'repair', monthlySales: 110, marginPct: 52, revenueCents: 2739000, marginCents: 1424280 },
    { name: 'Tire Rotation', category: 'maintenance', monthlySales: 280, marginPct: 82, revenueCents: 1119720, marginCents: 918170 },
    { name: 'Full Inspection', category: 'diagnostic', monthlySales: 190, marginPct: 78, revenueCents: 1709810, marginCents: 1333652 },
    { name: 'Engine Diagnostic', category: 'diagnostic', monthlySales: 160, marginPct: 76, revenueCents: 2064000, marginCents: 1568640 },
    { name: 'AC Recharge', category: 'repair', monthlySales: 90, marginPct: 64, revenueCents: 1341000, marginCents: 858240 },
    { name: 'Alignment', category: 'maintenance', monthlySales: 120, marginPct: 74, revenueCents: 1199880, marginCents: 887911 },
    { name: 'Battery Replace', category: 'repair', monthlySales: 85, marginPct: 48, revenueCents: 1606500, marginCents: 771120 },
    { name: 'Transmission Flush', category: 'maintenance', monthlySales: 60, marginPct: 56, revenueCents: 1074000, marginCents: 601440 },
  ],
  smoke_shop: [
    { name: 'Cigarette Carton', category: 'tobacco', monthlySales: 340, marginPct: 22, revenueCents: 2210000, marginCents: 486200 },
    { name: 'Vape Pod Pack', category: 'vape', monthlySales: 380, marginPct: 52, revenueCents: 912000, marginCents: 474240 },
    { name: 'Premium Cigar', category: 'tobacco', monthlySales: 200, marginPct: 48, revenueCents: 360000, marginCents: 172800 },
    { name: 'E-Liquid 60ml', category: 'vape', monthlySales: 250, marginPct: 58, revenueCents: 550000, marginCents: 319000 },
    { name: 'Glass Pipe', category: 'accessories', monthlySales: 80, marginPct: 68, revenueCents: 360000, marginCents: 244800 },
    { name: 'Rolling Papers', category: 'accessories', monthlySales: 420, marginPct: 72, revenueCents: 189000, marginCents: 136080 },
    { name: 'Lighter Collection', category: 'accessories', monthlySales: 350, marginPct: 65, revenueCents: 280000, marginCents: 182000 },
    { name: 'CBD Gummies', category: 'cbd', monthlySales: 110, marginPct: 62, revenueCents: 385000, marginCents: 238700 },
    { name: 'Hookah Tobacco', category: 'tobacco', monthlySales: 70, marginPct: 45, revenueCents: 196000, marginCents: 88200 },
    { name: 'Grinder', category: 'accessories', monthlySales: 95, marginPct: 64, revenueCents: 237500, marginCents: 152000 },
  ],
}

export function generateMenuEngineering(): MenuEngItem[] {
  const bt = getActiveBusinessType()
  const items = MENU_ENG_ITEMS[bt] || MENU_ENG_ITEMS.coffee_shop
  const config = getMenuEngConfig()

  const avgSales = Math.round(items.reduce((s, i) => s + i.monthlySales, 0) / items.length)
  const avgMargin = Math.round(items.reduce((s, i) => s + i.marginPct, 0) / items.length)

  function classify(sales: number, margin: number): MenuQuadrant {
    if (sales >= avgSales && margin >= avgMargin) return 'star'
    if (sales < avgSales && margin >= avgMargin) return 'puzzle'
    if (sales >= avgSales && margin < avgMargin) return 'plowhorse'
    return 'dog'
  }

  const recommendations: Record<MenuQuadrant, string> = {
    star: `${config.quadrantLabels.star} — protect and promote, premium placement, never discount`,
    puzzle: `${config.quadrantLabels.puzzle} — increase visibility, add to bundles, train staff to upsell`,
    plowhorse: `${config.quadrantLabels.plowhorse} — raise price incrementally or reduce cost`,
    dog: `${config.quadrantLabels.dog} — consider removing or completely reinventing`,
  }

  return items.map(item => {
    const q = classify(item.monthlySales, item.marginPct)
    return {
      ...item,
      revenueCents: scaleCents(item.revenueCents),
      marginCents: scaleCents(item.marginCents),
      quadrant: q,
      popularityIndex: Math.round((item.monthlySales / avgSales) * 100),
      profitabilityIndex: Math.round((item.marginPct / avgMargin) * 100),
      recommendation: recommendations[q],
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
}

const ANOMALIES_BY_TYPE: Record<string, Anomaly[]> = {
  coffee_shop: [
    { id: 'a1', type: 'traffic_anomaly', severity: 'critical', title: 'Morning rush lasted 40 min longer Thursday', description: 'Queue extended past the door from 8:10am to 9:50am. Average wait hit 11 minutes. Estimated 14 walkouts at $7.50 avg ticket — $105 lost revenue in one morning.', detectedAt: hoursAgo(2), metric: 'queue_duration_min', expected: 90, actual: 130, deviationPct: 44, agentSource: 'queue-monitor', acknowledged: false },
    { id: 'a2', type: 'cost_spike', severity: 'warning', title: 'Cold brew sold out by 11am Wed and Thu', description: 'Batch prep insufficient for midweek demand. Stockout cost estimated at $340 in lost sales across both days. Increase Wednesday/Thursday batch size by 40%.', detectedAt: hoursAgo(6), metric: 'stockout_hours', expected: 0, actual: 5, deviationPct: 500, agentSource: 'inventory-intelligence', acknowledged: false },
    { id: 'a3', type: 'revenue_drop', severity: 'warning', title: '41 morning regulars not visited in 18+ days', description: 'Above normal churn pattern for this time of month. These customers historically drive $3,200/month. Recommend targeted winback offer before 28-day lapsed threshold.', detectedAt: hoursAgo(8), metric: 'lapsed_regulars', expected: 12, actual: 41, deviationPct: 242, agentSource: 'retention-strategist', acknowledged: false },
    { id: 'a4', type: 'cost_spike', severity: 'warning', title: 'Oat milk usage up 40%', description: 'Oat milk consumption jumped 40% without corresponding sales increase. Possible over-portioning or waste issue.', detectedAt: hoursAgo(12), metric: 'ingredient_usage_oz', expected: 320, actual: 448, deviationPct: 40, agentSource: 'inventory-intelligence', acknowledged: true },
    { id: 'a5', type: 'void_spike', severity: 'warning', title: 'Void transactions 3x normal Tuesday evenings', description: 'Tuesday 6-9PM saw 14 void transactions vs. 4-5 average. Concentrated on Register 2. Possible training issue or policy abuse.', detectedAt: hoursAgo(26), metric: 'void_count', expected: 5, actual: 14, deviationPct: 180, agentSource: 'transaction-analyst', acknowledged: true },
    { id: 'a6', type: 'traffic_anomaly', severity: 'info', title: 'Queue abandonment spike at 8:15AM', description: 'Queue Monitor detected 5 line abandonments between 8:10-8:25AM — 2x the daily average. Wait time peaked at 7.2 minutes.', detectedAt: hoursAgo(4), metric: 'queue_abandonments', expected: 2, actual: 5, deviationPct: 150, agentSource: 'queue-monitor', acknowledged: false },
  ],
  restaurant: [
    { id: 'a1', type: 'revenue_drop', severity: 'critical', title: 'Revenue dropped 22% on Tuesday vs prior Tuesday', description: 'No corresponding drop in foot traffic. Conversion rate fell from 94% to 71%. Possible: server shortage or kitchen delay causing order abandonment.', detectedAt: hoursAgo(2), metric: 'daily_revenue', expected: 234000, actual: 182520, deviationPct: -22, agentSource: 'transaction-analyst', acknowledged: false },
    { id: 'a2', type: 'revenue_drop', severity: 'warning', title: 'Table 12-16 average ticket $18 below floor average', description: 'Zone is staffed but reorder rate is lowest in the restaurant. Server assignment or menu visibility issue in this section.', detectedAt: hoursAgo(5), metric: 'avg_ticket_zone', expected: 4200, actual: 2400, deviationPct: -43, agentSource: 'peak-hour-optimizer', acknowledged: false },
    { id: 'a3', type: 'cost_spike', severity: 'warning', title: 'Dessert attachment rate fell from 31% to 9%', description: 'No menu change this week — likely a service or recommendation issue. Lost dessert revenue estimated at $1,440/month at this rate.', detectedAt: hoursAgo(8), metric: 'dessert_attach_pct', expected: 31, actual: 9, deviationPct: -71, agentSource: 'product-intelligence', acknowledged: false },
    { id: 'a4', type: 'traffic_anomaly', severity: 'info', title: 'Bar revenue up 40% Saturday — nearby event', description: 'Local gallery opening drove walk-in bar traffic. Saturday bar revenue $2,800 vs $2,000 average. Consider partnering with venue for recurring events.', detectedAt: hoursAgo(26), metric: 'bar_revenue', expected: 200000, actual: 280000, deviationPct: 40, agentSource: 'peak-hour-optimizer', acknowledged: true },
    { id: 'a5', type: 'void_spike', severity: 'warning', title: 'Void transactions 2x on Thursday evening', description: '8 voids during dinner service vs 3-4 average. Multiple voids on appetizers suggest kitchen timing issue forcing reorders.', detectedAt: hoursAgo(48), metric: 'void_count', expected: 4, actual: 8, deviationPct: 100, agentSource: 'transaction-analyst', acknowledged: true },
  ],
  fast_food: [
    { id: 'a1', type: 'traffic_anomaly', severity: 'critical', title: 'Drive-through speed spiked to 7.2 min Tuesday 12-1pm', description: 'Nearly double your 3.8-minute target. Order count was normal. Bottleneck appears at payment window — possible POS or staffing issue.', detectedAt: hoursAgo(2), metric: 'drive_thru_speed_min', expected: 3.8, actual: 7.2, deviationPct: 89, agentSource: 'queue-monitor', acknowledged: false },
    { id: 'a2', type: 'revenue_drop', severity: 'warning', title: 'Combo attachment rate dropped to 44%', description: 'Down from 61% last week. No promotion change. Possible POS prompting issue or crew not suggesting combos at order point.', detectedAt: hoursAgo(5), metric: 'combo_attach_pct', expected: 61, actual: 44, deviationPct: -28, agentSource: 'product-intelligence', acknowledged: false },
    { id: 'a3', type: 'traffic_anomaly', severity: 'info', title: 'Seating area occupancy 0% from 2-4pm three days running', description: 'Afternoon daypart revenue is down 18% week over week. All orders are takeout/drive-through after 2pm. Consider reducing dining area HVAC costs during this window.', detectedAt: hoursAgo(8), metric: 'seating_occupancy_pct', expected: 15, actual: 0, deviationPct: -100, agentSource: 'foot-traffic-analyst', acknowledged: true },
    { id: 'a4', type: 'traffic_anomaly', severity: 'info', title: 'Breakfast daypart up 28% since menu change', description: '7-9AM revenue averaging $1,840 vs. $1,437 prior month. New breakfast sandwich driving incremental visits. Consider extending breakfast hours.', detectedAt: hoursAgo(24), metric: 'breakfast_revenue', expected: 143700, actual: 184000, deviationPct: 28, agentSource: 'revenue-forecaster', acknowledged: true },
    { id: 'a5', type: 'refund_surge', severity: 'warning', title: 'Register 3 refund rate 3x other registers', description: 'Register 3 processed 12 refunds this week vs. 3-4 on other registers. Possible training issue or need for register reassignment.', detectedAt: hoursAgo(12), metric: 'refund_count_register', expected: 4, actual: 12, deviationPct: 200, agentSource: 'transaction-analyst', acknowledged: false },
  ],
  auto_shop: [
    { id: 'a1', type: 'revenue_drop', severity: 'critical', title: 'Bay utilization dropped to 54% Tue-Wed', description: 'Significantly below your 85% target. Appointment volume was normal but jobs ran long. Technician efficiency may need review or scheduling adjustment.', detectedAt: hoursAgo(2), metric: 'bay_utilization_pct', expected: 85, actual: 54, deviationPct: -36, agentSource: 'peak-hour-optimizer', acknowledged: false },
    { id: 'a2', type: 'revenue_drop', severity: 'warning', title: 'Average repair order value fell $67 this week', description: 'Advisor upsell capture rate dropped from 34% to 12%. No change in job types — possible training opportunity or advisor engagement issue.', detectedAt: hoursAgo(5), metric: 'avg_ro_cents', expected: 18500, actual: 11800, deviationPct: -36, agentSource: 'staff-performance-analyst', acknowledged: false },
    { id: 'a3', type: 'traffic_anomaly', severity: 'warning', title: 'Customer wait time in lounge exceeded 90 min on 6 visits', description: 'Above the threshold correlated with reduced rebooking rates. Customers waiting over 90 minutes rebook at 40% vs. 72% for under-60-minute waits.', detectedAt: hoursAgo(8), metric: 'lounge_wait_min', expected: 60, actual: 95, deviationPct: 58, agentSource: 'dwell-time-analyzer', acknowledged: false },
    { id: 'a4', type: 'cost_spike', severity: 'warning', title: 'Parts inventory discrepancy: 12 filters unaccounted for', description: 'Oil filter count shows 12 fewer than system records. Possible miscount, unreported use, or shrinkage. Recommend physical audit.', detectedAt: hoursAgo(24), metric: 'parts_variance', expected: 0, actual: 12, deviationPct: 1200, agentSource: 'inventory-intelligence', acknowledged: true },
    { id: 'a5', type: 'traffic_anomaly', severity: 'info', title: 'Saturday morning bookings up 35%', description: 'Overflow risk if trend continues. Saturday 8-10AM slots are 95% booked for next two weeks. Consider extending Saturday hours or adding a technician.', detectedAt: hoursAgo(48), metric: 'booking_count', expected: 14, actual: 19, deviationPct: 35, agentSource: 'peak-hour-optimizer', acknowledged: true },
  ],
  smoke_shop: [
    { id: 'a1', type: 'revenue_drop', severity: 'critical', title: '7 regular customers (4+ visits/week) not returned in 10+ days', description: 'Above normal for your 7-day replenishment cycle. These customers represent ~$1,400/month. Possible competitor opening or product availability issue.', detectedAt: hoursAgo(2), metric: 'lapsed_regulars', expected: 2, actual: 7, deviationPct: 250, agentSource: 'retention-strategist', acknowledged: false },
    { id: 'a2', type: 'traffic_anomaly', severity: 'warning', title: 'Accessory wall dwell time up 34% but conversion stayed at 3%', description: 'Customers are browsing more but buying at the same low rate. Possible pricing confusion or lack of clear value hierarchy on the display wall.', detectedAt: hoursAgo(5), metric: 'accessory_conversion_pct', expected: 3, actual: 3, deviationPct: 0, agentSource: 'dwell-time-analyzer', acknowledged: false },
    { id: 'a3', type: 'revenue_drop', severity: 'warning', title: 'Tuesday 4-7pm revenue 41% below prior Tuesday', description: 'Traffic counts were normal. Conversion dropped sharply — possible staffing or product availability issue during peak after-work window.', detectedAt: hoursAgo(8), metric: 'peak_revenue', expected: 84000, actual: 49560, deviationPct: -41, agentSource: 'peak-hour-optimizer', acknowledged: false },
    { id: 'a4', type: 'cost_spike', severity: 'warning', title: 'CBD inventory approaching expiry on 14 units', description: '14 CBD gummy packages expire within 21 days. Current sell-through rate: 3/week. Recommend markdown or bundle to move inventory before write-off.', detectedAt: hoursAgo(24), metric: 'expiring_units', expected: 0, actual: 14, deviationPct: 1400, agentSource: 'inventory-intelligence', acknowledged: true },
    { id: 'a5', type: 'traffic_anomaly', severity: 'info', title: 'Weekend foot traffic up 22%', description: 'Likely driven by nearby event. Saturday and Sunday traffic averaged 116 vs. 95 normal. Revenue was proportionally up — no conversion issue.', detectedAt: hoursAgo(48), metric: 'weekend_traffic', expected: 95, actual: 116, deviationPct: 22, agentSource: 'foot-traffic-analyst', acknowledged: true },
  ],
}

export function generateAnomalies(): Anomaly[] {
  const bt = getActiveBusinessType()
  return ANOMALIES_BY_TYPE[bt] || ANOMALIES_BY_TYPE.coffee_shop
}

// ─── #3 Cohort Analysis ─────────────────────────────────────

export interface CohortRow {
  cohort: string
  totalCustomers: number
  retentionByMonth: number[]
}

const COHORTS_BY_TYPE: Record<string, CohortRow[]> = {
  coffee_shop: [
    { cohort: 'Jan 2026', totalCustomers: 42, retentionByMonth: [100, 74, 62, 55] },
    { cohort: 'Feb 2026', totalCustomers: 38, retentionByMonth: [100, 71, 58] },
    { cohort: 'Mar 2026', totalCustomers: 51, retentionByMonth: [100, 78] },
    { cohort: 'Apr 2026', totalCustomers: 47, retentionByMonth: [100] },
  ],
  restaurant: [
    { cohort: 'Jan 2026', totalCustomers: 28, retentionByMonth: [100, 68, 54, 46] },
    { cohort: 'Feb 2026', totalCustomers: 32, retentionByMonth: [100, 65, 50] },
    { cohort: 'Mar 2026', totalCustomers: 36, retentionByMonth: [100, 72] },
    { cohort: 'Apr 2026', totalCustomers: 30, retentionByMonth: [100] },
  ],
  fast_food: [
    { cohort: 'Jan 2026', totalCustomers: 68, retentionByMonth: [100, 58, 42, 35] },
    { cohort: 'Feb 2026', totalCustomers: 72, retentionByMonth: [100, 55, 38] },
    { cohort: 'Mar 2026', totalCustomers: 80, retentionByMonth: [100, 62] },
    { cohort: 'Apr 2026', totalCustomers: 75, retentionByMonth: [100] },
  ],
  auto_shop: [
    { cohort: 'Jan 2026', totalCustomers: 18, retentionByMonth: [100, 82, 72, 65] },
    { cohort: 'Feb 2026', totalCustomers: 22, retentionByMonth: [100, 78, 68] },
    { cohort: 'Mar 2026', totalCustomers: 25, retentionByMonth: [100, 84] },
    { cohort: 'Apr 2026', totalCustomers: 20, retentionByMonth: [100] },
  ],
  smoke_shop: [
    { cohort: 'Jan 2026', totalCustomers: 35, retentionByMonth: [100, 70, 58, 48] },
    { cohort: 'Feb 2026', totalCustomers: 40, retentionByMonth: [100, 66, 52] },
    { cohort: 'Mar 2026', totalCustomers: 45, retentionByMonth: [100, 72] },
    { cohort: 'Apr 2026', totalCustomers: 38, retentionByMonth: [100] },
  ],
}

export function generateCohorts(): CohortRow[] {
  const bt = getActiveBusinessType()
  return COHORTS_BY_TYPE[bt] || COHORTS_BY_TYPE.coffee_shop
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
    // ── POS Core Web ──────────────────────────────────────────
    { from: 'transaction-analyst', to: 'product-intelligence', trigger: 'new_transactions_batch', dataPassed: 'Transaction line items + timestamps' },
    { from: 'transaction-analyst', to: 'customer-segmentor', trigger: 'new_transactions_batch', dataPassed: 'Customer IDs + spend amounts' },
    { from: 'product-intelligence', to: 'margin-optimizer', trigger: 'sku_velocity_updated', dataPassed: 'SKU rankings + co-purchase rates' },
    { from: 'margin-optimizer', to: 'revenue-forecaster', trigger: 'pricing_opportunity_found', dataPassed: 'Price change proposals + elasticity data' },
    { from: 'customer-segmentor', to: 'retention-strategist', trigger: 'segments_updated', dataPassed: 'RFM segments + churn risk scores' },
    { from: 'peak-hour-optimizer', to: 'staff-performance-analyst', trigger: 'staffing_gap_detected', dataPassed: 'Peak hours + current schedules' },
    { from: 'inventory-intelligence', to: 'margin-optimizer', trigger: 'cost_anomaly_detected', dataPassed: 'Ingredient cost changes + usage rates' },

    // ── Camera Core Web ─────────────────────────────────────
    { from: 'foot-traffic-analyst', to: 'conversion-tracker', trigger: 'traffic_count_updated', dataPassed: 'Hourly entry/exit counts + timestamps' },
    { from: 'foot-traffic-analyst', to: 'occupancy-optimizer', trigger: 'traffic_count_updated', dataPassed: 'Real-time occupancy deltas' },
    { from: 'heatmap-generator', to: 'zone-performance', trigger: 'heatmap_updated', dataPassed: 'Zone density matrices + dwell concentrations' },
    { from: 'heatmap-generator', to: 'dwell-time-analyzer', trigger: 'heatmap_updated', dataPassed: 'Zone intensity data for dwell correlation' },
    { from: 'dwell-time-analyzer', to: 'customer-flow-mapper', trigger: 'dwell_anomaly_detected', dataPassed: 'Zone dwell times + rapid-exit flags' },
    { from: 'camera-health-monitor', to: 'security-sentinel', trigger: 'feed_status_change', dataPassed: 'Camera uptime + blind-spot alerts' },

    // ── POS × Camera Cross-References ───────────────────────
    // Traffic → POS: every walk-in gets matched against transactions
    { from: 'conversion-tracker', to: 'peak-hour-optimizer', trigger: 'conversion_rate_calculated', dataPassed: 'Walk-in vs. purchase rates by hour' },
    { from: 'conversion-tracker', to: 'transaction-analyst', trigger: 'conversion_gap_detected', dataPassed: 'Hours with high traffic but low sales — POS needs to verify no system issues' },
    { from: 'conversion-tracker', to: 'revenue-forecaster', trigger: 'conversion_trend_shift', dataPassed: 'Rolling conversion rate for revenue model adjustment' },

    // Queue → POS: wait times cross-referenced with ticket values and staff
    { from: 'queue-monitor', to: 'peak-hour-optimizer', trigger: 'queue_threshold_exceeded', dataPassed: 'Queue length + wait time + abandonment count' },
    { from: 'queue-monitor', to: 'staff-performance-analyst', trigger: 'queue_by_register', dataPassed: 'Per-register queue depth — correlate with staff speed' },
    { from: 'queue-monitor', to: 'transaction-analyst', trigger: 'abandonment_event', dataPassed: 'Timestamp + count of line abandonments for lost-revenue calc' },

    // Zones → POS: spatial revenue attribution
    { from: 'zone-performance', to: 'margin-optimizer', trigger: 'zone_revenue_mapped', dataPassed: 'Revenue per sqft per zone + product attribution' },
    { from: 'zone-performance', to: 'product-intelligence', trigger: 'zone_product_correlation', dataPassed: 'Which products sell in which zones — placement optimization' },
    { from: 'zone-performance', to: 'inventory-intelligence', trigger: 'zone_demand_signal', dataPassed: 'Zone-level demand intensity for stock positioning' },

    // Demographics → POS: audience insights enriching customer data
    { from: 'demographic-profiler', to: 'customer-segmentor', trigger: 'demographics_updated', dataPassed: 'Anonymous age/gender distribution by time slot' },
    { from: 'demographic-profiler', to: 'product-intelligence', trigger: 'demographic_preference_shift', dataPassed: 'Product preference by demographic cohort' },
    { from: 'demographic-profiler', to: 'retention-strategist', trigger: 'demographic_churn_signal', dataPassed: 'Demographic segments with declining visit frequency' },

    // Flow → POS: path data enriching product and layout decisions
    { from: 'customer-flow-mapper', to: 'product-intelligence', trigger: 'path_analysis_complete', dataPassed: 'Movement paths + zone visit sequences before purchase' },
    { from: 'customer-flow-mapper', to: 'margin-optimizer', trigger: 'impulse_zone_identified', dataPassed: 'High-traffic zones with low product placement — margin capture opportunity' },

    // POS → Camera: POS data enriching vision analysis
    { from: 'transaction-analyst', to: 'foot-traffic-analyst', trigger: 'hourly_revenue_spike', dataPassed: 'Revenue spikes that need traffic correlation' },
    { from: 'peak-hour-optimizer', to: 'heatmap-generator', trigger: 'peak_window_identified', dataPassed: 'Peak hours for targeted heatmap capture' },
    { from: 'product-intelligence', to: 'zone-performance', trigger: 'high_margin_product_identified', dataPassed: 'Top-margin SKUs for zone placement analysis' },
    { from: 'staff-performance-analyst', to: 'queue-monitor', trigger: 'staff_schedule_updated', dataPassed: 'Shift changes for queue prediction model' },

    // ── Coordination Hub (all paths converge) ───────────────
    { from: 'insight-narrator', to: 'action-prioritizer', trigger: 'all_agents_complete', dataPassed: 'All POS + camera findings merged into unified insight set' },
    { from: 'action-prioritizer', to: 'revenue-forecaster', trigger: 'action_ranked', dataPassed: 'Top actions with camera + POS impact projections' },
    { from: 'revenue-forecaster', to: 'insight-narrator', trigger: 'forecast_updated', dataPassed: 'Updated projections incorporating vision data' },
    { from: 'camera-health-monitor', to: 'insight-narrator', trigger: 'camera_alert', dataPassed: 'Camera status changes + edge agent health' },
    { from: 'security-sentinel', to: 'insight-narrator', trigger: 'security_event', dataPassed: 'Anomalous behavior alerts + severity level' },
    { from: 'occupancy-optimizer', to: 'insight-narrator', trigger: 'capacity_warning', dataPassed: 'Occupancy threshold alerts for operational narrative' },
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
    // Camera Intelligence calibration
    { agentId: 'foot-traffic-analyst', agentName: 'Foot Traffic Analyst', predictionDate: '2026-04-15', predictedValue: 310, actualValue: 318, confidenceScore: 92, accuracyPct: 97, category: 'daily walk-ins' },
    { agentId: 'conversion-tracker', agentName: 'Conversion Tracker', predictionDate: '2026-04-15', predictedValue: 38, actualValue: 36, confidenceScore: 88, accuracyPct: 95, category: 'conversion rate %' },
    { agentId: 'queue-monitor', agentName: 'Queue Monitor', predictionDate: '2026-04-20', predictedValue: 5, actualValue: 6, confidenceScore: 85, accuracyPct: 83, category: 'peak wait time min' },
    { agentId: 'heatmap-generator', agentName: 'Heatmap Generator', predictionDate: '2026-04-22', predictedValue: 240, actualValue: 255, confidenceScore: 84, accuracyPct: 94, category: 'zone dwell index' },
    { agentId: 'occupancy-optimizer', agentName: 'Occupancy Optimizer', predictionDate: '2026-05-01', predictedValue: 85, actualValue: 87, confidenceScore: 91, accuracyPct: 98, category: 'peak occupancy %' },
    { agentId: 'demographic-profiler', agentName: 'Demographic Profiler', predictionDate: '2026-05-01', predictedValue: 65, actualValue: null, confidenceScore: 76, accuracyPct: null, category: 'age bracket %' },
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
      type: 'fast_casual', label: 'Fast Casual',
      benchmarks: { avgTicketCents: 1400, marginPct: 65, peakHours: '11:30AM-1:30PM', topCategory: 'Bowls/Wraps', wastePct: 8, staffingRatio: '1 per $500/hr' },
      agentThresholds: { voidAlertPct: 1.5, refundAlertPct: 2.5, revenueDropAlertPct: 18, lowMarginPct: 58, highMarginPct: 75, peakStaffingMin: 4 },
    },
    {
      type: 'bakery', label: 'Bakery',
      benchmarks: { avgTicketCents: 1100, marginPct: 68, peakHours: '8-11AM', topCategory: 'Pastries', wastePct: 12, staffingRatio: '1 per $350/hr' },
      agentThresholds: { voidAlertPct: 2, refundAlertPct: 3, revenueDropAlertPct: 15, lowMarginPct: 55, highMarginPct: 75, peakStaffingMin: 2 },
    },
    {
      type: 'retail', label: 'Retail Store',
      benchmarks: { avgTicketCents: 2800, marginPct: 45, peakHours: '12-3PM', topCategory: 'Merchandise', wastePct: 2, staffingRatio: '1 per $800/hr' },
      agentThresholds: { voidAlertPct: 1, refundAlertPct: 5, revenueDropAlertPct: 20, lowMarginPct: 35, highMarginPct: 55, peakStaffingMin: 2 },
    },
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
