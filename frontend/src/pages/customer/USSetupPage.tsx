import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { getAuthHeaders } from '@/lib/supabase'
import POSSystemPicker from '@/components/POSSystemPicker'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import {
  MapPin, ArrowRight, CheckCircle2, Loader2, Wifi,
  LayoutDashboard,
} from 'lucide-react'

// The password reset is owned by the login page (USLoginPage forces it on
// first login via the must_reset_password flag), so this wizard does NOT prompt
// for a password again — otherwise the customer would be asked to reset twice.
// Flow: welcome -> connect POS -> done.
type Step = 'welcome' | 'pos' | 'done'

export default function USSetupPage() {
  const navigate = useNavigate()
  const { user, org, connectPos, markOnboarded } = useAuth()

  const [step, setStep] = useState<Step>('welcome')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [posProvider, setPosProvider] = useState<string | null>(null)

  if (!user || !org) {
    navigate('/us/login', { replace: true })
    return null
  }

  async function handleConnectPos() {
    if (!posProvider) { setError('Please select your POS system'); return }
    setLoading(true)
    setError(null)
    try {
      // Record the chosen POS as pending — credentials are entered later from
      // the dashboard, so onboarding isn't blocked on the customer having API
      // keys on hand. Mirrors USCustomerOnboardingWizard.handlePosNext.
      const apiUrl = import.meta.env.VITE_API_URL || ''
      if (org?.org_id) {
        const headers = await getAuthHeaders()
        await fetch(`${apiUrl}/api/pos/select`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ org_id: org.org_id, pos_system: posProvider, connection_status: 'pending' }),
        })
      } else {
        const err = await connectPos(posProvider, {})
        if (err && err !== 'API key is required') { setError(err); setLoading(false); return }
      }
      setStep('done')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connection failed')
    } finally {
      setLoading(false)
    }
  }

  function goToDashboard() {
    markOnboarded()
    navigate('/us/dashboard', { replace: true })
  }

  function handleSkipPos() { goToDashboard() }
  function handleFinish() { goToDashboard() }

  const firstName = org.owner_name?.split(' ')[0] || 'there'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="flex items-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#1A8FD6]/10 border border-[#1A8FD6]/20">
            <MapPin size={12} className="text-[#1A8FD6]" />
            <span className="text-[11px] text-[#1A8FD6] font-semibold uppercase tracking-wider">Account Setup</span>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {(['welcome', 'pos', 'done'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div className={`w-2.5 h-2.5 rounded-full transition-colors ${
                step === s ? 'bg-[#1A8FD6]' : i < ['welcome', 'pos', 'done'].indexOf(step) ? 'bg-[#1A8FD6]/50' : 'bg-[#1F1F23]'
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
            <div className="w-16 h-16 rounded-2xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 size={32} className="text-[#1A8FD6]" />
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
              onClick={() => setStep('pos')}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#1A8FD6] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 transition-all"
            >
              Get Started <ArrowRight size={16} />
            </button>
          </div>
        )}

        {/* CONNECT POS */}
        {step === 'pos' && (
          <div className="card p-6 sm:p-8 border border-[#1F1F23]">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center">
                <Wifi size={18} className="text-[#1A8FD6]" />
              </div>
              <div>
                <h2 className="text-base font-bold text-[#F5F5F7]">Connect Your POS</h2>
                <p className="text-[11px] text-[#A1A1A8]">Link your point-of-sale system to start receiving insights</p>
              </div>
            </div>
            <div className="mb-6">
              <POSSystemPicker
                value={posProvider}
                onChange={(posKey: string) => { setPosProvider(posKey); setError(null) }}
                mode="new-customer"
                portalContext="us"
                currency="USD"
              />
            </div>
            <button onClick={handleConnectPos} disabled={loading || !posProvider}
              className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#1A8FD6] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 disabled:opacity-50 transition-all">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <><Wifi size={16} /> Connect</>}
            </button>
            <button onClick={handleSkipPos} className="w-full mt-3 text-center text-[11px] text-[#A1A1A8] hover:text-white transition-colors">
              Skip — I'll connect later
            </button>
          </div>
        )}

        {/* DONE */}
        {step === 'done' && (
          <div className="card p-6 sm:p-8 border border-[#1F1F23] text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-6">
              <LayoutDashboard size={32} className="text-[#1A8FD6]" />
            </div>
            <h2 className="text-xl font-bold text-[#F5F5F7] mb-2">You're All Set!</h2>
            <p className="text-sm text-[#A1A1A8] mb-6">
              Your dashboard will start populating with insights as your POS data comes in.
            </p>
            <button onClick={handleFinish}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#1A8FD6] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#1A8FD6]/90 transition-all">
              <LayoutDashboard size={16} /> Go to Dashboard
            </button>
          </div>
        )}

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian US v0.2.0
        </p>
      </div>
    </div>
  )
}
