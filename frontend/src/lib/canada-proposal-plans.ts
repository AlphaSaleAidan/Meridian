/**
 * Canada plans — base USD pricing × 1.4, rounded to the nearest $50, for CAD.
 * Source of truth for USD pricing lives in proposal-plans.ts.
 *
 * Standard US$250 → CA$350 · Premium US$350 → CA$500 · Command US$500 → CA$700
 *
 * Per-order Meridian fees are set explicitly (not formula-derived) so they
 * keep sane price points: Premium CA$1.99/order, Command CA$1.39/order.
 */
import { PLAN_TIERS as US_PLAN_TIERS, closestMonthlyPlan, type PlanTier } from './proposal-plans'

export const CAD_RATE = 1.4

/** Max CAD amount a rep can add on top of a tier's base price (US$100 × 1.4 → nearest $50). */
export const REP_PRICE_HEADROOM_CAD = 150

export type { PlanTier }

const CAD_ORDER_FEES: Record<PlanTier['id'], number> = {
  standard: 0,
  premium: 1.99,
  command: 1.39,
}

// REDLINES for the rep fee slider — DERIVED from the US floors ($0.65/$0.45)
// via the standard CAD_RATE ×1.4 (Aidan 2026-07-19, supersedes the hand-set
// CA$0.85/CA$0.65): premium CA$0.91, command CA$0.63. One source of truth —
// a future US floor change propagates here automatically. The backend clamps
// to the same cents values (fee_terms.py ORDER_FEE_FLOOR_CENTS['ca']).
function cadOrderFeeFloor(usdFloor: number): number {
  return Math.round(usdFloor * CAD_RATE * 100) / 100
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
      .replace('$1.49 per-order transaction fee', 'CA$1.99 per-order transaction fee')
      .replace('$1.00 Meridian fee per order', 'CA$1.39 Meridian fee per order')
      .replace('then $0.45/min', 'then CA$0.45/min')
  ),
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
