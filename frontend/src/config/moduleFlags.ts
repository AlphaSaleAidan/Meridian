import { useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { packFor } from '@/config/niches'

/**
 * Module feature flags — disable-never-delete switchboard.
 *
 * The Canada customer portal is trimmed to three money pillars (INVENTORY,
 * SCHEDULE, PHONE CALLS) plus CAMERA as a secondary tab. Everything else is
 * disabled here rather than deleted, so the underlying routes/components stay
 * intact and can be re-enabled by flipping a flag.
 *
 * The US merchant portal (/us/merchant) and US demo (/demo) mirror the Canada
 * product, so they share the trimmed set. Legacy surfaces (/app, /us/dashboard)
 * keep their existing behaviour via `defaultModuleFlags`.
 */
export interface ModuleFlags {
  /** Reservations and appointments (migrations/081-083). Off for trades whose
   *  phone is order volume rather than a calendar — a takeout shop shown a
   *  table plan concludes the product was not built for them, correctly. */
  bookings: boolean
  // Money pillars (kept ON for Canada)
  inventory: boolean
  schedule: boolean
  phoneCalls: boolean
  // Secondary tab (kept ON for Canada)
  camera: boolean
  marginHomeTile: boolean
  // Cut / deferred for Canada
  textToOrder: boolean
  spaces3D: boolean
  lakehouse: boolean
  // Disabled extras for Canada
  insights: boolean
  agents: boolean
  topActions: boolean
  taxExpenses: boolean
  customers: boolean
  myWebsite: boolean
  content: boolean
}

/** Everything on — preserves existing behaviour for `/`, `/demo`, US portal. */
export const defaultModuleFlags: ModuleFlags = {
  bookings: true,
  inventory: true,
  schedule: true,
  phoneCalls: true,
  camera: true,
  marginHomeTile: true,
  textToOrder: true,
  spaces3D: true,
  lakehouse: true,
  insights: true,
  agents: true,
  topActions: true,
  taxExpenses: true,
  customers: true,
  // Website Builder is not shippable yet (renders an "Under Construction" wall),
  // so keep it out of the nav until the builder backend is real. Flip back to
  // true when MyWebsitePage is functional.
  myWebsite: false,
  content: true,
}

/** Canada customer portal: 3 money pillars + camera; cut 3D; disable the rest. */
export const canadaModuleFlags: ModuleFlags = {
  bookings: true,
  inventory: true,
  schedule: true,
  phoneCalls: true,
  camera: true,
  marginHomeTile: true,
  textToOrder: false,
  spaces3D: false,
  lakehouse: false,
  insights: false,
  agents: false,
  topActions: false,
  taxExpenses: false,
  customers: false,
  myWebsite: false,
  content: false,
}

/**
 * Resolve flags for a route. Canada customer surfaces use the trimmed set.
 *
 * PATH IS NOW ONLY THE BASE. Which modules a merchant sees is a property of
 * their TRADE, not of the URL they happen to be under — see flagsForMerchant.
 * This stays because it is the correct floor: a portal that trims modules for
 * a market must keep trimming them whatever trade the merchant is in.
 */
export function flagsForPath(pathname: string): ModuleFlags {
  if (pathname.startsWith('/canada')) return canadaModuleFlags
  // US merchant portal + US demo mirror the Canada product exactly (same
  // trimmed pillar set). Legacy surfaces (/app, /us/dashboard) keep the full set.
  if (pathname.startsWith('/us/merchant') || pathname.startsWith('/demo')) return canadaModuleFlags
  return defaultModuleFlags
}

/**
 * Layer the merchant's trade on top of the route's floor.
 *
 * ORDER MATTERS AND IS DELIBERATE: the path decides the base set, then the
 * trade may only turn things OFF within it. A pack cannot switch a module ON
 * that its market has disabled — otherwise a barbershop pack would resurrect
 * a module Canada deliberately cut, and the market trim would silently stop
 * meaning anything.
 */
export function flagsForMerchant(
  pathname: string,
  tradeModules?: Partial<ModuleFlags> | null,
): ModuleFlags {
  const base = flagsForPath(pathname)
  if (!tradeModules) return base
  const out = { ...base }
  for (const [key, wanted] of Object.entries(tradeModules) as [keyof ModuleFlags, boolean][]) {
    // AND, never OR.
    if (wanted === false) out[key] = false
  }
  return out
}

/**
 * Flags for the current route AND the signed-in merchant's trade.
 *
 * A merchant with no trade set — which is every merchant in production today —
 * gets exactly what they got before, because packFor() falls back to a pack
 * that turns nothing off.
 */
export function useModuleFlags(): ModuleFlags {
  const { pathname } = useLocation()
  const { org } = useAuth()
  const pack = packFor(org?.business_type)
  return flagsForMerchant(pathname, pack.modules)
}
