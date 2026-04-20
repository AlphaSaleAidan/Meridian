import { useState } from 'react'
import {
  X, ShoppingBag, CreditCard, Banknote, Smartphone,
  ChevronDown, ChevronUp, Package,
} from 'lucide-react'
import type { TransactionDetail } from '@/lib/api'
import { formatCents, formatNumber } from '@/lib/format'
import { useApi } from '@/hooks/useApi'
import { api } from '@/lib/api'
import { LoadingSpinner } from '@/components/LoadingState'

const ORG_ID = import.meta.env.VITE_ORG_ID || 'demo'

const paymentIcons: Record<string, typeof CreditCard> = {
  card: CreditCard,
  cash: Banknote,
  apple_pay: Smartphone,
  google_pay: Smartphone,
}

function TransactionRow({ tx }: { tx: TransactionDetail }) {
  const [open, setOpen] = useState(false)
  const time = new Date(tx.created_at).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
  const PayIcon = paymentIcons[tx.payment_method] || CreditCard
  const Chevron = open ? ChevronUp : ChevronDown

  return (
    <div className="border-b border-[#1F1F23]/50 last:border-0">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-[#7C5CFF]/[0.03] transition-colors"
      >
        <div className="w-8 h-8 rounded-lg bg-[#1F1F23] flex items-center justify-center flex-shrink-0">
          <ShoppingBag size={14} className="text-[#A1A1A8]/50" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[#F5F5F7] font-mono">{formatCents(tx.total_cents)}</span>
            {tx.refund_cents > 0 && <span className="badge-red text-[10px]">REFUND</span>}
            {tx.discount_cents > 0 && <span className="badge-amber text-[10px]">-{formatCents(tx.discount_cents)}</span>}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-[#A1A1A8]/60">{time}</span>
            <span className="text-[#A1A1A8]/20">·</span>
            <span className="text-xs text-[#A1A1A8]/60 flex items-center gap-1">
              <PayIcon size={10} /> {tx.payment_method.replace('_', ' ')}
            </span>
            <span className="text-[#A1A1A8]/20">·</span>
            <span className="text-xs text-[#A1A1A8]/60">{tx.items.length} item{tx.items.length !== 1 ? 's' : ''}</span>
          </div>
        </div>
        <Chevron size={16} className="text-[#A1A1A8]/40 flex-shrink-0" />
      </button>

      {open && (
        <div className="px-4 pb-3 animate-fade-in">
          <div className="ml-11 space-y-1.5">
            {tx.items.map(item => (
              <div
                key={item.id}
                className="flex items-center justify-between py-1.5 px-3 rounded-lg bg-[#0A0A0B] border border-[#1F1F23]/40"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Package size={12} className="text-[#7C5CFF]/60 flex-shrink-0" />
                  <span className="text-xs text-[#F5F5F7] truncate">{item.product_name}</span>
                  {item.sku && (
                    <span className="text-[10px] text-[#A1A1A8]/30 font-mono hidden sm:inline">{item.sku}</span>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <span className="text-[10px] text-[#A1A1A8]/50">
                    {item.quantity > 1 ? `${item.quantity} × ` : ''}{formatCents(item.unit_price_cents)}
                  </span>
                  <span className="text-xs font-mono font-medium text-[#F5F5F7] w-16 text-right">
                    {formatCents(item.total_cents)}
                  </span>
                </div>
              </div>
            ))}
            {tx.tip_cents > 0 && (
              <div className="flex items-center justify-between px-3 py-1">
                <span className="text-[10px] text-[#4FE3C1]/60">Tip</span>
                <span className="text-[10px] font-mono text-[#4FE3C1]">+{formatCents(tx.tip_cents)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface Props {
  date: string
  onClose: () => void
}

export default function TransactionDrillDown({ date, onClose }: Props) {
  const dayData = useApi(() => api.dayTransactions(ORG_ID, date), [date])

  const displayDate = new Date(date + 'T12:00:00').toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  })

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 sm:pt-16 px-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative w-full max-w-2xl max-h-[80vh] flex flex-col bg-[#111113] border border-[#1F1F23] rounded-2xl shadow-2xl shadow-black/50 overflow-hidden animate-fade-in">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[#1F1F23] flex-shrink-0">
          <div>
            <h2 className="text-base font-semibold text-[#F5F5F7]">Transaction History</h2>
            <p className="text-xs text-[#A1A1A8] mt-0.5">{displayDate}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Summary row */}
        {dayData.data && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-5 py-3 border-b border-[#1F1F23] flex-shrink-0">
            <div>
              <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider">Revenue</p>
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCents(dayData.data.summary.total_revenue_cents)}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider">Transactions</p>
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatNumber(dayData.data.summary.transaction_count)}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider">Avg Ticket</p>
              <p className="text-sm font-bold font-mono text-[#F5F5F7]">{formatCents(dayData.data.summary.avg_ticket_cents)}</p>
            </div>
            <div>
              <p className="text-[10px] text-[#A1A1A8]/50 uppercase tracking-wider">Top Product</p>
              <p className="text-sm font-medium text-[#7C5CFF] truncate">{dayData.data.summary.top_product} ({dayData.data.summary.top_product_qty})</p>
            </div>
          </div>
        )}

        {/* Transaction list */}
        <div className="flex-1 overflow-y-auto">
          {dayData.loading && (
            <div className="flex items-center justify-center h-48">
              <LoadingSpinner />
            </div>
          )}
          {dayData.error && (
            <div className="flex items-center justify-center h-48 text-red-400 text-sm">
              {dayData.error}
            </div>
          )}
          {dayData.data && (
            <div>
              {dayData.data.transactions.map(tx => (
                <TransactionRow key={tx.id} tx={tx} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
