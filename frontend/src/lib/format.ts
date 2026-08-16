/**
 * Formatting utilities for currency, numbers, dates, and percentages.
 * Currency/locale adapts based on portal path (Canada vs US).
 */

function getLocaleConfig(): { locale: string; currency: string } {
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/canada')) {
    return { locale: 'en-CA', currency: 'CAD' }
  }
  return { locale: 'en-US', currency: 'USD' }
}

/**
 * The symbol this portal quotes prices in.
 *
 * Exported because several modules synthesize their own money strings, and
 * every one of them hardcoded "$" while already converting the amount to
 * Canadian dollars — a Canadian figure under a US sign, which is worse than
 * an unqualified one. One source for the symbol, one answer.
 */
export function currencyPrefix(): string {
  return getLocaleConfig().currency === 'CAD' ? 'CA$' : '$'
}

export function formatCents(cents: number | null | undefined): string {
  const { locale, currency } = getLocaleConfig()
  // `Intl` renders CAD under en-CA as a BARE "$" — the same defect
  // formatCentsCompact already carries a note about, and the reason a Canadian
  // screen could show "CA$1.4K" as its headline and "$1,159.20" directly
  // underneath. On a portal that quotes Canadian prices to Canadian merchants
  // an unqualified "$" is not a formatting slip, it is an ambiguous price.
  const prefix = currencyPrefix()
  if (cents == null) return `${prefix}0.00`
  const dollars = cents / 100
  const sign = dollars < 0 ? '-' : ''
  const amount = Math.abs(dollars).toLocaleString(locale, {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  })
  return `${sign}${prefix}${amount}`
}

export function formatCentsCompact(cents: number | null | undefined): string {
  const { locale } = getLocaleConfig()
  const prefix = currencyPrefix()
  if (cents == null) return `${prefix}0`
  const dollars = cents / 100
  // Magnitude drives the unit, sign is re-applied outside the prefix, so
  // negatives read "-CA$1.2K" rather than "CA$-1.2K" (and no longer skip the
  // K/M branches entirely by failing a `>=` test).
  const sign = dollars < 0 ? '-' : ''
  const abs = Math.abs(dollars)
  if (abs >= 1_000_000) return `${sign}${prefix}${(abs / 1_000_000).toFixed(1)}M`
  if (abs >= 1_000) return `${sign}${prefix}${(abs / 1_000).toFixed(1)}K`
  // Under a thousand, `Intl` renders CAD under en-CA as a bare "$", which put
  // "CA$13.5K" and "$378" side by side in one stat row. Carrying the prefix
  // across every branch makes a single formatter read a single way.
  const amount = abs.toLocaleString(locale, { minimumFractionDigits: 0, maximumFractionDigits: 0 })
  return `${sign}${prefix}${amount}`
}

export function formatNumber(n: number | null | undefined): string {
  if (n == null) return '0'
  const { locale } = getLocaleConfig()
  return n.toLocaleString(locale)
}

export function formatPercent(pct: number | null | undefined, decimals = 1): string {
  if (pct == null) return '0%'
  return `${pct > 0 ? '+' : ''}${pct.toFixed(decimals)}%`
}

export function formatConfidence(score: number | null | undefined): string {
  if (score == null) return '—'
  return `${(score * 100).toFixed(0)}%`
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const { locale } = getLocaleConfig()
  const d = new Date(iso)
  return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' })
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const { locale } = getLocaleConfig()
  const d = new Date(iso)
  return d.toLocaleDateString(locale, {
    month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  })
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  const mins = Math.floor(diff / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d ago`
  return formatDate(iso)
}

export function formatChartTick(v: number): string {
  const sym = getLocaleConfig().currency === 'CAD' ? 'CA$' : '$'
  if (v >= 1000) return `${sym}${(v / 1000).toFixed(0)}K`
  return `${sym}${v}`
}

export function formatChartDate(iso: string): string {
  const { locale } = getLocaleConfig()
  const d = new Date(iso)
  return d.toLocaleDateString(locale, { month: 'short', day: 'numeric' })
}

// ── CAD-specific helpers (whole-dollar input) ──────────────────────────────
// These are the canonical formatters for the Canada portal. They always
// prefix `CA$` regardless of current path, so they're safe to use anywhere
// the value is known to be CAD (the /canada/* portal pages).

export function formatCad(amount: number | null | undefined): string {
  if (amount == null) return 'CA$0'
  return 'CA$' + Math.round(amount).toLocaleString('en-CA')
}

export function formatCadMo(amount: number | null | undefined): string {
  return formatCad(amount) + '/mo'
}

// ── Path-aware merchant-money helpers (whole-dollar input) ─────────────────
// For surfaces mounted under BOTH portals (/canada/* and /us/* or /demo):
// CA$ on Canada paths, plain $ elsewhere. Same output as formatCad on Canada.

export function formatMoney(amount: number | null | undefined): string {
  const { locale, currency } = getLocaleConfig()
  if (currency === 'CAD') return formatCad(amount)
  if (amount == null) return '$0'
  return '$' + Math.round(amount).toLocaleString(locale)
}

export function formatMoneyMo(amount: number | null | undefined): string {
  return formatMoney(amount) + '/mo'
}

// Canonical CAD pricing constants. Replaces hardcoded magic numbers across
// the portal (was: `parseInt(prefill.price) : 250` in the onboarding wizard).
export const PRICING = {
  /** Default monthly plan price in CAD when a customer-specific price is not
   *  supplied via the onboarding prefill query. */
  DEFAULT_MONTHLY_CAD: 250,
} as const
