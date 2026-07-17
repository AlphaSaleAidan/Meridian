import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth, checkIsSalesRep } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import PasswordInput from '@/components/ui/PasswordInput'
import { MapPin } from 'lucide-react'

export default function CanadaLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { ready, authenticated, org, logout, isRecovery } = useAuth()

  const from = (location.state as { from?: string })?.from || '/canada/merchant'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForgot, setShowForgot] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)
  const [cleared, setCleared] = useState(false)
  const [justLoggedIn, setJustLoggedIn] = useState(false)
  const [loggingIn, setLoggingIn] = useState(false)
  const [mustReset, setMustReset] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  // Give the tab a real title instead of inheriting the generic landing title.
  useEffect(() => {
    document.title = 'Sign in — Meridian Canada'
  }, [])

  // When Supabase fires PASSWORD_RECOVERY (user clicked email reset link), show
  // the set-password form instead of auto-logging the recovery session out.
  useEffect(() => {
    if (isRecovery && authenticated && !mustReset && !cleared) {
      setMustReset(true)
      setCleared(true) // prevent the auto-logout branch below from racing
    }
  }, [isRecovery, authenticated, mustReset, cleared])

  useEffect(() => {
    if (!ready) return
    // A sign-in is in flight: signInWithPassword fires onAuthStateChange (which
    // flips `authenticated` true) before handleLogin can set mustReset/justLoggedIn.
    // Without this guard the auto-logout branch below would race in and kill the
    // fresh session mid-login — the "spinner then nothing loads" symptom.
    if (loggingIn) return
    // Hold on the page while the customer sets a new password on first login or
    // after clicking an email reset link — the session is valid, don't logout.
    if (mustReset) return
    // isRecovery: PASSWORD_RECOVERY session — handled by the effect above.
    if (isRecovery) return
    if (authenticated && !justLoggedIn && !cleared) {
      logout().then(() => setCleared(true))
      return
    }
    if (!justLoggedIn || !authenticated || !org) return
    if (!org.onboarded) {
      navigate('/canada/setup', { replace: true })
      return
    }
    navigate(from, { replace: true })
  }, [ready, authenticated, org, from, navigate, justLoggedIn, cleared, logout, mustReset, loggingIn, isRecovery])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setLoggingIn(true)

    if (!supabase) {
      setError('Authentication service unavailable')
      setLoading(false)
      setLoggingIn(false)
      return
    }

    const { data, error: authError } = await supabase.auth.signInWithPassword({ email, password })
    if (authError) {
      setLoading(false)
      setError(authError.message)
      setLoggingIn(false)
      return
    }
    // Section isolation: sales-rep accounts sign in at the rep portal login,
    // never here — mirror of the gate in sales-auth that keeps customers out
    // of the rep portal.
    const repRole = String(data.user?.user_metadata?.role ?? '').toLowerCase() === 'sales_rep'
    const isRepAccount = repRole || await checkIsSalesRep(data.user?.email || email)
    if (isRepAccount) {
      await supabase.auth.signOut()
      setLoading(false)
      setError('This is a sales rep account. Please sign in at the rep portal: /canada/portal/login')
      setLoggingIn(false)
      return
    }
    setLoading(false)
    // First login with a rep-issued temporary password — force a reset before
    // letting the customer into the portal.
    if (data.user?.user_metadata?.must_reset_password) {
      setCleared(true)
      setMustReset(true)
      setLoggingIn(false)
      return
    }
    setJustLoggedIn(true)
    setLoggingIn(false)
  }

  async function handleSetNewPassword(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!supabase) { setError('Authentication service unavailable'); return }
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    const { error: updateError } = await supabase.auth.updateUser({
      password: newPassword,
      data: { must_reset_password: false },
    })
    setLoading(false)
    if (updateError) {
      setError(updateError.message)
      return
    }
    setMustReset(false)
    setJustLoggedIn(true)
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
          <Link to="/canada" aria-label="Meridian Canada home" className="flex items-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </Link>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <MapPin size={12} className="text-[#17C5B0]" />
            <span className="text-[11px] text-[#17C5B0] font-semibold uppercase tracking-wider">Canada</span>
          </div>
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <h2 className="text-lg font-bold text-[#F5F5F7] text-center mb-1">
            {mustReset ? 'Set your password' : showForgot ? 'Reset password' : 'Sign in to your account'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {mustReset
              ? 'Choose a new password to finish setting up your account'
              : showForgot
                ? "We'll send a reset link to your email"
                : 'Enter the credentials provided by your Meridian rep'}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-xs text-[#17C5B0]">{success}</div>
          )}

          {mustReset ? (
            <form onSubmit={handleSetNewPassword} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">New password</label>
                <PasswordInput required value={newPassword} onChange={e => setNewPassword(e.target.value)} className={inputClass} placeholder="At least 8 characters" autoComplete="new-password" autoFocus />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Confirm password</label>
                <PasswordInput required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className={inputClass} placeholder="Re-enter your password" autoComplete="new-password" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Saving...' : 'Set password & continue'}
              </button>
            </form>
          ) : !showForgot ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@email.com" autoComplete="username" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
                <PasswordInput required value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Enter your password" autoComplete="current-password" />
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
