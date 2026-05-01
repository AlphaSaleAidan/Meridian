/**shadcn/ui Dialog — modal overlay, Meridian dark theme.**/
import { useEffect, useRef, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { cn } from '@/lib/utils'

interface DialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: ReactNode
}

export function Dialog({ open, onOpenChange, children }: DialogProps) {
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

  useEffect(() => {
    if (open && contentRef.current) {
      const first = contentRef.current.querySelector<HTMLElement>('button, a, input, [tabindex]')
      first?.focus()
    }
  }, [open])

  if (!open) return null

  return createPortal(
    <>
      <div
        className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm animate-in fade-in-0"
        onClick={() => onOpenChange(false)}
        aria-hidden
      />
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          ref={contentRef}
          role="dialog"
          aria-modal="true"
          className="relative w-full max-w-lg rounded-xl border border-[#1F1F23] bg-[#111113] p-6 shadow-xl"
          onClick={e => e.stopPropagation()}
        >
          {children}
        </div>
      </div>
    </>,
    document.body,
  )
}

export function DialogHeader({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('flex flex-col space-y-1.5 mb-4', className)}>{children}</div>
}

export function DialogTitle({ children, className }: { children: ReactNode; className?: string }) {
  return <h2 className={cn('text-lg font-semibold text-[#F5F5F7]', className)}>{children}</h2>
}

export function DialogDescription({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn('text-sm text-[#A1A1A8]', className)}>{children}</p>
}

export function DialogFooter({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn('flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-6', className)}>
      {children}
    </div>
  )
}

export function DialogClose({ children, onClose, className }: { children: ReactNode; onClose: () => void; className?: string }) {
  return (
    <button onClick={onClose} className={cn('', className)}>
      {children}
    </button>
  )
}
