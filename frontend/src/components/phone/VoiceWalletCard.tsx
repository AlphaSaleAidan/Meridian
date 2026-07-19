import { useState, useEffect } from 'react'
import { clsx } from 'clsx'
import { Wallet, ArrowDownRight, ArrowUpRight, Gauge, ShieldCheck, AlertTriangle } from 'lucide-react'
import { phoneService } from '@/lib/phone-service'
import type { VoiceWallet } from '@/lib/phone-service'

/**
 * Per-location Voice Wallet (READ-ONLY).
 *
 * The location's voice self-funding P&L from voice_ledger: the Stripe/Clover
 * service fees it EARNS credit the wallet, each Vapi call's cost DEBITS it, and
 * the balance is whether this location is paying for its own AI phone agent.
 * When it runs past its floor, incoming calls fall back to the cheaper rail.
 * Nothing here mutates anything.
 *
 * Hidden in demo mode and when the ledger has no activity yet (balance 0 and no
 * window traffic), so it only shows once a location has real voice economics.
 */

interface Props {
  merchantId: string
  isDemo: boolean
  /** Currency symbol for display (merchant's billing currency). */
  currency?: string
  /** Lookback window in days for the run-rate figures. */
  days?: number
}

function money(cents: number, sym: string): string {
  const v = Math.abs(cents) / 100
  return `${cents < 0 ? '−' : ''}${sym}${v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function VoiceWalletCard({ merchantId, isDemo, currency = '$', days = 30 }: Props) {
  const [wallet, setWallet] = useState<VoiceWallet | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    if (isDemo || !merchantId) { setLoading(false); return }
    phoneService.getVoiceWallet(merchantId, days)
      .then(w => { if (alive) setWallet(w) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [merchantId, isDemo, days])

  if (isDemo || loading || !wallet) return null
  // No activity yet → don't clutter the dashboard.
  if (wallet.balance_cents === 0 && wallet.window_credit_cents === 0 && wallet.window_debit_cents === 0) {
    return null
  }

  const funded = wallet.self_funded
  const netPositive = wallet.window_net_cents >= 0

  return (
    <div className="bg-[#141418] border border-[#1F1F23] rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Wallet size={16} className="text-[#17C5B0]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Voice Wallet</h3>
          <span className="text-[10px] text-[#6b7280]">self-funding · last {wallet.window_days}d</span>
        </div>
        <span className={clsx('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium border',
          funded ? 'text-[#17C5B0] bg-[#17C5B0]/10 border-[#17C5B0]/20'
                 : 'text-red-400 bg-red-400/10 border-red-400/20')}>
          {funded ? <ShieldCheck size={10} /> : <AlertTriangle size={10} />}
          {funded ? 'Self-funded' : 'Underwater'}
        </span>
      </div>

      {/* Balance — the headline self-funding line */}
      <div className="mb-4">
        <p className="text-[11px] text-[#8b8b93] uppercase tracking-wider">Balance</p>
        <p className={clsx('text-2xl font-bold', funded ? 'text-[#F5F5F7]' : 'text-red-400')}>
          {money(wallet.balance_cents, currency)}
        </p>
        <p className="text-[11px] text-[#6b7280] mt-0.5">
          fees earned minus AI phone-agent cost, all time
        </p>
      </div>

      {/* 30-day flow */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div>
          <div className="flex items-center gap-1 text-[10px] text-[#8b8b93]"><ArrowUpRight size={11} className="text-[#17C5B0]" /> Fees in</div>
          <p className="text-sm font-semibold text-[#17C5B0]">{money(wallet.window_credit_cents, currency)}</p>
        </div>
        <div>
          <div className="flex items-center gap-1 text-[10px] text-[#8b8b93]"><ArrowDownRight size={11} className="text-amber-400" /> Voice cost</div>
          <p className="text-sm font-semibold text-amber-400">{money(wallet.window_debit_cents, currency)}</p>
        </div>
        <div>
          <div className="flex items-center gap-1 text-[10px] text-[#8b8b93]"><Gauge size={11} className="text-[#A1A1A8]" /> Net</div>
          <p className={clsx('text-sm font-semibold', netPositive ? 'text-[#17C5B0]' : 'text-red-400')}>
            {money(wallet.window_net_cents, currency)}
          </p>
        </div>
      </div>

      {/* Runway + fallback status */}
      <div className="flex items-center justify-between pt-3 border-t border-[#1F1F23] text-[11px]">
        <span className="text-[#8b8b93]">
          {wallet.runway_days != null
            ? <>Runway <span className="text-[#F5F5F7] font-medium">~{wallet.runway_days} days</span> at current burn</>
            : funded ? <>No burn — fees cover usage</> : <>Spending faster than it earns</>}
        </span>
        {wallet.below_floor ? (
          <span className="text-amber-400">↓ on cheaper rail (below floor)</span>
        ) : wallet.fallback_armed && wallet.floor_cents != null ? (
          <span className="text-[#6b7280]">floor {money(wallet.floor_cents, currency)}
            {wallet.floor_source === 'per_location' ? ' · custom' : ''}</span>
        ) : (
          <span className="text-[#6b7280]">no fallback floor set</span>
        )}
      </div>
    </div>
  )
}
