import { useEffect, useMemo, useState } from 'react'
import { clsx } from 'clsx'
import { AlertTriangle, Check, CheckCheck, Loader2, Trash2 } from 'lucide-react'
import { menuService, type MenuStoreItem } from '@/lib/menu-service'

/**
 * REVIEW-AND-CONFIRM SCREEN — the gate between ingestion and the live menu.
 *
 * Every scraped/CSV/photo item (and priceless POS items) lands here as
 * needs_review. Rows are editable inline (name/price/category), confidence
 * is badged (<0.7 → amber "check this"), and nothing reaches the agent or
 * the public page until it's accepted here. Shared by the setup wizard and
 * the phone settings menu manager.
 */

const LOW_CONFIDENCE = 0.7

interface Draft {
  name: string
  price: string
  category: string
}

interface Props {
  merchantId: string
  items: MenuStoreItem[]
  /** Called after any accept/delete so the parent can refetch. */
  onChanged: () => void
}

function toDraft(item: MenuStoreItem): Draft {
  return {
    name: item.name,
    price: item.price != null ? String(item.price) : '',
    category: item.category || '',
  }
}

function draftEdit(draft: Draft) {
  const edit: { name?: string; price?: number; category?: string } = {}
  if (draft.name.trim()) edit.name = draft.name.trim()
  const price = parseFloat(draft.price)
  if (!Number.isNaN(price) && price >= 0) edit.price = price
  if (draft.category.trim()) edit.category = draft.category.trim()
  return edit
}

export default function MenuReviewTable({ merchantId, items, onChanged }: Props) {
  const [drafts, setDrafts] = useState<Record<string, Draft>>({})
  const [busyId, setBusyId] = useState<string | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Hydrate drafts for new rows; keep in-progress edits across refetches.
  useEffect(() => {
    setDrafts(prev => {
      const next: Record<string, Draft> = {}
      for (const item of items) next[item.id] = prev[item.id] || toDraft(item)
      return next
    })
  }, [items])

  const lowConfidenceCount = useMemo(
    () => items.filter(i => (i.confidence ?? 1) < LOW_CONFIDENCE).length,
    [items],
  )

  if (items.length === 0) return null

  const setDraft = (id: string, patch: Partial<Draft>) =>
    setDrafts(prev => ({ ...prev, [id]: { ...prev[id], ...patch } }))

  const acceptOne = async (item: MenuStoreItem) => {
    setBusyId(item.id); setError(null)
    try {
      await menuService.confirm(merchantId, [{ id: item.id, ...draftEdit(drafts[item.id] || toDraft(item)) }])
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'confirm failed')
    } finally {
      setBusyId(null)
    }
  }

  const deleteOne = async (item: MenuStoreItem) => {
    setBusyId(item.id); setError(null)
    try {
      await menuService.deleteItem(merchantId, item.id)
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'delete failed')
    } finally {
      setBusyId(null)
    }
  }

  const confirmAll = async () => {
    setBulkBusy(true); setError(null)
    try {
      await menuService.confirm(
        merchantId,
        items.map(item => ({ id: item.id, ...draftEdit(drafts[item.id] || toDraft(item)) })),
      )
      onChanged()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'confirm failed')
    } finally {
      setBulkBusy(false)
    }
  }

  return (
    <div className="rounded-lg border border-amber-500/25 bg-amber-500/[0.03] p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <AlertTriangle size={14} className="text-amber-400 shrink-0" />
          <h4 className="text-sm font-semibold text-[#F5F5F7] truncate">
            {items.length} item{items.length === 1 ? '' : 's'} waiting for your review
          </h4>
        </div>
        <button
          type="button"
          onClick={confirmAll}
          disabled={bulkBusy}
          className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-colors"
        >
          {bulkBusy ? <Loader2 size={12} className="animate-spin" /> : <CheckCheck size={12} />}
          Confirm all
        </button>
      </div>
      <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
        Imported items never go live until you confirm them — check names and prices, then accept.
        {lowConfidenceCount > 0 && (
          <span className="text-amber-300/90"> {lowConfidenceCount} highlighted in amber need a closer look.</span>
        )}
      </p>

      <div className="max-h-64 overflow-y-auto space-y-1 pr-1">
        {items.map(item => {
          const draft = drafts[item.id] || toDraft(item)
          const lowConfidence = (item.confidence ?? 1) < LOW_CONFIDENCE
          const busy = busyId === item.id
          return (
            <div
              key={item.id}
              className={clsx(
                'flex items-center gap-2 px-3 py-2 rounded-lg bg-[#111113]',
                lowConfidence && 'ring-1 ring-amber-500/40',
              )}
            >
              <input
                className="flex-1 min-w-0 bg-transparent text-xs text-[#F5F5F7] focus:outline-none"
                value={draft.name}
                aria-label="Item name"
                onChange={e => setDraft(item.id, { name: e.target.value })}
              />
              <input
                className="w-24 bg-transparent text-xs text-[#A1A1A8] focus:outline-none hidden sm:block"
                value={draft.category}
                placeholder="category"
                aria-label="Item category"
                onChange={e => setDraft(item.id, { category: e.target.value })}
              />
              <div className={clsx('flex items-center text-xs font-mono',
                draft.price ? 'text-[#17C5B0]' : 'text-amber-400')}>
                <span>$</span>
                <input
                  className="w-14 bg-transparent text-right focus:outline-none"
                  type="number"
                  step="0.01"
                  min="0"
                  value={draft.price}
                  placeholder="0.00"
                  aria-label="Item price"
                  onChange={e => setDraft(item.id, { price: e.target.value })}
                />
              </div>
              {lowConfidence && (
                <span className="hidden sm:inline text-[9px] font-medium px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-300 whitespace-nowrap">
                  check this
                </span>
              )}
              <span className="text-[9px] text-[#A1A1A8]/50 uppercase w-10 text-center hidden sm:block">
                {item.source}
              </span>
              <button
                type="button"
                onClick={() => acceptOne(item)}
                disabled={busy}
                aria-label={`Accept ${draft.name}`}
                className="p-1.5 rounded-md text-[#17C5B0] hover:bg-[#17C5B0]/10 disabled:opacity-40 transition-colors shrink-0"
              >
                {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
              </button>
              <button
                type="button"
                onClick={() => deleteOne(item)}
                disabled={busy}
                aria-label={`Delete ${draft.name}`}
                className="p-1.5 rounded-md text-[#A1A1A8]/60 hover:text-red-400 hover:bg-red-500/10 disabled:opacity-40 transition-colors shrink-0"
              >
                <Trash2 size={13} />
              </button>
            </div>
          )
        })}
      </div>

      {error && <p className="text-[11px] text-red-400">{error}</p>}
    </div>
  )
}
