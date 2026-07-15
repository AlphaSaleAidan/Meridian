/**
 * Meridian plan tiers — single source of truth for pricing and features.
 *
 * Three tiers (USD). Every tier includes all Meridian features; the axis is
 * the AI phone agent and the per-order Meridian fee:
 *   Standard $250 — everything except the phone agent, no per-order fee
 *   Premium  $350 — phone agent included, $1.49 Meridian fee per order
 *   Command  $500 — phone agent included, $1.00 Meridian fee per order
 *
 * Reps may add up to REP_PRICE_HEADROOM on top of any tier via the price
 * slider — the base prices above are floors, never discounted.
 */

export interface PlanTier {
  id: 'standard' | 'premium' | 'command'
  label: string
  price: number
  interval?: 'month' | 'week'
  tag?: string
  features: string[]
  /** AI phone agent included in this tier. */
  phoneAgent: boolean
  /** Per-order Meridian fee in the plan's currency (0 = no per-order fee). */
  orderFee: number
  /** REDLINE: lowest per-order fee a rep may negotiate down to on the fee
   *  slider (Aidan 2026-07-15: premium $0.65, command $0.45). The backend
   *  clamps to the same floor. */
  orderFeeFloor: number
}

/** Max amount (in the plan's currency) a rep can add on top of a tier's base price. */
export const REP_PRICE_HEADROOM = 100

/** Voice-call overage billing — every call includes the first
 *  VOICE_INCLUDED_MINUTES; each additional (whole) minute bills at
 *  VOICE_OVERAGE_PER_MIN to the merchant's Meridian account. Mirrors the
 *  live backend dials (GET /api/phone/fees); shown wherever pricing is. */
export const VOICE_INCLUDED_MINUTES = 3
export const VOICE_OVERAGE_PER_MIN = 0.45

export const PLAN_TIERS: PlanTier[] = [
  {
    id: 'standard',
    label: 'Standard',
    price: 250,
    interval: 'month',
    phoneAgent: false,
    orderFee: 0,
    orderFeeFloor: 0,
    features: [
      'POS analytics dashboard',
      'Revenue + product insights',
      'Predictive engine (churn, demand)',
      'Menu engineering AI',
      'Camera intelligence',
      'Email alerts + priority support',
    ],
  },
  {
    id: 'premium',
    label: 'Premium',
    price: 350,
    interval: 'month',
    tag: 'MOST POPULAR',
    phoneAgent: true,
    orderFee: 1.49,
    orderFeeFloor: 0.65,
    features: [
      'Everything in Standard',
      'AI phone agent — answers calls + takes orders',
      'Pay-by-text checkout',
      '$1.49 per-order transaction fee',
      'Calls: first 3 min included, then $0.45/min',
    ],
  },
  {
    id: 'command',
    label: 'Command',
    price: 500,
    interval: 'month',
    phoneAgent: true,
    orderFee: 1.0,
    orderFeeFloor: 0.45,
    features: [
      'Everything in Premium',
      'Lowest per-order rate — $1.00 Meridian fee per order',
      'Calls: first 3 min included, then $0.45/min',
      'Multi-location support',
      'Dedicated account manager',
    ],
  },
]

export function getPlan(id: string): PlanTier {
  return PLAN_TIERS.find(p => p.id === id) || PLAN_TIERS[1] // default to Premium
}

/**
 * Closest monthly tier for a custom monthly price. Reps can slide above a
 * tier's base price, so plan labels shown on SLAs/emails/checkout links are
 * derived from the canonical tier prices above rather than hardcoded
 * thresholds.
 */
export function closestMonthlyPlan(monthly: number, tiers: PlanTier[] = PLAN_TIERS): PlanTier {
  const monthlyTiers = tiers.filter(p => (p.interval ?? 'month') === 'month')
  return monthlyTiers.reduce((best, p) =>
    Math.abs(p.price - monthly) < Math.abs(best.price - monthly) ? p : best
  )
}
