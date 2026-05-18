import { useState, useEffect } from 'react'
import { Loader2 } from 'lucide-react'
import { MeridianEmblem } from './MeridianLogo'

export function LoadingSpinner({ size = 24 }: { size?: number }) {
  return <Loader2 size={size} className="animate-spin text-[#7C5CFF]" />
}

const TIPS = [
  'Revenue data updates every 15 minutes once your POS is connected.',
  'The Insights tab uses AI to detect anomalies in your sales patterns.',
  'Peak Hours analysis helps you optimize staffing for maximum profit.',
  'Product performance scores identify your top margin items.',
  'Customer segmentation helps you target the right audience.',
  'Set up cameras to unlock foot traffic and conversion analytics.',
  'Forecasts use 30 days of data to predict future revenue trends.',
  'The Anomaly Detector catches unusual patterns before they cost you money.',
  'Staff performance tracking identifies your top performers.',
  'Menu Matrix analysis shows which items to promote, keep, or rethink.',
]

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

export function RadarLoadingState({ title, description }: { title?: string; description?: string }) {
  const [tipIdx, setTipIdx] = useState(() => Math.floor(Math.random() * TIPS.length))

  useEffect(() => {
    const interval = setInterval(() => {
      setTipIdx(prev => (prev + 1) % TIPS.length)
    }, 6000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center justify-center min-h-[320px]">
      <div className="flex flex-col items-center gap-5 text-center max-w-sm mx-auto">
        <MeridianEmblem size={72} animate />
        <div className="space-y-2">
          <p className="text-sm font-semibold text-[#F5F5F7]">{title || 'Waiting for data'}</p>
          <p className="text-xs text-[#A1A1A8]/60 leading-relaxed">{description || 'Connect your POS to start receiving insights and analytics.'}</p>
        </div>
        <div className="px-4 py-2 rounded-lg bg-[#111113] border border-[#1F1F23] max-w-xs">
          <p className="text-[10px] text-[#7C5CFF] font-medium mb-0.5">Did you know?</p>
          <p className="text-[11px] text-[#A1A1A8]/70 leading-relaxed transition-opacity duration-500">{TIPS[tipIdx]}</p>
        </div>
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
  const [tipIdx, setTipIdx] = useState(() => Math.floor(Math.random() * TIPS.length))

  useEffect(() => {
    const interval = setInterval(() => {
      setTipIdx(prev => (prev + 1) % TIPS.length)
    }, 6000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <div className="flex flex-col items-center gap-4 text-center max-w-xs mx-auto">
        <MeridianEmblem size={48} animate />
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-[#F5F5F7]/70">{title}</p>
          <p className="text-xs text-[#A1A1A8]/60">{description}</p>
        </div>
        <p className="text-[10px] text-[#A1A1A8]/40 italic">{TIPS[tipIdx]}</p>
      </div>
    </div>
  )
}
