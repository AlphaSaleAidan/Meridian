import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useSalesAuth } from '@/lib/sales-auth'
import { MeridianEmblem } from '@/components/MeridianLogo'

export default function CanadaPortalSignupPage() {
  const navigate = useNavigate()
  const { authenticated, signup } = useSalesAuth()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (authenticated) navigate('/canada/portal/dashboard', { replace: true })
  }, [authenticated, navigate])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    if (!name.trim()) { setError('Please enter your full name'); return }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) { setError('Please enter a valid email address'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters'); return }
    setLoading(true)

    const err = await signup(name, email, password, phone || undefined)
    setLoading(false)
    if (err) {
      setError(err)
      return
    }
    setSuccess(true)
    setTimeout(() => navigate('/canada/portal/onboarding', { replace: true }), 1200)
  }

  const inputClass = 'w-full px-3 py-2.5 bg-pm-surface border border-pm-border rounded-lg text-sm text-pm-text placeholder-pm-muted/40 focus:outline-none focus:border-pm-teal/50 focus:ring-1 focus:ring-pm-teal/20 transition-colors'
  const btnClass = 'w-full py-2.5 bg-pm-teal text-pm-bg text-sm font-semibold rounded-lg hover:bg-pm-teal/90 disabled:opacity-50 transition-all'

  return (
    <div className="min-h-screen bg-pm-bg flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="flex flex-col items-center gap-1 mb-8">
          <MeridianEmblem size={40} />
          <span className="text-xl font-bold text-pm-text mt-2">Join Meridian Sales</span>
          <span className="text-2xs font-semibold text-pm-teal uppercase tracking-widest flex items-center gap-1">
            Canada — New Rep Registration {'\u{1F1E8}\u{1F1E6}'}
          </span>
        </div>

        <div className="card p-6 sm:p-8 border border-pm-border">
          <p className="text-sm text-pm-muted text-center mb-6">
            Create your account to begin onboarding.
          </p>

          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-pm-teal/10 border border-pm-teal/20 text-xs text-pm-teal">
              Account created! Redirecting to your dashboard...
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-pm-muted mb-1.5">Full Name</label>
              <input type="text" required value={name} onChange={e => setName(e.target.value)} className={inputClass} placeholder="Jane Smith" />
            </div>
            <div>
              <label className="block text-xs font-medium text-pm-muted mb-1.5">Email</label>
              <input type="email" required value={email} onChange={e => setEmail(e.target.value)} className={inputClass} placeholder="you@meridian.com" />
            </div>
            <div>
              <label className="block text-xs font-medium text-pm-muted mb-1.5">Phone</label>
              <input type="tel" value={phone} onChange={e => setPhone(e.target.value)} className={inputClass} placeholder="(555) 123-4567" />
            </div>
            <div>
              <label className="block text-xs font-medium text-pm-muted mb-1.5">Password</label>
              <input type="password" required minLength={8} value={password} onChange={e => setPassword(e.target.value)} className={inputClass} placeholder="Min 8 characters" />
              {password.length > 0 && (() => {
                let strength = 0
                if (password.length >= 8) strength++
                if (password.length >= 12) strength++
                if (/[A-Z]/.test(password) && /[a-z]/.test(password)) strength++
                if (/[0-9]/.test(password)) strength++
                if (/[^A-Za-z0-9]/.test(password)) strength++
                const level = strength <= 1 ? 'Weak' : strength <= 2 ? 'Fair' : strength <= 3 ? 'Good' : 'Strong'
                const color = strength <= 1 ? 'bg-red-500' : strength <= 2 ? 'bg-pm-amber-orange' : strength <= 3 ? 'bg-pm-teal' : 'bg-pm-accent'
                const textColor = strength <= 1 ? 'text-red-400' : strength <= 2 ? 'text-pm-amber-orange' : strength <= 3 ? 'text-pm-teal' : 'text-pm-accent'
                return (
                  <div className="mt-2">
                    <div className="flex gap-1">
                      {[0, 1, 2, 3, 4].map(i => (
                        <div key={i} className={`h-1 flex-1 rounded-full transition-all ${i < strength ? color : 'bg-pm-border'}`} />
                      ))}
                    </div>
                    <p className={`text-2xs mt-1 ${textColor}`}>{level}{password.length < 8 && ' — need at least 8 characters'}</p>
                  </div>
                )
              })()}
            </div>
            <button type="submit" disabled={loading} className={btnClass}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <p className="text-center text-2xs text-pm-muted mt-5">
            Already have an account?{' '}
            <Link to="/canada/portal/login" className="text-pm-teal hover:text-pm-teal/80 transition-colors font-medium">
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-2xs text-pm-muted/30 mt-6 font-mono">
          Meridian Canada Sales CRM v0.2.0
        </p>
      </div>
    </div>
  )
}
