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

  return org?.org_id || import.meta.env.VITE_ORG_ID || ''
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

/**
 * Command-tier check for gating the Multi-Location Hub.
 *
 * The sales `command` plan maps onto the account tier `enterprise`
 * (backend onboarding._PLAN_TIER_MAP), so on the merchant side the Command tier
 * shows as plan === 'enterprise'. This is UI convenience only — the server
 * re-checks the tier on every /api/hub/* call (docs/multi-location-hub-journey.md).
 */
export function useIsCommandTier(): boolean {
  return useTier() === 'enterprise'
}

export const tierLimits = {
  trial:      { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  starter:    { insightLimit: 5,   forecastDays: 7,   moneyLeft: false },
  growth:     { insightLimit: 999, forecastDays: 30,  moneyLeft: true  },
  enterprise: { insightLimit: 999, forecastDays: 999, moneyLeft: true  },
} as const
