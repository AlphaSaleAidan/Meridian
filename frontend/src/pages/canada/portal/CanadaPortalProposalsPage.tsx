import { useMemo, useState } from 'react'
import { clsx } from 'clsx'
import {
  Search,
  ExternalLink,
  Copy,
  Check,
  UtensilsCrossed,
  ShoppingBag,
  Sparkles,
  Activity,
  HeartPulse,
  Car,
  BedDouble,
  Hammer,
  Palette,
  Star,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import {
  CAD_VERTICALS,
  CAD_GROUPS,
  CAD_GROUP_ORDER,
  DECK_BASE_URL,
  type CadGroupKey,
  type CadVerticalDeck,
} from '@/data/cadVerticals'

// Local aliases — preserve naming used throughout the rest of this file.
type GroupKey = CadGroupKey
type VerticalDeck = CadVerticalDeck

// Group metadata extended with icons (icons stay UI-local; data lives in shared module).
const GROUP_ICONS: Record<GroupKey, typeof UtensilsCrossed> = {
  food:        UtensilsCrossed,
  retail:      ShoppingBag,
  personal:    Sparkles,
  fitness:     Activity,
  health:      HeartPulse,
  auto:        Car,
  hospitality: BedDouble,
  specialty:   Hammer,
  culture:     Palette,
}

const GROUPS: Record<GroupKey, { label: string; icon: typeof UtensilsCrossed; color: string }> =
  CAD_GROUP_ORDER.reduce((acc, key) => {
    acc[key] = { label: CAD_GROUPS[key].label, icon: GROUP_ICONS[key], color: CAD_GROUPS[key].color }
    return acc
  }, {} as Record<GroupKey, { label: string; icon: typeof UtensilsCrossed; color: string }>)

const DECKS: VerticalDeck[] = CAD_VERTICALS

// (Legacy inline catalog removed — data now lives in @/data/cadVerticals.)

export default function CanadaPortalProposalsPage() {
  const { rep } = useSalesAuth()
  const [activeGroup, setActiveGroup] = useState<GroupKey | 'all'>('all')
  const [search, setSearch] = useState('')
  const [copiedSlug, setCopiedSlug] = useState<string | null>(null)

  const groupCounts = useMemo(() => {
    const c: Record<string, number> = { all: DECKS.length }
    for (const k of Object.keys(GROUPS)) c[k] = DECKS.filter(d => d.group === k).length
    return c
  }, [])

  const filtered = useMemo(() => {
    let list = DECKS
    if (activeGroup !== 'all') list = list.filter(d => d.group === activeGroup)
    const q = search.trim().toLowerCase()
    if (q) {
      list = list.filter(d =>
        d.title.toLowerCase().includes(q) ||
        d.blurb.toLowerCase().includes(q) ||
        d.slug.toLowerCase().includes(q)
      )
    }
    return list
  }, [activeGroup, search])

  function personalizedUrl(slug: string): string {
    const params = new URLSearchParams()
    if (rep?.name) params.set('rep', rep.name)
    if (rep?.email) params.set('email', rep.email)
    if (rep?.phone) params.set('phone', rep.phone)
    const q = params.toString()
    return `${DECK_BASE_URL}/${slug}${q ? `?${q}` : ''}`
  }

  async function copyLink(slug: string) {
    try {
      await navigator.clipboard.writeText(personalizedUrl(slug))
      setCopiedSlug(slug)
      setTimeout(() => setCopiedSlug(prev => (prev === slug ? null : prev)), 1800)
    } catch {
      // ignore
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center">
          <Star size={18} className="text-[#00d4aa]" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold text-white">Sales Proposals</h1>
          <p className="text-[11px] text-[#6b7a74]">
            Industry-specific Meridian decks · CAD pricing baked in · {DECKS.length} verticals · all auto-personalize with your name + email when shared.
          </p>
        </div>
        <a
          href={`${DECK_BASE_URL}/ca${(() => {
            const params = new URLSearchParams()
            if (rep?.name) params.set('rep', rep.name)
            if (rep?.email) params.set('email', rep.email)
            if (rep?.phone) params.set('phone', rep.phone)
            const q = params.toString()
            return q ? `?${q}` : ''
          })()}`}
          target="_blank"
          rel="noopener"
          className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1a3a30] bg-[#00d4aa]/5 text-[#00d4aa] text-[11px] font-medium hover:bg-[#00d4aa]/10 hover:border-[#00d4aa]/40 transition-colors"
        >
          Open full portal
          <ExternalLink size={12} />
        </a>
      </header>

      {/* Search + filter row */}
      <div className="space-y-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6b7a74]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search verticals — bar, dental, retail, pharmacy…"
            className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-[#1f2a26] bg-[#0a0e0c] text-white text-[13px] placeholder-[#6b7a74] outline-none focus:border-[#00d4aa]/50 focus:ring-2 focus:ring-[#00d4aa]/20 transition-colors"
          />
        </div>

        <div className="flex flex-wrap gap-1.5 overflow-x-auto -mx-1 px-1">
          <FilterChip
            label="All"
            count={groupCounts.all}
            active={activeGroup === 'all'}
            color="#00d4aa"
            onClick={() => setActiveGroup('all')}
          />
          {(Object.keys(GROUPS) as GroupKey[]).map(k => {
            const meta = GROUPS[k]
            return (
              <FilterChip
                key={k}
                label={meta.label}
                count={groupCounts[k]}
                active={activeGroup === k}
                color={meta.color}
                icon={meta.icon}
                onClick={() => setActiveGroup(k)}
              />
            )
          })}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-[#1f2a26] bg-[#0a0e0c] p-8 text-center">
          <p className="text-[13px] text-[#6b7a74]">No verticals match "{search}". Try a broader term.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {filtered.map(deck => {
            const meta = GROUPS[deck.group]
            const Icon = meta.icon
            const isCopied = copiedSlug === deck.slug
            return (
              <article
                key={deck.slug}
                className="group rounded-xl border border-[#1f2a26] bg-gradient-to-b from-[#0a0e0c] to-[#070a09] p-4 flex flex-col gap-3 hover:border-[#1a3a30] transition-colors"
              >
                <header className="flex items-start gap-2.5">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                    style={{ background: `${meta.color}15`, border: `1px solid ${meta.color}30` }}
                  >
                    <Icon size={14} style={{ color: meta.color }} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-[14px] font-semibold text-white leading-tight">{deck.title}</h3>
                    <div className="text-[10px] uppercase tracking-wider mt-0.5" style={{ color: meta.color }}>
                      {meta.label}
                    </div>
                  </div>
                </header>

                <p className="text-[12px] text-[#a0a8a4] leading-relaxed">{deck.blurb}</p>

                <dl className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1a201c]">
                  <div>
                    <dt className="text-[9px] uppercase tracking-wider text-[#6b7a74]">Avg ticket</dt>
                    <dd className="text-[13px] text-white font-medium">{deck.avgTicket}</dd>
                  </div>
                  <div>
                    <dt className="text-[9px] uppercase tracking-wider text-[#6b7a74]">Payback</dt>
                    <dd className="text-[12px] text-[#00d4aa] font-medium">{deck.payback}</dd>
                  </div>
                </dl>

                <div className="flex gap-2 mt-1">
                  <a
                    href={personalizedUrl(deck.slug)}
                    target="_blank"
                    rel="noopener"
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#00d4aa] hover:bg-[#00bd97] active:scale-[0.98] text-[#001a14] text-[12px] font-semibold transition-all"
                  >
                    Open
                    <ExternalLink size={11} />
                  </a>
                  <button
                    onClick={() => copyLink(deck.slug)}
                    className={clsx(
                      'inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border text-[12px] font-medium transition-all',
                      isCopied
                        ? 'border-[#00d4aa]/40 bg-[#00d4aa]/10 text-[#00d4aa]'
                        : 'border-[#1f2a26] bg-[#0a0e0c] text-[#a0a8a4] hover:border-[#1a3a30] hover:text-white active:scale-[0.98]'
                    )}
                    title="Copy personalized link"
                  >
                    {isCopied ? <Check size={11} /> : <Copy size={11} />}
                    {isCopied ? 'Copied' : 'Copy link'}
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      )}

      <footer className="rounded-xl border border-[#1f2a26] bg-[#0a0e0c]/50 p-4">
        <h2 className="text-[11px] uppercase tracking-wider text-[#6b7a74] mb-2">How this works</h2>
        <ul className="text-[12px] text-[#a0a8a4] space-y-1.5 list-disc pl-4">
          <li>Every deck link auto-includes your name, email{rep?.phone ? ', and phone' : ''} as URL params.</li>
          <li>When the prospect opens it, the cover shows "Prepared by {rep?.name || '[your name]'}" and all email CTAs route to you.</li>
          <li>Add the prospect's business name during lead creation — the deck title becomes "Meridian × [business name]" on their screen.</li>
          <li>All decks are CAD-priced (C$350/mo per location) and feature interactive ROI calculators tuned to each industry's typical economics.</li>
        </ul>
      </footer>
    </div>
  )
}

interface FilterChipProps {
  label: string
  count: number
  active: boolean
  color: string
  icon?: typeof UtensilsCrossed
  onClick: () => void
}

function FilterChip({ label, count, active, color, icon: Icon, onClick }: FilterChipProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[11px] font-medium transition-all whitespace-nowrap',
        active
          ? 'text-[#001a14] border-transparent'
          : 'border-[#1f2a26] bg-[#0a0e0c] text-[#a0a8a4] hover:border-[#1a3a30] hover:text-white'
      )}
      style={active ? { background: color } : undefined}
    >
      {Icon && <Icon size={11} />}
      {label}
      <span
        className={clsx('text-[9px] font-mono', active ? 'opacity-70' : 'opacity-50')}
      >
        {count}
      </span>
    </button>
  )
}
