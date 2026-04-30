import { useState, useEffect } from 'react'
import { useNavigate, useLocation, Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { MeridianEmblem } from '@/components/MeridianLogo'

export default function SalesLoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { authenticated, login } = useSalesAuth()

  const from = (location.state as { from?: string })?.from || '/sales/dashboard'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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

  const inputClass = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#17C5B0]/50 focus:ring-1 focus:ring-[#17C5B0]/20 transition-colors'
  const btnClass = 'w-full py-2.5 bg-[#17C5B0] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#17C5B0]/90 disabled:opacity-50 transition-all'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-1 mb-8">
          <MeridianEmblem size={40} />
          <span className="text-xl font-bold text-[#F5F5F7] mt-2">Meridian Sales</span>
          <span className="text-[10px] font-semibold text-[#17C5B0] uppercase tracking-widest">Internal CRM</span>
        </div>

        <div className="card p-6 sm:p-8 border border-[#1F1F23]">
          <p className="text-sm text-[#A1A1A8] text-center mb-6">
            Sign in to access your pipeline and leads.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@meridian.com" />
            </div>
            <div>
              <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Password</label>
              <input type="password" required value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Enter your password" />
            </div>
            <button type="submit" disabled={loading} className={btnClass}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p className="text-center text-[11px] text-[#A1A1A8] mt-5">
            New sales rep?{' '}
            <Link to="/sales/signup" className="text-[#17C5B0] hover:text-[#17C5B0]/80 transition-colors font-medium">
              Create your account
            </Link>
          </p>
        </div>

        <p className="text-center text-[11px] text-[#A1A1A8]/50 mt-5">
          Business owner?{' '}
          <Link to="/customer/login" className="text-[#1A8FD6] hover:text-[#1A8FD6]/80 transition-colors font-medium">
            Sign in here
          </Link>
        </p>

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-4 font-mono">
          Meridian Sales CRM v0.2.0
        </p>
      </div>
    </div>
  )
}
