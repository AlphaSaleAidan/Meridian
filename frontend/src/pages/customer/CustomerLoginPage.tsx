import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import PasswordInput from '@/components/ui/PasswordInput'

export default function CustomerLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { authenticated, login, resetPassword } = useAuth()

  // Land customers on the current merchant portal (pillars + connect wizard),
  // not the legacy /app dashboard. A deep-link in location.state (e.g. an OAuth
  // return) still wins; only the bare-login default changed.
  const from = (location.state as { from?: string })?.from || '/us/merchant'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForgot, setShowForgot] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  // Rep-issued temp password flow: force a reset before entering the portal.
  const [mustReset, setMustReset] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  useEffect(() => {
    if (authenticated && !mustReset) navigate(from, { replace: true })
  }, [authenticated, mustReset, from, navigate])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const err = await login(email, password)
    if (err) {
      setLoading(false)
      setError(err)
      return
    }
    // First login with a rep-issued temporary password — force a reset before
    // letting the customer into the portal.
    if (supabase) {
      const { data } = await supabase.auth.getUser()
      if (data.user?.user_metadata?.must_reset_password) {
        setMustReset(true)
        setLoading(false)
        return
      }
    }
    setLoading(false)
    navigate(from, { replace: true })
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
    navigate(from, { replace: true })
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const err = await resetPassword(email)
    setLoading(false)
    if (err) { setError(err); return }
    setSuccess('If that email exists, a reset link has been sent.')
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors'
  const btnClass = 'w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex items-center justify-center mb-8">
          <Link to="/" aria-label="Meridian home" className="flex items-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </Link>
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <h2 className="text-lg font-bold text-[#F5F5F7] text-center mb-1">
            {mustReset ? 'Set your password' : showForgot ? 'Reset password' : 'Welcome back'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {mustReset
              ? 'Your temporary password worked — now choose your own to finish setup'
              : showForgot ? "We'll send a reset link to your email" : 'Sign in to your Meridian dashboard'}
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
                <label htmlFor="new-password" className="block text-xs font-medium text-[#A1A1A8] mb-1.5">New password</label>
                <PasswordInput id="new-password" required value={newPassword} onChange={e => setNewPassword(e.target.value)} className={inputClass} placeholder="At least 8 characters" />
              </div>
              <div>
                <label htmlFor="confirm-password" className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Confirm password</label>
                <PasswordInput id="confirm-password" required value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className={inputClass} placeholder="Repeat your new password" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Saving...' : 'Save & Continue'}
              </button>
            </form>
          ) : !showForgot ? (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label htmlFor="login-email" className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input id="login-email" type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@business.com" />
              </div>
              <div>
                <label htmlFor="login-password" className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
                <PasswordInput id="login-password" required value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Enter your password" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
              <div className="flex items-center justify-between text-[11px]">
                <button type="button" onClick={() => { setShowForgot(true); setError(null); setSuccess(null) }} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Forgot password?
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label htmlFor="forgot-email" className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input id="forgot-email" type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@business.com" />
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

          {!showForgot && !mustReset && (
            <p className="text-center text-[11px] text-[#A1A1A8] mt-5">
              Don't have an account?{' '}
              <Link to="/customer/signup" className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors font-medium">
                Sign up
              </Link>
            </p>
          )}
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian
        </p>
      </div>
    </div>
  )
}
