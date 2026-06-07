import { useLocation } from 'react-router-dom'
import { MERCHANT_BASE_PATH } from '@/config/merchantPillars'

/**
 * Demo-aware merchant base path. The merchant portal renders both at the
 * auth-gated /canada/merchant and the public /canada/demo. Nav links must
 * resolve within whichever context the user is in, so demo visitors stay on
 * /canada/demo/* (synthetic data) instead of bouncing to the login gate.
 */
export function useMerchantBasePath(): string {
  const { pathname } = useLocation()
  return pathname.startsWith('/canada/demo') ? '/canada/demo' : MERCHANT_BASE_PATH
}
