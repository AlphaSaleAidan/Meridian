import { useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

export type Tier = 'trial' | 'starter' | 'growth' | 'enterprise'

export function useOrgId(): string {
  const location = useLocation()
  const { org } = useAuth()

  // Always use 'demo' on the /demo route regardless of auth state
  if (location.pathname.startsWith('/demo')) return 'demo'

  return org?.org_id || import.meta.env.VITE_ORG_ID || 'demo'
}

export function useTier(): Tier {
  const location = useLocation()
  const { org } = useAuth()

  // Demo route always uses trial tier
  if (location.pathname.startsWith('/demo')) return 'trial'

  return (org?.plan as Tier) || 'trial'
}

export const tierLimits = {
  trial:      { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  starter:    { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  growth:     { insightLimit: 999, forecastDays: 30,  moneyLeft: true  },
  enterprise: { insightLimit: 999, forecastDays: 999, moneyLeft: true  },
} as const
