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

  // 1. Try to find existing record
  const { data: repData } = await supabase
    .from('sales_reps')
    .select('*')
    .eq('email', email)
    .eq('is_active', true)
    .single()

  if (repData) return repFromRow(repData)

  // 2. No record — try to auto-create one
  const { data: inserted, error: insertErr } = await supabase
    .from('sales_reps')
    .insert({
      name: email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      email,
      commission_rate: 70,
      is_active: true,
      total_earned: 0,
      total_paid: 0,
    })
    .select()
    .single()

  if (inserted && !insertErr) return repFromRow(inserted)

  // 3. INSERT blocked by RLS — create a local-only profile so the CRM is usable
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

    const { data: { subscription } } = sb.auth.onAuthStateChange(async (_event, session) => {
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
      // No Supabase — demo mode, just create local rep
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

    // 1. Create Supabase auth account
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) return error.message
    if (!data.user) return 'Signup failed'

    // 2. Try to create sales_reps record
    const { error: insertErr } = await supabase
      .from('sales_reps')
      .insert({ name, email, phone: phone || null, commission_rate: 70, is_active: true, total_earned: 0, total_paid: 0 })

    // 3. Resolve profile (handles INSERT failure gracefully)
    const profile = await resolveRepProfile(email)
    if (profile) {
      // Override name from the signup form
      profile.name = name
      if (phone) profile.phone = phone
      saveRep(profile)
      setRep(profile)
    }

    return null
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

function resolvePortalContext(email: string): PortalContext {
  const e = email.toLowerCase()
  if (e.includes('enoch')) return 'canada'
  if (e.includes('aidan')) return 'all'
  return 'all'
}

function repFromRow(data: Record<string, unknown>): SalesRepProfile {
  return {
    rep_id: data.id as string,
    name: data.name as string,
    email: data.email as string,
    phone: (data.phone as string) || null,
    commission_rate: Number(data.commission_rate) || 70,
    recruiter: (data.recruiter as string) || null,
    is_active: data.is_active as boolean,
    total_earned: Number(data.total_earned) || 0,
    total_paid: Number(data.total_paid) || 0,
    created_at: data.created_at as string,
    portal_context: (data.portal_context as PortalContext) || resolvePortalContext(data.email as string),
  }
}
