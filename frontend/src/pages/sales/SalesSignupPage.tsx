import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { MeridianEmblem } from '@/components/MeridianLogo'

export default function SalesSignupPage() {
  const navigate = useNavigate()
  const { authenticated, login } = useSalesAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (authenticated) navigate('/sales/dashboard', { replace: true })
  }, [authenticated, navigate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)

    const err = await login(email, password)
    setLoading(false)
    if (err) {
      setError(err)
      return
    }
    setSuccess(true)
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors'
  const btnClass = 'w-full py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-1 mb-8">
          <MeridianEmblem size={40} />
          <span className="text-xl font-bold text-[#F5F5F7] mt-2">Join Meridian Sales</span>
          <span className="text-[10px] font-semibold text-[#17C5B0] uppercase tracking-widest">New Rep Registration</span>
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <p className="text-sm text-[#A1A1A8] text-center mb-6">
            Create your account to begin onboarding.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-xs text-[#17C5B0]">
              Account created! Redirecting to your dashboard...
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Full Name</label>
              <input type="text" required value={name} onChange={e => setName(e.target.value)} className={inputClass} placeholder="Jane Smith" />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@meridian.com" />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Phone</label>
              <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} className={inputClass} placeholder="(555) 123-4567" />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
              <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Min 8 characters" />
            </div>
            <button type="submit" disabled={loading} className={btnClass}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-[11px] text-[#A1A1A8] mt-5">
            Already have an account?{' '}
            <Link to="/sales/login" className="text-[#17C5B0] hover:text-[#17C5B0]/80 transition-colors font-medium">
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian Sales CRM v0.2.0
        </p>
      </div>
    </div>
  )
}
