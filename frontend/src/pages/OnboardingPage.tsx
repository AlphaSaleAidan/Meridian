import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowRight, ArrowLeft, CheckCircle2, Loader2,
  Store, BarChart3, Lightbulb, Shield,
} from 'lucide-react'
import MeridianLogo, { MeridianWordmark } from '@/components/MeridianLogo'
import { api } from '@/lib/api'

type Step = 'welcome' | 'connect' | 'syncing' | 'ready'

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>('welcome')
  const [syncProgress, setSyncProgress] = useState(0)
  const [syncStage, setSyncStage] = useState('')
  const navigate = useNavigate()

  // Simulate sync progress
  useEffect(() => {
    if (step !== 'syncing') return

    const stages = [
      { pct: 10, label: 'Connecting to Square...' },
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
        setTimeout(() => setStep('ready'), 800)
      }
    }, 1200)

    return () => clearInterval(timer)
  }, [step])

  const handleConnect = () => {
    // Read org_id from URL params or default to 'demo'
    const params = new URLSearchParams(window.location.search)
    const orgId = params.get('org_id') || 'demo'

    if (orgId === 'demo') {
      // Demo mode — simulate the flow
      setStep('syncing')
    } else {
      // Production — redirect to Square OAuth via the backend
      window.location.href = api.squareAuthorize(orgId)
    }
  }

  // Handle return from Square OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.get('oauth') === 'success') {
      setStep('syncing')
    } else if (params.get('oauth') === 'denied') {
      // Could show an error, for now stay on connect step
      setStep('connect')
    }
  }, [])

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
          className="h-full bg-[#1A8FD6] transition-all duration-700 ease-out shadow-[0_0_12px_rgba(124,92,255,0.4)]"
          style={{
            width: step === 'welcome' ? '25%'
              : step === 'connect' ? '50%'
              : step === 'syncing' ? '75%'
              : '100%'
          }}
        />
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-lg">

          {/* Step 1: Welcome */}
          {step === 'welcome' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#1A8FD6]/10 border border-[#1A8FD6]/20 flex items-center justify-center mx-auto mb-6">
                <Store size={28} className="text-[#1A8FD6]" />
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                Welcome to <MeridianWordmark className="text-3xl" />
              </h1>
              <p className="text-[#A1A1A8] mb-8 leading-relaxed">
                Let's get your POS data connected so our AI can start finding revenue opportunities for your business.
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
                onClick={() => setStep('connect')}
                className="w-full py-3.5 text-base font-semibold text-white bg-[#1A8FD6] rounded-xl hover:bg-[#6B4FE0] transition-all duration-200 shadow-lg shadow-[#1A8FD6]/25 flex items-center justify-center gap-2"
              >
                Let's Go <ArrowRight size={18} />
              </button>
              <p className="text-xs text-[#A1A1A8]/30 mt-4">Takes less than 60 seconds</p>
            </div>
          )}

          {/* Step 2: Connect Square */}
          {step === 'connect' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#1F1F23] border border-[#2A2A30] flex items-center justify-center mx-auto mb-6">
                {/* Square icon */}
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="3" fill="#fff"/>
                  <rect x="7" y="7" width="10" height="10" rx="1.5" fill="#0A0A0B"/>
                </svg>
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                Connect Your Square
              </h1>
              <p className="text-[#A1A1A8] mb-8 leading-relaxed">
                We'll securely connect to your Square account to import your transaction data. You can disconnect anytime.
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

              <button
                onClick={handleConnect}
                className="w-full py-3.5 text-base font-semibold text-white bg-[#006AFF] rounded-xl hover:bg-[#0055CC] transition-all duration-200 shadow-lg shadow-blue-700/25 flex items-center justify-center gap-2"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                  <rect x="3" y="3" width="18" height="18" rx="3" fill="#fff"/>
                  <rect x="7" y="7" width="10" height="10" rx="1.5" fill="#006AFF"/>
                </svg>
                Connect with Square
              </button>

              <button
                onClick={() => setStep('welcome')}
                className="mt-3 text-sm text-[#A1A1A8]/50 hover:text-[#A1A1A8] transition-colors"
              >
                ← Back
              </button>
            </div>
          )}

          {/* Step 3: Syncing */}
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

              {/* Progress bar */}
              <div className="mb-4">
                <div className="flex items-center justify-between text-xs mb-2">
                  <span className="text-[#A1A1A8]">{syncStage}</span>
                  <span className="text-[#1A8FD6] font-mono">{syncProgress}%</span>
                </div>
                <div className="h-2 bg-[#1F1F23] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] rounded-full transition-all duration-1000 ease-out shadow-[0_0_16px_rgba(124,92,255,0.3)]"
                    style={{ width: `${syncProgress}%` }}
                  />
                </div>
              </div>

              {/* Sync stages checklist */}
              <div className="space-y-2 text-left mt-8">
                {[
                  { label: 'Connected to Square', threshold: 10 },
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

          {/* Step 4: Ready */}
          {step === 'ready' && (
            <div className="text-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-[#17C5B0]/10 border border-[#17C5B0]/20 flex items-center justify-center mx-auto mb-6">
                <CheckCircle2 size={28} className="text-[#17C5B0]" />
              </div>
              <h1 className="text-3xl font-bold text-[#F5F5F7] mb-3">
                You're All Set! 🎉
              </h1>
              <p className="text-[#A1A1A8] mb-8 leading-relaxed">
                We've analyzed 847 transactions and found <span className="text-[#17C5B0] font-semibold font-mono">$2,340/month</span> in revenue opportunities for your business.
              </p>

              {/* Quick preview stats */}
              <div className="grid grid-cols-3 gap-3 mb-8">
                <div className="card p-4 text-center">
                  <p className="text-lg font-bold font-mono text-[#1A8FD6]">$2,340</p>
                  <p className="text-xs text-[#A1A1A8]/50 mt-0.5">Money Left</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-lg font-bold font-mono text-[#F5F5F7]">8</p>
                  <p className="text-xs text-[#A1A1A8]/50 mt-0.5">AI Insights</p>
                </div>
                <div className="card p-4 text-center">
                  <p className="text-lg font-bold font-mono text-[#F5F5F7]">14</p>
                  <p className="text-xs text-[#A1A1A8]/50 mt-0.5">Day Forecast</p>
                </div>
              </div>

              <button
                onClick={() => navigate('/demo')}
                className="w-full py-3.5 text-base font-semibold text-white bg-[#1A8FD6] rounded-xl hover:bg-[#6B4FE0] transition-all duration-200 shadow-lg shadow-[#1A8FD6]/25 flex items-center justify-center gap-2"
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
