import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { MeridianEmblem } from '@/components/MeridianLogo'
import PasswordInput from '@/components/ui/PasswordInput'

export default function CanadaPortalLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { authenticated, login, resetPassword } = useSalesAuth()

  const from = (location.state as { from?: string })?.from || '/canada/portal/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showForgot, setShowForgot] = useState(false)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (authenticated) navigate(from, { replace: true })
  }, [authenticated, from, navigate])

  async function handleSubmit(e: React.FormEvent) {
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
    setSuccess(null)
    if (!email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError('Please enter a valid email address')
      return
    }
    setLoading(true)
    const err = await resetPassword(email)
    setLoading(false)
    if (err) { setError(err); return }
    setSuccess('If that email is registered, a reset link has been sent. Check your inbox.')
  }

  const inputClass = 'w-full px-3 py-2.5 bg-pm-surface border border-pm-border rounded-lg text-sm text-pm-text placeholder-pm-muted/40 focus:outline-none focus:border-pm-teal/50 focus:ring-1 focus:ring-pm-teal/20 transition-colors'
  const btnClass = 'w-full py-2.5 bg-pm-teal text-pm-bg text-sm font-semibold rounded-lg hover:bg-pm-teal/90 disabled:opacity-50 transition-all'

  return (
    <div className="min-h-screen bg-pm-bg flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-1 mb-8">
          <Link to="/canada" aria-label="Meridian Canada home">
            <MeridianEmblem size={40} />
          </Link>
          <span className="text-xl font-bold text-pm-text mt-2">Meridian Sales</span>
          <span className="text-2xs font-semibold text-pm-teal uppercase tracking-widest flex items-center gap-1">
            Canada CRM
            {/* maple leaf (mdi leaf-maple, Apache-2.0) — brand rule: SVG, not color emoji */}
            <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" aria-hidden="true">
              <path d="M21.79,13L16,16L17,18L13,17.25V21H11V17.25L7,18L8,16L2.21,13L3.21,11.27L1.61,8L5.21,7.77L6.21,6L9.63,9.9L8,5H10L12,2L14,5H16L14.37,9.9L17.79,6L18.79,7.73L22.39,7.96L20.79,11.19L21.79,13Z" />
            </svg>
          </span>
        </div>

        <div className="card p-6 sm:p-8 border border-pm-border">
          <p className="text-sm text-pm-muted text-center mb-6">
            {showForgot ? "Enter your email and we'll send a reset link." : 'Sign in to access your pipeline and leads.'}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-pm-teal/10 border border-pm-teal/20 text-xs text-pm-teal">{success}</div>
          )}

          {!showForgot ? (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-pm-muted mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@meridian.com" />
              </div>
              <div>
                <label className="block text-xs font-medium text-pm-muted mb-1.5">Password</label>
                <PasswordInput required value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Enter your password" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
              <div className="text-center">
                <button type="button" onClick={() => { setShowForgot(true); setError(null); setSuccess(null) }} className="inline-flex items-center justify-center min-h-[44px] -my-3 px-2 text-2xs text-pm-teal hover:text-pm-teal/80 transition-colors">
                  Forgot password?
                </button>
              </div>
            </form>
          ) : (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-pm-muted mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@meridian.com" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
              <p className="text-center text-2xs text-pm-muted">
                <button type="button" onClick={() => { setShowForgot(false); setError(null); setSuccess(null) }} className="inline-flex items-center justify-center min-h-[44px] -my-3 px-2 text-pm-teal hover:text-pm-teal/80 transition-colors">
                  Back to sign in
                </button>
              </p>
            </form>
          )}

          <p className="text-center text-2xs text-pm-muted mt-5">
            New sales rep?{' '}
            <Link to="/canada/portal/signup" className="inline-flex items-center justify-center min-h-[44px] -my-3 px-2 text-pm-teal hover:text-pm-teal/80 transition-colors font-medium">
              Create your account
            </Link>
          </p>
        </div>

        <p className="text-center text-2xs text-pm-muted/50 mt-5">
          Business owner?{' '}
          <Link to="/canada/login" className="inline-flex items-center justify-center min-h-[44px] -my-3 px-2 text-pm-accent hover:text-pm-accent/80 transition-colors font-medium">
            Sign in here
          </Link>
        </p>

        <p className="text-center text-2xs text-pm-muted/30 mt-4 font-mono">
          Meridian Canada Sales CRM v0.2.0
        </p>
      </div>
    </div>
  )
}
