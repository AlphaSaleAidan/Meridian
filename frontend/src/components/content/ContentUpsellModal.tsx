import { motion, AnimatePresence } from 'framer-motion'
import { X, Check, Sparkles } from 'lucide-react'
import { clsx } from 'clsx'
import { isCanadaPath } from '@/lib/demo-context'

interface ContentUpsellModalProps {
  open: boolean
  onClose: () => void
}

interface Tier {
  name: string
  priceUsd: number
  priceCad: number
  features: string[]
  recommended?: boolean
}

const TIERS: Tier[] = [
  {
    name: 'Starter',
    priceUsd: 49,
    priceCad: 67,
    features: [
      '3 posts per week',
      '1 platform',
      'Basic SEO optimization',
      'AI-generated images',
    ],
  },
  {
    name: 'Growth',
    priceUsd: 129,
    priceCad: 177,
    recommended: true,
    features: [
      '7 posts per week',
      '3 platforms',
      'Advanced SEO + articles',
      'AI images + video briefs',
      'Rank tracking',
    ],
  },
  {
    name: 'Command',
    priceUsd: 299,
    priceCad: 409,
    features: [
      '10 posts per week',
      'All platforms',
      'Premium articles (Claude Sonnet)',
      'Full video production briefs',
      'Rank tracking + AI citations',
      'Dedicated brand voice',
      'WordPress publishing',
    ],
  },
]

export default function ContentUpsellModal({ open, onClose }: ContentUpsellModalProps) {
  const isCA = isCanadaPath()

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', duration: 0.4 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              className="relative bg-[#131316] border border-[#1F1F23] rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-5 border-b border-[#1F1F23]">
                <div className="flex items-center gap-2">
                  <Sparkles size={18} className="text-[#1A8FD6]" />
                  <h2 className="text-lg font-bold text-[#F5F5F7]">Upgrade Your Content</h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Tier cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 p-5">
                {TIERS.map(tier => (
                  <div
                    key={tier.name}
                    className={clsx(
                      'rounded-lg p-5 flex flex-col',
                      tier.recommended
                        ? 'bg-[#1A8FD6]/5 border-2 border-[#1A8FD6] relative'
                        : 'bg-[#0A0A0B] border border-[#1F1F23]',
                    )}
                  >
                    {tier.recommended && (
                      <span className="absolute -top-3 left-1/2 -translate-x-1/2 text-[10px] font-bold bg-[#1A8FD6] text-white px-2.5 py-0.5 rounded-full uppercase tracking-wider">
                        Recommended
                      </span>
                    )}

                    <h3 className="text-sm font-semibold text-[#F5F5F7]">{tier.name}</h3>
                    <div className="mt-2 mb-4">
                      <span className="text-2xl font-bold text-[#F5F5F7] font-mono">
                        {isCA ? `CA$${tier.priceCad}` : `$${tier.priceUsd}`}
                      </span>
                      <span className="text-xs text-[#A1A1A8]">/mo</span>
                    </div>

                    <ul className="space-y-2 flex-1">
                      {tier.features.map(f => (
                        <li key={f} className="flex items-start gap-2 text-xs text-[#A1A1A8]">
                          <Check size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                          {f}
                        </li>
                      ))}
                    </ul>

                    <button
                      className={clsx(
                        'mt-5 w-full py-2 rounded-lg text-sm font-semibold transition-colors',
                        tier.recommended
                          ? 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90'
                          : 'bg-[#1F1F23] text-[#F5F5F7] hover:bg-[#1F1F23]/80',
                      )}
                    >
                      Get Started
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
