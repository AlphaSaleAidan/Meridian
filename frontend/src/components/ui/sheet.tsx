/**shadcn/ui Sheet — slide-in side panel for mobile nav.**/
import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

type Side = 'left' | 'right' | 'top' | 'bottom'

interface SheetProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  side?: Side
  children: ReactNode
  className?: string
}

const slideClasses: Record<Side, { base: string; open: string; closed: string }> = {
  left: {
    base: 'fixed inset-y-0 left-0 z-50 w-[280px] sm:w-[320px]',
    open: 'translate-x-0',
    closed: '-translate-x-full',
  },
  right: {
    base: 'fixed inset-y-0 right-0 z-50 w-[280px] sm:w-[320px]',
    open: 'translate-x-0',
    closed: 'translate-x-full',
  },
  top: {
    base: 'fixed inset-x-0 top-0 z-50',
    open: 'translate-y-0',
    closed: '-translate-y-full',
  },
  bottom: {
    base: 'fixed inset-x-0 bottom-0 z-50',
    open: 'translate-y-0',
    closed: 'translate-y-full',
  },
}

export function Sheet({ open, onOpenChange, side = 'left', children, className }: SheetProps) {
  const panelRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onOpenChange(false)
    }
    document.addEventListener('keydown', handler)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handler)
      document.body.style.overflow = ''
    }
  }, [open, onOpenChange])

  useEffect(() => {
    if (open && panelRef.current) {
      const first = panelRef.current.querySelector<HTMLElement>('[data-autofocus], button, a, input')
      first?.focus()
    }
  }, [open])

  const slide = slideClasses[side]

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className={cn(
          'fixed inset-0 z-40 bg-black/70 backdrop-blur-sm transition-opacity duration-300',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        className={cn(
          slide.base,
          'border-[#1F1F23] bg-[#0A0A0B] shadow-xl transition-transform duration-300 ease-out',
          side === 'left' || side === 'right' ? 'border-r' : 'border-b',
          open ? slide.open : slide.closed,
          className,
        )}
      >
        {children}
      </div>
    </>,
    document.body,
  )
}

interface SheetHeaderProps {
  children: ReactNode
  className?: string
  onClose?: () => void
}

export function SheetHeader({ children, className, onClose }: SheetHeaderProps) {
  return (
    <div className={cn('flex items-center justify-between p-4 border-b border-[#1F1F23]', className)}>
      <div className="flex-1">{children}</div>
      {onClose && (
        <button
          onClick={onClose}
          className="p-2 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Close"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      )}
    </div>
  )
}

export function SheetContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('flex-1 overflow-y-auto', className)}>{children}</div>
}
