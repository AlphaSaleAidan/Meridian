import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

export default function CustomerLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { authenticated, login, resetPassword } = useAuth()

  const from = (location.state as { from?: string })?.from || '/app'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForgot, setShowForgot] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (authenticated) navigate(from, { replace: true })
  }, [authenticated, from, navigate])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const err = await login(email, password)
    setLoading(false)
    if (err) setError(err)
    else navigate(from, { replace: true })
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
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <MeridianEmblem size={36} />
          <MeridianWordmark className="text-xl" />
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <h2 className="text-lg font-bold text-[#F5F5F7] text-center mb-1">
            {showForgot ? 'Reset password' : 'Welcome back'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {showForgot ? "We'll send a reset link to your email" : 'Sign in to your Meridian dashboard'}
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
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@business.com" />
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
              </div>
            </form>
          ) : (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@business.com" />
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

          {!showForgot && (
            <p className="text-center text-[11px] text-[#A1A1A8] mt-5">
              Don't have an account?{' '}
              <Link to="/customer/signup" className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors font-medium">
                Sign up
              </Link>
            </p>
          )}
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian POS Intelligence v0.2.0
        </p>
      </div>
    </div>
  )
}
