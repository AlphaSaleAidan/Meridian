import type { Insight } from './api'
import { getActiveBusinessType } from './demo-context'
import { getIndustryOverrides } from './demo-industries'

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
  if (overrides.topActions.length > 0) {
    return overrides.topActions
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
  const overrides = getIndustryOverrides(getActiveBusinessType())
  if (overrides.peakHourHeatmap.length > 0) {
    return overrides.peakHourHeatmap
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
  const avgSales = 290
  const avgMargin = 68

  function classify(sales: number, margin: number): MenuQuadrant {
    if (sales >= avgSales && margin >= avgMargin) return 'star'
    if (sales < avgSales && margin >= avgMargin) return 'puzzle'
    if (sales >= avgSales && margin < avgMargin) return 'plowhorse'
    return 'dog'
  }

  const items: Omit<MenuEngItem, 'quadrant' | 'popularityIndex' | 'profitabilityIndex' | 'recommendation'>[] = [
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
  ]

  const recommendations: Record<MenuQuadrant, string> = {
    star: 'Protect and promote — premium menu placement, never discount',
    puzzle: 'High profit but low sales — increase visibility, add to combos, train staff to upsell',
    plowhorse: 'Popular but low margin — raise price incrementally or reduce portion cost',
    dog: 'Low profit, low popularity — consider removing or completely reinventing',
  }

  return items.map(item => {
    const q = classify(item.monthlySales, item.marginPct)
    return {
      ...item,
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

export function generateAnomalies(): Anomaly[] {
  return [
    { id: 'a1', type: 'void_spike', severity: 'critical', title: 'Void transactions 3x normal', description: 'Tuesday 6-9PM saw 14 void transactions vs. 4-5 average. Concentrated on Register 2. Possible training issue or policy abuse.', detectedAt: minutesAgo(45), metric: 'void_count', expected: 5, actual: 14, deviationPct: 180, agentSource: 'transaction-analyst', acknowledged: false },
    { id: 'a2', type: 'revenue_drop', severity: 'warning', title: 'Morning revenue down 22%', description: 'Revenue between 7-9AM dropped 22% vs. prior 4-week average. Weather was clear, no holidays. Possible competitor event or staffing issue.', detectedAt: hoursAgo(3), metric: 'peak_revenue', expected: 48000, actual: 37440, deviationPct: -22, agentSource: 'peak-hour-optimizer', acknowledged: false },
    { id: 'a3', type: 'cost_spike', severity: 'warning', title: 'Oat milk usage up 40%', description: 'Oat milk consumption jumped 40% without corresponding sales increase. Possible over-portioning or waste issue.', detectedAt: hoursAgo(8), metric: 'ingredient_usage_oz', expected: 320, actual: 448, deviationPct: 40, agentSource: 'inventory-intelligence', acknowledged: true },
    { id: 'a4', type: 'traffic_anomaly', severity: 'info', title: 'Unusual Saturday surge', description: 'Transactions 35% above Saturday average. Nearby event (farmers market) likely driving foot traffic. Consider staffing up for recurring events.', detectedAt: hoursAgo(26), metric: 'transaction_count', expected: 180, actual: 243, deviationPct: 35, agentSource: 'peak-hour-optimizer', acknowledged: true },
    { id: 'a5', type: 'refund_surge', severity: 'warning', title: 'Refund rate doubled this week', description: 'Refund rate hit 4.2% vs. 2.1% trailing average. 6 of 8 refunds were on Breakfast Sandwich — possible quality issue with current batch.', detectedAt: hoursAgo(5), metric: 'refund_rate_pct', expected: 2.1, actual: 4.2, deviationPct: 100, agentSource: 'transaction-analyst', acknowledged: false },
    { id: 'a6', type: 'traffic_anomaly', severity: 'warning', title: 'Walk-in conversion dropped 12% vs. last week', description: 'Foot Traffic Analyst counted 340 entries but only 112 transactions (33% conversion). Same period last week: 38% conversion. Potential cause: nearby construction deterring browse-to-buy.', detectedAt: hoursAgo(2), metric: 'conversion_rate_pct', expected: 38, actual: 33, deviationPct: -13, agentSource: 'conversion-tracker', acknowledged: false },
    { id: 'a7', type: 'traffic_anomaly', severity: 'info', title: 'Queue abandonment spike at 8:15AM', description: 'Queue Monitor detected 5 line abandonments between 8:10-8:25AM — 2x the daily average. Wait time peaked at 7.2 minutes. Consider adding expediter during this window.', detectedAt: hoursAgo(4), metric: 'queue_abandonments', expected: 2, actual: 5, deviationPct: 150, agentSource: 'queue-monitor', acknowledged: false },
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
