import { useAuth } from '@/lib/auth'

export type Tier = 'trial' | 'starter' | 'growth' | 'enterprise'

export function useOrgId(): string {
  const { org } = useAuth()
  return org?.org_id || import.meta.env.VITE_ORG_ID || 'demo'
}

export function useTier(): Tier {
  const { org } = useAuth()
  return (org?.plan as Tier) || 'trial'
}

export const tierLimits = {
  trial:      { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  starter:    { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  growth:     { insightLimit: 999, forecastDays: 30,  moneyLeft: true  },
  enterprise: { insightLimit: 999, forecastDays: 999, moneyLeft: true  },
} as const
