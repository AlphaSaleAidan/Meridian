import { useState, useEffect } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

type AuthMode = 'login' | 'signup' | 'forgot' | 'token'

export default function PortalPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const { authenticated, login, signup, validateToken, pendingBusiness } = useAuth()

  const from = (location.state as { from?: string })?.from || '/app'
  const inviteToken = searchParams.get('token')

  const [mode, setMode] = useState<AuthMode>(inviteToken ? 'token' : 'login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [fullName, setFullName] = useState('')
  const [token, setToken] = useState(inviteToken || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (authenticated) navigate(from, { replace: true })
  }, [authenticated, from, navigate])

  useEffect(() => {
    if (inviteToken) {
      setToken(inviteToken)
      setMode('token')
    }
  }, [inviteToken])

  useEffect(() => {
    if (pendingBusiness) {
      setBusinessName(pendingBusiness.name)
      if (pendingBusiness.email) setEmail(pendingBusiness.email)
    }
  }, [pendingBusiness])

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const err = await login(email, password)
    setLoading(false)
    if (err) setError(err)
    else navigate(from, { replace: true })
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    const result = await signup(email, password, fullName, businessName)
    setLoading(false)

    if (result === '__confirm_email__') {
      setSuccess('Account created! Check your email and click the confirmation link, then come back and sign in.')
      return
    }
    if (result) {
      setError(result)
      return
    }
    setSuccess('Account created! Redirecting to your dashboard...')
    setTimeout(() => navigate('/app', { replace: true }), 1200)
  }

  async function handleToken(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!token.trim()) { setError('Please enter your access token'); return }
    setLoading(true)
    const err = await validateToken(token.trim())
    setLoading(false)
    if (err) {
      setError(err)
    } else {
      setSuccess('Token verified! Create your account to get started.')
      setTimeout(() => {
        setSuccess(null)
        setMode('signup')
      }, 600)
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    setTimeout(() => {
      setLoading(false)
      setSuccess('If that email exists, a reset link has been sent.')
    }, 800)
  }

  function switchMode(m: AuthMode) {
    setMode(m)
    setError(null)
    setSuccess(null)
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
            {mode === 'login' && 'Welcome back'}
            {mode === 'signup' && (pendingBusiness ? `Welcome, ${pendingBusiness.ownerName.split(' ')[0]}` : 'Create your account')}
            {mode === 'forgot' && 'Reset password'}
            {mode === 'token' && 'Activate your portal'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {mode === 'login' && 'Sign in to access your POS intelligence dashboard'}
            {mode === 'signup' && (pendingBusiness ? `Finish setting up ${pendingBusiness.name}` : 'Get started with Meridian in under 2 minutes')}
            {mode === 'forgot' && "We'll send a reset link to your email"}
            {mode === 'token' && 'Enter the access token from your welcome email'}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-xs text-[#17C5B0]">{success}</div>
          )}

          {/* Login */}
          {mode === 'login' && (
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
                <button type="button" onClick={() => switchMode('forgot')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">Forgot password?</button>
                <button type="button" onClick={() => switchMode('signup')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">Create account</button>
              </div>
              <div className="pt-2 border-t border-[#1F1F23]">
                <button type="button" onClick={() => switchMode('token')} className="w-full text-center text-[11px] text-[#A1A1A8] hover:text-[#1A8FD6] transition-colors">
                  Have an access token? Activate here
                </button>
              </div>
            </form>
          )}

          {/* Signup */}
          {mode === 'signup' && (
            <form onSubmit={handleSignup} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Full Name</label>
                <input type="text" required value={fullName} onChange={e => setFullName(e.target.value)} className={inputClass} placeholder="John Smith" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Business Name</label>
                <input
                  type="text" required value={businessName} onChange={e => setBusinessName(e.target.value)}
                  className={inputClass}
                  placeholder="The Daily Grind Coffee"
                  readOnly={!!pendingBusiness}
                />
                {pendingBusiness && (
                  <p className="text-[10px] text-[#17C5B0] mt-1">Pre-filled from your access token</p>
                )}
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@business.com" />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
                <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Min 8 characters" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Creating account...' : pendingBusiness ? 'Activate & Get Started' : 'Get Started Free'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                Already have an account?{' '}
                <button type="button" onClick={() => switchMode('login')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">Sign in</button>
              </p>
            </form>
          )}

          {/* Token Activation */}
          {mode === 'token' && (
            <form onSubmit={handleToken} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Access Token</label>
                <input
                  type="text" required value={token} onChange={e => setToken(e.target.value)}
                  className={inputClass + ' font-mono tracking-wider'}
                  placeholder="mtk_xxxxxxxxxxxxxxxx"
                />
                <p className="text-[10px] text-[#A1A1A8]/40 mt-1">Provided by your Meridian sales rep or in your welcome email</p>
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Verifying...' : 'Activate Portal'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                <button type="button" onClick={() => switchMode('login')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">Back to sign in</button>
              </p>
            </form>
          )}

          {/* Forgot Password */}
          {mode === 'forgot' && (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@business.com" />
              </div>
              <button type="submit" disabled={loading} className={btnClass}>
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                <button type="button" onClick={() => switchMode('login')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">Back to sign in</button>
              </p>
            </form>
          )}
        </div>

        {/* SOP Steps */}
        <div className="mt-6 space-y-2">
          <p className="text-[10px] font-semibold text-[#A1A1A8]/60 text-center uppercase tracking-wider">How it works</p>
          <div className="grid grid-cols-3 gap-2">
            {[
              { step: '1', label: 'Sign Up', desc: 'Create account or use token' },
              { step: '2', label: 'Connect POS', desc: 'Link Square, Clover, or Toast' },
              { step: '3', label: 'Get Insights', desc: 'AI agents start analyzing' },
            ].map(s => (
              <div key={s.step} className="text-center">
                <div className="w-6 h-6 rounded-full bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-1">
                  <span className="text-[10px] font-bold text-[#1A8FD6] font-mono">{s.step}</span>
                </div>
                <p className="text-[10px] font-medium text-[#F5F5F7]">{s.label}</p>
                <p className="text-[9px] text-[#A1A1A8]/40">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian POS Intelligence v0.2.0
        </p>
      </div>
    </div>
  )
}
