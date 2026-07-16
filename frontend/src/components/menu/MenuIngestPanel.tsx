import { useRef, useState } from 'react'
import { clsx } from 'clsx'
import {
  Camera, CheckCircle2, ChevronRight, Download, FileSpreadsheet,
  Globe, Loader2, Plug, AlertCircle,
} from 'lucide-react'
import { menuService, type MenuIngestResult } from '@/lib/menu-service'

/**
 * FOUR WAYS TO BUILD YOUR MENU — ranked, one panel, shared by the setup
 * wizard's menu step and the phone settings menu manager.
 *
 *   1. Import from your POS   (shown when a POS is connected; trusted → live)
 *   2. Scrape my website      (URL → review queue)
 *   3. Upload a CSV           (template download + row-by-row errors)
 *   4. Photo of your menu     (vision/OCR → review queue)
 *
 * Manual add stays wherever the host surface already offers it. Everything
 * except POS lands in the review queue — the host should render
 * <MenuReviewTable/> and call back via onIngested to refresh it.
 */

type Busy = 'pos' | 'scrape' | 'csv' | 'photo' | null

interface Props {
  merchantId: string
  posConnected: boolean
  posName?: string
  disabled?: boolean
  /** Fired after any successful ingest so the host refetches items/review. */
  onIngested: (result: { pending_review: number; source: string }) => void
}

