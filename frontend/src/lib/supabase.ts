import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || ''
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

if (!supabaseUrl || !supabaseAnonKey) {
  console.error('[Meridian] Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY — running without Supabase (demo mode)')
}

const noLock = <R>(_name: string, _acquireTimeout: number, fn: () => Promise<R>): Promise<R> => fn()

export const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey, {
      auth: { lock: noLock },
    })
  : null

export async function getAuthHeaders(): Promise<Record<string, string>> {
  const base = { 'Content-Type': 'application/json' }
  if (!supabase) return base
  let session = (await supabase.auth.getSession()).data?.session ?? null
  // Refresh proactively when the access token is missing or within 30s of
  // expiry. getSession() returns the stored (possibly stale) session without
  // blocking on a refresh, so backend calls that forward this token would
  // otherwise hit `Invalid or expired token` (401).
  const expiresAtMs = (session?.expires_at ?? 0) * 1000
  const expiringSoon = expiresAtMs > 0 && expiresAtMs < Date.now() + 30_000
  if (!session?.access_token || expiringSoon) {
    session = (await supabase.auth.refreshSession()).data?.session ?? session
  }
  const token = session?.access_token
  if (!token) return base
  return { ...base, 'Authorization': `Bearer ${token}` }
}
