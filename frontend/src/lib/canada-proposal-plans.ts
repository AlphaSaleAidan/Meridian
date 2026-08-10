/**
 * Canada plans — base USD pricing × 1.4, rounded to the nearest $50, for CAD.
 * Source of truth for USD pricing lives in proposal-plans.ts.
 *
 * Standard US$250 → CA$350 · Premium US$350 → CA$500 · Command US$500 → CA$700
 *
 * Per-order service fees are set explicitly (not formula-derived) so they
 * keep sane price points: Premium CA$0.75/order, Command CA$0.60/order
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
  premium: 0.75,
  command: 0.6,
}

// CAD overrides that deliberately BREAK the x1.4 derivation (Aidan 2026-08-07).
// CA premium is CA$0.75 ALL-IN — the merchant's total per-order cost including
// Stripe's flat 30c, which Meridian absorbs rather than passing through.
// Derivation would say CA$0.90. Mirrors fee_terms.ORDER_FEE_FLOOR_CENTS_CAD_OVERRIDE.
const CAD_ORDER_FEE_FLOOR_OVERRIDE: Partial<Record<PlanTier['id'], number>> = {
  premium: 0.75,
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
  orderFeeFloor: CAD_ORDER_FEE_FLOOR_OVERRIDE[p.id] ?? cadOrderFeeFloor(p.orderFeeFloor),
  features: p.features.map(f =>
    f
      .replace('$0.65 per-order transaction fee', 'CA$0.75 per-order service fee')
      .replace('$0.45 service fee per order', 'CA$0.60 service fee per order')
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
// Custom CRM build is rep-priced per deal, so there is no fixed CAD price to
// convert — the definition and the amount parser are shared verbatim.
export { CUSTOM_CRM_SERVICE, parseSetupServiceAmount } from './proposal-plans'
// Voice-call terms are market-independent: call time is not billed in either
// market (overage retired 2026-08-07), so there is nothing to FX-convert —
// only the shared included-minutes and hard call cap carry over.
export { VOICE_INCLUDED_MINUTES, VOICE_OVERAGE_PER_MIN, VOICE_MAX_CALL_MINUTES } from './proposal-plans'
// "$0 per order" minutes plan — buckets + overage from Aidan's settled card
// (2026-08-09): Premium 600 min / Command 1,000 min per month, CA$0.35/min
// past the bucket, 5-min hard cap unchanged. THE MONTHLY DOES NOT CHANGE —
// the merchant pays the same tier retail; wholesale (CA$175/220, what a
// partner org is charged on the backend) never appears in merchant pricing.
// Do NOT re-derive these numbers — they change only on Aidan's instruction.
// Mirrors backend fee_terms.ZERO_PER_ORDER_TERMS['ca'] — keep in sync.
export type { ZeroPerOrderCard } from './proposal-plans'
export const ZERO_PER_ORDER_CARDS: Partial<Record<PlanTier['id'], import('./proposal-plans').ZeroPerOrderCard>> = {
  premium: { includedMinutes: 600, overagePerMin: 0.35 },
  command: { includedMinutes: 1000, overagePerMin: 0.35 },
}
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
