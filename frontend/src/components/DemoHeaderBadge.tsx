import { useLocation } from 'react-router-dom'
import { useDemoContext } from '@/lib/demo-context'

export default function DemoHeaderBadge() {
  const { businessType, businessLabel, openSelector } = useDemoContext()
  const location = useLocation()
  const isCanada = location.pathname.startsWith('/canada')

  if (!businessType) return null

  return (
    <div className="fixed top-2 right-4 z-50 flex items-center gap-2 px-3 py-1.5 bg-[#111113]/90 backdrop-blur border border-[#1F1F23] rounded-full text-xs">
      <span className="text-[#1A8FD6] font-medium">Demo</span>
      <span className="text-[#A1A1A8]/30">|</span>
      <span className="text-[#F5F5F7] font-medium">{isCanada ? '🇨🇦 CAD' : '🇺🇸 USD'}</span>
      <span className="text-[#A1A1A8]/30">|</span>
      <span className="text-[#F5F5F7] font-medium">{businessLabel}</span>
      <button
        onClick={openSelector}
        className="text-[#17C5B0] hover:text-[#17C5B0]/80 font-medium ml-1 transition-colors"
      >
        Switch
      </button>
    </div>
  )
}
