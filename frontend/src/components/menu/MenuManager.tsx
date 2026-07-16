import { useCallback, useEffect, useMemo, useState } from 'react'
import { clsx } from 'clsx'
import { Copy, ExternalLink, Globe, ListOrdered, Loader2, Trash2 } from 'lucide-react'
import { menuService, type MenuStoreItem, type PublicMenuInfo } from '@/lib/menu-service'
import MenuIngestPanel from './MenuIngestPanel'
import MenuReviewTable from './MenuReviewTable'

/**
 * MANAGED MENU (phone settings) — the store-backed replacement for the old
 * read-only menu card.
 *
 *   - live items with instant per-item sold-out toggles (PATCH → the agent
 *     prompt and the public /m page update through the store mirror)
 *   - the review queue for ingested items (MenuReviewTable)
 *   - the four ingestion options (MenuIngestPanel)
 *   - the hosted public menu page: publish + copyable /m/{slug} URL
 *
 * Demo mode (no merchantId): renders the provided fallback items read-only.
 */

interface FallbackItem {
  id: string | number
  name: string
  price: number
  category?: string
}

interface Props {
  merchantId: string
  posConnected: boolean
  posName?: string
  /** Demo-mode items (biz.menu) rendered read-only when merchantId is empty. */
  fallbackMenu?: FallbackItem[]
  currency?: string
}

