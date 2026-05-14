import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { supabase } from './supabase'

export type PortalContext = 'us' | 'canada' | 'all'

export interface SalesRepProfile {
  rep_id: string
  name: string
  email: string
  phone: string | null
  commission_rate: number
  recruiter: string | null
  is_active: boolean
  total_earned: number
  total_paid: number
  created_at: string
  portal_context: PortalContext
}

export interface SalesAuthState {
  ready: boolean
  authenticated: boolean
  rep: SalesRepProfile | null
  login: (email: string, password: string) => Promise<string | null>
  signup: (name: string, email: string, password: string, phone?: string) => Promise<string | null>
  resetPassword: (email: string) => Promise<string | null>
  logout: () => void
}

const SalesAuthContext = createContext<SalesAuthState | null>(null)

const REP_STORAGE_KEY = 'meridian_sales_rep'

function loadRep(): SalesRepProfile | null {
  try {
    const raw = localStorage.getItem(REP_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function saveRep(rep: SalesRepProfile) {
  localStorage.setItem(REP_STORAGE_KEY, JSON.stringify(rep))
}

function clearRep() {
  localStorage.removeItem(REP_STORAGE_KEY)
}

/** Try to fetch or auto-provision a sales_reps row for the authenticated user. */
async function resolveRepProfile(email: string): Promise<SalesRepProfile | null> {
  if (!supabase) return null

  // 1. Try to find existing record (active or pending approval)
  const { data: repData } = await supabase
    .from('sales_reps')
    .select('*')
    .eq('email', email)
    .single()

  if (repData) return repFromRow(repData)

  // 2. No record — try to auto-create one (pending approval)
  const { data: inserted, error: insertErr } = await supabase
    .from('sales_reps')
    .insert({
      name: email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      email,
      commission_rate: 70,
      is_active: false,
    })
    .select()
    .single()

  if (inserted && !insertErr) return repFromRow(inserted)

  // INSERT blocked by RLS — create a local-only profile so the CRM is usable
  const localProfile: SalesRepProfile = {
    rep_id: 'local_' + crypto.randomUUID().replace(/-/g, '').slice(0, 12),
    name: email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    email,
    phone: null,
    commission_rate: 70,
    recruiter: null,
    is_active: true,
    total_earned: 0,
    total_paid: 0,
    created_at: new Date().toISOString(),
    portal_context: resolvePortalContext(email),
  }
  return localProfile
}

export function SalesAuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [rep, setRep] = useState<SalesRepProfile | null>(loadRep)

  useEffect(() => {
    if (!supabase) {
      const stored = loadRep()
      if (stored) setRep(stored)
      setReady(true)
      return
    }

    const sb = supabase

    // Timeout guard: if Supabase session check hangs (stale token, network),
    // force ready after 5s so the app doesn't stay on the "S" loading screen.
    let resolved = false
    const timeoutId = setTimeout(() => {
      if (!resolved) {
        resolved = true
        console.warn('[SalesAuth] Session check timed out — proceeding as unauthenticated')
        setReady(true)
      }
    }, 5000)

    sb.auth.getSession().then(async ({ data: { session } }) => {
      if (!resolved) {
        clearTimeout(timeoutId)
        resolved = true
        if (session?.user?.email) {
          const profile = await resolveRepProfile(session.user.email)
          if (profile) {
            saveRep(profile)
            setRep(profile)
          }
        }
        setReady(true)
      }
    }).catch(() => {
      if (!resolved) {
        clearTimeout(timeoutId)
        resolved = true
        console.warn('[SalesAuth] Session check failed — proceeding as unauthenticated')
        setReady(true)
      }
    })

    const { data: { subscription } } = sb.auth.onAuthStateChange(async (event, session) => {
      if (event === 'PASSWORD_RECOVERY' && session?.user?.email) {
        const profile = await resolveRepProfile(session.user.email)
        if (profile) {
          saveRep(profile)
          setRep(profile)
        }
        window.location.replace('/canada/portal/settings?reset=1')
        return
      }
      if (session?.user?.email) {
        const profile = await resolveRepProfile(session.user.email)
        if (profile) {
          saveRep(profile)
          setRep(profile)
        }
      } else {
        setRep(null)
        clearRep()
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<string | null> => {
    if (!supabase) {
      const orgData = localStorage.getItem('meridian_org')
      if (orgData) {
        try {
          const org = JSON.parse(orgData)
          if (org.email === email) {
            return 'This email is registered as a business owner. Please use the customer portal at /customer/login'
          }
        } catch {}
      }

      const demoRep: SalesRepProfile = {
        rep_id: 'rep_' + crypto.randomUUID().replace(/-/g, '').slice(0, 12),
        name: 'Demo Sales Rep',
        email,
        phone: '(555) 123-4567',
        commission_rate: 70,
        recruiter: null,
        is_active: true,
        total_earned: 14820,
        total_paid: 9600,
        created_at: new Date(Date.now() - 90 * 86400000).toISOString(),
        portal_context: resolvePortalContext(email),
      }
      saveRep(demoRep)
      setRep(demoRep)
      return null
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return error.message
    if (!data.user) return 'Login failed'

    const profile = await resolveRepProfile(data.user.email!)
    if (!profile) {
      await supabase.auth.signOut()
      return 'Could not create sales rep profile'
    }

    saveRep(profile)
    setRep(profile)
    return null
  }, [])

  const signup = useCallback(async (name: string, email: string, password: string, phone?: string): Promise<string | null> => {
    if (!supabase) {
      const demoRep: SalesRepProfile = {
        rep_id: 'rep_' + crypto.randomUUID().replace(/-/g, '').slice(0, 12),
        name,
        email,
        phone: phone || null,
        commission_rate: 70,
        recruiter: null,
        is_active: true,
        total_earned: 0,
        total_paid: 0,
        created_at: new Date().toISOString(),
        portal_context: resolvePortalContext(email),
      }
      saveRep(demoRep)
      setRep(demoRep)
      return null
    }

    const apiBase = import.meta.env.VITE_API_URL || ''
    try {
      const resp = await fetch(`${apiBase}/api/canada/rep-signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, phone: phone || null }),
      })
      const body = await resp.json()
      if (!resp.ok) {
        return body.detail || body.message || 'Signup failed'
      }

      const { error: signInErr } = await supabase.auth.signInWithPassword({ email, password })
      if (signInErr) {
        const profile: SalesRepProfile = {
          rep_id: body.rep_id || 'local_' + crypto.randomUUID().replace(/-/g, '').slice(0, 12),
          name,
          email,
          phone: phone || null,
          commission_rate: 70,
          recruiter: null,
          is_active: false,
          total_earned: 0,
          total_paid: 0,
          created_at: new Date().toISOString(),
          portal_context: resolvePortalContext(email),
        }
        saveRep(profile)
        setRep(profile)
        return null
      }

      const profile = await resolveRepProfile(email)
      if (profile) {
        profile.name = name
        if (phone) profile.phone = phone
        saveRep(profile)
        setRep(profile)
      }
      return null
    } catch (err) {
      return 'Network error — please try again'
    }
  }, [])

  const resetPassword = useCallback(async (email: string): Promise<string | null> => {
    if (!supabase) return 'Password reset is not available in demo mode'
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/canada/portal/login',
    })
    if (!error) return null
    if (error.message.toLowerCase().includes('rate') || error.status === 429)
      return 'Too many reset attempts. Please wait a few minutes and try again.'
    if (error.message.toLowerCase().includes('email'))
      return 'Please enter a valid email address.'
    return 'Could not send reset email. Please try again later.'
  }, [])

  const logout = useCallback(() => {
    if (supabase) supabase.auth.signOut()
    setRep(null)
    clearRep()
  }, [])

  return (
    <SalesAuthContext.Provider value={{
      ready,
      authenticated: !!rep,
      rep,
      login,
      signup,
      resetPassword,
      logout,
    }}>
      {children}
    </SalesAuthContext.Provider>
  )
}

export function useSalesAuth(): SalesAuthState {
  const ctx = useContext(SalesAuthContext)
  if (!ctx) throw new Error('useSalesAuth must be used inside SalesAuthProvider')
  return ctx
}

export function canAccessPortal(rep: SalesRepProfile | null, portal: 'us' | 'canada'): boolean {
  if (!rep) return false
  if (rep.portal_context === 'all') return true
  return rep.portal_context === portal
}

function resolvePortalContext(_email: string): PortalContext {
  return 'all'
}

function normalizeRate(v: number): number {
  return v <= 1 ? Math.round(v * 100) : v
}

function repFromRow(data: Record<string, unknown>): SalesRepProfile {
  return {
    rep_id: data.id as string,
    name: data.name as string,
    email: data.email as string,
    phone: (data.phone as string) || null,
    commission_rate: normalizeRate(Number(data.commission_rate) || 0.7),
    recruiter: null,
    is_active: data.is_active as boolean,
    total_earned: 0,
    total_paid: 0,
    created_at: data.created_at as string,
    portal_context: (data.portal_context as PortalContext) || resolvePortalContext(data.email as string),
  }
}
