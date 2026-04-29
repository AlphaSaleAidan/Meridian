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
  login: (email: string, password: string) => Promise<string | null>
  signup: (email: string, password: string, fullName: string, businessName: string) => Promise<string | null>
  logout: () => Promise<void>
  redeemToken: (token: string) => Promise<string | null>
}

const AuthContext = createContext<AuthState | null>(null)

const ORG_STORAGE_KEY = 'meridian_org'
const TOKEN_STORAGE_KEY = 'meridian_access_token'

function loadOrg(): OrgProfile | null {
  try {
    const raw = localStorage.getItem(ORG_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

function saveOrg(org: OrgProfile) {
  localStorage.setItem(ORG_STORAGE_KEY, JSON.stringify(org))
}

function clearOrg() {
  localStorage.removeItem(ORG_STORAGE_KEY)
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

function generateOrgId(): string {
  return 'org_' + crypto.randomUUID().replace(/-/g, '').slice(0, 16)
}

async function provisionOrg(
  userId: string,
  email: string,
  fullName: string,
  businessName: string,
): Promise<OrgProfile> {
  const org: OrgProfile = {
    org_id: generateOrgId(),
    business_name: businessName,
    owner_name: fullName,
    email,
    plan: 'trial',
    pos_provider: null,
    created_at: new Date().toISOString(),
    onboarded: false,
  }

  if (supabase) {
    await supabase.from('organizations').upsert({
      id: org.org_id,
      owner_user_id: userId,
      business_name: businessName,
      owner_name: fullName,
      email,
      plan: 'trial',
      created_at: org.created_at,
    }, { onConflict: 'owner_user_id' }).select().single()

    const { data } = await supabase
      .from('organizations')
      .select('*')
      .eq('owner_user_id', userId)
      .single()

    if (data) {
      org.org_id = data.id
      org.business_name = data.business_name
      org.plan = data.plan || 'trial'
      org.pos_provider = data.pos_provider || null
      org.onboarded = data.onboarded || false
      org.created_at = data.created_at
    }
  }

  saveOrg(org)
  return org
}

async function fetchOrgForUser(userId: string, email: string): Promise<OrgProfile | null> {
  if (!supabase) return loadOrg()

  const { data } = await supabase
    .from('organizations')
    .select('*')
    .eq('owner_user_id', userId)
    .single()

  if (data) {
    const org: OrgProfile = {
      org_id: data.id,
      business_name: data.business_name,
      owner_name: data.owner_name || '',
      email: data.email || email,
      plan: data.plan || 'trial',
      pos_provider: data.pos_provider || null,
      created_at: data.created_at,
      onboarded: data.onboarded || false,
    }
    saveOrg(org)
    return org
  }

  return loadOrg()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const [user, setUser] = useState<{ id: string; email: string } | null>(null)
  const [org, setOrg] = useState<OrgProfile | null>(loadOrg)

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
        fetchOrgForUser(u.id, u.email).then(o => {
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
        fetchOrgForUser(u.id, u.email).then(o => { if (o) setOrg(o) })
      } else {
        setUser(null)
        setOrg(null)
        clearOrg()
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<string | null> => {
    if (!supabase) {
      const stored = loadOrg()
      if (stored) {
        setOrg(stored)
        setUser({ id: 'local', email })
      }
      return null
    }

    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) return error.message
    if (data.user) {
      const u = { id: data.user.id, email: data.user.email || email }
      setUser(u)
      const o = await fetchOrgForUser(u.id, u.email)
      if (o) setOrg(o)
    }
    return null
  }, [])

  const signup = useCallback(async (
    email: string, password: string, fullName: string, businessName: string
  ): Promise<string | null> => {
    if (!supabase) {
      const org = await provisionOrg('local', email, fullName, businessName)
      setUser({ id: 'local', email })
      setOrg(org)
      return null
    }

    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName, business_name: businessName } },
    })
    if (error) return error.message

    if (data.user) {
      const u = { id: data.user.id, email: data.user.email || email }
      setUser(u)
      const org = await provisionOrg(u.id, email, fullName, businessName)
      setOrg(org)
    }
    return null
  }, [])

  const logout = useCallback(async () => {
    if (supabase) await supabase.auth.signOut()
    setUser(null)
    setOrg(null)
    clearOrg()
  }, [])

  const redeemToken = useCallback(async (token: string): Promise<string | null> => {
    if (!supabase) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token)
      return null
    }

    const { data, error } = await supabase
      .from('access_tokens')
      .select('*, organizations(*)')
      .eq('token', token)
      .eq('redeemed', false)
      .single()

    if (error || !data) return 'Invalid or expired access token'

    await supabase.from('access_tokens').update({ redeemed: true, redeemed_at: new Date().toISOString() }).eq('id', data.id)

    if (data.organizations) {
      const o: OrgProfile = {
        org_id: data.organizations.id,
        business_name: data.organizations.business_name,
        owner_name: data.organizations.owner_name || '',
        email: data.organizations.email || '',
        plan: data.organizations.plan || 'trial',
        pos_provider: data.organizations.pos_provider || null,
        created_at: data.organizations.created_at,
        onboarded: data.organizations.onboarded || false,
      }
      saveOrg(o)
      setOrg(o)
    }
    return null
  }, [])

  return (
    <AuthContext.Provider value={{
      ready,
      authenticated: !!user || !!org,
      user,
      org,
      login,
      signup,
      logout,
      redeemToken,
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
