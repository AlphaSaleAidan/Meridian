import { Loader2 } from 'lucide-react'

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-[#7C5CFF]" />
}

export function LoadingPage() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <LoadingSpinner size={32} />
        <p className="text-sm text-[#A1A1A8]">Loading data...</p>
      </div>
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="text-center space-y-3">
        <p className="text-sm text-red-400">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-4 py-2 text-sm font-medium text-white bg-[#7C5CFF] rounded-lg hover:bg-[#6B4FE0] transition-colors shadow-[0_0_16px_rgba(124,92,255,0.25)]"
          >
            Try Again
          </button>
        )}
      </div>
    </div>
  )
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex items-center justify-center h-48">
      <div className="text-center space-y-2">
        <p className="text-sm font-medium text-[#F5F5F7]/70">{title}</p>
        <p className="text-xs text-[#A1A1A8]/60">{description}</p>
      </div>
    </div>
  )
}
