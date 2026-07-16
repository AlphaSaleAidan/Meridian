import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Lock, Sparkles, User, Users, CheckSquare,
  ChevronRight, ChevronLeft, Check,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { onboardingEmails } from '@/lib/email-service'
import { MeridianEmblem } from '@/components/MeridianLogo'
import PasswordInput from '@/components/ui/PasswordInput'
import EmailPreviewModal from '@/components/EmailPreviewModal'
import { supabase } from '@/lib/supabase'

const STEPS = [
  { id: 'password', label: 'Password', icon: Lock },
  { id: 'welcome', label: 'Welcome', icon: Sparkles },
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'manager', label: 'Manager', icon: Users },
  { id: 'checklist', label: 'Checklist', icon: CheckSquare },
] as const

type StepId = typeof STEPS[number]['id']

const REQUIRED_ITEMS = [
  { id: 'training', label: 'Complete all training modules', link: '/canada/portal/training' },
  { id: 'product-overview', label: 'Read the Meridian product overview', link: '/canada/portal/training' },
  { id: 'demo-practice', label: 'Practice the demo at least once', link: '/canada/portal/leads?new=true' },
]
const RECOMMENDED_ITEMS = [
  { id: 'book-call', label: 'Book your onboarding call with your manager' },
  { id: 'prospects', label: 'Identify your first 10 prospects' },
  { id: 'first-lead', label: 'Submit your first lead' },
]

const PROVINCES = ['Alberta','British Columbia','Manitoba','New Brunswick','Newfoundland and Labrador','Northwest Territories','Nova Scotia','Nunavut','Ontario','Prince Edward Island','Quebec','Saskatchewan','Yukon']

