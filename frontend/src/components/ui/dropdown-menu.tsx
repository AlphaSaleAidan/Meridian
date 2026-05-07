/**shadcn/ui DropdownMenu — lightweight, Meridian dark theme.**/
import { useState, useRef, useEffect, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface DropdownMenuProps {
  trigger: ReactNode
  children: ReactNode
  align?: 'start' | 'center' | 'end'
  className?: string
}

export function DropdownMenu({ trigger, children, align = 'end', className }: DropdownMenuProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    document.addEventListener('keydown', keyHandler)
    return () => {
      document.removeEventListener('mousedown', handler)
      document.removeEventListener('keydown', keyHandler)
    }
  }, [open])

  return (
    <div ref={ref} className={cn('relative inline-block', className)}>
      <div onClick={() => setOpen(o => !o)}>{trigger}</div>
      {open && (
        <div
          className={cn(
            'absolute z-50 mt-1 min-w-[180px] rounded-lg border border-[#1F1F23] bg-[#111113] p-1 shadow-xl',
            align === 'start' && 'left-0',
            align === 'center' && 'left-1/2 -translate-x-1/2',
            align === 'end' && 'right-0',
          )}
          role="menu"
        >
          {children}
        </div>
      )}
    </div>
  )
}

interface DropdownItemProps {
  children: ReactNode
  onClick?: () => void
  className?: string
  disabled?: boolean
  destructive?: boolean
}

export function DropdownItem({ children, onClick, className, disabled, destructive }: DropdownItemProps) {
  return (
    <button
      role="menuitem"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors min-h-[44px] sm:min-h-0',
        destructive
          ? 'text-red-400 hover:bg-red-500/10'
          : 'text-[#F5F5F7] hover:bg-[#1F1F23]',
        disabled && 'pointer-events-none opacity-50',
        className,
      )}
    >
      {children}
    </button>
  )
}

export function DropdownSeparator({ className }: { className?: string }) {
  return <div className={cn('-mx-1 my-1 h-px bg-[#1F1F23]', className)} />
}

export function DropdownLabel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('px-3 py-1.5 text-[10px] font-medium text-[#A1A1A8] uppercase tracking-wider', className)}>
      {children}
    </div>
  )
}
