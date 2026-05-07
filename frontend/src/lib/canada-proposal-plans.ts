/**
 * Canada plans — base USD pricing × 1.37 for CAD display.
 * Source of truth for USD pricing lives in proposal-plans.ts.
 */
import { PLAN_TIERS as US_PLAN_TIERS, getPlan as getUsPlan, type PlanTier } from './proposal-plans'

export const CAD_RATE = 1.37

export type { PlanTier }

export const PLAN_TIERS: PlanTier[] = US_PLAN_TIERS.map(p => ({
  ...p,
  price: Math.round(p.price * CAD_RATE),
}))

export function getPlan(id: string): PlanTier {
  return PLAN_TIERS.find(p => p.id === id) || PLAN_TIERS[1]
}

export function toCad(usd: number): number {
  return Math.round(usd * CAD_RATE)
}
