import { useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'

export type Tier = 'trial' | 'starter' | 'growth' | 'enterprise'

function isDemoPath(pathname: string): boolean {
  return pathname.startsWith('/demo') || pathname.startsWith('/canada/demo')
}

export function useOrgId(): string {
  const location = useLocation()
  const { org } = useAuth()

  if (isDemoPath(location.pathname)) return 'demo'

  // Intentionally no VITE_ORG_ID fallback. A baked-in dev org_id leaked into
  // prod builds — any route that mounts the global Layout (admin dashboards,
  // etc.) would fire api.notifications with the stale id and the backend
  // would 500 because no such org exists. Without a real auth context,
  // return '' and let callers skip the call (useUnreadNotifications already
  // guards with `if (!orgId) return`).
  return org?.org_id || ''
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
