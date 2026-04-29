import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { supabase } from './supabase'

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
}

export interface SalesAuthState {
  ready: boolean
  authenticated: boolean
  rep: SalesRepProfile | null
  login: (email: string, password: string) => Promise<string | null>
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
    sb.auth.getSession().then(async ({ data: { session } }) => {
      if (session?.user) {
        const { data } = await sb
          .from('sales_reps')
          .select('*')
          .eq('email', session.user.email)
          .eq('is_active', true)
          .single()

        if (data) {
          const profile = repFromRow(data)
          saveRep(profile)
          setRep(profile)
        }
      }
      setReady(true)
    })

    const { data: { subscription } } = sb.auth.onAuthStateChange(async (_event, session) => {
      if (session?.user) {
        const { data } = await sb
          .from('sales_reps')
          .select('*')
          .eq('email', session.user.email)
          .eq('is_active', true)
          .single()

        if (data) {
          const profile = repFromRow(data)
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
        commission_rate: 35,
        recruiter: null,
        is_active: true,
        total_earned: 14820,
        total_paid: 9600,
        created_at: new Date(Date.now() - 90 * 86400000).toISOString(),
      }
      saveRep(demoRep)
      setRep(demoRep)
      return null
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return error.message
    if (!data.user) return 'Login failed'

    const { data: repData, error: repErr } = await supabase
      .from('sales_reps')
      .select('*')
      .eq('email', data.user.email)
      .eq('is_active', true)
      .single()

    if (repErr || !repData) {
      await supabase.auth.signOut()
      return 'No active sales rep account found for this email'
    }

    const profile = repFromRow(repData)
    saveRep(profile)
    setRep(profile)
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

function repFromRow(data: Record<string, unknown>): SalesRepProfile {
  return {
    rep_id: data.id as string,
    name: data.name as string,
    email: data.email as string,
    phone: (data.phone as string) || null,
    commission_rate: Number(data.commission_rate) || 30,
    recruiter: (data.recruiter as string) || null,
    is_active: data.is_active as boolean,
    total_earned: Number(data.total_earned) || 0,
    total_paid: Number(data.total_paid) || 0,
    created_at: data.created_at as string,
  }
}
