import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/lib/auth'
import { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import {
  MapPin, ArrowRight, CheckCircle2, Loader2, Wifi,
} from 'lucide-react'

// US mirror of CanadaSetupPage — same flow, US paths.
// The password reset is owned by the login page (USLoginPage forces it on
// first login via the must_reset_password flag), so this wizard does NOT prompt
// for a password again — otherwise the customer would be asked to reset twice.
// POS connection is owned by the real merchant onboarding wizard
// (/us/merchant/onboard) — this page never claims a connection itself.
// Flow: welcome -> done (hand off to the merchant wizard).
type Step = 'welcome' | 'done'

export default function USSetupPage() {
  const navigate = useNavigate()
  const { user, org, markOnboarded } = useAuth()

  const [step, setStep] = useState<Step>('welcome')
  const [loading, setLoading] = useState(false)

  if (!user || !org) {
    navigate('/us/login', { replace: true })
    return null
  }

  // Await markOnboarded so the flag is persisted server-side (with one retry)
  // before we leave — otherwise a reload mid-flight bounces back to /setup.
  async function goToPosConnect() {
    setLoading(true)
    await markOnboarded()
    navigate('/us/merchant/onboard', { replace: true })
  }

  async function goToDashboard() {
    setLoading(true)
    await markOnboarded()
    navigate('/us/merchant', { replace: true })
  }

  const firstName = org.owner_name?.split(' ')[0] || 'there'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="flex items-center gap-2.5">
            <MeridianEmblem size={36} />
            <MeridianWordmark className="text-xl" />
          </div>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#17C5B0]/10 border border-[#17C5B0]/20">
            <MapPin size={12} className="text-[#17C5B0]" />
            <span className="text-[11px] text-[#17C5B0] font-semibold uppercase tracking-wider">Account Setup</span>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-2 mb-8">
          {(['welcome', 'done'] as Step[]).map((s, i) => (
            <div key={s} className="flex items-center">
              <div className={`w-2.5 h-2.5 rounded-full transition-colors ${
                step === s ? 'bg-[#00d4aa]' : i < ['welcome', 'done'].indexOf(step) ? 'bg-[#00d4aa]/50' : 'bg-[#1F1F23]'
              }`} />
              {i < 1 && <div className="w-8 h-[1px] bg-[#1F1F23]" />}
            </div>
          ))}
        </div>

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
              Next, connect your point-of-sale so your dashboard fills with real data — it takes less than 2 minutes.
            </p>
            <button
              onClick={() => setStep('done')}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#00d4aa] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all"
            >
              Connect your POS <ArrowRight size={16} />
            </button>
          </div>
        )}

        {/* DONE — hand off to the real merchant onboarding wizard */}
        {step === 'done' && (
          <div className="card p-6 sm:p-8 border border-[#1F1F23] text-center">
            <div className="w-16 h-16 rounded-2xl bg-[#00d4aa]/10 border border-[#00d4aa]/20 flex items-center justify-center mx-auto mb-6">
              <Wifi size={32} className="text-[#00d4aa]" />
            </div>
            <h2 className="text-xl font-bold text-[#F5F5F7] mb-2">Connect Your POS</h2>
            <p className="text-sm text-[#A1A1A8] mb-6">
              We'll walk you through linking your point-of-sale and importing your sales history.
            </p>
            <button onClick={goToPosConnect} disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 bg-[#00d4aa] text-[#0A0A0B] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 disabled:opacity-50 transition-all">
              {loading ? <Loader2 size={16} className="animate-spin" /> : <><Wifi size={16} /> Connect your POS</>}
            </button>
            <button onClick={goToDashboard} disabled={loading}
              className="w-full mt-3 text-center text-[11px] text-[#A1A1A8] hover:text-white disabled:opacity-50 transition-colors">
              Skip — I'll connect later
            </button>
          </div>
        )}

        <p className="text-center text-[10px] text-[#A1A1A8]/30 mt-6 font-mono">
          Meridian v0.2.0
        </p>
      </div>
    </div>
  )
}
