import { useLocation } from 'react-router-dom'

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

/** Resolve flags for a route. Canada customer surfaces use the trimmed set. */
export function flagsForPath(pathname: string): ModuleFlags {
  if (pathname.startsWith('/canada')) return canadaModuleFlags
  // US merchant portal + US demo mirror the Canada product exactly (same
  // trimmed pillar set). Legacy surfaces (/app, /us/dashboard) keep the full set.
  if (pathname.startsWith('/us/merchant') || pathname.startsWith('/demo')) return canadaModuleFlags
  return defaultModuleFlags
}

/** Route-aware flags hook for shared components rendered under multiple layouts. */
export function useModuleFlags(): ModuleFlags {
  const { pathname } = useLocation()
  return flagsForPath(pathname)
}
