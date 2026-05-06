import { createContext, useContext, useState, type ReactNode } from 'react'

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
let _activeBusinessType: BusinessType = 'coffee_shop'
export function getActiveBusinessType(): BusinessType { return _activeBusinessType }

export function DemoContextProvider({ children }: { children: ReactNode }) {
  const [businessType, setBusinessTypeState] = useState<BusinessType | null>(null)
  const [showSelector, setShowSelector] = useState(true)

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
