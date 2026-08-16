import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import {
  Car, Coffee, Pizza, Sandwich, Scissors, Sparkles, Store, Syringe, Truck,
  UtensilsCrossed, Wrench, type LucideIcon,
} from 'lucide-react'
import { useAuth } from './auth'

export type BusinessType =
  | 'coffee_shop' | 'restaurant' | 'fast_food' | 'auto_shop' | 'smoke_shop'
  // The trades Meridian 2.0 targets. Each has a real profile in
  // business-config.ts — a barbershop demo shows pomade and blades, not
  // croissants, because a prospect reads the wrong products as "not for me".
  | 'barbershop' | 'nails' | 'medspa' | 'detailing' | 'mobile_detailing'
  | 'pizzeria'

export interface BusinessTypeOption {
  id: BusinessType
  label: string
  /** A stroke icon component, never an emoji: a coloured glyph is the one thing
   *  on the opening screen that cannot be themed, and it is the first thing a
   *  prospect sees. */
  icon: LucideIcon
  description: string
  /** Section this sits under in the opening screen. */
  group: 'Food and drink' | 'Appointments' | 'Vehicles' | 'Retail'
}

export const BUSINESS_TYPES: BusinessTypeOption[] = [
  // Food and drink
  { id: 'restaurant', icon: UtensilsCrossed, group: 'Food and drink', label: 'Restaurant', description: 'Full-service dining — covers, table turns, server performance' },
  { id: 'fast_food', icon: Sandwich, group: 'Food and drink', label: 'Quick Service', description: 'Counter and drive-through — order throughput, wait times, queues' },
  { id: 'pizzeria', icon: Pizza, group: 'Food and drink', label: 'Pizza Shop', description: 'Delivery and takeaway — every driver on one map, late drops before they are late' },
  { id: 'coffee_shop', icon: Coffee, group: 'Food and drink', label: 'Coffee Shop', description: 'Cafe and beverage — morning rush, loyalty regulars, menu velocity' },

  // Appointments
  { id: 'barbershop', icon: Scissors, group: 'Appointments', label: 'Barbershop', description: 'Chairs and barbers — the book, no-shows, retail on the shelf' },
  { id: 'nails', icon: Sparkles, group: 'Appointments', label: 'Nail & Lash Studio', description: 'Stations and technicians — rebooking, fills, product burn' },
  { id: 'medspa', icon: Syringe, group: 'Appointments', label: 'Med Spa', description: 'Rooms and providers — consults, deposits, high-value courses' },

  // Vehicles
  { id: 'detailing', icon: Car, group: 'Vehicles', label: 'Auto Detailing', description: 'Bays and detailers — job length, packages, coating margin' },
  { id: 'mobile_detailing', icon: Truck, group: 'Vehicles', label: 'Mobile Detailing', description: 'A van and a route — drive time between jobs, service radius' },
  { id: 'auto_shop', icon: Wrench, group: 'Vehicles', label: 'Auto Shop', description: 'Automotive service — bay utilization, wait times, service upsells' },

  // Retail
  { id: 'smoke_shop', icon: Store, group: 'Retail', label: 'Smoke Shop', description: 'Tobacco and accessories — product zone dwell, repeat customers' },
]

/** The order the sections appear in, so a group cannot be added and silently
 *  not render. */
export const BUSINESS_GROUPS = [
  'Food and drink', 'Appointments', 'Vehicles', 'Retail',
] as const

interface DemoContextValue {
  businessType: BusinessType | null
  setBusinessType: (type: BusinessType) => void
  showSelector: boolean
  openSelector: () => void
  businessLabel: string
}

const DemoContext = createContext<DemoContextValue>({
  businessType: null,
  setBusinessType: () => {},
  showSelector: true,
  openSelector: () => {},
  businessLabel: '',
})

export function useDemoContext() {
  return useContext(DemoContext)
}

const STORAGE_KEY = 'meridian.demo.businessType'
// Derived, not hand-listed: a trade added above but forgotten here would be
// rejected on reload and silently drop the visitor back to the opening screen.
const VALID_TYPES: BusinessType[] = BUSINESS_TYPES.map((b) => b.id)

function readStoredBusinessType(): BusinessType | null {
  if (typeof window === 'undefined') return null
  try {
    const v = window.localStorage.getItem(STORAGE_KEY)
    return v && (VALID_TYPES as string[]).includes(v) ? (v as BusinessType) : null
  } catch {
    return null
  }
}

function writeStoredBusinessType(type: BusinessType): void {
  if (typeof window === 'undefined') return
  try { window.localStorage.setItem(STORAGE_KEY, type) } catch { /* private mode */ }
}

// Module-level state so non-React code (api.ts, demo-data.ts) can read the selection
let _activeBusinessType: BusinessType = readStoredBusinessType() ?? 'restaurant'
export function getActiveBusinessType(): BusinessType { return _activeBusinessType }

