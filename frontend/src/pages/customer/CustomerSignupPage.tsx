import { useState, useEffect } from 'react'
import { useNavigate, Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'

export default function CustomerSignupPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { authenticated, signup, validateToken, pendingBusiness } = useAuth()

  const inviteToken = searchParams.get('token')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [fullName, setFullName] = useState('')
  const [token, setToken] = useState(inviteToken || '')
  const [showTokenInput, setShowTokenInput] = useState(!!inviteToken)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (authenticated) navigate('/app', { replace: true })
  }, [authenticated, navigate])

  useEffect(() => {
    if (inviteToken) {
      setToken(inviteToken)
      setShowTokenInput(true)
      handleTokenValidation(inviteToken)
    }
  }, [inviteToken])

  useEffect(() => {
    if (pendingBusiness) {
      setBusinessName(pendingBusiness.name)
      if (pendingBusiness.email) setEmail(pendingBusiness.email)
    }
  }, [pendingBusiness])

  async function handleTokenValidation(t: string) {
    setError(null)
    if (!t.trim()) { setError('Please enter your access token'); return }
    setLoading(true)
    try {
      const err = await validateToken(t.trim())
      if (err) {
        setError(err)
      } else {
        setSuccess('Token verified! Complete your registration below.')
        setShowTokenInput(false)
      }
    } catch (err: any) {
      setError(err.message || 'Token validation failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSignup(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      const result = await signup(email, password, fullName, businessName)

      if (result === '__confirm_email__') {
        setSuccess('Account created! Check your email and click the confirmation link, then come back and sign in.')
        return
      }
      if (result) { setError(result); return }
      setSuccess('Account created! Redirecting to your dashboard...')
    } catch (err: any) {
      console.error('[Signup] Unhandled error:', err)
      setError(err.message || 'Something went wrong during signup. Please try again.')
    } finally {
      setLoading(false)
    }
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
            {pendingBusiness ? `Welcome, ${pendingBusiness.ownerName.split(' ')[0]}` : 'Get started with Meridian'}
          </h2>
          <p className="text-xs text-[#A1A1A8] text-center mb-6">
            {pendingBusiness ? `Finish setting up ${pendingBusiness.name}` : 'Connect your POS and start seeing insights'}
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-xs text-[#17C5B0]">{success}</div>
          )}

          {showTokenInput ? (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Access Token</label>
                <input
                  type="text" required value={token} onChange={e => setToken(e.target.value)}
                  className={inputClass + ' font-mono tracking-wider'}
                  placeholder="mtk_xxxxxxxxxxxxxxxx"
                />
                <p className="text-[10px] text-[#A1A1A8]/40 mt-1">Provided by your Meridian sales rep</p>
              </div>
              <button onClick={() => handleTokenValidation(token)} disabled={loading} className={btnClass}>
                {loading ? 'Verifying...' : 'Activate'}
              </button>
              <p className="text-center text-[11px] text-[#A1A1A8]">
                <button type="button" onClick={() => setShowTokenInput(false)} className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors">
                  Sign up without a token
                </button>
              </p>
            </div>
          ) : (
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
                {loading ? 'Creating account...' : 'Get Started Free'}
              </button>
              <div className="pt-2 border-t border-[#1F1F23]">
                <button type="button" onClick={() => setShowTokenInput(true)} className="w-full text-center text-[11px] text-[#A1A1A8] hover:text-[#1A8FD6] transition-colors">
                  Have an access token? Activate here
                </button>
              </div>
            </form>
          )}

          <p className="text-center text-[11px] text-[#A1A1A8] mt-5">
            Already have an account?{' '}
            <Link to="/customer/login" className="text-[#1A8FD6] hover:text-[#17C5B0] transition-colors font-medium">
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian POS Intelligence v0.2.0
        </p>
      </div>
    </div>
  )
}
