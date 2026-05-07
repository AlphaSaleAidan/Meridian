/**Bottom-sheet drawer (vaul-style) for mobile interactions.**/
import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

interface DrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
  className?: string
}

export function Drawer({ open, onOpenChange, children, className }: DrawerProps) {
  const contentRef = useRef<HTMLDivElement>(null)

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

  return createPortal(
    <>
      <div
        className={cn(
          'fixed inset-0 z-50 bg-black/60 transition-opacity duration-300',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        className={cn(
          'fixed inset-x-0 bottom-0 z-50 rounded-t-2xl border-t border-[#1F1F23] bg-[#111113] shadow-xl transition-transform duration-300 ease-out max-h-[85vh]',
          open ? 'translate-y-0' : 'translate-y-full',
          className,
        )}
      >
        {/* Drag handle */}
        <div className="flex justify-center pt-3 pb-1">
          <div className="h-1 w-10 rounded-full bg-[#A1A1A8]/30" />
        </div>
        {children}
      </div>
    </>,
    document.body,
  )
}

export function DrawerHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('px-5 py-3', className)}>{children}</div>
}

export function DrawerTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h3 className={cn('text-base font-semibold text-[#F5F5F7]', className)}>{children}</h3>
}

export function DrawerContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('px-5 pb-8 overflow-y-auto', className)}>{children}</div>
}

export function DrawerFooter({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex items-center gap-2 px-5 py-4 border-t border-[#1F1F23]', className)}>
      {children}
    </div>
  )
}