/**
 * Set the active trade without a React tree.
 *
 * Exists for tests that walk every trade and read the generated demo copy —
 * the alternative is mounting a provider per trade to assert on strings. Not
 * called by the app: the app sets this through setBusinessType, which also
 * persists the choice and closes the picker.
 */
export function setActiveBusinessTypeForTest(type: BusinessType): void {
  _activeBusinessType = type
}

export function isCanadaPath(): boolean {
  return typeof window !== 'undefined' && window.location.pathname.startsWith('/canada')
}

const CAD_RATE = 1.38
export function getCurrencyMultiplier(): number {
  return isCanadaPath() ? CAD_RATE : 1.0
}

function detectBusinessType(org: { business_type?: string | null; pos_provider?: string | null; business_name?: string }): BusinessType {
  const bt = org.business_type?.toLowerCase() || ''

  // ORDER MATTERS, and these go first.
  //   - "auto detailing" contains "auto", so detailing must beat the auto rule.
  //   - "mobile detailing" contains "detail", so it must beat plain detailing.
  //   - "barbershop" contains "bar", which the restaurant rule below matches —
  //     that is exactly the bug this ordering exists to prevent.
  if (bt.includes('pizza')) return 'pizzeria'
  if (bt.includes('mobile detail') || bt.includes('mobile_detail')) return 'mobile_detailing'
  if (bt.includes('detail')) return 'detailing'
  if (bt.includes('barber') || bt.includes('salon') || bt.includes('haircut')) return 'barbershop'
  if (bt.includes('nail') || bt.includes('lash') || bt.includes('brow')) return 'nails'
  if (bt.includes('med spa') || bt.includes('medspa') || bt.includes('aesthetic')
      || bt.includes('botox') || bt.includes('dermat')) return 'medspa'

  if (bt.includes('coffee') || bt.includes('cafe') || bt.includes('café') || bt.includes('tea') || bt.includes('bakery')) return 'coffee_shop'
  if (bt.includes('fast') || bt.includes('quick') || bt.includes('qsr') || bt.includes('pizza') || bt.includes('burger') || bt.includes('taco')) return 'fast_food'
  if (bt.includes('auto') || bt.includes('mechanic') || bt.includes('garage') || bt.includes('tire') || bt.includes('oil change')) return 'auto_shop'
  if (bt.includes('smoke') || bt.includes('tobacco') || bt.includes('vape') || bt.includes('cigar')) return 'smoke_shop'
  if (bt.includes('restaurant') || bt.includes('dining') || bt.includes('bistro') || bt.includes('grill') || bt.includes('bar')) return 'restaurant'

  const name = org.business_name?.toLowerCase() || ''
  if (name.includes('pizza') || name.includes('pizzeria')) return 'pizzeria'
  if (name.includes('barber') || name.includes('fade')) return 'barbershop'
  if (name.includes('nail') || name.includes('lash')) return 'nails'
  if (name.includes('detail')) return 'detailing'
  if (name.includes('coffee') || name.includes('cafe') || name.includes('café')) return 'coffee_shop'
  if (name.includes('auto') || name.includes('tire') || name.includes('mechanic')) return 'auto_shop'
  if (name.includes('smoke') || name.includes('vape')) return 'smoke_shop'
  if (name.includes('pizza') || name.includes('burger') || name.includes('taco')) return 'fast_food'

  return 'restaurant'
}

export function DemoContextProvider({ children }: { children: ReactNode }) {
  const { authenticated, org } = useAuth()
  const stored = readStoredBusinessType()
  const [businessType, setBusinessTypeState] = useState<BusinessType>(stored ?? 'restaurant')
  // Open the selector on first visit so demo viewers pick their vertical before
  // any data renders — otherwise every demo page silently shows restaurant SKUs.
  // Skip the prompt if we already have a stored selection from this session.
  // The auth effect below closes it for authenticated users with a real org.
  const [showSelector, setShowSelector] = useState(stored === null)

  useEffect(() => {
    // On /demo paths, never let auth state override the prospect's selection —
    // a logged-in salesperson would otherwise force their own org's vertical
    // onto the demo and silently close the selector before they can pick.
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/demo')) return
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/canada/demo')) return
    if (authenticated && org) {
      const detected = detectBusinessType(org)
      _activeBusinessType = detected
      setBusinessTypeState(detected)
      setShowSelector(false)
    }
  }, [authenticated, org])

  function setBusinessType(type: BusinessType) {
    _activeBusinessType = type
    writeStoredBusinessType(type)
    setBusinessTypeState(type)
    setShowSelector(false)
  }

  function openSelector() {
    setShowSelector(true)
  }

  const option = BUSINESS_TYPES.find(b => b.id === businessType)
  const businessLabel = option?.label || ''

  return (
    <DemoContext.Provider value={{ businessType, setBusinessType, showSelector, openSelector, businessLabel }}>
      {children}
    </DemoContext.Provider>
  )
}
