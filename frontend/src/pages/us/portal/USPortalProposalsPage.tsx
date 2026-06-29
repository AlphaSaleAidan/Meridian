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
import { getPlan } from '@/lib/proposal-plans'
import {
  US_VERTICALS,
  US_GROUPS,
  US_GROUP_ORDER,
  US_DECK_BASE_URL,
  buildUsDeckUrl,
  type UsGroupKey,
  type UsVerticalDeck,
} from '@/data/usVerticals'

// Local aliases — preserve naming used throughout the rest of this file.
type GroupKey = UsGroupKey
type VerticalDeck = UsVerticalDeck

// Headline price the shared decks render in USD (the "most popular" tier). Reps
// still set the exact per-lead price from the lead detail flow; this is the
// browse-page default that forces decks out of their native CAD rendering.
const HEADLINE_MONTHLY = getPlan('premium').price

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

// Per-group className bundles. textClass drives label + icon color; softBgClass
// is the icon tile fill; borderClass the tile border; solidBgClass the active
// FilterChip fill.
const GROUP_CLASSES: Record<GroupKey, { textClass: string; softBgClass: string; borderClass: string; solidBgClass: string }> = {
  food:        { textClass: 'text-amber-400',     softBgClass: 'bg-amber-400/10',     borderClass: 'border-amber-400/20',     solidBgClass: 'bg-amber-400' },
  retail:      { textClass: 'text-[#5fe7d2]',     softBgClass: 'bg-[#5fe7d2]/10',     borderClass: 'border-[#5fe7d2]/20',     solidBgClass: 'bg-[#5fe7d2]' },
  personal:    { textClass: 'text-rose-400',      softBgClass: 'bg-rose-400/10',      borderClass: 'border-rose-400/20',      solidBgClass: 'bg-rose-400' },
  fitness:     { textClass: 'text-lime-400',      softBgClass: 'bg-lime-400/10',      borderClass: 'border-lime-400/20',      solidBgClass: 'bg-lime-400' },
  health:      { textClass: 'text-emerald-400',   softBgClass: 'bg-emerald-400/10',   borderClass: 'border-emerald-400/20',   solidBgClass: 'bg-emerald-400' },
  auto:        { textClass: 'text-indigo-400',    softBgClass: 'bg-indigo-400/10',    borderClass: 'border-indigo-400/20',    solidBgClass: 'bg-indigo-400' },
  hospitality: { textClass: 'text-sky-400',       softBgClass: 'bg-sky-400/10',       borderClass: 'border-sky-400/20',       solidBgClass: 'bg-sky-400' },
  specialty:   { textClass: 'text-amber-300',     softBgClass: 'bg-amber-300/10',     borderClass: 'border-amber-300/20',     solidBgClass: 'bg-amber-300' },
  culture:     { textClass: 'text-purple-300',    softBgClass: 'bg-purple-300/10',    borderClass: 'border-purple-300/20',    solidBgClass: 'bg-purple-300' },
}

type GroupMeta = { label: string; icon: typeof UtensilsCrossed; textClass: string; softBgClass: string; borderClass: string; solidBgClass: string }
const GROUPS: Record<GroupKey, GroupMeta> = US_GROUP_ORDER.reduce((acc, key) => {
  acc[key] = { label: US_GROUPS[key].label, icon: GROUP_ICONS[key], ...GROUP_CLASSES[key] }
  return acc
}, {} as Record<GroupKey, GroupMeta>)

const DECKS: VerticalDeck[] = US_VERTICALS

