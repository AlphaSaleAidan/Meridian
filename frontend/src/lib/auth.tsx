import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react'
import { supabase } from './supabase'

export interface OrgProfile {
  org_id: string
  business_name: string
  owner_name: string
  email: string
  plan: 'trial' | 'starter' | 'growth' | 'enterprise'
  pos_provider: string | null
  created_at: string
  onboarded: boolean
}

export interface AuthState {
  ready: boolean
  authenticated: boolean
  user: { id: string; email: string } | null
  org: OrgProfile | null
  pendingBusiness: { id: string; name: string; ownerName: string; email: string } | null
  login: (email: string, password: string) => Promise<string | null>
  signup: (email: string, password: string, fullName: string, businessName: string) => Promise<string | null>
  logout: () => Promise<void>
  validateToken: (token: string) => Promise<string | null>
}

const AuthContext = createContext<AuthState | null>(null)

const ORG_STORAGE_KEY = 'meridian_org'
const TOKEN_STORAGE_KEY = 'meridian_pending_token'

function loadOrg(): OrgProfile | null {
  try {
    const raw = localStorage.getItem(ORG_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function saveOrg(org: OrgProfile) {
  localStorage.setItem(ORG_STORAGE_KEY, JSON.stringify(org))
}

function clearAuth() {
  localStorage.removeItem(ORG_STORAGE_KEY)
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

function orgFromBusiness(data: Record<string, unknown>, fallbackEmail: string): OrgProfile {
  return {
    org_id: data.id as string,
    business_name: (data.name as string) || '',
    owner_name: (data.owner_name as string) || '',
    email: (data.email as string) || fallbackEmail,
    plan: (data.plan_tier as OrgProfile['plan']) || 'trial',
    pos_provider: (data.pos_provider as string) || null,
    created_at: data.created_at as string,
    onboarded: (data.onboarded as boolean) || false,
  }
}

async function fetchBusinessForUser(userId: string, email: string): Promise<OrgProfile | null> {
  if (!supabase) return loadOrg()

  const { data } = await supabase
    .from('businesses')
    .select('*')
    .eq('owner_user_id', userId)
    .single()

  if (data) {
    const org = orgFromBusiness(data, email)
    saveOrg(org)
    return org
  }

  return loadOrg()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [user, setUser] = useState<{ id: string; email: string } | null>(null)
  const [org, setOrg] = useState<OrgProfile | null>(loadOrg)
  const [pendingBusiness, setPendingBusiness] = useState<{
    id: string; name: string; ownerName: string; email: string
  } | null>(null)

  useEffect(() => {
    if (!supabase) {
      const stored = loadOrg()
      if (stored) setOrg(stored)
      setReady(true)
      return
    }

    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        const u = { id: session.user.id, email: session.user.email || '' }
        setUser(u)
        fetchBusinessForUser(u.id, u.email).then(o => {
          if (o) setOrg(o)
          setReady(true)
        })
      } else {
        setReady(true)
      }
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        const u = { id: session.user.id, email: session.user.email || '' }
        setUser(u)
        fetchBusinessForUser(u.id, u.email).then(o => { if (o) setOrg(o) })
      } else {
        setUser(null)
        setOrg(null)
        clearAuth()
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<string | null> => {
    if (!supabase) {
      const stored = loadOrg()
      if (stored) { setOrg(stored); setUser({ id: 'local', email }) }
      return null
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return error.message
    if (data.user) {
      const u = { id: data.user.id, email: data.user.email || email }
      setUser(u)
      const o = await fetchBusinessForUser(u.id, u.email)
      if (o) setOrg(o)
    }
    return null
  }, [])

  const signup = useCallback(async (
    email: string, password: string, fullName: string, businessName: string,
  ): Promise<string | null> => {
    if (!supabase) {
      const org: OrgProfile = {
        org_id: 'biz_' + crypto.randomUUID().replace(/-/g, '').slice(0, 16),
        business_name: businessName, owner_name: fullName, email,
        plan: 'trial', pos_provider: null, created_at: new Date().toISOString(), onboarded: false,
      }
      saveOrg(org)
      setUser({ id: 'local', email })
      setOrg(org)
      return null
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, business_name: businessName },
        emailRedirectTo: window.location.origin + '/portal',
      },
    })
    if (error) return error.message
    if (!data.user) return 'Signup failed — please try again'

    const userId = data.user.id
    const userEmail = data.user.email || email

    const storedToken = localStorage.getItem(TOKEN_STORAGE_KEY)
    if (storedToken) {
      await supabase.rpc('redeem_access_token', {
        input_token: storedToken,
        redeeming_user_id: userId,
      })
      localStorage.removeItem(TOKEN_STORAGE_KEY)
      setPendingBusiness(null)
    } else {
      await supabase.rpc('create_business_for_user', {
        user_id: userId,
        biz_name: businessName,
        biz_owner_name: fullName,
        biz_email: userEmail,
      })
    }

    if (data.session) {
      const u = { id: userId, email: userEmail }
      setUser(u)
      const o = await fetchBusinessForUser(u.id, u.email)
      if (o) setOrg(o)
      return null
    }

    return '__confirm_email__'
  }, [])

  const logout = useCallback(async () => {
    if (supabase) await supabase.auth.signOut()
    setUser(null)
    setOrg(null)
    clearAuth()
  }, [])

  const validateToken = useCallback(async (token: string): Promise<string | null> => {
    if (!supabase) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
      return null
    }

    const { data, error } = await supabase.rpc('validate_access_token', { input_token: token })
    if (error || !data?.valid) return 'Invalid or expired access token'

    localStorage.setItem(TOKEN_STORAGE_KEY, token)
    setPendingBusiness({
      id: data.business_id,
      name: data.business_name,
      ownerName: data.owner_name,
      email: data.email || '',
    })
    return null
  }, [])

  return (
    <AuthContext.Provider value={{
      ready,
      authenticated: supabase ? !!user : (!!user || !!org),
      user,
      org,
      pendingBusiness,
      login,
      signup,
      logout,
      validateToken,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
