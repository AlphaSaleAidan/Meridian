import { lazy, Suspense, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, ChevronRight, Shield, Clock } from 'lucide-react'

import MeridianLogo, { MeridianEmblem, MeridianWordmark } from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'
import { TextRevealStagger } from '@/components/landing/TextReveal'
import ScrollReveal from '@/components/landing/ScrollReveal'
import MagneticButton from '@/components/landing/MagneticButton'
import CountUp from '@/components/landing/CountUp'
import BentoGrid from '@/components/landing/CanadaBentoGrid'

const MeshGradient = lazy(() => import('@/components/landing/MeshGradient'))

const EASE = [0.16, 1, 0.3, 1] as const

const testimonials = [
  {
    quote: 'Meridian found CA$4,416 in monthly revenue we were leaving on the table. The pricing insights alone paid for a year of service in two weeks.',
    author: 'Sarah Chen',
    role: 'Owner, Sunrise Coffee Co. — Vancouver',
  },
  {
    quote: 'We finally understand our data. The forecasting is scary accurate — we cut food waste by 30% in the first month.',
    author: 'Marcus Tremblay',
    role: 'GM, Eastside Kitchen — Toronto',
  },
  {
    quote: 'Setup took 45 seconds. I connected my POS and had actionable insights before my espresso was ready.',
    author: 'Priya Patel',
    role: 'Founder, Chai & Co. — Montreal',
  },
]

const logos = ['Square', 'Shopify', 'Toast', 'Clover', 'Lightspeed']

const dashboardStats = [
  { label: 'Revenue Today', value: 'CA$2,549', change: '+12.4%' },
  { label: 'Transactions', value: '124', change: '+8.2%' },
  { label: 'Avg Order', value: 'CA$20.55', change: '+3.1%' },
  { label: 'Money Left', value: 'CA$3,229', change: '', accent: true },
]

const metrics = [
  { end: 3229, prefix: 'CA$', suffix: '/mo', label: 'Avg. revenue found per merchant' },
  { end: 94, suffix: '%', label: 'Forecast accuracy rate' },
  { end: 45, suffix: 's', label: 'Average setup time' },
]

