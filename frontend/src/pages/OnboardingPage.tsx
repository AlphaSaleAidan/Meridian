import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, CheckCircle2, Loader2,
  Store, BarChart3, Lightbulb, Shield, Star, Users,
  CreditCard, TrendingUp, Zap, ChevronRight,
  UtensilsCrossed, ShoppingBag, Pizza, Scissors, Package,
  DollarSign, BarChart, Rocket, Search,
} from 'lucide-react'
import MeridianLogo, { MeridianWordmark } from '@/components/MeridianLogo'
import { api } from '@/lib/api'

type Step = 'welcome' | 'questions' | 'connect' | 'syncing' | 'offer' | 'checkout' | 'ready'

/* ──────────────── Qualifying questions ──────────────── */
interface QAnswer {
  transactions: string
  staff: string
  industry: string
  revenue: string
  painPoint: string
  pos: string
}

const QUESTIONS: {
  key: keyof QAnswer
  label: string
  options: { value: string; label: string; sub?: string; icon?: React.ReactNode }[]
}[] = [
  {
    key: 'industry',
    label: 'What type of business do you run?',
    options: [
      { value: 'restaurant', label: 'Restaurant / Café', icon: <UtensilsCrossed size={18} /> },
      { value: 'retail', label: 'Retail Store', icon: <ShoppingBag size={18} /> },
      { value: 'qsr', label: 'Quick-Service / Food Truck', icon: <Pizza size={18} /> },
      { value: 'salon', label: 'Salon / Spa', icon: <Scissors size={18} /> },
      { value: 'other', label: 'Other', icon: <Package size={18} /> },
    ],
  },
  {
    key: 'transactions',
    label: 'How many transactions do you process a month?',
    options: [
      { value: '<500', label: 'Under 500', sub: 'Just getting started' },
      { value: '500-2000', label: '500 – 2,000', sub: 'Growing steadily' },
      { value: '2000-5000', label: '2,000 – 5,000', sub: 'Established business' },
      { value: '5000+', label: '5,000+', sub: 'High volume' },
    ],
  },
  {
    key: 'staff',
    label: 'How many staff members do you have?',
    options: [
      { value: '1-3', label: '1 – 3', sub: 'Owner-operated' },
      { value: '4-10', label: '4 – 10', sub: 'Small team' },
      { value: '11-25', label: '11 – 25', sub: 'Growing team' },
      { value: '25+', label: '25+', sub: 'Large team' },
    ],
  },
  {
    key: 'revenue',
    label: "What's your approximate monthly revenue?",
    options: [
      { value: '<25k', label: 'Under $25K' },
      { value: '25-75k', label: '$25K – $75K' },
      { value: '75-200k', label: '$75K – $200K' },
      { value: '200k+', label: '$200K+' },
    ],
  },
  {
    key: 'painPoint',
    label: "What's your biggest challenge right now?",
    options: [
      { value: 'pricing', label: 'Not sure if my prices are right', icon: <DollarSign size={18} /> },
      { value: 'staffing', label: 'Staffing & labor costs', icon: <Users size={18} /> },
      { value: 'inventory', label: 'Inventory waste & dead stock', icon: <BarChart size={18} /> },
      { value: 'growth', label: 'Growing revenue', icon: <Rocket size={18} /> },
      { value: 'visibility', label: 'Lack of data visibility', icon: <Search size={18} /> },
    ],
  },
]

