/**Cline proactive alert toast — shows when auto-fix is in progress or done.**/
import { useEffect, useState } from 'react'
import { clsx } from 'clsx'
import { Wrench, CheckCircle, X } from 'lucide-react'

interface ClineProactiveAlertProps {
  message: string
  visible: boolean
  onDismiss: () => void
}

export default function ClineProactiveAlert({ message, visible, onDismiss }: ClineProactiveAlertProps) {
  const [phase, setPhase] = useState<'fixing' | 'fixed'>('fixing')

  useEffect(() => {
    if (!visible) {
      setPhase('fixing')
      return
    }
    const timer = setTimeout(() => setPhase('fixed'), 3000)
    return () => clearTimeout(timer)
  }, [visible])

  if (!visible) return null

  return (
    <div
      className={clsx(
        'fixed bottom-20 sm:bottom-6 right-4 sm:right-6 z-50 max-w-sm',
        'rounded-xl border shadow-xl px-4 py-3 flex items-start gap-3',
        'transition-all duration-500 animate-fade-in',
        phase === 'fixing'
          ? 'bg-[#111113] border-[#17C5B0]/30'
          : 'bg-[#111113] border-emerald-500/30',
      )}
      role="alert"
    >
      <div className={clsx(
        'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5',
        phase === 'fixing' ? 'bg-[#17C5B0]/10' : 'bg-emerald-500/10',
      )}>
        {phase === 'fixing' ? (
          <Wrench size={16} className="text-[#17C5B0] animate-pulse" />
        ) : (
          <CheckCircle size={16} className="text-emerald-400" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[#F5F5F7]">
          {phase === 'fixing' ? 'Cline noticed an issue and is fixing it...' : 'Fixed!'}
        </p>
        <p className="text-xs text-[#A1A1A8] mt-0.5 line-clamp-2">
          {phase === 'fixing' ? 'Auto-remediation in progress' : message}
        </p>
      </div>
      <button
        onClick={onDismiss}
        className="p-1 rounded text-[#A1A1A8]/50 hover:text-[#F5F5F7] transition-colors flex-shrink-0"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  )
}