export default function MenuManager({ merchantId, posConnected, posName, fallbackMenu = [], currency = '$' }: Props) {
  const [items, setItems] = useState<MenuStoreItem[]>([])
  const [loaded, setLoaded] = useState(false)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [publicInfo, setPublicInfo] = useState<PublicMenuInfo | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!merchantId) return
    try {
      const res = await menuService.getItems(merchantId)
      setItems(res.items)
      setLoaded(true)
    } catch { /* store not reachable — fallback view below */ }
    try {
      setPublicInfo(await menuService.getPublicInfo(merchantId))
    } catch { /* optional */ }
  }, [merchantId])

  useEffect(() => { reload() }, [reload])

  const pending = useMemo(() => items.filter(i => i.needs_review), [items])
  const live = useMemo(() => items.filter(i => i.published && !i.needs_review), [items])

  const toggleSoldOut = async (item: MenuStoreItem) => {
    setBusyId(item.id); setError(null)
    // Optimistic — the toggle should feel instant.
    setItems(prev => prev.map(i => (i.id === item.id ? { ...i, sold_out: !i.sold_out } : i)))
    try {
      await menuService.patchItem(merchantId, item.id, { sold_out: !item.sold_out })
    } catch (err) {
      setItems(prev => prev.map(i => (i.id === item.id ? { ...i, sold_out: item.sold_out } : i)))
      setError(err instanceof Error ? err.message : 'update failed')
    } finally {
      setBusyId(null)
    }
  }

  const removeItem = async (item: MenuStoreItem) => {
    setBusyId(item.id); setError(null)
    try {
      await menuService.deleteItem(merchantId, item.id)
      await reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'delete failed')
    } finally {
      setBusyId(null)
    }
  }

  const publish = async () => {
    setPublishing(true); setError(null)
    try {
      const res = await menuService.publish(merchantId)
      setPublicInfo({ published: true, slug: res.slug, url: res.url })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'publish failed')
    } finally {
      setPublishing(false)
    }
  }

  const copyUrl = async () => {
    if (!publicInfo?.url) return
    try {
      await navigator.clipboard.writeText(publicInfo.url)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard unavailable */ }
  }

  const priceOf = (item: MenuStoreItem): string => {
    if (item.size_prices && Object.keys(item.size_prices).length) {
      return Object.entries(item.size_prices)
        .map(([size, price]) => `${size} ${currency}${Number(price).toFixed(0)}`)
        .join(' / ')
    }
    return item.price != null ? `${currency}${Number(item.price).toFixed(2)}` : '—'
  }

  // Demo / store-unavailable: the old read-only card.
  if (!merchantId || !loaded) {
    return (
      <div className="card p-4 space-y-3">
        <div className="flex items-center gap-2">
          <ListOrdered size={14} className="text-[#1A8FD6]" />
          <h3 className="text-sm font-semibold text-[#F5F5F7]">Menu ({fallbackMenu.length} items)</h3>
        </div>
        <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
          {fallbackMenu.map(item => (
            <div key={item.id} className="flex items-center justify-between px-3 py-1.5 bg-[#111113] rounded-lg">
              <div>
                <p className="text-xs text-[#F5F5F7]">{item.name}</p>
                <p className="text-[9px] text-[#A1A1A8]">{item.category}</p>
              </div>
              <span className="text-xs font-mono text-[#17C5B0]">{currency}{item.price.toFixed(2)}</span>
            </div>
          ))}
        </div>
        {!merchantId && (
          <p className="text-[10px] text-[#A1A1A8]/60">Menu management is available once your account is live.</p>
        )}
      </div>
    )
  }

  return (
    <div className="card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <ListOrdered size={14} className="text-[#1A8FD6]" />
        <h3 className="text-sm font-semibold text-[#F5F5F7]">Menu ({live.length} live item{live.length === 1 ? '' : 's'})</h3>
      </div>

      {/* Review queue first — pending items block nothing but deserve attention. */}
      {pending.length > 0 && (
        <MenuReviewTable merchantId={merchantId} items={pending} onChanged={reload} />
      )}

      {/* Live items with sold-out toggles */}
      <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
        {live.length === 0 && (
          <p className="text-[10px] text-[#A1A1A8]/60 py-3 text-center">
            No items yet — build your menu with the options below.
          </p>
        )}
        {live.map(item => (
          <div
            key={item.id}
            className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#111113]',
              item.sold_out && 'opacity-60')}
          >
            <div className="flex-1 min-w-0">
              <p className={clsx('text-xs text-[#F5F5F7] truncate', item.sold_out && 'line-through')}>{item.name}</p>
              <p className="text-[9px] text-[#A1A1A8]">{item.category || ''}</p>
            </div>
            <span className="text-xs font-mono text-[#17C5B0] whitespace-nowrap">{priceOf(item)}</span>
            <button
              type="button"
              onClick={() => toggleSoldOut(item)}
              disabled={busyId === item.id}
              aria-label={item.sold_out ? `Mark ${item.name} back in stock` : `Mark ${item.name} sold out`}
              title={item.sold_out ? 'Sold out — tap to restore' : 'In stock — tap to mark sold out'}
              className={clsx('relative w-8 h-4 rounded-full transition-colors shrink-0',
                item.sold_out ? 'bg-[#2A2A30]' : 'bg-[#17C5B0]')}
            >
              <span className={clsx('absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform',
                item.sold_out ? 'left-0.5' : 'left-[18px]')} />
            </button>
            <button
              type="button"
              onClick={() => removeItem(item)}
              disabled={busyId === item.id}
              aria-label={`Remove ${item.name}`}
              className="text-[#A1A1A8]/40 hover:text-red-400 transition-colors shrink-0"
            >
              <Trash2 size={12} />
            </button>
          </div>
        ))}
      </div>
      <p className="text-[9px] text-[#A1A1A8]/50">
        Sold-out items stay off the phone agent's menu (it apologizes if asked) and show a
        "Sold out today" chip on your public menu page.
      </p>

      {/* Ingestion options */}
      <MenuIngestPanel
        merchantId={merchantId}
        posConnected={posConnected}
        posName={posName}
        onIngested={reload}
      />

      {/* Hosted public menu page */}
      <div className="rounded-lg border border-[#1F1F23] bg-[#0E0E10] p-3 space-y-2">
        <div className="flex items-center gap-2">
          <Globe size={13} className="text-[#17C5B0]" />
          <h4 className="text-xs font-semibold text-[#F5F5F7]">Public menu page</h4>
        </div>
        {publicInfo?.published && publicInfo.url ? (
          <div className="flex items-center gap-2">
            <code className="flex-1 min-w-0 truncate px-2.5 py-1.5 rounded-md bg-[#111113] text-[11px] text-[#17C5B0]">
              {publicInfo.url}
            </code>
            <button
              type="button"
              onClick={copyUrl}
              className="px-2 py-1.5 rounded-md border border-[#1F1F23] text-[10px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors flex items-center gap-1"
            >
              <Copy size={10} /> {copied ? 'Copied' : 'Copy'}
            </button>
            <a
              href={publicInfo.url}
              target="_blank"
              rel="noreferrer"
              className="px-2 py-1.5 rounded-md border border-[#1F1F23] text-[10px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors flex items-center gap-1"
            >
              <ExternalLink size={10} /> View
            </a>
          </div>
        ) : (
          <div className="flex items-center justify-between gap-3">
            <p className="text-[10px] text-[#A1A1A8] leading-relaxed">
              Get a shareable menu link — the phone agent mentions it when callers ask to see the menu.
            </p>
            <button
              type="button"
              onClick={publish}
              disabled={publishing || live.length === 0}
              className="shrink-0 px-3 py-1.5 rounded-lg bg-[#17C5B0] text-[#0A0A0B] text-xs font-semibold hover:bg-[#17C5B0]/90 disabled:opacity-40 transition-colors flex items-center gap-1.5"
            >
              {publishing && <Loader2 size={11} className="animate-spin" />} Publish
            </button>
          </div>
        )}
      </div>

      {error && <p className="text-[11px] text-red-400">{error}</p>}
    </div>
  )
}
