/**
 * Meridian plan tiers — single source of truth for pricing and features.
 */

export interface PlanTier {
  id: 'standard' | 'premium' | 'command'
  label: string
  price: number
  tag?: string
  features: string[]
}

export const PLAN_TIERS: PlanTier[] = [
  {
    id: 'standard',
    label: 'Standard',
    price: 250,
    features: [
      'POS analytics dashboard',
      'Revenue + product insights',
      'Anomaly detection',
      'Email alerts',
      '1 POS integration',
    ],
  },
  {
    id: 'premium',
    label: 'Premium',
    price: 500,
    tag: 'MOST POPULAR',
    features: [
      'Everything in Standard',
      'Predictive engine (churn, demand)',
      'Menu engineering AI',
      'Staff optimization',
      'Camera intelligence (1 feed)',
      'Priority support',
    ],
  },
  {
    id: 'command',
    label: 'Command',
    price: 1000,
    features: [
      'Everything in Premium',
      'Unlimited camera feeds',
      'Multi-location support',
      'Custom AI models',
      'White-glove onboarding',
      'Dedicated account manager',
    ],
  },
]

export function getPlan(id: string): PlanTier {
  return PLAN_TIERS.find(p => p.id === id) || PLAN_TIERS[0]
}
