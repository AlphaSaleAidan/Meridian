import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { ExternalLink, Loader2, AlertCircle } from 'lucide-react'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { getAuthHeaders } from '@/lib/supabase'
import { formatCents } from '@/lib/format'

const API_URL = import.meta.env.VITE_API_URL || ''

interface BillingStatus {
  status: string
  tier: string | null
  monthly_price_cents?: number
  current_period_end?: string
  billing_method?: string
}

export default function CanadaInvoicePage() {
  const { invoiceId } = useParams<{ invoiceId: string }>()

  const [billing, setBilling] = useState<BillingStatus | null>(null)
  const [invoiceUrl, setInvoiceUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!invoiceId) { setLoading(false); return }
    let alive = true
    ;(async () => {
      try {
        const headers = await getAuthHeaders()
        const [statusRes, urlRes] = await Promise.all([
          fetch(`${API_URL}/api/billing/status/${invoiceId}`, { headers }),
          fetch(`${API_URL}/api/billing/invoice-url/${invoiceId}`, { headers }),
        ])
        if (!alive) return
        if (statusRes.ok) {
          const d = await statusRes.json()
          setBilling(d)
        } else {
          setError('Could not load invoice — check the link or contact your rep.')
        }
        if (urlRes.ok) {
          const d = await urlRes.json()
          setInvoiceUrl(d.invoice_url || null)
        }
      } catch {
        if (alive) setError('Could not reach the billing server.')
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => { alive = false }
  }, [invoiceId])

  const statusLabel =
    billing?.status === 'active' ? 'Active' :
    billing?.status === 'pending_payment' ? 'Pending Payment' :
    billing?.status === 'past_due' ? 'Past Due' :
    billing?.status === 'trialing' ? 'Trial' : 'No Plan'

  const statusColor =
    billing?.status === 'active' ? 'text-[#17C5B0]' :
    billing?.status === 'past_due' ? 'text-red-400' :
    billing?.status === 'pending_payment' ? 'text-amber-400' : 'text-[#A1A1A8]'

  if (!invoiceId) {
    return (
      <div className="min-h-screen bg-[#0a0f0d] flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md text-center space-y-6">
          <div className="flex items-center justify-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </div>
          <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-6 space-y-4">
            <h1 className="text-lg font-bold text-white">Invoice Not Found</h1>
            <p className="text-sm text-[#6b7a74]">
              This invoice link is invalid. Please check the URL or contact your sales representative.
            </p>
            <a href="/canada" className="block w-full py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all text-center">
              Go to Meridian Canada
            </a>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0a0f0d] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center justify-center gap-2.5">
          <MeridianEmblem size={36} />
          <MeridianWordmark className="text-xl" />
        </div>

        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-[#1a2420]">
            <h1 className="text-lg font-bold text-white">Invoice</h1>
            <p className="text-[11px] text-[#4a5550] font-mono mt-0.5">ref: {invoiceId}</p>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-[#00d4aa]" size={22} />
            </div>
          ) : error ? (
            <div className="p-5 space-y-4">
              <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-500/10 border border-red-500/20">
                <AlertCircle size={14} className="text-red-400 mt-0.5 shrink-0" />
                <p className="text-xs text-red-400">{error}</p>
              </div>
              <a href="/canada/login" className="block w-full py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all text-center">
                Log In to Your Dashboard
              </a>
            </div>
          ) : (
            <div className="p-5 space-y-4">
              <div className="space-y-2 text-xs">
                <div className="flex items-center justify-between py-2 border-b border-[#1a2420]/60">
                  <span className="text-[#6b7a74]">Status</span>
                  <span className={`font-semibold ${statusColor}`}>{statusLabel}</span>
                </div>
                {billing?.tier && (
                  <div className="flex items-center justify-between py-2 border-b border-[#1a2420]/60">
                    <span className="text-[#6b7a74]">Plan</span>
                    <span className="text-white font-medium">
                      {billing.tier.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </span>
                  </div>
                )}
                {billing?.monthly_price_cents != null && billing.monthly_price_cents > 0 && (
                  <div className="flex items-center justify-between py-2 border-b border-[#1a2420]/60">
                    <span className="text-[#6b7a74]">Amount (CAD)</span>
                    <span className="text-white font-mono font-semibold">
                      {formatCents(billing.monthly_price_cents)}
                    </span>
                  </div>
                )}
                {billing?.current_period_end && (
                  <div className="flex items-center justify-between py-2 border-b border-[#1a2420]/60">
                    <span className="text-[#6b7a74]">Due / Renewal</span>
                    <span className="text-[#A1A1A8] font-mono">
                      {new Date(billing.current_period_end).toLocaleDateString('en-CA')}
                    </span>
                  </div>
                )}
                <div className="flex items-center justify-between py-2">
                  <span className="text-[#6b7a74]">Currency</span>
                  <span className="text-[#00d4aa] font-medium">CAD</span>
                </div>
              </div>

              {invoiceUrl ? (
                <a
                  href={invoiceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-center gap-2 w-full py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
                >
                  <ExternalLink size={14} />
                  Pay Invoice
                </a>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-[#6b7a74] text-center">
                    Contact your Meridian rep for payment details or to download the invoice PDF.
                  </p>
                  <a
                    href="/canada/login"
                    className="block w-full py-2.5 bg-[#1a2420] text-[#00d4aa] text-sm font-semibold rounded-lg hover:bg-[#1a2420]/80 transition-all text-center border border-[#00d4aa]/20"
                  >
                    Log In to Your Dashboard
                  </a>
                </div>
              )}
            </div>
          )}
        </div>

        <p className="text-center text-[10px] text-[#4a5550]">Meridian Intelligence Inc. — Canada</p>
      </div>
    </div>
  )
}