/* ──────────────── Fake reviews ──────────────── */
const REVIEWS = [
  {
    name: 'Marcus T.',
    role: 'Owner, Brewed Awakening',
    text: 'Within the first week, Meridian found $1,800/mo in pricing opportunities I completely missed. Paid for itself 7x over.',
    stars: 5,
    avatar: 'MT',
  },
  {
    name: 'Sarah K.',
    role: 'GM, The Local Kitchen',
    text: 'The staffing insights alone saved us $3,200 last month. We cut one overstaffed shift and added coverage during our actual peak hours.',
    stars: 5,
    avatar: 'SK',
  },
  {
    name: 'James P.',
    role: 'Owner, Fresh & Fast',
    text: 'I was skeptical about another SaaS tool, but the free month convinced me. Now I can\'t imagine running my shop without the daily insights.',
    stars: 5,
    avatar: 'JP',
  },
  {
    name: 'Emily R.',
    role: 'Owner, Bloom Boutique',
    text: 'The dead stock analysis found $450/mo in inventory I should have clearanced weeks ago. The ROI is undeniable.',
    stars: 5,
    avatar: 'ER',
  },
  {
    name: 'David L.',
    role: 'Operator, Taco City',
    text: 'We went from guessing to knowing. Revenue is up 12% since we started acting on Meridian\'s recommendations.',
    stars: 5,
    avatar: 'DL',
  },
]