export default function CanadaLandingPage() {
  const navigate = useNavigate()
  const heroRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: heroRef, offset: ['start start', 'end start'] })
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0])
  const heroY = useTransform(scrollYProgress, [0, 0.8], [0, -60])

  return (
    <div className="min-h-screen bg-[#0A0A0B] overflow-x-hidden">
      <GrainOverlay />

      {/* NAV */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#1F1F23]/60 bg-[#0A0A0B]/70 backdrop-blur-[20px]">
        <div className="max-w-content mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <MeridianEmblem size={28} />
            <div className="flex flex-col">
              <MeridianWordmark height={14} />
              <span className="text-[8px] font-bold text-[#17C5B0] uppercase tracking-[0.2em] mt-0.5">Canada</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <MagneticButton onClick={() => navigate('/canada/demo')} className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200">
              Live Demo
            </MagneticButton>
            <MagneticButton onClick={() => navigate('/canada/careers')} className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200">
              Careers
            </MagneticButton>
            <MagneticButton onClick={() => navigate('/canada/portal/login')} className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200">
              Sales Portal
            </MagneticButton>
            <MagneticButton onClick={() => navigate('/canada/login')} className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200">
              Customer Login
            </MagneticButton>
            <MagneticButton onClick={() => navigate('/canada/onboard')} className="px-4 py-1.5 text-[13px] font-medium text-[#F5F5F7] bg-[#1A8FD6] rounded-md hover:bg-[#1574B8] transition-colors duration-200">
              Get Started
            </MagneticButton>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section ref={heroRef} className="relative min-h-screen flex items-center justify-center pt-14">
        <Suspense fallback={null}><MeshGradient /></Suspense>
        <div className="absolute top-1/4 left-1/4 aurora-glow aurora-blue" />
        <div className="absolute top-1/3 right-1/4 aurora-glow aurora-teal" style={{ width: 400, height: 400 }} />

        <motion.div style={{ opacity: heroOpacity, y: heroY }} className="relative z-10 max-w-content mx-auto px-6 text-center">
          <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, ease: EASE, delay: 0.05 }} className="flex justify-center mb-6">
            <MeridianEmblem size={72} />
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6, ease: EASE, delay: 0.1 }} className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#1F1F23] bg-[#111113]/80 text-[#A1A1A8] text-[11px] font-medium tracking-wide uppercase mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-[#17C5B0] animate-pulse" />
            AI POS Analytics &middot; Profit Growth — Canada
          </motion.div>

          <h1 className="text-[clamp(2.5rem,6vw,4.5rem)] font-bold text-[#F5F5F7] tracking-tight leading-[1.05] max-w-4xl mx-auto text-balance">
            <TextRevealStagger staggerDelay={0.06} baseDelay={0.3}>
              {[
                <span key="1">See the revenue you're</span>,
                <span key="2"><em className="font-serif italic font-normal bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">leaving behind</em></span>,
              ]}
            </TextRevealStagger>
          </h1>

          <motion.p initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE, delay: 0.55 }} className="mt-6 text-[#A1A1A8] text-lg max-w-xl mx-auto leading-relaxed">
            Connect your Square, Clover, or Lightspeed POS. Meridian's AI finds pricing gaps, upsell opportunities, and hidden revenue across Canada — with exact dollar amounts in CAD.
          </motion.p>

          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7, ease: EASE, delay: 0.7 }} className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
            <MagneticButton onClick={() => navigate('/canada/onboard')} className="group px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg transition-all duration-300 hover:shadow-[0_0_32px_rgba(26,143,214,0.3)] flex items-center gap-2">
              Get Started Free <ArrowRight size={15} className="transition-transform duration-300 group-hover:translate-x-0.5" />
            </MagneticButton>
            <MagneticButton onClick={() => navigate('/canada/demo')} className="group px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:border-[#2A2A30] hover:text-[#F5F5F7] transition-all duration-300 flex items-center gap-2">
              See Live Demo <ChevronRight size={15} className="transition-transform duration-300 group-hover:translate-x-0.5" />
            </MagneticButton>
          </motion.div>
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.6, ease: EASE, delay: 0.9 }} className="mt-4 text-[12px] text-[#A1A1A8]/50 text-center">
            No credit card required &middot; 45-second setup &middot; Cancel anytime
          </motion.p>

          {/* Dashboard preview */}
          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1, ease: EASE, delay: 0.9 }} className="mt-16 relative max-w-3xl mx-auto">
            <div className="rounded-xl border border-[#1F1F23] bg-[#111113] shadow-2xl shadow-black/50 overflow-hidden">
              <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-[#1F1F23]">
                {[0,1,2].map(n => <div key={n} className="w-2.5 h-2.5 rounded-full bg-[#1F1F23]" />)}
                <div className="flex-1 mx-4 h-5 rounded bg-[#0A0A0B] border border-[#1F1F23]" />
              </div>
              <div className="p-6 space-y-4">
                <div className="grid grid-cols-4 gap-3">
                  {dashboardStats.map(s => (
                    <div key={s.label} className="rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-3">
                      <p className="text-[10px] text-[#A1A1A8]">{s.label}</p>
                      <p className={`text-sm font-semibold font-mono mt-0.5 ${s.accent ? 'text-[#1A8FD6]' : 'text-[#F5F5F7]'}`}>{s.value}</p>
                      {s.change && <p className="text-[9px] text-[#17C5B0] mt-0.5">{s.change}</p>}
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-[80%] h-40 bg-[#1A8FD6] opacity-[0.06] blur-[80px] rounded-full" />
          </motion.div>
        </motion.div>
      </section>

      {/* LOGO BAR */}
      <section className="py-16 border-t border-[#1F1F23]/40">
        <ScrollReveal className="max-w-content mx-auto px-6">
          <p className="text-center text-[11px] uppercase tracking-[0.2em] text-[#A1A1A8]/50 mb-8">Works with your existing POS</p>
          <div className="flex items-center justify-center gap-12 opacity-30">
            {logos.map(name => <span key={name} className="text-[#A1A1A8] text-sm font-medium tracking-wide">{name}</span>)}
          </div>
        </ScrollReveal>
      </section>

      {/* BENTO FEATURES */}
      <section className="py-24 border-t border-[#1F1F23]/40">
        <div className="max-w-content mx-auto px-6">
          <ScrollReveal className="text-center mb-16 relative">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow aurora-blue" style={{ width: 400, height: 400, opacity: 0.08 }} />
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight relative">
              Your POS data, <em className="font-serif italic font-normal bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">decoded</em>
            </h2>
            <p className="mt-4 text-[#A1A1A8] max-w-md mx-auto text-[15px] leading-relaxed relative">
              Meridian transforms raw transaction data into intelligence you can act on today.
            </p>
          </ScrollReveal>
          <BentoGrid />
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="py-24 border-t border-[#1F1F23]/40 relative overflow-hidden">
        <div className="absolute top-0 right-0 aurora-glow aurora-teal" style={{ width: 500, height: 500, opacity: 0.06 }} />
        <div className="max-w-content mx-auto px-6 relative">
          <ScrollReveal className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">From connected to <em className="font-serif italic font-normal text-[#17C5B0]">profitable</em></h2>
            <p className="mt-4 text-[#A1A1A8] text-[15px]">Three steps. Under sixty seconds.</p>
          </ScrollReveal>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto">
            {[
              { step: '01', title: 'Connect Your POS', desc: 'One-click Square, Clover, or Lightspeed authorization. No API keys, no config files.' },
              { step: '02', title: 'AI Analyzes', desc: 'Our engine processes your entire transaction history and surfaces patterns humans miss.' },
              { step: '03', title: 'Capture Revenue', desc: 'Get specific, dollar-denominated recommendations on pricing, staffing, and products.' },
            ].map((s, i) => (
              <ScrollReveal key={s.step} delay={i * 0.12}>
                <div className="text-left">
                  <span className="font-mono text-[11px] text-[#1A8FD6] tracking-wider">{s.step}</span>
                  <h3 className="text-[#F5F5F7] font-semibold text-lg mt-2 mb-2">{s.title}</h3>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{s.desc}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* METRICS */}
      <section className="py-28 border-t border-[#1F1F23]/40 relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow aurora-blue" style={{ width: 700, height: 700, opacity: 0.08 }} />
        <div className="max-w-content mx-auto px-6 relative">
          <ScrollReveal className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">
              The numbers <em className="font-serif italic font-normal bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">speak</em>
            </h2>
          </ScrollReveal>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-2xl mx-auto text-center">
            {metrics.map((stat, i) => (
              <ScrollReveal key={stat.label} delay={i * 0.1}>
                <div>
                  <div className="text-4xl md:text-5xl font-bold text-[#F5F5F7]">
                    <CountUp end={stat.end} prefix={stat.prefix || ''} suffix={stat.suffix} duration={2200} />
                  </div>
                  <p className="text-[#A1A1A8] text-[13px] mt-2">{stat.label}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="py-24 border-t border-[#1F1F23]/40">
        <div className="max-w-content mx-auto px-6">
          <ScrollReveal className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">
              Trusted by <em className="font-serif italic font-normal text-[#17C5B0]">operators</em>
            </h2>
          </ScrollReveal>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            {testimonials.map((t, i) => (
              <ScrollReveal key={t.author} delay={i * 0.1}>
                <blockquote className="relative">
                  <p className="text-[#F5F5F7] text-[15px] leading-relaxed font-light">"{t.quote}"</p>
                  <footer className="mt-6">
                    <p className="text-[#F5F5F7] text-[13px] font-medium">{t.author}</p>
                    <p className="text-[#A1A1A8] text-[12px] mt-0.5">{t.role}</p>
                  </footer>
                </blockquote>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-28 border-t border-[#1F1F23]/40 relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow aurora-blue" style={{ width: 500, height: 500, opacity: 0.1 }} />
        <div className="max-w-content mx-auto px-6 text-center relative">
          <ScrollReveal>
            <div className="flex justify-center mb-8"><MeridianEmblem size={48} /></div>
            <h2 className="text-3xl md:text-5xl font-bold text-[#F5F5F7] tracking-tight text-balance max-w-2xl mx-auto leading-[1.1]">
              Stop guessing.<br />Start <em className="font-serif italic font-normal bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">knowing.</em>
            </h2>
            <p className="mt-6 text-[#A1A1A8] text-[15px] max-w-md mx-auto leading-relaxed">
              Connect your Square, Clover, or Lightspeed POS and see exactly where your revenue is hiding. First month free — start seeing results in 60 seconds.
            </p>
            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3">
              <MagneticButton onClick={() => navigate('/canada/onboard')} className="group px-8 py-3.5 text-[15px] font-medium text-white bg-[#1A8FD6] rounded-lg transition-all duration-300 hover:shadow-[0_0_40px_rgba(26,143,214,0.35)] inline-flex items-center gap-2">
                Get Started Free <ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-0.5" />
              </MagneticButton>
              <MagneticButton onClick={() => navigate('/canada/demo')} className="group px-8 py-3.5 text-[15px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:border-[#2A2A30] hover:text-[#F5F5F7] transition-all duration-300 inline-flex items-center gap-2">
                Book a Demo <ChevronRight size={16} className="transition-transform duration-300 group-hover:translate-x-0.5" />
              </MagneticButton>
            </div>
            <p className="mt-3 text-[11px] text-[#A1A1A8]/40">No credit card &middot; No contracts &middot; First month free</p>
          </ScrollReveal>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#1F1F23]/40 py-8">
        <div className="max-w-content mx-auto px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <MeridianEmblem size={20} />
              <div className="flex flex-col">
                <MeridianWordmark height={10} />
                <span className="text-[7px] font-bold text-[#17C5B0] uppercase tracking-[0.2em] mt-0.5">Canada</span>
              </div>
              <div className="flex items-center gap-1.5 text-[11px] text-[#A1A1A8]/50">
                <span className="w-1.5 h-1.5 rounded-full bg-[#17C5B0]" />
                All systems operational
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-4 text-[12px] text-[#A1A1A8]/60">
                <span className="flex items-center gap-1.5"><Shield size={12} /> Bank-level encryption</span>
                <span className="flex items-center gap-1.5"><Clock size={12} /> Real-time sync</span>
                <a onClick={() => navigate('/canada/careers')} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">Careers</a>
                <a onClick={() => navigate('/canada/portal/login')} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">Sales Portal</a>
                <a onClick={() => navigate('/canada/login')} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">Customer Login</a>
              </div>
              <p className="text-[11px] text-[#A1A1A8]/30">&copy; 2026 <span className="font-semibold bg-gradient-to-r from-[#1A8FD6] to-[#17C5B0] bg-clip-text text-transparent">Meridian</span></p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
