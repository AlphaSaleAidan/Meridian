// Sales regions — isolated rep territories inside a portal (20260812).
//
// A region is a named, walled-off group of reps. The backend is the
// enforcement plane (hierarchy.partition_by_region + /api/leaderboard): a
// region member only ever receives their own region's roster and is excluded
// from the portal leaderboard. Everything in this file is presentation —
// display names, per-region leaderboard opt-out, and the region's visual
// identity in the Team section.
//
// First tenant: 'odyssey' — Enoch Cheung's territory. One login spans both
// portals (portal_context='all' on his sales_reps row); the leaderboard is
// off at his request (revisit when he wants it back: flip showLeaderboard).

export interface SalesRegion {
  id: string
  /** Display name shown as the Team-section title for region members. */
  name: string
  /** false = the Leaderboard tab does not exist for this region's members. */
  showLeaderboard: boolean
  /** Two-tone theme, used ONLY inside the Team section for region members. */
  theme: {
    /** Metallic accent (borders, initials, wordmark). */
    accent: string
    /** Deep base for the banner gradient. */
    deep: string
    /** Lighter stop for the banner gradient. */
    mid: string
  }
}

export const REGIONS: Record<string, SalesRegion> = {
  odyssey: {
    id: 'odyssey',
    name: 'Odyssey Region',
    showLeaderboard: false,
    // Aegean navy + antique gold — deliberately distinct from the core portal
    // teal so a region member always knows whose waters they are in.
    theme: {
      accent: '#C9A24B',
      deep: '#0B1D33',
      mid: '#13314F',
    },
  },
}

/** Region for a rep's `region` slug; null for core-team reps. */
export function getRegion(regionId: string | null | undefined): SalesRegion | null {
  if (!regionId) return null
  return REGIONS[regionId] ?? null
}

// Demo mode only (no Supabase configured): map known emails to a region so
// the portals are previewable without a backend. Real sessions get `region`
// from their sales_reps row — this list is never consulted for them.
const DEMO_REGION_EMAILS: Record<string, string> = {
  'cheungenochmgmt@gmail.com': 'odyssey',
  'enoch@odyssey.demo': 'odyssey',
}

export function resolveDemoRegion(email: string | null | undefined): string | null {
  const key = (email ?? '').trim().toLowerCase()
  if (!key) return null
  if (DEMO_REGION_EMAILS[key]) return DEMO_REGION_EMAILS[key]
  return key.includes('odyssey') ? 'odyssey' : null
}
