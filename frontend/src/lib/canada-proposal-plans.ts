/**
 * Canada plans — base USD pricing × 1.4, rounded to the nearest $50, for CAD.
 * Source of truth for USD pricing lives in proposal-plans.ts.
 *
 * Standard US$250 → CA$350 · Premium US$350 → CA$500 · Command US$500 → CA$700
 *
 * Per-order Meridian fees are set explicitly (not formula-derived) so they
 * keep sane price points: Premium CA$0.90/order, Command CA$0.60/order
 * (2026-08-06, Aidan: adjusted DOWN to the former redlines and FIXED — the
 * rep fee slider is retired).
 */
import { PLAN_TIERS as US_PLAN_TIERS, closestMonthlyPlan, type PlanTier } from './proposal-plans'

export const CAD_RATE = 1.4

/** Max CAD amount a rep can add on top of a tier's base price (US$100 × 1.4 → nearest $50). */
export const REP_PRICE_HEADROOM_CAD = 150

export type { PlanTier }

const CAD_ORDER_FEES: Record<PlanTier['id'], number> = {
  standard: 0,
  premium: 0.9,
  command: 0.6,
}

// REDLINES for the rep fee slider — DERIVED from the US floors ($0.65/$0.45)
// via CAD_RATE ×1.4, rounded DOWN to the nearest 5¢ (Aidan 2026-07-19,
// supersedes the hand-set CA$0.85/CA$0.65): premium CA$0.90, command CA$0.60.
// One source of truth — a future US floor change propagates here automatically.
// Matches the backend clamp (fee_terms.py ORDER_FEE_FLOOR_CENTS['ca']).
function cadOrderFeeFloor(usdFloor: number): number {
  const cents = Math.floor((usdFloor * CAD_RATE * 100) / 5) * 5
  return cents / 100
}

function roundToNearest50(n: number): number {
  return Math.round(n / 50) * 50
}

export const PLAN_TIERS: PlanTier[] = US_PLAN_TIERS.map(p => ({
  ...p,
  price: roundToNearest50(p.price * CAD_RATE),
  orderFee: CAD_ORDER_FEES[p.id],
  orderFeeFloor: cadOrderFeeFloor(p.orderFeeFloor),
  features: p.features.map(f =>
    f
      .replace('$0.65 per-order transaction fee', 'CA$0.90 per-order transaction fee')
      .replace('$0.45 Meridian fee per order', 'CA$0.60 Meridian fee per order')
      .replace('then $0.45/min', 'then CA$0.45/min')
  ),
}))

// Website Buildout modules in CAD (≈ US × 1.4, kept to clean price points).
// All one-time modules together = CA$700 (the package).
const CAD_MODULE_PRICES: Record<string, number> = {
  core: 350,
  scroll: 105,
  anim3d: 175,
  forms: 70,
  maint: 55,
  host: 50,
}

export type { WebsiteModule } from './proposal-plans'
export { websiteMonthlyFree } from './proposal-plans'
// Voice-call billing dials are identical in CAD (CA$0.45/min — deliberately
// not FX-converted, matches the plan feature copy and backend env).
export { VOICE_INCLUDED_MINUTES, VOICE_OVERAGE_PER_MIN, VOICE_MAX_CALL_MINUTES } from './proposal-plans'
import { WEBSITE_MODULES as US_WEBSITE_MODULES } from './proposal-plans'

export const WEBSITE_MODULES = US_WEBSITE_MODULES.map(m => ({
  ...m,
  price: CAD_MODULE_PRICES[m.id] ?? Math.round(m.price * CAD_RATE),
}))

export function getPlan(id: string): PlanTier {
  return PLAN_TIERS.find(p => p.id === id) || PLAN_TIERS[1]
}

export function toCad(usd: number): number {
  return Math.round(usd * CAD_RATE)
}

/** Closest monthly tier for a custom CAD monthly price (compares against CAD tier prices). */
export function closestMonthlyPlanCad(monthlyCad: number): PlanTier {
  return closestMonthlyPlan(monthlyCad, PLAN_TIERS)
}