export default function USPortalProposalsPage() {
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
    return buildUsDeckUrl(slug, rep, HEADLINE_MONTHLY)
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
        <div className="w-10 h-10 rounded-xl bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center">
          <Star size={18} className="text-[#17C5B0]" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-lg font-bold text-white">Sales Proposals</h1>
          <p className="text-[11px] text-[#A1A1A8]">
            Industry-specific Meridian decks · USD pricing baked in · {DECKS.length} verticals · all auto-personalize with your name + email when shared.
          </p>
        </div>
        <a
          href={buildUsDeckUrl('', rep)}
          target="_blank"
          rel="noopener"
          className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[#1F1F23] bg-[#17C5B0]/5 text-[#17C5B0] text-[11px] font-medium hover:bg-[#17C5B0]/10 hover:border-[#17C5B0]/40 transition-colors"
        >
          Open full portal
          <ExternalLink size={12} />
        </a>
      </header>

      {/* Search + filter row */}
      <div className="space-y-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#A1A1A8]" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search verticals — bar, dental, retail, pharmacy…"
            className="w-full pl-9 pr-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#111113] text-white text-sm placeholder-[#A1A1A8] outline-none focus:border-[#17C5B0]/50 focus:ring-2 focus:ring-[#17C5B0]/20 transition-colors"
          />
        </div>

        <div className="flex flex-wrap gap-1.5 overflow-x-auto -mx-1 px-1">
          <FilterChip
            label="All"
            count={groupCounts.all}
            active={activeGroup === 'all'}
            solidBgClass="bg-[#17C5B0]"
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
                solidBgClass={meta.solidBgClass}
                icon={meta.icon}
                onClick={() => setActiveGroup(k)}
              />
            )
          })}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-8 text-center">
          <p className="text-sm text-[#A1A1A8]">No verticals match "{search}". Try a broader term.</p>
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
                className="group rounded-xl border border-[#1F1F23] bg-[#111113] p-4 flex flex-col gap-3 hover:border-[#2a3430] transition-colors"
              >
                <header className="flex items-start gap-2.5">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 border ${meta.softBgClass} ${meta.borderClass}`}>
                    <Icon size={14} className={meta.textClass} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <h3 className="text-sm font-semibold text-white leading-tight">{deck.title}</h3>
                    <div className={`text-[11px] uppercase tracking-wider mt-0.5 ${meta.textClass}`}>
                      {meta.label}
                    </div>
                  </div>
                </header>

                <p className="text-xs text-[#A1A1A8] leading-relaxed">{deck.blurb}</p>

                <dl className="grid grid-cols-2 gap-2 pt-2 border-t border-[#1F1F23]">
                  <div>
                    <dt className="text-[9px] uppercase tracking-wider text-[#A1A1A8]">Avg ticket</dt>
                    <dd className="text-sm text-white font-medium">{deck.avgTicket}</dd>
                  </div>
                  <div>
                    <dt className="text-[9px] uppercase tracking-wider text-[#A1A1A8]">Payback</dt>
                    <dd className="text-xs text-[#17C5B0] font-medium">{deck.payback}</dd>
                  </div>
                </dl>

                <div className="flex gap-2 mt-1">
                  <a
                    href={personalizedUrl(deck.slug)}
                    target="_blank"
                    rel="noopener"
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-[#17C5B0] hover:bg-[#17C5B0]/90 active:scale-[0.98] text-[#0A0A0B] text-xs font-semibold transition-all"
                  >
                    Open
                    <ExternalLink size={11} />
                  </a>
                  <button
                    onClick={() => copyLink(deck.slug)}
                    className={clsx(
                      'inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg border text-xs font-medium transition-all',
                      isCopied
                        ? 'border-[#17C5B0]/40 bg-[#17C5B0]/10 text-[#17C5B0]'
                        : 'border-[#1F1F23] bg-[#111113] text-[#A1A1A8] hover:border-[#2a3430] hover:text-white active:scale-[0.98]'
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

      <footer className="rounded-xl border border-[#1F1F23] bg-[#111113]/50 p-4">
        <h2 className="text-[11px] uppercase tracking-wider text-[#A1A1A8] mb-2">How this works</h2>
        <ul className="text-xs text-[#A1A1A8] space-y-1.5 list-disc pl-4">
          <li>Every deck link auto-includes your name, email{rep?.phone ? ', and phone' : ''} as URL params.</li>
          <li>When the prospect opens it, the cover shows "Prepared by {rep?.name || '[your name]'}" and all email CTAs route to you.</li>
          <li>Add the prospect's business name during lead creation — the deck title becomes "Meridian × [business name]" on their screen.</li>
          <li>All decks render in USD (${HEADLINE_MONTHLY.toLocaleString()}/mo per location) with interactive ROI calculators tuned to each industry's typical economics.</li>
        </ul>
        <p className="text-[10px] text-[#4a5550] mt-3">
          Hosted at {US_DECK_BASE_URL.replace('https://', '')}
        </p>
      </footer>
    </div>
  )
}

interface FilterChipProps {
  label: string
  count: number
  active: boolean
  solidBgClass: string
  icon?: typeof UtensilsCrossed
  onClick: () => void
}

function FilterChip({ label, count, active, solidBgClass, icon: Icon, onClick }: FilterChipProps) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[11px] font-medium transition-all whitespace-nowrap',
        active
          ? `text-[#0A0A0B] border-transparent ${solidBgClass}`
          : 'border-[#1F1F23] bg-[#111113] text-[#A1A1A8] hover:border-[#2a3430] hover:text-white'
      )}
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
