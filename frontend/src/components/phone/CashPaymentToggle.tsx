import { useState } from 'react'
import { clsx } from 'clsx'
import { Banknote, AlertTriangle } from 'lucide-react'

/**
 * "Pay with Cash" opt-in control (phone_agent_config.accept_cash, migration 047).
 *
 * When ON, the phone agent may offer cash on pickup; those orders reach the
 * kitchen flagged UNPAID / CASH ON PICKUP with NO payment link. Because that
 * lets potentially-unpaid orders reach the kitchen, turning it ON requires an
 * explicit confirmation modal — cancelling leaves it OFF. Turning it back OFF
 * is immediate (no warning needed).
 *
 * Shared by the setup wizard's payment step and the phone Settings tab so the
 * warning copy lives in exactly one place.
 */

// EXACT warning copy — do not reword. Enabling cash lets unpaid orders through.
export const CASH_WARNING_COPY =
  'By selecting this you are allowing potentially unpaid orders to reach your ' +
  'kitchen, are you sure you want to set this up?'

interface Props {
  enabled: boolean
  onChange: (next: boolean) => void
  /** Compact renders a tighter row for the settings card; default is the wizard card. */
  className?: string
}

export default function CashPaymentToggle({ enabled, onChange, className }: Props) {
  const [confirming, setConfirming] = useState(false)

  function requestToggle() {
    if (enabled) {
      // Turning OFF is safe — no confirmation.
      onChange(false)
      return
    }
    // Turning ON requires explicit confirmation.
    setConfirming(true)
  }

  return (
    <div className={clsx('space-y-1', className)}>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-start gap-2">
          <Banknote size={14} className="text-[#17C5B0] mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-[#F5F5F7]">Pay with Cash</p>
            <p className="text-[10px] text-[#A1A1A8]/70 mt-0.5 leading-relaxed">
              Let callers pay cash on pickup. Cash orders reach your kitchen marked
              UNPAID — CASH ON PICKUP, with no payment link sent.
            </p>
          </div>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          aria-label="Pay with Cash"
          onClick={requestToggle}
          className={clsx('relative w-10 h-5 rounded-full transition-colors flex-shrink-0',
            enabled ? 'bg-[#17C5B0]' : 'bg-[#2A2A30]')}
        >
          <span className={clsx('absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform',
            enabled ? 'left-5' : 'left-0.5')} />
        </button>
      </div>

      {confirming && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
          role="dialog"
          aria-modal="true"
          onClick={() => setConfirming(false)}
        >
          <div
            className="w-full max-w-sm bg-[#0A0A0B] border border-amber-500/30 rounded-xl shadow-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="p-5 space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-amber-500/10 flex items-center justify-center flex-shrink-0">
                  <AlertTriangle size={18} className="text-amber-400" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-[#F5F5F7]">Allow cash orders?</h4>
                  <p className="text-xs text-[#A1A1A8] leading-relaxed mt-1.5">
                    {CASH_WARNING_COPY}
                  </p>
                </div>
              </div>
              <div className="flex items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => setConfirming(false)}
                  className="px-4 py-2 text-xs font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => { onChange(true); setConfirming(false) }}
                  className="px-4 py-2 bg-amber-500 text-[#0A0A0B] text-xs font-semibold rounded-lg hover:bg-amber-400 transition-colors"
                >
                  Yes, enable cash
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
