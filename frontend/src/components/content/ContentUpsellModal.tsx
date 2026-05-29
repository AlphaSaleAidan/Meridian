import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Coins, Zap, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { isCanadaPath } from '@/lib/demo-context'
import { CREDIT_PACKS, CREDIT_COSTS } from '@/lib/content-demo-data'
import { api } from '@/lib/api'

type Currency = 'USD' | 'CAD'

interface ContentUpsellModalProps {
  open: boolean
  onClose: () => void
  creditBalance?: number
  merchantId?: string
  customerEmail?: string
  customerName?: string
}

export default function ContentUpsellModal({
  open,
  onClose,
  creditBalance = 0,
  merchantId,
  customerEmail,
  customerName = '',
}: ContentUpsellModalProps) {
  const isCA = isCanadaPath()
  const currency: Currency = isCA ? 'CAD' : 'USD'
  const [busyPackId, setBusyPackId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Demo accounts can't actually purchase — they hit the demo merchant
  // which bypasses credit checks anyway. Showing a clean error beats a
  // broken redirect for the showcase tour.
  const isDemo = !merchantId || merchantId === 'demo'

  async function handleBuy(packId: string) {
    setError(null)
    if (isDemo) {
      setError('Purchases require a signed-in account. Sign up to enable real credit purchases.')
      return
    }
    if (!customerEmail) {
      setError('Add a billing email to your account before purchasing credits.')
      return
    }
    setBusyPackId(packId)
    try {
      const res = await api.creditPurchase({
        merchant_id: merchantId!,
        pack_id: packId,
        customer_email: customerEmail,
        customer_name: customerName,
        currency,
      })
      const invoiceUrl = res.invoice_url
      if (!invoiceUrl) {
        throw new Error('No invoice URL returned')
      }
      // Hand off to Square's hosted checkout. The webhook will grant
      // credits on payment; the dashboard's balance poll will reflect it.
      window.location.assign(invoiceUrl)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Purchase failed'
      setError(msg)
      setBusyPackId(null)
    }
  }

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 20 }}
            transition={{ type: 'spring', duration: 0.4 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4"
          >
            <div
              className="relative bg-[#131316] border border-[#1F1F23] rounded-xl w-full max-w-lg max-h-[90vh] overflow-y-auto"
              onClick={e => e.stopPropagation()}
            >
              <div className="flex items-center justify-between p-5 border-b border-[#1F1F23]">
                <div className="flex items-center gap-2">
                  <Coins size={18} className="text-amber-400" />
                  <h2 className="text-lg font-bold text-[#F5F5F7]">Buy Credits</h2>
                </div>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-lg text-[#A1A1A8] hover:text-[#F5F5F7] hover:bg-[#1F1F23] transition-colors"
                >
                  <X size={18} />
                </button>
              </div>

              <div className="p-5 space-y-5">
                <div className="flex items-center justify-between p-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]">
                  <span className="text-xs text-[#A1A1A8]">Current balance</span>
                  <span className="text-sm font-bold text-[#F5F5F7] font-mono flex items-center gap-1.5">
                    <Coins size={14} className="text-amber-400" />
                    {creditBalance.toLocaleString()} credits
                  </span>
                </div>

                {error && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-[12px] text-red-300">
                    {error}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-3">
                  {CREDIT_PACKS.map(pack => {
                    const rec = 'recommended' in pack && pack.recommended
                    const busy = busyPackId === pack.pack_id
                    return (
                      <button
                        key={pack.pack_id}
                        onClick={() => handleBuy(pack.pack_id)}
                        disabled={busyPackId !== null}
                        className={clsx(
                          'relative rounded-lg p-4 text-left transition-colors disabled:opacity-50 disabled:cursor-not-allowed',
                          rec
                            ? 'bg-[#1A8FD6]/5 border-2 border-[#1A8FD6] hover:bg-[#1A8FD6]/10'
                            : 'bg-[#0A0A0B] border border-[#1F1F23] hover:border-[#A1A1A8]/30',
                        )}
                      >
                        {rec && (
                          <span className="absolute -top-2.5 left-3 text-[9px] font-bold bg-[#1A8FD6] text-white px-2 py-0.5 rounded-full uppercase tracking-wider">
                            Best Value
                          </span>
                        )}
                        <p className="text-lg font-bold text-[#F5F5F7] font-mono">{pack.credits.toLocaleString()}</p>
                        <p className="text-[10px] text-[#A1A1A8] mb-2">credits</p>
                        <p className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-1.5">
                          {busy && <Loader2 size={12} className="animate-spin" />}
                          {isCA ? `CA$${pack.priceCad.toFixed(2)}` : `$${pack.priceUsd.toFixed(2)}`}
                        </p>
                        <p className="text-[10px] text-[#A1A1A8]">
                          {isCA
                            ? `CA$${(pack.priceCad / pack.credits).toFixed(4)}`
                            : `$${(pack.priceUsd / pack.credits).toFixed(4)}`
                          }/credit
                        </p>
                      </button>
                    )
                  })}
                </div>

                <div className="space-y-2">
                  <h3 className="text-xs font-semibold text-[#F5F5F7]">What credits buy</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {[
                      { label: 'AI phone call (per min)', cost: CREDIT_COSTS.phone_call_per_min },
                      { label: 'SMS exchange (in + out)', cost: CREDIT_COSTS.sms_inbound + CREDIT_COSTS.sms_outbound },
                      { label: 'Social post (image + copy)', cost: CREDIT_COSTS.social_post },
                      { label: 'SEO article', cost: CREDIT_COSTS.seo_article },
                      { label: 'Regenerate image', cost: CREDIT_COSTS.image_regen },
                      { label: 'Caption rewrite', cost: CREDIT_COSTS.caption_only },
                    ].map(item => (
                      <div key={item.label} className="flex items-center justify-between p-2 rounded bg-[#0A0A0B] border border-[#1F1F23]">
                        <span className="text-[10px] text-[#A1A1A8]">{item.label}</span>
                        <span className="text-[10px] font-mono font-semibold text-amber-400 flex items-center gap-0.5">
                          <Coins size={9} /> {item.cost}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex items-start gap-2 p-3 rounded-lg bg-[#17C5B0]/5 border border-[#17C5B0]/15">
                  <Zap size={14} className="text-[#17C5B0] flex-shrink-0 mt-0.5" />
                  <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                    Every new account gets <span className="text-[#F5F5F7] font-semibold">1,000 free credits</span> — enough
                    for ~20 minutes of AI phone calls, ~30 SMS conversations, 10 social posts, or 4 SEO articles.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
