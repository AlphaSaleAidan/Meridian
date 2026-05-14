import { useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

export type Tier = 'trial' | 'starter' | 'growth' | 'enterprise'

function isDemoPath(pathname: string): boolean {
  return pathname.startsWith('/demo') || pathname === '/canada/demo'
}

export function useOrgId(): string {
  const location = useLocation()
  const { org } = useAuth()

  if (isDemoPath(location.pathname)) return 'demo'

  return org?.org_id || import.meta.env.VITE_ORG_ID || 'demo'
}

export function useTier(): Tier {
  const location = useLocation()
  const { org } = useAuth()

  if (isDemoPath(location.pathname)) return 'trial'

  return (org?.plan as Tier) || 'trial'
}

export function useIsDemo(): boolean {
  const location = useLocation()
  return isDemoPath(location.pathname)
}

export const tierLimits = {
  trial:      { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  starter:    { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  growth:     { insightLimit: 999, forecastDays: 30,  moneyLeft: true  },
  enterprise: { insightLimit: 999, forecastDays: 999, moneyLeft: true  },
} as const
