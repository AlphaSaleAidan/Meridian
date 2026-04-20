import { Loader2 } from 'lucide-react'

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-meridian-500" />
}

export function LoadingPage() {
  return (
    <div className="flex items-center justify-center h-64">
      <div className="flex flex-col items-center gap-3">
        <LoadingSpinner size={32} />
        <p className="text-sm text-slate-400">Loading data...</p>
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
            className="px-4 py-2 text-sm font-medium text-white bg-meridian-700 rounded-lg hover:bg-meridian-600 transition-colors"
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
        <p className="text-sm font-medium text-slate-300">{title}</p>
        <p className="text-xs text-slate-500">{description}</p>
      </div>
    </div>
  )
}
