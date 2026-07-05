import { useState } from 'react'
import { clsx } from 'clsx'
import { CalendarCheck, Check, ExternalLink, X } from 'lucide-react'
import { phoneService, saveConfigErrorMessage, type ReservationConfig } from '@/lib/phone-service'

// "dine_in" was renamed to "reservation" in the UI + agent; stored configs may
// still contain the legacy value, so membership/toggling treat them as one.
export const ORDER_TYPE_OPTIONS = [
  { value: 'pickup', label: 'Pickup' },
  { value: 'delivery', label: 'Delivery' },
  { value: 'reservation', label: 'Reservation' },
] as const

export function hasOrderType(types: string[], value: string): boolean {
  if (value === 'reservation') return types.includes('reservation') || types.includes('dine_in')
  return types.includes(value)
}

export function toggleOrderType(types: string[], value: string): string[] {
  if (hasOrderType(types, value)) {
    return types.filter(t => t !== value && !(value === 'reservation' && t === 'dine_in'))
  }
  return [...types, value]
}

/**
 * "Connect your reservation system" — short questionnaire shown when the
 * Reservation order type is enabled: is the reservation system on their
 * website, and if so at what URL. The phone agent uses this to point callers
 * to online booking (or take the reservation itself when there's none).
 */
export function ConnectReservationSystem({
  merchantId,
  config,
  onSaved,
}: {
  merchantId: string
  config: ReservationConfig | null
  onSaved: (c: ReservationConfig) => void
}) {
  const [open, setOpen] = useState(false)
  const [onWebsite, setOnWebsite] = useState<boolean | null>(config?.on_website ?? null)
  const [websiteUrl, setWebsiteUrl] = useState(config?.website_url ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const connected = !!config && config.on_website !== undefined

  const save = async () => {
    if (onWebsite === null) { setError('Pick yes or no first.'); return }
    let url = websiteUrl.trim()
    if (onWebsite) {
      if (!url) { setError('Enter your website URL.'); return }
      if (!/^https?:\/\//i.test(url)) url = `https://${url}`
      try { new URL(url) } catch { setError('That URL doesn’t look right.'); return }
    }
    setSaving(true)
    setError('')
    const next: ReservationConfig = { on_website: onWebsite, website_url: onWebsite ? url : '' }
    const res = await phoneService.saveConfig({ merchant_id: merchantId, reservation_config: next })
    setSaving(false)
    if (!res.ok) { setError(saveConfigErrorMessage(res)); return }
    onSaved(next)
    setOpen(false)
  }

  return (
    <div className="mt-3">
      <button onClick={() => setOpen(true)}
        className={clsx('flex items-center gap-2 px-3 py-2 rounded-lg border text-xs font-medium transition-all',
          connected ? 'border-[#17C5B0]/20 bg-[#17C5B0]/5 text-[#17C5B0]' : 'border-[#1A8FD6]/30 text-[#1A8FD6] hover:bg-[#1A8FD6]/10')}>
        <CalendarCheck size={13} />
        {connected
          ? (config?.on_website ? 'Reservation system connected — via your website' : 'Reservations taken by the agent')
          : 'Connect your reservation system'}
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={() => setOpen(false)}>
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div className="relative w-full max-w-sm bg-[#111113] border border-[#1F1F23] rounded-xl shadow-2xl p-5 space-y-4"
            onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-[#F5F5F7]">Connect your reservation system</h3>
              <button onClick={() => setOpen(false)} className="text-[#A1A1A8] hover:text-white transition-colors">
                <X size={16} />
              </button>
            </div>

            <div>
              <p className="text-[12px] text-[#F5F5F7] mb-2">Is your reservation system available on your website?</p>
              <div className="flex gap-2">
                {[{ v: true, label: 'Yes' }, { v: false, label: 'No' }].map(({ v, label }) => (
                  <button key={label} onClick={() => setOnWebsite(v)}
                    className={clsx('flex-1 px-3 py-2 rounded-lg border text-xs font-medium transition-all',
                      onWebsite === v ? 'border-[#17C5B0]/30 bg-[#17C5B0]/10 text-[#17C5B0]' : 'border-[#1F1F23] text-[#A1A1A8] hover:border-[#2A2A2E]')}>
                    {label}
                  </button>
                ))}
              </div>
            </div>

            {onWebsite === true && (
              <div>
                <label className="text-[11px] text-[#A1A1A8] block mb-1">What&rsquo;s your website URL?</label>
                <div className="flex items-center gap-2">
                  <ExternalLink size={13} className="text-[#A1A1A8] flex-shrink-0" />
                  <input value={websiteUrl} onChange={e => setWebsiteUrl(e.target.value)}
                    placeholder="yourrestaurant.com/reservations"
                    className="flex-1 px-3 py-2 text-xs bg-[#0A0A0B] border border-[#1F1F23] rounded-lg text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6]/40" />
                </div>
                <p className="text-[10px] text-[#A1A1A8]/60 mt-1.5">
                  The agent will point callers to book online here.
                </p>
              </div>
            )}
            {onWebsite === false && (
              <p className="text-[11px] text-[#A1A1A8] leading-relaxed">
                No problem — the agent will take reservations directly on the call
                (name, party size, date &amp; time) and log them for you.
              </p>
            )}

            {error && <p className="text-[11px] text-red-400">{error}</p>}

            <button onClick={save} disabled={saving}
              className="w-full flex items-center justify-center gap-1.5 px-4 py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold rounded-lg hover:bg-[#14b3a0] disabled:opacity-50 transition-colors">
              <Check size={13} /> {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
