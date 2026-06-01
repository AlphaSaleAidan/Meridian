import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { useAuth } from './auth'

export type BusinessType = 'coffee_shop' | 'restaurant' | 'fast_food' | 'auto_shop' | 'smoke_shop'

export interface BusinessTypeOption {
  id: BusinessType
  label: string
  icon: string
  description: string
}

export const BUSINESS_TYPES: BusinessTypeOption[] = [
  { id: 'restaurant', icon: '🍽️', label: 'Restaurant', description: 'Full-service dining — covers, table turns, server performance' },
  { id: 'fast_food', icon: '🍔', label: 'Fast Food', description: 'Quick service — drive-through wait times, order throughput, queues' },
  { id: 'coffee_shop', icon: '☕', label: 'Coffee Shop', description: 'Café & beverage — morning rush, loyalty regulars, menu velocity' },
  { id: 'auto_shop', icon: '🔧', label: 'Auto Shop', description: 'Automotive — bay utilization, customer wait times, service upsells' },
  { id: 'smoke_shop', icon: '💨', label: 'Smoke Shop', description: 'Tobacco & accessories — product zone dwell, repeat customers' },
]

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
const VALID_TYPES: BusinessType[] = ['coffee_shop', 'restaurant', 'fast_food', 'auto_shop', 'smoke_shop']

function readStoredBusinessType(): BusinessType | null {
  if (typeof window === 'undefined') return null
  try {
    const v = window.sessionStorage.getItem(STORAGE_KEY)
    return v && (VALID_TYPES as string[]).includes(v) ? (v as BusinessType) : null
  } catch {
    return null
  }
}

function writeStoredBusinessType(type: BusinessType): void {
  if (typeof window === 'undefined') return
  try { window.sessionStorage.setItem(STORAGE_KEY, type) } catch { /* private mode */ }
}

// Module-level state so non-React code (api.ts, demo-data.ts) can read the selection
let _activeBusinessType: BusinessType = readStoredBusinessType() ?? 'restaurant'
export function getActiveBusinessType(): BusinessType { return _activeBusinessType }

export function isCanadaPath(): boolean {
  return typeof window !== 'undefined' && window.location.pathname.startsWith('/canada')
}

const CAD_RATE = 1.38
export function getCurrencyMultiplier(): number {
  return isCanadaPath() ? CAD_RATE : 1.0
}

function detectBusinessType(org: { business_type?: string | null; pos_provider?: string | null; business_name?: string }): BusinessType {
  const bt = org.business_type?.toLowerCase() || ''
  if (bt.includes('coffee') || bt.includes('cafe') || bt.includes('café') || bt.includes('tea') || bt.includes('bakery')) return 'coffee_shop'
  if (bt.includes('fast') || bt.includes('quick') || bt.includes('qsr') || bt.includes('pizza') || bt.includes('burger') || bt.includes('taco')) return 'fast_food'
  if (bt.includes('auto') || bt.includes('mechanic') || bt.includes('garage') || bt.includes('tire') || bt.includes('oil change')) return 'auto_shop'
  if (bt.includes('smoke') || bt.includes('tobacco') || bt.includes('vape') || bt.includes('cigar')) return 'smoke_shop'
  if (bt.includes('restaurant') || bt.includes('dining') || bt.includes('bistro') || bt.includes('grill') || bt.includes('bar')) return 'restaurant'

  const name = org.business_name?.toLowerCase() || ''
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
