import { useEffect, useMemo, useState } from 'react'
import { clsx } from 'clsx'
import {
  CheckCircle2, ExternalLink, Loader2, Lock, Plug,
  Store, CreditCard, Calculator, CalendarClock, Wallet, Bike,
  ShoppingBag, BookOpenCheck, Heart, Megaphone, Boxes, Landmark,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import { useIsDemo, useOrgId } from '@/hooks/useOrg'
import { useAuth } from '@/lib/auth'

const API_BASE = import.meta.env.VITE_API_URL || ''

// Server-driven catalog — /api/integrations/catalog is the single source of
// truth so a provider flipping from partner→oauth (or unverified→verified)
// changes this page with zero frontend edits.
interface CatalogItem {
  key: string
  label: string
  category: string
  tier: 'live' | 'oauth' | 'manual' | 'partner'
  configured: boolean
  verified?: boolean
  connected: boolean
  connection_status: string
  authorize_path: string | null
  status_path: string | null
  description: string
  note: string
  docs_url: string
}

interface Catalog {
  categories: { key: string; label: string }[]
  integrations: CatalogItem[]
  connected_count: number
}

const CATEGORY_ICONS: Record<string, typeof Store> = {
  pos: Store,
  payments: CreditCard,
  accounting: Calculator,
  tax: Landmark,
  scheduling: CalendarClock,
  payroll: Wallet,
  delivery: Bike,
  ordering: ShoppingBag,
  reservations: BookOpenCheck,
  loyalty: Heart,
  marketing: Megaphone,
  inventory: Boxes,
}

export default function IntegrationsHubPage() {
  const orgId = useOrgId()
  const isDemo = useIsDemo()
  const { user, org } = useAuth()
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [loadError, setLoadError] = useState('')
  const [filter, setFilter] = useState<string>('all')
  // key of the provider whose OAuth tab is open (poll its status until it lands)
  const [waitingKey, setWaitingKey] = useState<string | null>(null)
  const [requested, setRequested] = useState<Record<string, boolean>>({})

  const requestEmail = user?.email || (org as { email?: string } | null)?.email || ''

  async function loadCatalog() {
    try {
      const qs = orgId && orgId !== 'demo' ? `?org_id=${encodeURIComponent(orgId)}` : ''
      const res = await fetch(`${API_BASE}/api/integrations/catalog${qs}`)
      if (!res.ok) throw new Error(`API ${res.status}`)
      setCatalog(await res.json())
      setLoadError('')
    } catch {
      setLoadError('Could not load the integrations catalog — retrying may help.')
    }
  }

  useEffect(() => { loadCatalog() }, [orgId]) // eslint-disable-line react-hooks/exhaustive-deps

  // While an OAuth tab is open, poll that provider's status endpoint (same
  // pattern as POSSelectorPanel) and refresh the catalog when it lands.
  useEffect(() => {
    if (!waitingKey || !orgId || orgId === 'demo') return
    const item = catalog?.integrations.find(i => i.key === waitingKey)
    if (!item?.status_path) return
    let active = true
    const tick = async () => {
      try {
        const res = await fetch(
          `${API_BASE}${item.status_path}?org_id=${encodeURIComponent(orgId)}`)
        if (!res.ok) return
        const st = await res.json()
        if (active && st?.connected) {
          setWaitingKey(null)
          loadCatalog()
        }
      } catch { /* transient — keep polling */ }
    }
    const id = setInterval(tick, 4000)
    return () => { active = false; clearInterval(id) }
  }, [waitingKey, orgId]) // eslint-disable-line react-hooks/exhaustive-deps

  function startConnect(item: CatalogItem) {
    if (isDemo || !item.authorize_path) return
    if (!orgId || orgId === 'demo') return
    const ret = encodeURIComponent(window.location.pathname)
    window.open(
      `${API_BASE}${item.authorize_path}?org_id=${encodeURIComponent(orgId)}&return_to=${ret}`,
      '_blank', 'noopener',
    )
    setWaitingKey(item.key)
  }

  async function requestAccess(item: CatalogItem) {
    if (!requestEmail || requested[item.key]) return
    setRequested(r => ({ ...r, [item.key]: true }))
    try {
      await fetch(`${API_BASE}/api/pos/waitlist`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: requestEmail,
          pos_system: item.key,
          org_id: orgId && orgId !== 'demo' ? orgId : null,
        }),
      })
    } catch {
      // The optimistic flag stays — demand capture is best-effort.
    }
  }

  const items = catalog?.integrations ?? []
  const visible = useMemo(
    () => (filter === 'all' ? items : items.filter(i => i.category === filter)),
    [items, filter],
  )
  // Only offer chips for categories that actually have entries.
  const presentCategories = useMemo(() => {
    const present = new Set(items.map(i => i.category))
    return (catalog?.categories ?? []).filter(c => present.has(c.key))
  }, [catalog, items])

  const categoryLabel = (key: string) =>
    catalog?.categories.find(c => c.key === key)?.label ?? key

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#F5F5F7]">Integrations</h1>
          <p className="text-sm text-[#A1A1A8] mt-1">
            Connect the tools your restaurant already runs on — most in one click.
          </p>
        </div>
        {catalog && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <Plug className="w-4 h-4 text-[#17C5B0]" />
            <span className="text-sm text-[#17C5B0] font-medium">
              {catalog.connected_count} connected
            </span>
          </div>
        )}
      </div>

      {loadError && (
        <div className="mb-6 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {loadError}
        </div>
      )}

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          onClick={() => setFilter('all')}
          className={clsx(
            'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
            filter === 'all'
              ? 'bg-[#1A8FD6]/15 border-[#1A8FD6]/40 text-[#1A8FD6]'
              : 'border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#A1A1A8]/40',
          )}
        >
          All
        </button>
        {presentCategories.map(c => (
          <button
            key={c.key}
            onClick={() => setFilter(c.key)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors',
              filter === c.key
                ? 'bg-[#1A8FD6]/15 border-[#1A8FD6]/40 text-[#1A8FD6]'
                : 'border-[#1F1F23] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#A1A1A8]/40',
            )}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Grid */}
      {!catalog && !loadError && (
        <div className="flex items-center justify-center py-20 text-[#A1A1A8]">
          <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading catalog…
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {visible.map(item => {
          const Icon = CATEGORY_ICONS[item.category] ?? Plug
          const oneClick = !!item.authorize_path && !item.connected
          const waiting = waitingKey === item.key
          return (
            <div
              key={item.key}
              className={clsx(
                'rounded-xl border p-4 flex flex-col bg-[#101013]',
                item.connected ? 'border-[#17C5B0]/40' : 'border-[#1F1F23]',
              )}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  {/* Monogram mark — inline SVG-style, no vendor logo assets */}
                  <div className="w-9 h-9 rounded-lg bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center shrink-0">
                    <Icon className="w-4.5 h-4.5 text-[#1A8FD6]" strokeWidth={1.75} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-sm font-semibold text-[#F5F5F7] truncate">{item.label}</div>
                    <div className="text-[11px] text-[#A1A1A8]/70">{categoryLabel(item.category)}</div>
                  </div>
                </div>
                {item.connected && (
                  <span className="flex items-center gap-1 text-[11px] font-medium text-[#17C5B0] shrink-0">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Connected
                  </span>
                )}
              </div>

              <p className="text-xs text-[#A1A1A8] mt-3 leading-relaxed flex-1">
                {item.description}
              </p>
              {item.note && (
                <p className="text-[11px] text-[#A1A1A8]/60 mt-2 leading-relaxed">{item.note}</p>
              )}

              <div className="mt-4 flex items-center gap-2">
                {item.connected ? (
                  <Link
                    to="/app/settings"
                    className="text-[11px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors"
                  >
                    Manage in Settings
                  </Link>
                ) : oneClick ? (
                  <button
                    onClick={() => startConnect(item)}
                    disabled={waiting}
                    className={clsx(
                      'px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors',
                      waiting
                        ? 'bg-[#1A8FD6]/10 text-[#1A8FD6] cursor-default'
                        : 'bg-[#1A8FD6] text-white hover:bg-[#1678B4]',
                    )}
                  >
                    {waiting ? (
                      <span className="flex items-center gap-1.5">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" /> Waiting for approval…
                      </span>
                    ) : 'Connect'}
                  </button>
                ) : item.tier === 'manual' ? (
                  <Link
                    to="/app/settings"
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[#1A8FD6]/40 text-[#1A8FD6] hover:bg-[#1A8FD6]/10 transition-colors"
                  >
                    Connect with credentials
                  </Link>
                ) : item.tier === 'oauth' ? (
                  <span className="flex items-center gap-1.5 text-[11px] font-medium text-[#A1A1A8]/70">
                    <Lock className="w-3.5 h-3.5" /> Coming soon
                  </span>
                ) : requested[item.key] ? (
                  <span className="flex items-center gap-1 text-[11px] font-medium text-[#17C5B0]">
                    <CheckCircle2 className="w-3.5 h-3.5" /> Request recorded
                  </span>
                ) : (
                  <button
                    onClick={() => requestAccess(item)}
                    disabled={!requestEmail}
                    title={requestEmail ? undefined : 'Sign in to request this integration'}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold border border-[#7C5CFF]/40 text-[#7C5CFF] hover:bg-[#7C5CFF]/10 transition-colors disabled:opacity-50"
                  >
                    Request access
                  </button>
                )}
                {item.docs_url && (
                  <a
                    href={item.docs_url}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto text-[#A1A1A8]/50 hover:text-[#A1A1A8] transition-colors"
                    aria-label={`${item.label} developer docs`}
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {catalog && visible.length === 0 && (
        <div className="text-center py-16 text-sm text-[#A1A1A8]">
          Nothing in this category yet.
        </div>
      )}
    </div>
  )
}
