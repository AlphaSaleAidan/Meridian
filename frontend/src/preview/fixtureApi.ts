/**
 * The harness's fetch patch.
 *
 * The demo book itself now lives in the product (`lib/demo-bookings.ts`),
 * because /demo and /canada/demo need it too. What stays here is the one part
 * that must NOT ship: monkey-patching window.fetch globally.
 *
 * The product intercepts inside its own API client, scoped to demo paths. The
 * harness cannot do that — it renders arbitrary pages at arbitrary routes — so
 * it takes the blunt approach, and takes it in a file the app is forbidden to
 * import.
 */
import {
  demoBookingsRoute, demoDashboardRoute, resetToNewMerchant,
} from '@/lib/demo-bookings'

export { BASE_LOCATION, configureForTrade, resetToNewMerchant } from '@/lib/demo-bookings'

export function installFixtureApi() {
  if (typeof window !== 'undefined' && window.location.search.includes('wizard')) {
    resetToNewMerchant()
  }

  const real = window.fetch.bind(window)
  window.fetch = async (input: any, init: any = {}) => {
    const raw = typeof input === 'string' ? input : input.url
    const url = new URL(raw, window.location.origin)
    return (await demoDashboardRoute(url))
      ?? (await demoBookingsRoute(url, init))
      ?? real(input, init)
  }
}
