import { useState } from 'react'
import { ArrowRight } from 'lucide-react'
import { clsx } from 'clsx'
import { BUSINESS_TYPES, useDemoContext, type BusinessType } from '@/lib/demo-context'

export default function BusinessTypeSelector() {
  const { showSelector, setBusinessType } = useDemoContext()
  const [selected, setSelected] = useState<BusinessType | null>(null)

  if (!showSelector) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-[680px] bg-[#111113] border border-[#1F1F23] rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-6 pt-8 pb-4 text-center">
          <h2 className="text-xl sm:text-2xl font-bold text-[#F5F5F7]">
            What type of business are you?
          </h2>
          <p className="text-sm text-[#A1A1A8] mt-2">
            We'll build your demo around your industry.
          </p>
        </div>

        <div className="px-6 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
          {BUSINESS_TYPES.map(bt => (
            <button
              key={bt.id}
              onClick={() => setSelected(bt.id)}
              className={clsx(
                'group relative p-4 rounded-xl border text-left transition-all duration-200',
                selected === bt.id
                  ? 'border-[#17C5B0] bg-[#17C5B0]/5 shadow-[0_0_20px_rgba(23,197,176,0.1)]'
                  : 'border-[#1F1F23] bg-[#0A0A0B] hover:border-[#2A2A2E] hover:bg-[#141416]'
              )}
            >
              <div className="flex items-start gap-3">
                <span className="text-2xl flex-shrink-0 mt-0.5">{bt.icon}</span>
                <div className="min-w-0">
                  <p className={clsx(
                    'text-sm font-semibold transition-colors',
                    selected === bt.id ? 'text-[#17C5B0]' : 'text-[#F5F5F7]'
                  )}>
                    {bt.label}
                  </p>
                  <p className="text-xs text-[#A1A1A8]/60 mt-0.5 leading-relaxed">
                    {bt.description}
                  </p>
                </div>
              </div>
              {selected === bt.id && (
                <div className="absolute top-3 right-3 w-5 h-5 rounded-full bg-[#17C5B0] flex items-center justify-center">
                  <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
                    <path d="M1 4L3.5 6.5L9 1" stroke="#0A0A0B" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
            </button>
          ))}
        </div>

        <div className="px-6 pb-8 pt-2 flex justify-center">
          <button
            disabled={!selected}
            onClick={() => selected && setBusinessType(selected)}
            className={clsx(
              'flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold transition-all duration-200',
              selected
                ? 'bg-[#17C5B0] text-[#0A0A0B] hover:bg-[#17C5B0]/90 cursor-pointer'
                : 'bg-[#1F1F23] text-[#A1A1A8]/40 cursor-not-allowed'
            )}
          >
            View My Demo
            <ArrowRight size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
