import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import { CheckCircle2, AlertTriangle, X, Info } from 'lucide-react'
import { clsx } from 'clsx'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  message: string
  type: ToastType
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

const ICONS = {
  success: CheckCircle2,
  error: AlertTriangle,
  warning: AlertTriangle,
  info: Info,
}

const STYLES = {
  success: 'bg-[#00d4aa]/15 border-[#00d4aa]/30 text-[#00d4aa]',
  error: 'bg-red-500/15 border-red-500/30 text-red-400',
  warning: 'bg-[#f0b429]/15 border-[#f0b429]/30 text-[#f0b429]',
  info: 'bg-[#1A8FD6]/15 border-[#1A8FD6]/30 text-[#1A8FD6]',
}

function ToastItem({ toast, onDismiss }: { toast: Toast; onDismiss: (id: string) => void }) {
  const Icon = ICONS[toast.type]

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(toast.id), 4000)
    return () => clearTimeout(timer)
  }, [toast.id, onDismiss])

  return (
    <div className={clsx(
      'flex items-center gap-2.5 px-4 py-3 rounded-xl border backdrop-blur-sm shadow-lg animate-fade-in max-w-sm',
      STYLES[toast.type],
    )}>
      <Icon size={16} className="flex-shrink-0" />
      <p className="text-sm font-medium flex-1">{toast.message}</p>
      <button onClick={() => onDismiss(toast.id)} className="p-0.5 opacity-60 hover:opacity-100 transition-opacity" aria-label="Dismiss notification">
        <X size={14} />
      </button>
    </div>
  )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Date.now().toString(36) + Math.random().toString(36).slice(2, 6)
    setToasts(prev => [...prev.slice(-4), { id, message, type }])
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none" aria-live="polite" role="status">
        {toasts.map(t => (
          <div key={t.id} className="pointer-events-auto">
            <ToastItem toast={t} onDismiss={dismiss} />
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
