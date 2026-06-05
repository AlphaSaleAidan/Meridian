import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import { MapPin } from 'lucide-react'

export default function CanadaLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { ready, authenticated, org, logout } = useAuth()

  const from = (location.state as { from?: string })?.from || '/canada/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForgot, setShowForgot] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [cleared, setCleared] = useState(false)
  const [justLoggedIn, setJustLoggedIn] = useState(false)

  useEffect(() => {
    if (!ready) return
    // Clear a stale session on arrival, but never while a sign-in is in flight —
    // an async logout that resolves after signInWithPassword would wipe the fresh
    // session and force the user to click "Sign In" a second time.
    if (authenticated && !justLoggedIn && !cleared && !loading) {
      setCleared(true)
      logout()
      return
    }
    if (!justLoggedIn || !authenticated || !org) return
    if (!org.onboarded) {
      navigate('/canada/setup', { replace: true })
      return
    }
    navigate(from, { replace: true })
  }, [ready, authenticated, org, from, navigate, justLoggedIn, cleared, loading, logout])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!supabase) {
      setError('Authentication service unavailable')
      setLoading(false)
      return
    }

    // Tear down any stale session first, awaited, so it can't race with this sign-in.
    if (authenticated) {
      setCleared(true)
      await logout()
    }

    const { error: authError } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (authError) {
      setError(authError.message)
    } else {
      setJustLoggedIn(true)
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    if (!supabase) { setLoading(false); return }
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: window.location.origin + '/canada/login',
    })
    setLoading(false)
    if (resetError) { setError(resetError.message); return }
    setSuccess('If that email exists, a reset link has been sent.')
  }

  if (!ready) {
    return (
      <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
        <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
          <span className="text-[#1A8FD6] font-bold text-sm">M</span>
        </div>
      </div>
    )
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors'
  const btnClass = 'w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="flex items-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <MapPin size={12} className="text-[#17C5B0]" />
            <span className="text-[11px] text-[#17C5B0] font-semibold uppercase tracking-wider">Canada</span>
          </div>
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <h2 className="text-lg font-bold text-[#F5F5F7] text-center mb-1">
            {showForgot ? 'Reset password' : 'Sign in to your account'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {showForgot ? "We'll send a reset link to your email" : 'Enter the credentials provided by your Meridian rep'}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-xs text-[#17C5B0]">{success}</div>
          )}

          {!showForgot ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@email.com" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
                <input type="password" required value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Enter your password" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
              <div className="flex items-center justify-between text-[11px]">
                <button type="button" onClick={() => { setShowForgot(true); setError(null); setSuccess(null) }} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Forgot password?
                </button>
                <button type="button" onClick={() => navigate('/canada/onboard')} className="text-[#17C5B0] hover:text-[#1A8FD6] transition-colors">
                  Create account
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@email.com" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                <button type="button" onClick={() => { setShowForgot(false); setError(null); setSuccess(null) }} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Back to sign in
                </button>
              </p>
            </form>
          )}
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian Canada v0.2.0
        </p>
      </div>
    </div>
  )
}
