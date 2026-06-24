import { useRef, useState } from 'react'
import { clsx } from 'clsx'
import { Camera, Loader2, CheckCircle2, AlertCircle } from 'lucide-react'
import { useOrgId, useIsDemo } from '@/hooks/useOrg'
import { phoneService, type MenuScanResult } from '@/lib/phone-service'

/**
 * SUPPLEMENTARY MENU BUILDER (photo).
 *
 * Lets a merchant photograph a paper / printed menu (or daily-specials board).
 * The image is sent to POST /api/phone/menu/scan-photo, a vision model extracts
 * {name, price, category}, and the backend MERGES the items onto the existing
 * phone-agent menu (POS-synced or hand-entered). Pairs with <MenuBuildStatus/>:
 * that shows the POS-built menu; this adds items the POS doesn't carry.
 *
 * Demo: the file picker + backend call are disabled (no real merchant row).
 */
type UiState = 'idle' | 'scanning' | 'done' | 'error'

export default function MenuPhotoScanner() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const inputRef = useRef<HTMLInputElement>(null)
  const [state, setState] = useState<UiState>('idle')
  const [result, setResult] = useState<MenuScanResult | null>(null)
  const [error, setError] = useState<string>('')

  const disabled = isDemo || !orgId || state === 'scanning'

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // allow re-picking the same file
    if (!file || !orgId) return
    setState('scanning'); setError(''); setResult(null)
    try {
      const r = await phoneService.scanMenuPhoto(orgId, file)
      setResult(r)
      setState('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'scan failed')
      setState('error')
    }
  }

  return (
    <div className="rounded-lg border border-[#1F1F23] bg-[#0E0E10] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-[#F5F5F7] flex items-center gap-1.5">
            <Camera size={14} className="text-[#1A8FD6]" /> Scan a paper menu
          </h4>
          <p className="text-[11px] text-[#A1A1A8] mt-0.5">
            Photograph a printed menu or specials board — we read it and add the items to your phone menu.
          </p>
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={disabled}
          className={clsx(
            'shrink-0 px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5',
            disabled
              ? 'bg-[#1F1F23] text-[#A1A1A8]/50 cursor-not-allowed'
              : 'bg-[#1A8FD6] text-white hover:bg-[#1A8FD6]/90',
          )}
        >
          {state === 'scanning' ? <><Loader2 size={13} className="animate-spin" /> Reading…</> : <><Camera size={13} /> Scan menu</>}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={onPick}
        />
      </div>

      {isDemo && (
        <p className="text-[11px] text-[#A1A1A8]/60 mt-2">Available once your account is live.</p>
      )}

      {state === 'done' && result && (
        <div className="mt-2.5 flex items-start gap-2 text-[12px] text-[#5BC8A0]">
          <CheckCircle2 size={14} className="mt-0.5 shrink-0" />
          <div>
            {result.added > 0
              ? <span><b>{result.added}</b> new item{result.added === 1 ? '' : 's'} added — menu now has <b>{result.item_count}</b>.</span>
              : <span className="text-[#A1A1A8]">{result.reason || 'No new items found in that photo.'}</span>}
            {result.sample && result.sample.length > 0 && (
              <span className="block text-[#A1A1A8] mt-0.5">
                {result.sample.map(s => s.name).join(' · ')}
              </span>
            )}
          </div>
        </div>
      )}

      {state === 'error' && (
        <div className="mt-2.5 flex items-center gap-2 text-[12px] text-[#E06B5E]">
          <AlertCircle size={14} className="shrink-0" /> {error}
        </div>
      )}
    </div>
  )
}
