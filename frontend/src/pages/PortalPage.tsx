import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

type AuthMode = 'login' | 'signup' | 'forgot'

export default function PortalPage() {
  const navigate = useNavigate()
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!supabase) {
      setLoading(false)
      navigate('/app')
      return
    }

    const { error: err } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (err) {
      setError(err.message)
    } else {
      navigate('/app')
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!supabase) {
      setLoading(false)
      setSuccess('Account created! Redirecting to your dashboard...')
      setTimeout(() => navigate('/app'), 1500)
      return
    }

    const { error: err } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, business_name: businessName },
      },
    })
    setLoading(false)
    if (err) {
      setError(err.message)
    } else {
      setSuccess('Account created! Check your email to confirm, then log in.')
    }
  }

  async function handleForgot(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!supabase) {
      setLoading(false)
      setSuccess('If that email exists, a reset link has been sent.')
      return
    }

    const { error: err } = await supabase.auth.resetPasswordForEmail(email)
    setLoading(false)
    if (err) {
      setError(err.message)
    } else {
      setSuccess('If that email exists, a reset link has been sent.')
    }
  }

  function switchMode(m: AuthMode) {
    setMode(m)
    setError(null)
    setSuccess(null)
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <MeridianEmblem size={36} />
          <MeridianWordmark className="text-xl" />
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <h2 className="text-lg font-bold text-[#F5F5F7] text-center mb-1">
            {mode === 'login' && 'Welcome back'}
            {mode === 'signup' && 'Create your account'}
            {mode === 'forgot' && 'Reset password'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {mode === 'login' && 'Sign in to access your POS intelligence dashboard'}
            {mode === 'signup' && 'Get started with Meridian in under 2 minutes'}
            {mode === 'forgot' && "We'll send a reset link to your email"}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-xs text-[#17C5B0]">
              {success}
            </div>
          )}

          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input
                  type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="you@business.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
                <input
                  type="password" required value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="Enter your password"
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all"
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
              <div className="flex items-center justify-between text-[11px]">
                <button type="button" onClick={() => switchMode('forgot')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Forgot password?
                </button>
                <button type="button" onClick={() => switchMode('signup')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Create account
                </button>
              </div>
            </form>
          )}

          {mode === 'signup' && (
            <form onSubmit={handleSignup} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Full Name</label>
                <input
                  type="text" required value={fullName} onChange={e => setFullName(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="John Smith"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Business Name</label>
                <input
                  type="text" required value={businessName} onChange={e => setBusinessName(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="The Daily Grind Coffee"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input
                  type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="you@business.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
                <input
                  type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="Min 8 characters"
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all"
              >
                {loading ? 'Creating account...' : 'Get Started Free'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                Already have an account?{' '}
                <button type="button" onClick={() => switchMode('login')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Sign in
                </button>
              </p>
            </form>
          )}

          {mode === 'forgot' && (
            <form onSubmit={handleForgot} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
                <input
                  type="email" required value={email} onChange={e => setEmail(e.target.value)}
                  className="w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#1A8FD6]/50 focus:ring-1 focus:ring-[#1A8FD6]/20 transition-colors"
                  placeholder="you@business.com"
                />
              </div>
              <button
                type="submit" disabled={loading}
                className="w-full py-2.5 bg-[#1A8FD6] text-white text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all"
              >
                {loading ? 'Sending...' : 'Send Reset Link'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                <button type="button" onClick={() => switchMode('login')} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Back to sign in
                </button>
              </p>
            </form>
          )}
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/40 mt-6 font-mono">
          Meridian POS Intelligence v0.2.0
        </p>
      </div>
    </div>
  )
}