/* ──────────────── Component ──────────────── */
export default function OnboardingPage() {
  const [step, setStep] = useState<Step>('welcome')
  const [syncProgress, setSyncProgress] = useState(0)
  const [syncStage, setSyncStage] = useState('')
  const [questionIdx, setQuestionIdx] = useState(0)
  const [answers, setAnswers] = useState<Partial<QAnswer>>({})
  const [selectedPOS, setSelectedPOS] = useState<'square' | 'clover' | 'toast' | null>(null)
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'weekly'>('monthly')
  const [couponCode, setCouponCode] = useState('')
  const [couponApplied, setCouponApplied] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const navigate = useNavigate()

  const allQuestionsAnswered = questionIdx >= QUESTIONS.length

  // Simulate sync progress
  useEffect(() => {
    if (step !== 'syncing') return

    const posName = selectedPOS === 'clover' ? 'Clover' : selectedPOS === 'toast' ? 'Toast' : 'Square'
    const stages = [
      { pct: 10, label: `Connecting to ${posName}...` },
      { pct: 25, label: 'Fetching transaction history...' },
      { pct: 45, label: 'Processing 847 transactions...' },
      { pct: 60, label: 'Analyzing product catalog...' },
      { pct: 75, label: 'Running AI analysis...' },
      { pct: 88, label: 'Generating insights...' },
      { pct: 95, label: 'Building forecasts...' },
      { pct: 100, label: 'All done!' },
    ]

    let i = 0
    setSyncProgress(0)
    setSyncStage(stages[0].label)

    const timer = setInterval(() => {
      i++
      if (i < stages.length) {
        setSyncProgress(stages[i].pct)
        setSyncStage(stages[i].label)
      }
      if (i >= stages.length) {
        clearInterval(timer)
        setTimeout(() => setStep('offer'), 800)
      }
    }, 1200)

    return () => clearInterval(timer)
  }, [step, selectedPOS])

  const handleConnect = (pos: 'square' | 'clover' | 'toast') => {
    setSelectedPOS(pos)
    const params = new URLSearchParams(window.location.search)
    const orgId = params.get('org_id') || 'demo'

    if (orgId === 'demo') {
      setStep('syncing')
    } else if (pos === 'square') {
      window.location.href = api.squareAuthorize(orgId)
    } else if (pos === 'toast') {
      // Toast OAuth — update when backend route is ready
      setStep('syncing')
    } else {
      // Clover OAuth — update when backend route is ready
      setStep('syncing')
    }
  }

  const handleCheckout = async () => {
    setIsProcessing(true)
    // Simulate payment processing
    await new Promise(r => setTimeout(r, 2200))
    setIsProcessing(false)
    setStep('ready')
  }

  // Handle OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('oauth') === 'success') {
      setStep('syncing')
    } else if (params.get('oauth') === 'denied') {
      setStep('connect')
    }
  }, [])

  const handleAnswer = (key: keyof QAnswer, value: string) => {
    setAnswers(prev => ({ ...prev, [key]: value }))
    setTimeout(() => {
      if (questionIdx < QUESTIONS.length - 1) {
        setQuestionIdx(questionIdx + 1)
      } else {
        setQuestionIdx(QUESTIONS.length) // triggers connect step
        setTimeout(() => setStep('connect'), 400)
      }
    }, 300)
  }

  const stepProgress: Record<Step, number> = {
    welcome: 8,
    questions: 10 + (questionIdx / QUESTIONS.length) * 30,
    connect: 45,
    syncing: 60,
    offer: 75,
    checkout: 88,
    ready: 100,
  }

  return (
    <div className="min-h-screen bg-[#0A0A0B] flex flex-col">
      {/* Header */}
      <header className="border-b border-[#1F1F23] bg-[#0A0A0B]/80 backdrop-blur-xl">
        <div className="max-w-4xl mx-auto px-6 h-16 flex items-center justify-between">
          <MeridianLogo size={32} showWordmark />
          <button
            onClick={() => navigate('/landing')}
            className="text-sm text-[#A1A1A8] hover:text-white transition-colors flex items-center gap-1"
          >
            <ArrowLeft size={14} /> Back
          </button>
        </div>
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-[#1F1F23]">
        <div
          className="h-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] transition-all duration-700 ease-out shadow-[0_0_12px_rgba(26,143,214,0.4)]"
          style={{ width: `${stepProgress[step]}%` }}
        />
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-lg">

          {/* ──────── Step 1: Welcome ──────── */}
          {step === 'welcome' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-6">
                <Store size={28} className="text-[#1A8FD6]" />
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                Welcome to <MeridianWordmark className="text-3xl" />
              </h1>
              <p className="text-[#A1A1A8] mb-8 leading-relaxed">
                Let's personalize your experience. We'll ask a few quick questions, then connect your POS system so our AI can start finding revenue opportunities.
              </p>

              <div className="space-y-3 text-left mb-10">
                {[
                  { icon: BarChart3, text: 'See real-time revenue analytics & trends' },
                  { icon: Lightbulb, text: 'Get AI insights on pricing, staffing & products' },
                  { icon: Shield, text: 'Bank-level security — we never store card data' },
                ].map(item => (
                  <div key={item.text} className="flex items-center gap-3 p-3 rounded-lg bg-[#111113] border border-[#1F1F23]">
                    <item.icon size={18} className="text-[#1A8FD6] flex-shrink-0" />
                    <span className="text-sm text-[#A1A1A8]">{item.text}</span>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setStep('questions')}
                className="w-full py-3.5 text-base font-semibold text-white bg-[#1A8FD6] rounded-xl hover:bg-[#148ACF] transition-all duration-200 shadow-lg shadow-[#1A8FD6]/25 flex items-center justify-center gap-2"
              >
                Get Started <ArrowRight size={18} />
              </button>
              <p className="text-xs text-[#A1A1A8]/30 mt-4">Takes less than 2 minutes</p>
            </div>
          )}

          {/* ──────── Step 2: Qualifying Questions ──────── */}
          {step === 'questions' && !allQuestionsAnswered && (
            <div className="animate-fade-in" key={questionIdx}>
              <div className="flex items-center gap-2 mb-6">
                <span className="text-xs text-[#1A8FD6] font-mono font-semibold">
                  {questionIdx + 1} of {QUESTIONS.length}
                </span>
                <div className="flex-1 h-1 bg-[#1F1F23] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-[#1A8FD6] rounded-full transition-all duration-500"
                    style={{ width: `${((questionIdx + 1) / QUESTIONS.length) * 100}%` }}
                  />
                </div>
              </div>

              <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">
                {QUESTIONS[questionIdx].label}
              </h2>

              <div className="space-y-2.5">
                {QUESTIONS[questionIdx].options.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => handleAnswer(QUESTIONS[questionIdx].key, opt.value)}
                    className={`w-full text-left p-4 rounded-xl border transition-all duration-200 hover:border-[#1A8FD6]/50 hover:bg-[#1A8FD6]/5 group ${
                      answers[QUESTIONS[questionIdx].key] === opt.value
                        ? 'border-[#1A8FD6] bg-[#1A8FD6]/10'
                        : 'border-[#1F1F23] bg-[#111113]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {opt.icon && <span className="text-[#1A8FD6] shrink-0">{opt.icon}</span>}
                        <div>
                          <span className="text-[#F5F5F7] font-medium">{opt.label}</span>
                          {opt.sub && (
                            <span className="block text-xs text-[#A1A1A8]/60 mt-0.5">{opt.sub}</span>
                          )}
                        </div>
                      </div>
                      <ChevronRight size={16} className="text-[#A1A1A8]/30 group-hover:text-[#1A8FD6] transition-colors" />
                    </div>
                  </button>
                ))}
              </div>

              {questionIdx > 0 && (
                <button
                  onClick={() => setQuestionIdx(questionIdx - 1)}
                  className="mt-4 text-sm text-[#A1A1A8]/50 hover:text-[#A1A1A8] transition-colors"
                >
                  ← Previous question
                </button>
              )}
            </div>
          )}

          {/* ──────── Step 3: Connect Square/Clover ──────── */}
          {step === 'connect' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center mx-auto mb-6">
                <Store size={28} className="text-[#F5F5F7]" />
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                Connect Your POS
              </h1>
              <p className="text-[#A1A1A8] mb-8 leading-relaxed">
                We'll securely connect to your POS to import transaction data. Read-only access — you can disconnect anytime.
              </p>

              <div className="card p-5 mb-6 text-left">
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3">
                  <MeridianWordmark className="text-sm" /> will access:
                </h3>
                <div className="space-y-2.5">
                  {[
                    'Transaction & payment history',
                    'Product catalog & inventory',
                    'Customer purchase patterns',
                    'Location & business info',
                  ].map(item => (
                    <div key={item} className="flex items-center gap-2.5">
                      <CheckCircle2 size={14} className="text-[#17C5B0] flex-shrink-0" />
                      <span className="text-sm text-[#A1A1A8]">{item}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-4 pt-3 border-t border-[#1F1F23]">
                  <div className="flex items-center gap-2 text-xs text-[#A1A1A8]/50">
                    <Shield size={12} />
                    We never store credit card numbers or sensitive payment data
                  </div>
                </div>
              </div>

              {/* POS choice buttons */}
              <div className="space-y-3">
                <button
                  onClick={() => handleConnect('square')}
                  className="w-full py-3.5 text-base font-semibold text-white bg-[#006AFF] rounded-xl hover:bg-[#0055CC] transition-all duration-200 shadow-lg shadow-blue-700/25 flex items-center justify-center gap-3"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <rect x="3" y="3" width="18" height="18" rx="3" fill="#fff"/>
                    <rect x="7" y="7" width="10" height="10" rx="1.5" fill="#006AFF"/>
                  </svg>
                  Connect with Square
                </button>

                <button
                  onClick={() => handleConnect('clover')}
                  className="w-full py-3.5 text-base font-semibold text-white bg-[#43B02A] rounded-xl hover:bg-[#3A9A24] transition-all duration-200 shadow-lg shadow-green-700/25 flex items-center justify-center gap-3"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <circle cx="9" cy="9" r="5" fill="#fff" opacity="0.9"/>
                    <circle cx="15" cy="9" r="5" fill="#fff" opacity="0.7"/>
                    <circle cx="9" cy="15" r="5" fill="#fff" opacity="0.7"/>
                    <circle cx="15" cy="15" r="5" fill="#fff" opacity="0.5"/>
                  </svg>
                  Connect with Clover
                </button>

                <button
                  onClick={() => handleConnect('toast')}
                  className="w-full py-3.5 text-base font-semibold text-white bg-[#FF6100] rounded-xl hover:bg-[#E55800] transition-all duration-200 shadow-lg shadow-orange-700/25 flex items-center justify-center gap-3"
                >
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                    <rect x="2" y="6" width="20" height="12" rx="3" fill="#fff"/>
                    <path d="M7 10h10M7 14h6" stroke="#FF6100" strokeWidth="2" strokeLinecap="round"/>
                  </svg>
                  Connect with Toast
                </button>
              </div>

              <button
                onClick={() => { setQuestionIdx(QUESTIONS.length - 1); setStep('questions') }}
                className="mt-4 text-sm text-[#A1A1A8]/50 hover:text-[#A1A1A8] transition-colors"
              >
                ← Back
              </button>
            </div>
          )}

          {/* ──────── Step 4: Syncing ──────── */}
          {step === 'syncing' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-6">
                <Loader2 size={28} className="text-[#1A8FD6] animate-spin" />
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                Analyzing Your Data
              </h1>
              <p className="text-[#A1A1A8] mb-10">
                This usually takes about 30 seconds...
              </p>

              <div className="mb-4">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-[#A1A1A8]">{syncStage}</span>
                  <span className="text-[#1A8FD6] font-mono">{syncProgress}%</span>
                </div>
                <div className="h-2 bg-[#1F1F23] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] rounded-full transition-all duration-1000 ease-out shadow-[0_0_16px_rgba(26,143,214,0.3)]"
                    style={{ width: `${syncProgress}%` }}
                  />
                </div>
              </div>

              <div className="space-y-2 text-left mt-8">
                {[
                  { label: `Connected to ${selectedPOS === 'clover' ? 'Clover' : selectedPOS === 'toast' ? 'Toast' : 'Square'}`, threshold: 10 },
                  { label: 'Imported transaction history', threshold: 25 },
                  { label: 'Processed 847 transactions', threshold: 45 },
                  { label: 'Analyzed product catalog', threshold: 60 },
                  { label: 'Generated AI insights', threshold: 88 },
                  { label: 'Built revenue forecasts', threshold: 95 },
                ].map(item => {
                  const done = syncProgress >= item.threshold
                  const active = !done && syncProgress >= item.threshold - 15
                  return (
                    <div
                      key={item.label}
                      className={`flex items-center gap-3 p-2.5 rounded-lg transition-all duration-500 ${
                        done ? 'bg-[#17C5B0]/5 border border-[#17C5B0]/10' :
                        active ? 'bg-[#111113] border border-[#1F1F23]' :
                        'border border-transparent opacity-40'
                      }`}
                    >
                      {done ? (
                        <CheckCircle2 size={16} className="text-[#17C5B0] flex-shrink-0" />
                      ) : active ? (
                        <Loader2 size={16} className="text-[#1A8FD6] animate-spin flex-shrink-0" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-[#1F1F23] flex-shrink-0" />
                      )}
                      <span className={`text-sm ${done ? 'text-[#17C5B0]' : active ? 'text-[#A1A1A8]' : 'text-[#A1A1A8]/40'}`}>
                        {item.label}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* ──────── Step 5: Offer ──────── */}
          {step === 'offer' && (
            <div className="animate-fade-in">
              <div className="text-center mb-8">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#17C5B0]/10 border border-[#17C5B0]/20 text-[#17C5B0] text-xs font-semibold mb-4">
                  <Zap size={12} /> Analysis Complete
                </div>
                <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                  We Found <span className="text-[#17C5B0]">$2,340/mo</span> in Opportunities
                </h1>
                <p className="text-[#A1A1A8] leading-relaxed">
                  Unlock your full dashboard with AI-powered insights, forecasts, and real-time analytics.
                </p>
              </div>

              {/* Pricing card */}
              <div className="relative rounded-2xl border-2 border-[#1A8FD6] bg-gradient-to-b from-[#1A8FD6]/5 to-transparent p-6 mb-6">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-[#1A8FD6] text-white text-xs font-bold uppercase tracking-wider">
                  Limited Offer
                </div>

                <div className="text-center mb-5">
                  <div className="flex items-baseline justify-center gap-1 mb-1">
                    <span className="text-4xl font-bold text-[#F5F5F7]">$0</span>
                    <span className="text-[#A1A1A8] text-sm">/first month</span>
                  </div>
                  <p className="text-sm text-[#A1A1A8]">
                    Then <span className="text-[#F5F5F7] font-semibold">$250/mo</span> or <span className="text-[#F5F5F7] font-semibold">$65/wk</span> · First month free
                  </p>
                </div>

                <div className="space-y-2.5 mb-5">
                  {[
                    { icon: TrendingUp, text: 'Real-time revenue analytics & trends' },
                    { icon: Lightbulb, text: 'PhD-level AI insights with citations' },
                    { icon: BarChart3, text: '14-day revenue forecasts' },
                    { icon: Users, text: 'Staffing & labor optimization' },
                    { icon: Store, text: 'Inventory & dead stock detection' },
                    { icon: CreditCard, text: 'Pricing & discount ROI analysis' },
                  ].map(item => (
                    <div key={item.text} className="flex items-center gap-3">
                      <div className="w-6 h-6 rounded-md bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0">
                        <item.icon size={13} className="text-[#1A8FD6]" />
                      </div>
                      <span className="text-sm text-[#A1A1A8]">{item.text}</span>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => setStep('checkout')}
                  className="w-full py-3.5 text-base font-semibold text-white bg-[#1A8FD6] rounded-xl hover:bg-[#148ACF] transition-all duration-200 shadow-lg shadow-[#1A8FD6]/25 flex items-center justify-center gap-2"
                >
                  Start Free Month <ArrowRight size={18} />
                </button>

                <p className="text-center text-xs text-[#A1A1A8]/40 mt-3">
                  Cancel anytime after 3 months · No hidden fees
                </p>
              </div>

              {/* Social proof strip */}
              <div className="flex items-center justify-center gap-4 py-3">
                <div className="flex -space-x-2">
                  {['MT', 'SK', 'JP', 'ER'].map(initials => (
                    <div key={initials} className="w-7 h-7 rounded-full bg-[#1F1F23] border-2 border-[#0A0A0B] flex items-center justify-center text-[10px] font-bold text-[#A1A1A8]">
                      {initials}
                    </div>
                  ))}
                </div>
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map(i => (
                    <Star key={i} size={14} className="text-[#F59E0B] fill-[#F59E0B]" />
                  ))}
                </div>
                <span className="text-xs text-[#A1A1A8]/60">Trusted by 200+ businesses</span>
              </div>
            </div>
          )}

          {/* ──────── Step 6: Checkout ──────── */}
          {step === 'checkout' && (
            <div className="animate-fade-in">
              <div className="text-center mb-6">
                <h1 className="text-2xl font-bold text-[#F5F5F7] mb-2">
                  Start Your Free Month
                </h1>
                <p className="text-sm text-[#A1A1A8]">
                  Choose your billing cycle · First 30 days free with a 3-month commitment
                </p>
              </div>

              {/* Billing cycle toggle */}
              <div className="card p-6 mb-6">
                <h3 className="text-sm font-semibold text-[#F5F5F7] mb-3">Choose billing frequency</h3>
                <div className="grid grid-cols-2 gap-3 mb-5">
                  <button
                    onClick={() => setBillingCycle('monthly')}
                    className={`p-4 rounded-xl border-2 transition-all text-center ${
                      billingCycle === 'monthly'
                        ? 'border-[#1A8FD6] bg-[#1A8FD6]/5'
                        : 'border-[#1F1F23] bg-[#111113] hover:border-[#2A2A30]'
                    }`}
                  >
                    <p className="text-lg font-bold text-[#F5F5F7] font-mono">$250</p>
                    <p className="text-xs text-[#A1A1A8]">/month</p>
                    {billingCycle === 'monthly' && (
                      <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#1A8FD6]/10 text-[#1A8FD6] text-[10px] font-semibold">
                        <CheckCircle2 size={10} /> Selected
                      </div>
                    )}
                  </button>
                  <button
                    onClick={() => setBillingCycle('weekly')}
                    className={`p-4 rounded-xl border-2 transition-all text-center ${
                      billingCycle === 'weekly'
                        ? 'border-[#1A8FD6] bg-[#1A8FD6]/5'
                        : 'border-[#1F1F23] bg-[#111113] hover:border-[#2A2A30]'
                    }`}
                  >
                    <p className="text-lg font-bold text-[#F5F5F7] font-mono">$65</p>
                    <p className="text-xs text-[#A1A1A8]">/week</p>
                    {billingCycle === 'weekly' && (
                      <div className="mt-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-[#1A8FD6]/10 text-[#1A8FD6] text-[10px] font-semibold">
                        <CheckCircle2 size={10} /> Selected
                      </div>
                    )}
                  </button>
                </div>

                {/* Order summary */}
                <div className="pt-4 border-t border-[#1F1F23]">
                  {billingCycle === 'monthly' ? (
                    <>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-[#A1A1A8]">Month 1 (today)</span>
                        <span className="text-[#17C5B0] font-semibold">
                          <span className="line-through text-[#A1A1A8]/40 mr-1.5">$250</span> FREE
                        </span>
                      </div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-[#A1A1A8]">Month 2</span>
                        <span className="text-[#F5F5F7] font-mono">$250</span>
                      </div>
                      <div className="flex justify-between text-sm mb-3">
                        <span className="text-[#A1A1A8]">Month 3</span>
                        <span className="text-[#F5F5F7] font-mono">$250</span>
                      </div>
                      <div className="flex justify-between text-sm pt-3 border-t border-[#1F1F23]">
                        <span className="text-[#F5F5F7] font-semibold">3-month total</span>
                        <span className="text-[#F5F5F7] font-bold font-mono">$500</span>
                      </div>
                      <p className="text-xs text-[#A1A1A8]/40 mt-2">Auto-renews at $250/mo · Cancel anytime after commitment</p>
                    </>
                  ) : (
                    <>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-[#A1A1A8]">Weeks 1–4 (first 30 days)</span>
                        <span className="text-[#17C5B0] font-semibold">
                          <span className="line-through text-[#A1A1A8]/40 mr-1.5">$260</span> FREE
                        </span>
                      </div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-[#A1A1A8]">Weeks 5–8</span>
                        <span className="text-[#F5F5F7] font-mono">$65/wk</span>
                      </div>
                      <div className="flex justify-between text-sm mb-3">
                        <span className="text-[#A1A1A8]">Weeks 9–12</span>
                        <span className="text-[#F5F5F7] font-mono">$65/wk</span>
                      </div>
                      <div className="flex justify-between text-sm pt-3 border-t border-[#1F1F23]">
                        <span className="text-[#F5F5F7] font-semibold">3-month total</span>
                        <span className="text-[#F5F5F7] font-bold font-mono">$520</span>
                      </div>
                      <p className="text-xs text-[#A1A1A8]/40 mt-2">Auto-renews at $65/wk · Cancel anytime after commitment</p>
                    </>
                  )}
                </div>

                {/* Coupon code */}
                <div className="mt-5 pt-4 border-t border-[#1F1F23]">
                  <label className="block text-xs font-semibold text-[#A1A1A8] mb-1.5 uppercase tracking-wider">Have a promo code?</label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={couponCode}
                      onChange={e => { setCouponCode(e.target.value.toUpperCase()); setCouponApplied(false) }}
                      placeholder="Enter code"
                      className="flex-1 px-4 py-2.5 rounded-xl bg-[#111113] border border-[#1F1F23] text-[#F5F5F7] placeholder-[#A1A1A8]/30 focus:outline-none focus:border-[#1A8FD6] transition-colors text-sm font-mono"
                    />
                    <button
                      onClick={() => {
                        if (couponCode === 'FREEMONTH') setCouponApplied(true)
                      }}
                      className="px-4 py-2.5 rounded-xl bg-[#1F1F23] border border-[#2A2A30] text-sm font-semibold text-[#F5F5F7] hover:bg-[#2A2A30] transition-colors"
                    >
                      Apply
                    </button>
                  </div>
                  {couponApplied && (
                    <div className="flex items-center gap-1.5 mt-2 text-xs text-[#17C5B0] font-medium">
                      <CheckCircle2 size={12} /> First month free — code applied!
                    </div>
                  )}
                  {couponCode && !couponApplied && couponCode !== 'FREEMONTH' && couponCode.length >= 5 && (
                    <p className="mt-2 text-xs text-red-400">Invalid promo code</p>
                  )}
                </div>

                {/* Square Checkout button — monthly or weekly */}
                <a
                  href={billingCycle === 'weekly'
                    ? (import.meta.env.VITE_SQUARE_CHECKOUT_WEEKLY_URL || 'https://square.link/u/JuktuGXs')
                    : (import.meta.env.VITE_SQUARE_CHECKOUT_URL || 'https://square.link/u/0ScYp9tI')
                  }
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full mt-5 py-3.5 text-base font-semibold text-white bg-[#1A8FD6] rounded-xl hover:bg-[#148ACF] transition-all duration-200 shadow-lg shadow-[#1A8FD6]/25 flex items-center justify-center gap-2"
                >
                  <CreditCard size={18} /> Start Free Month — Pay Securely
                </a>

                <div className="flex items-center justify-center gap-3 mt-3">
                  <div className="flex items-center gap-1.5 text-xs text-[#A1A1A8]/40">
                    <Shield size={12} />
                    Powered by Square
                  </div>
                  <span className="text-[#A1A1A8]/20">·</span>
                  <span className="text-xs text-[#A1A1A8]/40">PCI compliant</span>
                  <span className="text-[#A1A1A8]/20">·</span>
                  <span className="text-xs text-[#A1A1A8]/40">256-bit SSL</span>
                </div>
              </div>

              {/* Reviews */}
              <div className="space-y-3">
                <h3 className="text-xs font-semibold text-[#A1A1A8]/50 uppercase tracking-wider text-center">
                  What business owners are saying
                </h3>
                {REVIEWS.map(review => (
                  <div key={review.name} className="p-4 rounded-xl bg-[#111113] border border-[#1F1F23]">
                    <div className="flex items-center gap-1 mb-2">
                      {[1, 2, 3, 4, 5].map(i => (
                        <Star key={i} size={12} className="text-[#F59E0B] fill-[#F59E0B]" />
                      ))}
                    </div>
                    <p className="text-sm text-[#A1A1A8] leading-relaxed mb-3">
                      &ldquo;{review.text}&rdquo;
                    </p>
                    <div className="flex items-center gap-2.5">
                      <div className="w-7 h-7 rounded-full bg-[#1F1F23] flex items-center justify-center text-[10px] font-bold text-[#A1A1A8]">
                        {review.avatar}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-[#F5F5F7]">{review.name}</p>
                        <p className="text-xs text-[#A1A1A8]/50">{review.role}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <button
                onClick={() => setStep('offer')}
                className="mt-4 w-full text-sm text-[#A1A1A8]/50 hover:text-[#A1A1A8] transition-colors text-center"
              >
                ← Back to offer
              </button>
            </div>
          )}

          {/* ──────── Step 7: Ready ──────── */}
          {step === 'ready' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 size={28} className="text-[#17C5B0]" />
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                You're All Set!
              </h1>
              <p className="text-[#A1A1A8] mb-8 leading-relaxed">
                Your free month is active. We've analyzed 847 transactions and found <span className="text-[#17C5B0] font-semibold font-mono">$2,340/month</span> in revenue opportunities for your business.
              </p>

              <div className="grid grid-cols-3 gap-3 mb-8">
                <div className="card p-4 text-center">
                  <p className="text-lg font-bold font-mono text-[#1A8FD6]">$2,340</p>
                  <p className="text-xs text-[#A1A1A8]/50 mt-0.5">Money Left</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-lg font-bold font-mono text-[#F5F5F7]">10</p>
                  <p className="text-xs text-[#A1A1A8]/50 mt-0.5">AI Insights</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-lg font-bold font-mono text-[#F5F5F7]">14</p>
                  <p className="text-xs text-[#A1A1A8]/50 mt-0.5">Day Forecast</p>
                </div>
              </div>

              <button
                onClick={() => navigate('/demo')}
                className="w-full py-3.5 text-base font-semibold text-white bg-[#1A8FD6] rounded-xl hover:bg-[#148ACF] transition-all duration-200 shadow-lg shadow-[#1A8FD6]/25 flex items-center justify-center gap-2"
              >
                Go to Dashboard <ArrowRight size={18} />
              </button>
              <p className="text-xs text-[#A1A1A8]/30 mt-4">
                Your data syncs automatically every 15 minutes
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
