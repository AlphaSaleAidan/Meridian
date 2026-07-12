import { useLocation } from 'react-router-dom'
import { MERCHANT_BASE_PATH, US_MERCHANT_BASE_PATH } from '@/config/merchantPillars'

/**
 * Demo-aware merchant base path. The merchant portal renders at the auth-gated
 * /canada/merchant and /us/merchant, plus the public demos /canada/demo and
 * /demo (US). Nav links must resolve within whichever context the user is in,
 * so demo visitors stay on the demo tree (synthetic data) instead of bouncing
 * to the login gate.
 */
export function useMerchantBasePath(): string {
  const { pathname } = useLocation()
  if (pathname.startsWith('/canada/demo')) return '/canada/demo'
  if (pathname.startsWith('/demo')) return '/demo'
  if (pathname.startsWith(US_MERCHANT_BASE_PATH)) return US_MERCHANT_BASE_PATH
  return MERCHANT_BASE_PATH
}
