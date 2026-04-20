import { useNavigate } from 'react-router-dom'
import {
  Zap, TrendingUp, Lightbulb, Shield, ArrowRight,
  BarChart3, DollarSign, Clock, ChevronRight,
} from 'lucide-react'

const features = [
  {
    icon: TrendingUp,
    title: 'Revenue Intelligence',
    desc: 'Real-time revenue tracking with daily, weekly, and hourly breakdowns. Know exactly how your business is performing.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
  {
    icon: DollarSign,
    title: 'Money Left on the Table',
    desc: 'Our AI finds pricing gaps, upsell opportunities, and waste reduction — showing you exactly where hidden revenue is.',
    color: 'text-meridian-400',
    bg: 'bg-meridian-500/10',
  },
  {
    icon: Lightbulb,
    title: 'AI-Powered Insights',
    desc: 'Actionable recommendations backed by data — from staffing optimization to product bundling to seasonal trends.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  {
    icon: BarChart3,
    title: 'Revenue Forecasting',
    desc: 'Know what\'s coming. AI-powered predictions with confidence intervals help you plan inventory, staff, and promotions.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
]

const stats = [
  { value: '$2,340', label: 'Avg. Monthly Savings Found', suffix: '/mo' },
  { value: '94%', label: 'Forecast Accuracy', suffix: '' },
  { value: '< 60s', label: 'Setup Time', suffix: '' },
]

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-slate-950 overflow-x-hidden">
      {/* Nav */}
      <header className="border-b border-slate-800/40 backdrop-blur-xl bg-slate-950/80 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-meridian-700 flex items-center justify-center">
              <Zap className="w-4 h-4 text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight text-white">Meridian</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/demo')}
              className="px-4 py-2 text-sm font-medium text-slate-300 hover:text-white transition-colors"
            >
              Live Demo
            </button>
            <button
              onClick={() => navigate('/onboarding')}
              className="px-4 py-2 text-sm font-medium text-white bg-meridian-700 rounded-lg hover:bg-meridian-600 transition-colors flex items-center gap-1.5"
            >
              Get Started <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        {/* Gradient orbs */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] opacity-20">
          <div className="absolute top-20 left-0 w-72 h-72 bg-meridian-700 rounded-full blur-[120px]" />
          <div className="absolute top-40 right-0 w-60 h-60 bg-purple-600 rounded-full blur-[100px]" />
        </div>

        <div className="relative max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-meridian-700/10 border border-meridian-700/20 text-meridian-400 text-xs font-medium mb-8">
            <Zap size={12} />
            AI-Powered POS Analytics for Independent Businesses
          </div>

          <h1 className="text-4xl sm:text-5xl md:text-6xl font-bold text-white tracking-tight leading-[1.1] max-w-4xl mx-auto">
            See the money you're
            <span className="text-meridian-400"> leaving on the table</span>
          </h1>

          <p className="mt-6 text-lg text-slate-400 max-w-2xl mx-auto leading-relaxed">
            Connect your Square POS and Meridian's AI instantly finds pricing gaps, 
            upsell opportunities, and hidden revenue — showing you exactly where to grow.
          </p>

          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => navigate('/onboarding')}
              className="w-full sm:w-auto px-8 py-3.5 text-base font-semibold text-white bg-meridian-700 rounded-xl hover:bg-meridian-600 transition-all duration-200 shadow-lg shadow-meridian-700/25 flex items-center justify-center gap-2"
            >
              Connect Your Square <ArrowRight size={18} />
            </button>
            <button
              onClick={() => navigate('/demo')}
              className="w-full sm:w-auto px-8 py-3.5 text-base font-medium text-slate-300 border border-slate-700 rounded-xl hover:border-slate-500 hover:text-white transition-all duration-200 flex items-center justify-center gap-2"
            >
              See Live Demo <ChevronRight size={18} />
            </button>
          </div>

          {/* Stats */}
          <div className="mt-16 grid grid-cols-3 gap-8 max-w-lg mx-auto">
            {stats.map(s => (
              <div key={s.label} className="text-center">
                <p className="text-2xl font-bold text-white">
                  {s.value}<span className="text-meridian-400 text-lg">{s.suffix}</span>
                </p>
                <p className="text-xs text-slate-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="py-24 border-t border-slate-800/40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white">
              Your POS data, <span className="text-meridian-400">supercharged</span>
            </h2>
            <p className="mt-4 text-slate-400 max-w-xl mx-auto">
              Meridian connects to your Square POS and transforms transaction data into actionable intelligence.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {features.map(f => (
              <div key={f.title} className="card p-6 hover:border-slate-700/80 transition-all duration-200 group">
                <div className={`w-10 h-10 rounded-xl ${f.bg} flex items-center justify-center mb-4`}>
                  <f.icon size={20} className={f.color} />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{f.title}</h3>
                <p className="text-sm text-slate-400 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24 border-t border-slate-800/40 bg-slate-900/30">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-white">
              Up and running in <span className="text-meridian-400">60 seconds</span>
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {[
              { step: '1', title: 'Connect Square', desc: 'One-click OAuth. No API keys, no config files. Just authorize and go.' },
              { step: '2', title: 'AI Analyzes', desc: 'Our engine processes your transaction history and surfaces patterns humans miss.' },
              { step: '3', title: 'Find Revenue', desc: 'Get actionable insights on pricing, staffing, products, and more — with dollar amounts attached.' },
            ].map(s => (
              <div key={s.step} className="text-center">
                <div className="w-12 h-12 rounded-full bg-meridian-700/15 border border-meridian-700/25 flex items-center justify-center mx-auto mb-4">
                  <span className="text-meridian-400 font-bold text-lg">{s.step}</span>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-sm text-slate-400">{s.desc}</p>
              </div>
            ))}
          </div>

          <div className="text-center mt-12">
            <button
              onClick={() => navigate('/onboarding')}
              className="px-8 py-3.5 text-base font-semibold text-white bg-meridian-700 rounded-xl hover:bg-meridian-600 transition-all duration-200 shadow-lg shadow-meridian-700/25 inline-flex items-center gap-2"
            >
              Get Started Free <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {/* Trust bar */}
      <section className="py-16 border-t border-slate-800/40">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-8 text-sm text-slate-500">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-emerald-500" />
              <span>Bank-level encryption</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock size={16} className="text-meridian-500" />
              <span>Real-time sync</span>
            </div>
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-amber-500" />
              <span>No credit card required</span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-slate-800/40 py-8">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded bg-meridian-700 flex items-center justify-center">
              <Zap className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-medium text-slate-400">Meridian</span>
          </div>
          <p className="text-xs text-slate-600">© 2026 Meridian. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
