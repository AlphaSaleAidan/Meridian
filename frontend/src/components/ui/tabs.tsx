/**shadcn/ui Tabs — New York style, Meridian dark theme.**/
import { createContext, useContext, useState, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

const TabsContext = createContext<{ value: string; onChange: (v: string) => void }>({
  value: '',
  onChange: () => {},
})

interface TabsProps {
  defaultValue: string
  value?: string
  onValueChange?: (value: string) => void
  children: ReactNode
  className?: string
}

export function Tabs({ defaultValue, value: controlledValue, onValueChange, children, className }: TabsProps) {
  const [internal, setInternal] = useState(defaultValue)
  const value = controlledValue ?? internal
  const onChange = (v: string) => {
    setInternal(v)
    onValueChange?.(v)
  }

  return (
    <TabsContext.Provider value={{ value, onChange }}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  )
}

export function TabsList({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex items-center gap-1 rounded-lg bg-[#1F1F23]/50 p-1',
        className,
      )}
    >
      {children}
    </div>
  )
}

interface TabsTriggerProps {
  value: string
  children: ReactNode
  className?: string
  disabled?: boolean
}

export function TabsTrigger({ value, children, className, disabled }: TabsTriggerProps) {
  const ctx = useContext(TabsContext)
  const active = ctx.value === value

  return (
    <button
      role="tab"
      aria-selected={active}
      disabled={disabled}
      onClick={() => ctx.onChange(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-all min-h-[44px] sm:min-h-0',
        active
          ? 'bg-[#111113] text-[#F5F5F7] shadow-sm border border-[#1F1F23]'
          : 'text-[#A1A1A8] hover:text-[#F5F5F7] border border-transparent',
        disabled && 'pointer-events-none opacity-50',
        className,
      )}
    >
      {children}
    </button>
  )
}

export function TabsContent({ value, children, className }: { value: string; children: ReactNode; className?: string }) {
  const ctx = useContext(TabsContext)
  if (ctx.value !== value) return null

  return (
    <div role="tabpanel" className={cn('mt-3 focus-visible:outline-none', className)}>
      {children}
    </div>
  )
}
