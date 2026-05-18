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

// Module-level state so non-React code (api.ts, demo-data.ts) can read the selection
let _activeBusinessType: BusinessType = 'restaurant'
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
  const [businessType, setBusinessTypeState] = useState<BusinessType>('restaurant')
  const [showSelector, setShowSelector] = useState(false)

  useEffect(() => {
    if (authenticated && org) {
      const detected = detectBusinessType(org)
      _activeBusinessType = detected
      setBusinessTypeState(detected)
      setShowSelector(false)
    }
  }, [authenticated, org])

  function setBusinessType(type: BusinessType) {
    _activeBusinessType = type
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