export default function CanadaPortalOnboardingPage() {
  const navigate = useNavigate()
  const { rep } = useSalesAuth()
  const [step, setStep] = useState<StepId>('password')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordError, setPasswordError] = useState('')

  const [profile, setProfile] = useState({
    display_name: rep?.name || '',
    phone: rep?.phone || '',
    city: '',
    province: '',
    bio: '',
  })

  const [checkedItems, setCheckedItems] = useState(new Set(['password']))
  const [showEmailPreview, setShowEmailPreview] = useState(false)

  const stepIdx = STEPS.findIndex(s => s.id === step)

  function nextStep() {
    if (stepIdx < STEPS.length - 1) setStep(STEPS[stepIdx + 1].id)
  }

  function prevStep() {
    if (stepIdx > 0) setStep(STEPS[stepIdx - 1].id)
  }

  async function handlePasswordSubmit() {
    if (password.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }
    if (password !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }
    setPasswordError('')
    if (supabase) {
      const { error } = await supabase.auth.updateUser({ password })
      if (error) {
        setPasswordError(error.message)
        return
      }
    }
    setCheckedItems(prev => new Set([...prev, 'password']))
    nextStep()
  }

  const [profileError, setProfileError] = useState('')

  async function handleProfileSubmit() {
    setProfileError('')
    if (supabase && rep) {
      const { error } = await supabase.from('sales_reps').update({
        name: profile.display_name || rep.name,
        phone: profile.phone,
        location: profile.city && profile.province ? `${profile.city}, ${profile.province}` : undefined,
      }).eq('email', rep.email)
      if (error) {
        setProfileError('Could not save profile. Please try again.')
        return
      }
    }
    setCheckedItems(prev => new Set([...prev, 'profile']))
    nextStep()
  }

  function handleFinish() {
    setShowEmailPreview(true)
  }

  async function handleConfirmSend() {
    localStorage.setItem('meridian_onboarding_complete', 'true')
    if (rep?.email) {
      await onboardingEmails.complete(rep.email, rep.name)
    }
    navigate('/canada/portal/dashboard')
  }

  const inputClass = 'w-full px-3 py-2.5 bg-pm-canada-bg border border-pm-canada-border rounded-lg text-sm text-white placeholder-pm-canada-text-muted focus:outline-none focus:border-pm-accent/50 focus:ring-1 focus:ring-pm-accent/20 transition-colors'
  const btnPrimary = 'flex items-center gap-1.5 px-5 py-2.5 bg-pm-accent text-pm-canada-bg text-sm font-semibold rounded-lg hover:bg-pm-accent/90 transition-all'
  const btnSecondary = 'flex items-center gap-1.5 px-4 py-2.5 text-sm text-pm-canada-text-muted hover:text-white transition-colors'

  return (
    <div className="min-h-screen bg-pm-bg flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="flex flex-col items-center gap-1 mb-6">
          <MeridianEmblem size={36} />
          <span className="text-lg font-bold text-pm-text mt-2">Sales Onboarding</span>
          <span className="text-2xs font-semibold text-pm-accent uppercase tracking-widest">
            Canada CRM
          </span>
        </div>

        {/* Step indicator */}
        <div className="flex items-center justify-center gap-1 mb-8">
          {STEPS.map((s, i) => {
            const Icon = s.icon
            const isActive = i === stepIdx
            const isDone = i < stepIdx
            return (
              <div key={s.id} className="flex items-center">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center transition-all ${
                    isActive ? 'bg-pm-accent text-pm-canada-bg' :
                    isDone ? 'bg-pm-accent/20 text-pm-accent' :
                    'bg-pm-canada-border text-pm-canada-text-muted'
                  }`}
                >
                  {isDone ? <Check size={14} /> : <Icon size={14} />}
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-6 h-0.5 mx-0.5 ${i < stepIdx ? 'bg-pm-accent/40' : 'bg-pm-canada-border'}`} />
                )}
              </div>
            )
          })}
        </div>

        {/* Card */}
        <div className="bg-pm-canada-surface border border-pm-canada-border rounded-xl p-6 sm:p-8">
          {/* Step 1: Password */}
          {step === 'password' && (
            <div className="space-y-5">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mx-auto mb-3">
                  <Lock size={22} className="text-pm-accent" />
                </div>
                <h2 className="text-lg font-bold text-white">Set Your Password</h2>
                <p className="text-sm text-pm-canada-text-muted mt-1">Secure your account with a strong password.</p>
              </div>
              {passwordError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{passwordError}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">New Password</label>
                <PasswordInput
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  className={inputClass}
                  placeholder="Min 8 characters"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Confirm Password</label>
                <PasswordInput value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className={inputClass} placeholder="Confirm your password" />
              </div>
              <div className="flex justify-end">
                <button onClick={handlePasswordSubmit} className={btnPrimary}>
                  Continue <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Welcome */}
          {step === 'welcome' && (
            <div className="space-y-5">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mx-auto mb-3">
                  <Sparkles size={22} className="text-pm-accent" />
                </div>
                <h2 className="text-lg font-bold text-white">
                  Welcome to Meridian, {rep?.name?.split(' ')[0] || 'there'}
                </h2>
                <p className="text-sm text-pm-canada-text-muted mt-1">
                  You're now part of the Meridian Canada sales team.
                </p>
              </div>

              {/* TODO(training): Income projections below are illustrative. With custom per-deal
                  pricing, the actual amounts depend on the deal prices reps negotiate. Review
                  these figures once typical custom deal sizes are established. */}
              {/* Income Projection Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { label: 'Month 1', amount: 'CA$2,025', sub: '5 closes' },
                  { label: 'Month 6', amount: 'CA$12,150', sub: '30 closes' },
                  { label: 'Month 12', amount: 'CA$24,300', sub: '60 closes' },
                ].map(card => (
                  <div key={card.label} className="bg-pm-canada-bg border border-pm-canada-border rounded-xl p-4 text-center">
                    <p className="text-2xs font-medium text-pm-canada-text-muted uppercase tracking-wide">{card.label}</p>
                    <p className="text-xl font-bold text-pm-amber-gold mt-1">{card.amount}</p>
                    <p className="text-2xs text-pm-canada-text-faint mt-0.5">{card.sub}</p>
                  </div>
                ))}
              </div>

              <p className="text-center text-sm font-semibold text-white">
                Every account you close pays you every month.
              </p>

              <div className="flex justify-between">
                <button onClick={prevStep} className={btnSecondary}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button onClick={nextStep} className={btnPrimary}>
                  Let's Get Started <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* Step 3: Profile */}
          {step === 'profile' && (
            <div className="space-y-5">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mx-auto mb-3">
                  <User size={22} className="text-pm-accent" />
                </div>
                <h2 className="text-lg font-bold text-white">Your Profile</h2>
                <p className="text-sm text-pm-canada-text-muted mt-1">Fill in your details so your team and manager can find you.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Display Name</label>
                  <input value={profile.display_name} onChange={e => setProfile(p => ({ ...p, display_name: e.target.value }))} className={inputClass} placeholder="Your name" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Phone</label>
                  <input type="tel" value={profile.phone} onChange={e => setProfile(p => ({ ...p, phone: e.target.value }))} className={inputClass} placeholder="(604) 555-1234" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">City</label>
                  <input value={profile.city} onChange={e => setProfile(p => ({ ...p, city: e.target.value }))} className={inputClass} placeholder="Vancouver" />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Province</label>
                  <select value={profile.province} onChange={e => setProfile(p => ({ ...p, province: e.target.value }))} className={inputClass}>
                    <option value="" disabled>Choose your province...</option>
                    {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-pm-canada-text-muted mb-1.5">Short Bio (optional)</label>
                  <textarea value={profile.bio} onChange={e => setProfile(p => ({ ...p, bio: e.target.value }))} className={inputClass + ' resize-none h-16'} placeholder="A few words about yourself..." />
                </div>
              </div>
              {profileError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{profileError}</div>
              )}
              <div className="flex justify-between">
                <button onClick={prevStep} className={btnSecondary}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button onClick={handleProfileSubmit} className={btnPrimary}>
                  Continue <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* Step 4: Meet Your Managers */}
          {step === 'manager' && (
            <div className="space-y-5">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mx-auto mb-3">
                  <Users size={22} className="text-pm-accent" />
                </div>
                <h2 className="text-lg font-bold text-white">Meet Your Managers</h2>
                <p className="text-sm text-pm-canada-text-muted mt-1">Here's who you'll be working with in Canada.</p>
              </div>
              <div className="space-y-3">
                <div className="bg-pm-canada-bg border border-pm-canada-border rounded-xl p-5">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full bg-pm-accent/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-pm-accent">EC</span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Enoch Cheung</p>
                      <p className="text-xs text-pm-canada-text-muted">Canadian Regional Director</p>
                      <p className="text-2xs text-pm-accent mt-0.5">Meridian AI Business Solutions — CRO</p>
                    </div>
                  </div>
                  <p className="text-xs text-pm-canada-text-muted mt-4 leading-relaxed">
                    Enoch leads Meridian's Canadian expansion. He's your primary contact for pipeline strategy,
                    deal support, and regional questions. Don't hesitate to reach out.
                  </p>
                </div>
                <div className="bg-pm-canada-bg border border-pm-canada-border rounded-xl p-5">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full bg-pm-purple/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-pm-purple">AN</span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Aidan Nguyen</p>
                      <p className="text-xs text-pm-canada-text-muted">Canadian Admin</p>
                      <p className="text-2xs text-pm-accent mt-0.5">Meridian</p>
                    </div>
                  </div>
                  <p className="text-xs text-pm-canada-text-muted mt-4 leading-relaxed">
                    Aidan handles onboarding support, training materials, and account setup.
                    Reach out for any technical or portal questions.
                  </p>
                </div>
              </div>
              <div className="flex justify-between">
                <button onClick={prevStep} className={btnSecondary}>
                  <ChevronLeft size={16} /> Back
                </button>
                <button onClick={nextStep} className={btnPrimary}>
                  Continue <ChevronRight size={16} />
                </button>
              </div>
            </div>
          )}

          {/* Step 5: Checklist */}
          {step === 'checklist' && (() => {
            const requiredDone = REQUIRED_ITEMS.filter(i => checkedItems.has(i.id)).length
            const allRequiredDone = requiredDone === REQUIRED_ITEMS.length
            return (
              <div className="space-y-5">
                <div className="text-center">
                  <div className="w-12 h-12 rounded-full bg-pm-accent/10 flex items-center justify-center mx-auto mb-3">
                    <CheckSquare size={22} className="text-pm-accent" />
                  </div>
                  <h2 className="text-lg font-bold text-white">Getting Started Checklist</h2>
                  <p className="text-sm text-pm-canada-text-muted mt-1">Complete the required items to unlock your dashboard.</p>
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-pm-canada-text-muted">Required Progress</span>
                    <span className="text-xs font-semibold text-pm-accent">{requiredDone}/{REQUIRED_ITEMS.length}</span>
                  </div>
                  <div className="h-2 bg-pm-canada-border rounded-full overflow-hidden">
                    <div
                      className="h-full bg-pm-accent rounded-full transition-all duration-500"
                      style={{ width: `${(requiredDone / REQUIRED_ITEMS.length) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Required items */}
                <div>
                  <p className="text-2xs font-semibold text-pm-canada-text-muted uppercase tracking-wider mb-2">Required</p>
                  <div className="space-y-2">
                    {REQUIRED_ITEMS.map(item => {
                      const checked = checkedItems.has(item.id)
                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            setCheckedItems(prev => {
                              const next = new Set(prev)
                              if (next.has(item.id)) next.delete(item.id)
                              else next.add(item.id)
                              return next
                            })
                          }}
                          className="w-full flex items-center gap-3 p-3 bg-pm-canada-bg rounded-lg hover:bg-pm-canada-bg/80 transition-colors text-left"
                        >
                          <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                            checked ? 'bg-pm-accent text-pm-canada-bg' : 'border border-pm-canada-border'
                          }`}>
                            {checked && <Check size={12} />}
                          </div>
                          <span className={`text-sm flex-1 ${checked ? 'text-pm-canada-text-muted line-through' : 'text-white'}`}>
                            {item.label}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Recommended items */}
                <div>
                  <p className="text-2xs font-semibold text-pm-canada-text-muted uppercase tracking-wider mb-2">Recommended</p>
                  <div className="space-y-2">
                    {RECOMMENDED_ITEMS.map(item => {
                      const checked = checkedItems.has(item.id)
                      return (
                        <button
                          key={item.id}
                          onClick={() => {
                            setCheckedItems(prev => {
                              const next = new Set(prev)
                              if (next.has(item.id)) next.delete(item.id)
                              else next.add(item.id)
                              return next
                            })
                          }}
                          className="w-full flex items-center gap-3 p-3 bg-pm-canada-bg/50 rounded-lg hover:bg-pm-canada-bg/80 transition-colors text-left"
                        >
                          <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                            checked ? 'bg-pm-accent/60 text-pm-canada-bg' : 'border border-pm-canada-border/60'
                          }`}>
                            {checked && <Check size={12} />}
                          </div>
                          <span className={`text-sm ${checked ? 'text-pm-canada-text-faint line-through' : 'text-pm-canada-text-muted'}`}>
                            {item.label}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                <div className="flex justify-between items-center">
                  <button onClick={prevStep} className={btnSecondary}>
                    <ChevronLeft size={16} /> Back
                  </button>
                  <div className="flex gap-2">
                    <Link to="/canada/portal/training" className={btnSecondary + ' border border-pm-canada-border rounded-lg px-4'}>
                      Go to Training
                    </Link>
                    <button
                      onClick={handleFinish}
                      disabled={!allRequiredDone}
                      className={`${btnPrimary} ${!allRequiredDone ? 'opacity-40 cursor-not-allowed' : 'animate-pulse'}`}
                    >
                      Go to My Dashboard <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              </div>
            )
          })()}
        </div>

        <p className="text-center text-2xs text-pm-canada-text-faint mt-4">
          Step {stepIdx + 1} of {STEPS.length}
        </p>
      </div>

      {showEmailPreview && (
        <EmailPreviewModal
          template="onboarding_complete"
          firstName={rep?.name?.split(' ')[0] || 'there'}
          portal="canada"
          onClose={() => setShowEmailPreview(false)}
          onSend={handleConfirmSend}
        />
      )}
    </div>
  )
}
