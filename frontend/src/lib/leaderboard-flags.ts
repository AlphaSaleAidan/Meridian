// The Canada rep leaderboard is hidden for a 30-day window (2026-08-07 →
// 2026-09-06) at Aidan's request — a presentation change only. Scoring, the
// /api/leaderboard endpoint and every stored deal stay untouched, so the board
// returns with real standings when the window lapses; nothing to backfill.
//
// The window closes on its own: the date is compared at render time in the
// viewer's browser, so no redeploy is needed to bring the board back. To end
// the hide early, move LEADERBOARD_HIDDEN_UNTIL into the past. US portal is
// deliberately untouched.
export const LEADERBOARD_HIDDEN_UNTIL = '2026-09-06'

/** True while the Canada leaderboard is inside its hidden window. */
export function isLeaderboardHidden(now: Date = new Date()): boolean {
  // Explicit Eastern offset — the build host runs CEST, so a bare date string
  // would flip the board back a few hours early.
  return now.getTime() < new Date(`${LEADERBOARD_HIDDEN_UNTIL}T00:00:00-04:00`).getTime()
}
