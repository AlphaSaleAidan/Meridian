import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Lock, Sparkles, User, Users, CheckSquare,
  ChevronRight, ChevronLeft, Check, Eye, EyeOff,
} from 'lucide-react'
import { useSalesAuth } from '@/lib/sales-auth'
import { onboardingEmails } from '@/lib/email-service'
import { MeridianEmblem } from '@/components/MeridianLogo'

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
  const [showPassword, setShowPassword] = useState(false)
  const [passwordError, setPasswordError] = useState('')

  const [profile, setProfile] = useState({
    display_name: rep?.name || '',
    phone: rep?.phone || '',
    city: '',
    province: '',
    bio: '',
  })

  const [checkedItems, setCheckedItems] = useState(new Set(['password']))

  const stepIdx = STEPS.findIndex(s => s.id === step)

  function nextStep() {
    if (stepIdx < STEPS.length - 1) setStep(STEPS[stepIdx + 1].id)
  }

  function prevStep() {
    if (stepIdx > 0) setStep(STEPS[stepIdx - 1].id)
  }

  function handlePasswordSubmit() {
    if (password.length < 8) {
      setPasswordError('Password must be at least 8 characters')
      return
    }
    if (password !== confirmPassword) {
      setPasswordError('Passwords do not match')
      return
    }
    setPasswordError('')
    setCheckedItems(prev => new Set([...prev, 'password']))
    nextStep()
  }

  function handleProfileSubmit() {
    setCheckedItems(prev => new Set([...prev, 'profile']))
    nextStep()
  }

  function handleFinish() {
    localStorage.setItem('meridian_onboarding_complete', 'true')
    if (rep?.email) {
      onboardingEmails.complete(rep.email, rep.name)
    }
    navigate('/canada/portal/dashboard')
  }

  const inputClass = 'w-full px-3 py-2.5 bg-[#0a0f0d] border border-[#1a2420] rounded-lg text-sm text-white placeholder-[#6b7a74] focus:outline-none focus:border-[#00d4aa]/50 focus:ring-1 focus:ring-[#00d4aa]/20 transition-colors'
  const btnPrimary = 'flex items-center gap-1.5 px-5 py-2.5 bg-[#00d4aa] text-[#0a0f0d] text-sm font-semibold rounded-lg hover:bg-[#00d4aa]/90 transition-all'
  const btnSecondary = 'flex items-center gap-1.5 px-4 py-2.5 text-sm text-[#6b7a74] hover:text-white transition-colors'

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="flex flex-col items-center gap-1 mb-6">
          <MeridianEmblem size={36} />
          <span className="text-lg font-bold text-[#F5F5F7] mt-2">Sales Onboarding</span>
          <span className="text-[10px] font-semibold text-[#00d4aa] uppercase tracking-widest">
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
                    isActive ? 'bg-[#00d4aa] text-[#0a0f0d]' :
                    isDone ? 'bg-[#00d4aa]/20 text-[#00d4aa]' :
                    'bg-[#1a2420] text-[#6b7a74]'
                  }`}
                >
                  {isDone ? <Check size={14} /> : <Icon size={14} />}
                </div>
                {i < STEPS.length - 1 && (
                  <div className={`w-6 h-0.5 mx-0.5 ${i < stepIdx ? 'bg-[#00d4aa]/40' : 'bg-[#1a2420]'}`} />
                )}
              </div>
            )
          })}
        </div>

        {/* Card */}
        <div className="bg-[#0f1512] border border-[#1a2420] rounded-xl p-6 sm:p-8">
          {/* Step 1: Password */}
          {step === 'password' && (
            <div className="space-y-5">
              <div className="text-center">
                <div className="w-12 h-12 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                  <Lock size={22} className="text-[#00d4aa]" />
                </div>
                <h2 className="text-lg font-bold text-white">Set Your Password</h2>
                <p className="text-sm text-[#6b7a74] mt-1">Secure your account with a strong password.</p>
              </div>
              {passwordError && (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">{passwordError}</div>
              )}
              <div>
                <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">New Password</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    className={inputClass}
                    placeholder="Min 8 characters"
                  />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#6b7a74]">
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Confirm Password</label>
                <input type="password" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} className={inputClass} placeholder="Confirm your password" />
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
                <div className="w-12 h-12 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                  <Sparkles size={22} className="text-[#00d4aa]" />
                </div>
                <h2 className="text-lg font-bold text-white">
                  Welcome to Meridian, {rep?.name?.split(' ')[0] || 'there'}
                </h2>
                <p className="text-sm text-[#6b7a74] mt-1">
                  You're now part of the Meridian Canada sales team.
                </p>
              </div>

              {/* Income Projection Cards */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: 'Month 1', amount: 'CA$2,025', sub: '5 closes' },
                  { label: 'Month 6', amount: 'CA$12,150', sub: '30 closes' },
                  { label: 'Month 12', amount: 'CA$24,300', sub: '60 closes' },
                ].map(card => (
                  <div key={card.label} className="bg-[#0a0f0d] border border-[#1a2420] rounded-xl p-4 text-center">
                    <p className="text-[10px] font-medium text-[#6b7a74] uppercase tracking-wide">{card.label}</p>
                    <p className="text-xl font-bold text-[#f0b429] mt-1">{card.amount}</p>
                    <p className="text-[10px] text-[#4a5550] mt-0.5">{card.sub}</p>
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
                <div className="w-12 h-12 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                  <User size={22} className="text-[#00d4aa]" />
                </div>
                <h2 className="text-lg font-bold text-white">Your Profile</h2>
                <p className="text-sm text-[#6b7a74] mt-1">Fill in your details so your team and manager can find you.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Display Name</label>
                  <input value={profile.display_name} onChange={e => setProfile(p => ({ ...p, display_name: e.target.value }))} className={inputClass} placeholder="Your name" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Phone</label>
                  <input type="tel" value={profile.phone} onChange={e => setProfile(p => ({ ...p, phone: e.target.value }))} className={inputClass} placeholder="(604) 555-1234" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">City</label>
                  <input value={profile.city} onChange={e => setProfile(p => ({ ...p, city: e.target.value }))} className={inputClass} placeholder="Vancouver" />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Province</label>
                  <select value={profile.province} onChange={e => setProfile(p => ({ ...p, province: e.target.value }))} className={inputClass}>
                    <option value="">Select province</option>
                    {PROVINCES.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-xs font-medium text-[#6b7a74] mb-1.5">Short Bio (optional)</label>
                  <textarea value={profile.bio} onChange={e => setProfile(p => ({ ...p, bio: e.target.value }))} className={inputClass + ' resize-none h-16'} placeholder="A few words about yourself..." />
                </div>
              </div>
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
                <div className="w-12 h-12 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                  <Users size={22} className="text-[#00d4aa]" />
                </div>
                <h2 className="text-lg font-bold text-white">Meet Your Managers</h2>
                <p className="text-sm text-[#6b7a74] mt-1">Here's who you'll be working with in Canada.</p>
              </div>
              <div className="space-y-3">
                <div className="bg-[#0a0f0d] border border-[#1a2420] rounded-xl p-5">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full bg-[#00d4aa]/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-[#00d4aa]">EC</span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Enoch Cheung</p>
                      <p className="text-xs text-[#6b7a74]">Canadian Regional Director</p>
                      <p className="text-[10px] text-[#00d4aa] mt-0.5">Nexus Consulting</p>
                    </div>
                  </div>
                  <p className="text-xs text-[#6b7a74] mt-4 leading-relaxed">
                    Enoch leads Meridian's Canadian expansion. He's your primary contact for pipeline strategy,
                    deal support, and regional questions. Don't hesitate to reach out.
                  </p>
                </div>
                <div className="bg-[#0a0f0d] border border-[#1a2420] rounded-xl p-5">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-full bg-[#7c3aed]/20 flex items-center justify-center flex-shrink-0">
                      <span className="text-sm font-bold text-[#7c3aed]">AN</span>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-white">Aidan Nguyen</p>
                      <p className="text-xs text-[#6b7a74]">Canadian Admin</p>
                      <p className="text-[10px] text-[#00d4aa] mt-0.5">Meridian</p>
                    </div>
                  </div>
                  <p className="text-xs text-[#6b7a74] mt-4 leading-relaxed">
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
                  <div className="w-12 h-12 rounded-full bg-[#00d4aa]/10 flex items-center justify-center mx-auto mb-3">
                    <CheckSquare size={22} className="text-[#00d4aa]" />
                  </div>
                  <h2 className="text-lg font-bold text-white">Getting Started Checklist</h2>
                  <p className="text-sm text-[#6b7a74] mt-1">Complete the required items to unlock your dashboard.</p>
                </div>

                {/* Progress bar */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs text-[#6b7a74]">Required Progress</span>
                    <span className="text-xs font-semibold text-[#00d4aa]">{requiredDone}/{REQUIRED_ITEMS.length}</span>
                  </div>
                  <div className="h-2 bg-[#1a2420] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-[#00d4aa] rounded-full transition-all duration-500"
                      style={{ width: `${(requiredDone / REQUIRED_ITEMS.length) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Required items */}
                <div>
                  <p className="text-[10px] font-semibold text-[#6b7a74] uppercase tracking-wider mb-2">Required</p>
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
                          className="w-full flex items-center gap-3 p-3 bg-[#0a0f0d] rounded-lg hover:bg-[#0a0f0d]/80 transition-colors text-left"
                        >
                          <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                            checked ? 'bg-[#00d4aa] text-[#0a0f0d]' : 'border border-[#1a2420]'
                          }`}>
                            {checked && <Check size={12} />}
                          </div>
                          <span className={`text-sm flex-1 ${checked ? 'text-[#6b7a74] line-through' : 'text-white'}`}>
                            {item.label}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                </div>

                {/* Recommended items */}
                <div>
                  <p className="text-[10px] font-semibold text-[#6b7a74] uppercase tracking-wider mb-2">Recommended</p>
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
                          className="w-full flex items-center gap-3 p-3 bg-[#0a0f0d]/50 rounded-lg hover:bg-[#0a0f0d]/80 transition-colors text-left"
                        >
                          <div className={`w-5 h-5 rounded flex items-center justify-center flex-shrink-0 ${
                            checked ? 'bg-[#00d4aa]/60 text-[#0a0f0d]' : 'border border-[#1a2420]/60'
                          }`}>
                            {checked && <Check size={12} />}
                          </div>
                          <span className={`text-sm ${checked ? 'text-[#4a5550] line-through' : 'text-[#6b7a74]'}`}>
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
                    <a href="/canada/portal/training" className={btnSecondary + ' border border-[#1a2420] rounded-lg px-4'}>
                      Go to Training
                    </a>
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

        <p className="text-center text-[10px] text-[#4a5550] mt-4">
          Step {stepIdx + 1} of {STEPS.length}
        </p>
      </div>
    </div>
  )
}