export default function MenuIngestPanel({ merchantId, posConnected, posName, disabled, onIngested }: Props) {
  const csvRef = useRef<HTMLInputElement>(null)
  const photoRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState<Busy>(null)
  const [showUrlInput, setShowUrlInput] = useState(false)
  const [url, setUrl] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const locked = disabled || busy !== null

  const finish = (source: string, result: MenuIngestResult | { item_count?: number; needs_review?: number }) => {
    const pending = 'pending_review' in result ? (result.pending_review ?? 0) : (result.needs_review ?? 0)
    const found = 'found' in result ? result.found : (result as { item_count?: number }).item_count ?? 0
    const rowErrors = 'row_errors' in result ? (result.row_errors?.length ?? 0) : 0
    let text = `${found} item${found === 1 ? '' : 's'} found`
    if (pending > 0) text += ` — ${pending} waiting in review below`
    if (rowErrors > 0) text += ` · ${rowErrors} row${rowErrors === 1 ? '' : 's'} had errors`
    setMessage(text)
    onIngested({ pending_review: pending, source })
  }

  const run = async (source: Busy, fn: () => Promise<void>) => {
    setBusy(source); setError(null); setMessage(null)
    try {
      await fn()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'import failed')
    } finally {
      setBusy(null)
    }
  }

  const onPos = () => run('pos', async () => {
    const r = await menuService.syncPos(merchantId)
    if (!r.synced) throw new Error(r.reason || 'POS sync failed')
    finish('pos', { item_count: r.item_count, needs_review: r.needs_review })
  })

  const onScrape = () => run('scrape', async () => {
    finish('scrape', await menuService.scrape(merchantId, url.trim()))
    setShowUrlInput(false)
  })

  const onCsv = (file: File) => run('csv', async () => {
    finish('csv', await menuService.uploadCsv(merchantId, file))
  })

  const onPhoto = (file: File) => run('photo', async () => {
    finish('photo', await menuService.uploadPhoto(merchantId, file))
  })

  const optionCls = (active: boolean) => clsx(
    'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border text-left transition-colors',
    locked ? 'border-[#1F1F23] opacity-50 cursor-not-allowed'
      : active ? 'border-[#1A8FD6]/40 bg-[#1A8FD6]/5'
        : 'border-[#1F1F23] hover:border-[#2A2A30] cursor-pointer',
  )

  // Ranked 1-4 with POS first when connected; without a POS the list renumbers.
  const base = posConnected ? 1 : 0
  const Rank = ({ n }: { n: number }) => (
    <span className="w-5 h-5 rounded-full bg-[#1F1F23] text-[10px] font-semibold text-[#A1A1A8] flex items-center justify-center shrink-0">
      {n}
    </span>
  )

  return (
    <div className="space-y-1.5">
      {/* 1 — POS import (only when connected; the trusted path) */}
      {posConnected && (
        <button type="button" onClick={onPos} disabled={locked} className={optionCls(false)}>
          <Rank n={1} />
          <Plug size={14} className="text-[#17C5B0] shrink-0" />
          <span className="flex-1 min-w-0">
            <span className="block text-xs font-medium text-[#F5F5F7]">
              Import from your POS{posName ? ` (${posName})` : ''}
            </span>
            <span className="block text-[10px] text-[#A1A1A8]">
              Pulls your live catalog — items go straight to the menu.
            </span>
          </span>
          {busy === 'pos' ? <Loader2 size={14} className="animate-spin text-[#A1A1A8]" /> : <ChevronRight size={14} className="text-[#A1A1A8]/50" />}
        </button>
      )}

      {/* 2 — website scrape */}
      <div className={clsx('rounded-lg border transition-colors',
        showUrlInput ? 'border-[#1A8FD6]/40 bg-[#1A8FD6]/5' : 'border-[#1F1F23]')}>
        <button
          type="button"
          onClick={() => !locked && setShowUrlInput(v => !v)}
          disabled={locked}
          className="w-full flex items-center gap-3 px-3 py-2.5 text-left"
        >
          <Rank n={base + 1} />
          <Globe size={14} className="text-[#1A8FD6] shrink-0" />
          <span className="flex-1 min-w-0">
            <span className="block text-xs font-medium text-[#F5F5F7]">Scrape my website</span>
            <span className="block text-[10px] text-[#A1A1A8]">
              We read your menu page — you review everything before it goes live.
            </span>
          </span>
          {busy === 'scrape' ? <Loader2 size={14} className="animate-spin text-[#A1A1A8]" /> : <ChevronRight size={14} className={clsx('text-[#A1A1A8]/50 transition-transform', showUrlInput && 'rotate-90')} />}
        </button>
        {showUrlInput && (
          <div className="flex items-center gap-2 px-3 pb-2.5">
            <input
              className="flex-1 px-3 py-2 bg-[#111113] border border-[#1F1F23] rounded-lg text-xs text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50"
              placeholder="yourrestaurant.com/menu"
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && url.trim()) onScrape() }}
            />
            <button
              type="button"
              onClick={onScrape}
              disabled={locked || !url.trim()}
              className="px-3 py-2 rounded-lg bg-[#1A8FD6] text-white text-xs font-medium hover:bg-[#1A8FD6]/90 disabled:opacity-40 transition-colors"
            >
              Scrape
            </button>
          </div>
        )}
      </div>

      {/* 3 — CSV upload (div+role, not <button> — the template link nests inside) */}
      <div
        role="button"
        tabIndex={0}
        onClick={() => !locked && csvRef.current?.click()}
        onKeyDown={e => { if (!locked && (e.key === 'Enter' || e.key === ' ')) csvRef.current?.click() }}
        className={optionCls(false)}
      >
        <Rank n={base + 2} />
        <FileSpreadsheet size={14} className="text-[#7C5CFF] shrink-0" />
        <span className="flex-1 min-w-0">
          <span className="block text-xs font-medium text-[#F5F5F7]">Upload a CSV</span>
          <span className="block text-[10px] text-[#A1A1A8]">
            name, price, category, sizes… —{' '}
            <a
              href={menuService.csvTemplateUrl}
              download
              onClick={e => e.stopPropagation()}
              className="text-[#7C5CFF] hover:underline inline-flex items-center gap-0.5"
            >
              <Download size={9} /> download the template
            </a>
          </span>
        </span>
        {busy === 'csv' ? <Loader2 size={14} className="animate-spin text-[#A1A1A8]" /> : <ChevronRight size={14} className="text-[#A1A1A8]/50" />}
      </div>

      {/* 4 — photo */}
      <button type="button" onClick={() => photoRef.current?.click()} disabled={locked} className={optionCls(false)}>
        <Rank n={base + 3} />
        <Camera size={14} className="text-[#E0A83C] shrink-0" />
        <span className="flex-1 min-w-0">
          <span className="block text-xs font-medium text-[#F5F5F7]">Photo of your menu</span>
          <span className="block text-[10px] text-[#A1A1A8]">
            Snap a printed menu — we digitize it for your review.
          </span>
        </span>
        {busy === 'photo' ? <Loader2 size={14} className="animate-spin text-[#A1A1A8]" /> : <ChevronRight size={14} className="text-[#A1A1A8]/50" />}
      </button>

      <input
        ref={csvRef} type="file" accept=".csv,text/csv" className="hidden"
        onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (f) onCsv(f) }}
      />
      <input
        ref={photoRef} type="file" accept="image/*" capture="environment" className="hidden"
        onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (f) onPhoto(f) }}
      />

      {message && (
        <p className="flex items-center gap-1.5 text-[11px] text-[#5BC8A0] pt-0.5">
          <CheckCircle2 size={12} className="shrink-0" /> {message}
        </p>
      )}
      {error && (
        <p className="flex items-center gap-1.5 text-[11px] text-[#E06B5E] pt-0.5">
          <AlertCircle size={12} className="shrink-0" /> {error}
        </p>
      )}
    </div>
  )
}
