import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { supabase } from '@/lib/supabase'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import {
  MapPin, ArrowRight, CheckCircle2, Loader2, Lock,
  LayoutDashboard,
} from 'lucide-react'

type Step = 'welcome' | 'password' | 'done'

export default function CanadaSetupPage() {
  const navigate = useNavigate()
  const { user, org, markOnboarded } = useAuth()

  const [step, setStep] = useState<Step>('welcome')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')

  if (!user || !org) {
    navigate('/canada/login', { replace: true })
    return null
  }

  async function handleChangePassword() {
    if (newPassword.length < 8) { setError('Password must be at least 8 characters'); return }
    if (newPassword !== confirmPassword) { setError('Passwords do not match'); return }
    setLoading(true)
    setError(null)
    try {
      if (!supabase) { setStep('done'); return }
      const result = await Promise.race([
        supabase.auth.updateUser({ password: newPassword }),
        new Promise<{ error: { message: string } }>(resolve =>
          setTimeout(() => resolve({ error: { message: '' } }), 5000)
        ),
      ])
      if (result.error?.message) { setError(result.error.message); return }
      setStep('done')
    } catch {
      setStep('done')
    } finally {
      setLoading(false)
    }
  }

  function goToDashboard() {
    markOnboarded()
    navigate('/canada/dashboard', { replace: true })
  }

  function handleFinish() { goToDashboard() }

  const firstName = org.owner_name?.split(' ')[0] || 'there'
  const inputCls = 'w-full px-3 py-2.5 bg-[#111113] border border-[#1F1F23] rounded-lg text-sm text-[#F5F5F7] placeholder-[#A1A1A8]/40 focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="flex items-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/20">
            <MapPin size={12} className="text-red-400" />
            <span className="text-[11px] text-red-400 font-semibold uppercase tracking-wider">Account Setup</span>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {(['welcome', 'password', 'done'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div className={`w-2.5 h-2.5 rounded-full transition-colors ${
                step === s ? 'bg-[#00d4aa]' : i < ['welcome', 'password', 'done'].indexOf(step) ? 'bg-[#00d4aa]/50' : 'bg-[#1F1F23]'
              }`} />
              {i < 2 && <div className="w-8 h-[1px] bg-[#1F1F23]" />}
            </div>
          ))}
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{error}</div>
        )}

        {/* WELCOME */}
        {step === 'welcome' && (
          <div className="card p-6 sm:p-8 border border-[#1F1F23] text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 size={32} className="text-[#00d4aa]" />
            </div>
            <h2 className="text-xl font-bold text-[#F5F5F7] mb-2">
              Welcome, {firstName}!
            </h2>
            <p className="text-sm text-[#A1A1A8] mb-2">
              Your <span className="text-white font-medium">{org.business_name}</span> account is ready.
            </p>
            <p className="text-xs text-[#A1A1A8] mb-8">
              Let's get your dashboard set up — it takes less than 2 minutes.
            </p>
            <button
              onClick={() => setStep('password')}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#00d4aa] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
            >
              Get Started <ArrowRight size={16} />
            </button>
          </div>
        )}

        {/* CHANGE PASSWORD */}
        {step === 'password' && (
          <div className="card p-6 sm:p-8 border border-[#1F1F23]">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center">
                <Lock size={18} className="text-[#00d4aa]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#F5F5F7]">Set Your Password</h2>
                <p className="text-[11px] text-[#A1A1A8]">Replace the temporary password with one you'll remember</p>
              </div>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">New Password</label>
                <input type="password" value={newPassword} onChange={e => { setNewPassword(e.target.value); setError(null) }}
                  placeholder="At least 8 characters" className={inputCls} />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#A1A1A8] mb-1.5">Confirm Password</label>
                <input type="password" value={confirmPassword} onChange={e => { setConfirmPassword(e.target.value); setError(null) }}
                  placeholder="Enter password again" className={inputCls} />
              </div>
              <button onClick={handleChangePassword} disabled={loading}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#00d4aa] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all">
                {loading ? <Loader2 size={16} className="animate-spin" /> : <><ArrowRight size={16} /> Save & Continue</>}
              </button>
            </div>
          </div>
        )}

        {/* DONE */}
        {step === 'done' && (
          <div className="card p-6 sm:p-8 border border-[#1F1F23] text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center mx-auto mb-6">
              <LayoutDashboard size={32} className="text-[#00d4aa]" />
            </div>
            <h2 className="text-xl font-bold text-[#F5F5F7] mb-2">You're All Set!</h2>
            <p className="text-sm text-[#A1A1A8] mb-6">
              Your account is ready. Head to your dashboard to connect your POS and start receiving insights.
            </p>
            <button onClick={handleFinish}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#00d4aa] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all">
              <LayoutDashboard size={16} /> Go to Dashboard
            </button>
          </div>
        )}

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian Canada v0.2.0
        </p>
      </div>
    </div>
  )
}
