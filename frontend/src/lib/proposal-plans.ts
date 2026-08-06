/**
 * Meridian plan tiers — single source of truth for pricing and features.
 *
 * Three tiers (USD). Every tier includes all Meridian features; the axis is
 * the AI phone agent and the per-order Meridian fee:
 *   Standard $250 — everything except the phone agent, no per-order fee
 *   Premium  $350 — phone agent included, $0.65 Meridian fee per order
 *   Command  $500 — phone agent included, $0.45 Meridian fee per order
 *
 * 2026-08-06 (Aidan): per-order fees adjusted DOWN to the former redlines and
 * FIXED — the rep fee slider is retired, so orderFee === orderFeeFloor.
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
  /** Server-side floor for the per-order fee. The fee slider is retired
   *  (Aidan 2026-08-06) — the tier rate IS the floor; the backend still
   *  clamps any client-sent fee to it. */
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
/** Hard cap — Vapi force-ends every call at this length, so per-call overage
 *  never exceeds (cap − included) × rate = $0.90. */
export const VOICE_MAX_CALL_MINUTES = 5

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
    orderFee: 0.65,
    orderFeeFloor: 0.65,
    features: [
      'Everything in Standard',
      'AI phone agent — answers calls + takes orders',
      'Pay-by-text checkout',
      '$0.65 per-order transaction fee',
      'Calls: first 3 min included, then $0.45/min (calls are capped at 5 min)',
    ],
  },
  {
    id: 'command',
    label: 'Command',
    price: 500,
    interval: 'month',
    phoneAgent: true,
    orderFee: 0.45,
    orderFeeFloor: 0.45,
    features: [
      'Everything in Premium',
      'Lowest per-order rate — $0.45 Meridian fee per order',
      'Calls: first 3 min included, then $0.45/min (calls are capped at 5 min)',
      'Multi-location support',
      'Dedicated account manager',
    ],
  },
]

/**
 * Website Buildout modules (Aidan 2026-08-06): the buildout is sold as
 * modular line items the rep toggles with the owner — each priced, summing
 * to the package total, so the merchant sees exactly what they're buying.
 * One-time modules bill into the setup fee; monthly ones are recurring and
 * listed separately. All one-time modules together = $500 (the package).
 */
export interface WebsiteModule {
  id: string
  label: string
  blurb: string
  price: number
  /** recurring — shown as /mo, never summed into the one-time setup fee */
  monthly?: boolean
  /** the core build — always included, can't be unchecked */
  core?: boolean
}

export const WEBSITE_MODULES: WebsiteModule[] = [
  { id: 'core', label: 'Custom build & launch', blurb: 'Full site designed, built, and launched in 48 hours', price: 250, core: true },
  { id: 'scroll', label: 'Scrolling animation', blurb: 'Scroll-driven motion and reveal effects', price: 75 },
  { id: 'anim3d', label: '3D product animation', blurb: 'Interactive 3D showcase of their product or space', price: 125 },
  { id: 'forms', label: 'Booking & quote form wiring', blurb: 'Forms wired to their email and phone', price: 50 },
  { id: 'maint', label: 'Meridian Maintenance', blurb: 'Content edits, updates, and fixes handled by us', price: 40, monthly: true },
  { id: 'host', label: 'Server hosting', blurb: 'Fast managed hosting with SSL', price: 35, monthly: true },
]

/** The monthly buildout modules (Meridian Maintenance + Server hosting) come
 *  FREE with the second tier and up (Aidan 2026-08-06) — only Standard pays
 *  the monthly. Index-based so future tiers above Premium stay included. */
export function websiteMonthlyFree(planId: string): boolean {
  return PLAN_TIERS.findIndex(p => p.id === planId) >= 1
}

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
