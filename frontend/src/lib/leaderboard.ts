import { getAuthHeaders } from './supabase'

/**
 * Peer-visible aggregate leaderboard — GET /api/leaderboard.
 *
 * The scoped roster endpoints (/api/canada/team, /api/us/team) intentionally
 * collapse to self+downline+upline for non-admins (#334), which turned the
 * Leaderboard tab into a board of one for leaf reps. This endpoint returns
 * ALL active reps in the caller's portal with ONLY aggregate, leaderboard-safe
 * fields — no emails, no phones, no lead rows, no commission details.
 */
export interface LeaderboardEntry {
  id: string
  name: string
  role: string
  deals_won: number
  deals_open: number
  total_mrr: number
}

export async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  const apiBase = import.meta.env.VITE_API_URL || ''
  const headers = await getAuthHeaders()
  const resp = await fetch(`${apiBase}/api/leaderboard`, { headers })
  if (!resp.ok) throw new Error(`Failed to load leaderboard (${resp.status})`)
  const data = await resp.json()
  return (data.leaderboard || []) as LeaderboardEntry[]
}
