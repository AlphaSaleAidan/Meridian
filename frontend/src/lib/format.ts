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

export function formatCents(cents: number | null | undefined): string {
  if (cents == null) return '$0.00'
  const { locale, currency } = getLocaleConfig()
  const dollars = cents / 100
  return dollars.toLocaleString(locale, { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export function formatCentsCompact(cents: number | null | undefined): string {
  if (cents == null) return '$0'
  const { locale, currency } = getLocaleConfig()
  const dollars = cents / 100
  const prefix = currency === 'CAD' ? 'CA$' : '$'
  if (dollars >= 1_000_000) return `${prefix}${(dollars / 1_000_000).toFixed(1)}M`
  if (dollars >= 1_000) return `${prefix}${(dollars / 1_000).toFixed(1)}K`
  return dollars.toLocaleString(locale, { style: 'currency', currency, minimumFractionDigits: 0, maximumFractionDigits: 0 })
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
