import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, useScroll, useTransform } from 'framer-motion'
import { ArrowRight, ChevronRight, Shield, Clock, Menu, X, Bot, Phone, TrendingUp } from 'lucide-react'

import { useGsapTimeline, useGsapFrom } from '@/hooks/useGsapScrollTrigger'
import SEO from '@/components/SEO'
import MeridianLogo, { MeridianEmblem } from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'
import { TextRevealStagger } from '@/components/landing/TextReveal'
import ScrollReveal from '@/components/landing/ScrollReveal'
import MagneticButton from '@/components/landing/MagneticButton'
import CountUp from '@/components/landing/CountUp'
import TiltCard from '@/components/landing/TiltCard'
import ScheduleQuote from '@/components/landing/ScheduleQuote'

const MeshGradient = lazy(() => import('@/components/landing/MeshGradient'))

const EASE = [0.16, 1, 0.3, 1] as const
const ACCENT = '#0066FF'
const ACCENT_CA = '#00B4D8'

const testimonials = [
  {
    quote: 'Meridian found $3,200 in monthly revenue we were leaving on the table. The pricing insights alone paid for a year of service in two weeks.',
    author: 'Sarah Chen',
    role: 'Owner, Sunrise Coffee Co.',
  },
  {
    quote: 'We finally understand our data. The forecasting is scary accurate — we cut food waste by 30% in the first month.',
    author: 'Marcus Rivera',
    role: 'GM, Eastside Kitchen',
  },
  {
    quote: 'Setup took 45 seconds. I connected my POS and had actionable insights before my espresso was ready.',
    author: 'Priya Patel',
    role: 'Founder, Chai & Co.',
  },
]

const posLogos = ['Square', 'Toast', 'Clover', 'Lightspeed', 'Shopify POS', 'TouchBistro', 'Moneris', 'Alice POS']

export default function LandingPage() {
  const navigate = useNavigate()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const heroRef = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ['start start', 'end start'],
  })
  const heroOpacity = useTransform(scrollYProgress, [0, 0.8], [1, 0])
  const heroY = useTransform(scrollYProgress, [0, 0.8], [0, -60])

  // GSAP ScrollTrigger — stats counter stagger reveal
  const { triggerRef: statsRef, timeline: statsTl } = useGsapTimeline({ start: 'top 85%' })

  // GSAP ScrollTrigger — POS logos slide-in
  const logosRef = useGsapFrom(
    { x: 100, opacity: 0, stagger: 0.1, duration: 0.6 },
    { start: 'top 90%' }
  )

  // GSAP ScrollTrigger — feature cards scale-up reveal
  const { triggerRef: featuresRef, timeline: featuresTl } = useGsapTimeline({ start: 'top 80%' })

  // Pre-compute random values to avoid Math.random() in render
  const barHeights = useMemo(
    () => Array.from({ length: 24 }, (_, i) => 20 + Math.sin(i * 0.5) * 30 + Math.random() * 25),
    [],
  )
  const dotStyles = useMemo(
    () =>
      Array.from({ length: 36 }, (_, i) => ({
        opacity: i < 24 ? 0.4 + Math.random() * 0.6 : 0.3,
        animationDuration: `${2 + Math.random() * 3}s`,
        animationDelay: `${Math.random() * 2}s`,
      })),
    [],
  )

  // Wire up GSAP timelines after mount
  useEffect(() => {
    if (statsTl.current) {
      statsTl.current.from('.gsap-stat-card', {
        y: 30,
        opacity: 0,
        stagger: 0.12,
        duration: 0.7,
        ease: 'power2.out',
      })
    }
    if (featuresTl.current) {
      featuresTl.current.from('.gsap-feature-card', {
        scale: 0.9,
        opacity: 0,
        y: 40,
        stagger: 0.15,
        duration: 0.8,
        ease: 'power2.out',
      })
    }
  }, [])


  return (
    <div className="min-h-screen bg-[#0A0A0B] overflow-x-hidden">
      <SEO
        title="Meridian Intelligence — Turn Every Transaction Into Intelligence"
        description="AI-powered POS analytics for restaurants, retail, auto shops & dispensaries. Connect Square, Toast, Clover and 77+ systems. First month free."
        path="/"
      />
      <GrainOverlay />

      {/* ─── NAV ──────────────────────────────────── */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-[#1F1F23]/60 bg-[#0A0A0B]/70 backdrop-blur-[20px]">
        <div className="max-w-content mx-auto px-6 h-14 flex items-center justify-between">
          <MeridianLogo size={28} showWordmark showTagline={false} />
          <div className="hidden md:flex items-center gap-2">
            {[
              { label: 'Live Demo', path: '/demo' },
              { label: 'Blog', path: '/blog' },
              { label: 'Careers', path: '/careers' },
              { label: 'Sales Portal', path: '/us/portal/login' },
              { label: 'Customer Login', path: '/customer/login' },
            ].map(link => (
              <MagneticButton
                key={link.path}
                onClick={() => navigate(link.path)}
                className="px-4 py-1.5 text-[13px] font-medium text-[#A1A1A8] hover:text-[#F5F5F7] transition-colors duration-200"
              >
                {link.label}
              </MagneticButton>
            ))}
            <MagneticButton
              onClick={() => navigate('/us/onboard')}
              className="px-4 py-1.5 text-[13px] font-medium text-[#F5F5F7] rounded-md hover:brightness-110 transition-all duration-200"
              style={{ backgroundColor: ACCENT }}
            >
              Start Today
            </MagneticButton>
          </div>
          <div className="flex md:hidden items-center gap-2">
            <button
              onClick={() => navigate('/customer/login')}
              className="px-3 py-1.5 text-[13px] font-medium text-[#F5F5F7] rounded-md transition-colors"
              style={{ backgroundColor: ACCENT }}
            >
              Sign In
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-[#A1A1A8] hover:text-white hover:bg-[#1F1F23] transition-colors"
              aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
            >
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </div>
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-[#1F1F23]/60 bg-[#0A0A0B]/95 backdrop-blur-[20px]">
            <div className="max-w-content mx-auto px-6 py-3 flex flex-col gap-1">
              {[
                { label: 'Customer Login', path: '/customer/login', accent: true },
                { label: 'Start Today', path: '/us/onboard' },
                { label: 'Live Demo', path: '/demo' },
                { label: 'Blog', path: '/blog' },
                { label: 'Careers', path: '/careers' },
              ].map(link => (
                <button
                  key={link.path}
                  onClick={() => { navigate(link.path); setMobileMenuOpen(false) }}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg text-[14px] font-medium transition-colors text-left min-h-[48px]"
                  style={{ color: link.accent ? ACCENT : '#F5F5F7' }}
                >
                  {link.label}
                </button>
              ))}
              <div className="border-t border-[#1F1F23]/60 mt-1 pt-1">
                <button
                  onClick={() => { navigate('/us/portal/login'); setMobileMenuOpen(false) }}
                  className="flex items-center gap-3 px-4 py-3 rounded-lg text-[13px] font-medium text-[#A1A1A8]/60 hover:text-[#A1A1A8] hover:bg-[#1F1F23] transition-colors text-left min-h-[48px] w-full"
                >
                  Sales Rep Portal
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* ─── HERO ─────────────────────────────────── */}
      <section ref={heroRef} className="relative min-h-screen flex items-center justify-center pt-14">
        <Suspense fallback={null}>
          <MeshGradient />
        </Suspense>
        <div className="absolute top-1/4 left-1/4 aurora-glow" style={{ background: `radial-gradient(circle, ${ACCENT} 0%, transparent 70%)` }} />
        <div className="absolute top-1/3 right-1/4 aurora-glow" style={{ width: 400, height: 400, background: `radial-gradient(circle, ${ACCENT_CA} 0%, transparent 70%)` }} />

        <motion.div
          style={{ opacity: heroOpacity, y: heroY }}
          className="relative z-10 max-w-content mx-auto px-6 text-center"
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, ease: EASE, delay: 0.05 }}
            className="flex justify-center mb-6"
          >
            <MeridianEmblem size={72} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE, delay: 0.1 }}
            className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#1F1F23] bg-[#111113]/80 text-[#A1A1A8] text-[11px] font-medium tracking-wide uppercase mb-8"
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ backgroundColor: ACCENT }} />
            AI POS Analytics · Revenue Intelligence
          </motion.div>

          <h1 className="text-[clamp(2.5rem,6vw,4.5rem)] font-bold text-[#F5F5F7] tracking-tight leading-[1.05] max-w-4xl mx-auto text-balance">
            <TextRevealStagger staggerDelay={0.06} baseDelay={0.15}>
              {[
                <span key="1">Turn Every Transaction</span>,
                <span key="2">
                  Into{' '}
                  <em className="font-serif italic font-normal bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(to right, ${ACCENT}, ${ACCENT_CA})` }}>
                    Intelligence
                  </em>
                </span>,
              ]}
            </TextRevealStagger>
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.3 }}
            className="mt-6 text-[#A1A1A8] text-lg max-w-xl mx-auto leading-relaxed"
          >
            AI-powered POS analytics for restaurants, retail, auto shops &amp; dispensaries.
            Connect your POS — Meridian finds your hidden revenue with exact dollar amounts.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, ease: EASE, delay: 0.4 }}
            className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-3"
          >
            <MagneticButton
              onClick={() => navigate('/us/onboard')}
              className="group px-6 py-3 text-[14px] font-medium text-white rounded-lg transition-all duration-300 flex items-center gap-2"
              style={{ backgroundColor: ACCENT, boxShadow: `0 0 32px ${ACCENT}30` }}
            >
              Start Today
              <ArrowRight size={15} className="transition-transform duration-300 group-hover:translate-x-0.5" />
            </MagneticButton>
            <MagneticButton
              onClick={() => navigate('/demo')}
              className="group px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:border-[#2A2A30] hover:text-[#F5F5F7] transition-all duration-300 flex items-center gap-2"
            >
              See it live
              <ChevronRight size={15} className="transition-transform duration-300 group-hover:translate-x-0.5" />
            </MagneticButton>
          </motion.div>

          {/* Dashboard preview */}
          <motion.div
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: EASE, delay: 0.55 }}
            className="mt-16 relative max-w-3xl mx-auto"
          >
            <div className="animate-float-slow">
              <div className="rounded-xl border border-[#1F1F23] bg-[#111113] shadow-2xl shadow-black/50 overflow-hidden">
                <div className="flex items-center gap-1.5 px-4 py-2.5 border-b border-[#1F1F23]">
                  <div className="w-2.5 h-2.5 rounded-full bg-[#1F1F23]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-[#1F1F23]" />
                  <div className="w-2.5 h-2.5 rounded-full bg-[#1F1F23]" />
                  <div className="flex-1 mx-4 h-5 rounded bg-[#0A0A0B] border border-[#1F1F23]" />
                </div>
                <div className="p-6 space-y-4">
                  <div className="grid grid-cols-4 gap-3">
                    {[
                      { label: 'Revenue Today', value: '$1,847', change: '+12.4%' },
                      { label: 'Transactions', value: '124', change: '+8.2%' },
                      { label: 'Avg Order', value: '$14.89', change: '+3.1%' },
                      { label: 'Money Left', value: '$2,340', change: '', accent: true },
                    ].map(s => (
                      <div key={s.label} className="rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-3">
                        <p className="text-[10px] text-[#A1A1A8]">{s.label}</p>
                        <p className="text-sm font-semibold font-mono mt-0.5" style={{ color: s.accent ? ACCENT : '#F5F5F7' }}>
                          {s.value}
                        </p>
                        {s.change && <p className="text-[9px] mt-0.5" style={{ color: ACCENT_CA }}>{s.change}</p>}
                      </div>
                    ))}
                  </div>
                  <div className="rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-4 h-28 flex items-end gap-1">
                    {barHeights.map((h, i) => (
                      <div
                        key={i}
                        className="flex-1 rounded-sm"
                        style={{ height: `${h}%`, background: i >= 20 ? `${ACCENT}50` : `${ACCENT}25` }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
            <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-[80%] h-40 opacity-[0.06] blur-[80px] rounded-full" style={{ backgroundColor: ACCENT }} />
          </motion.div>
        </motion.div>
      </section>

      {/* ─── POS MARQUEE ──────────────────────────── */}
      <section className="py-16 border-t border-[#1F1F23]/40">
        <ScrollReveal className="max-w-content mx-auto px-6">
          <h2 className="text-center text-[11px] uppercase tracking-[0.2em] text-[#A1A1A8]/50 mb-8 font-normal">
            Works with 80+ POS Systems
          </h2>
        </ScrollReveal>
        <div ref={logosRef} className="relative overflow-hidden">
          <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-[#0A0A0B] to-transparent z-10" />
          <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-[#0A0A0B] to-transparent z-10" />
          <div className="flex gap-16 items-center" style={{ animation: 'marquee-scroll 25s linear infinite', width: 'max-content' }}>
            {[...posLogos, ...posLogos].map((name, i) => (
              <span key={`${name}-${i}`} className="text-[#A1A1A8]/30 text-base font-medium tracking-wide whitespace-nowrap flex-shrink-0">
                {name}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ─── FEATURE TRIPTYCH ─────────────────────── */}
      <section className="py-24 border-t border-[#1F1F23]/40">
        <div className="max-w-content mx-auto px-6">
          <ScrollReveal className="text-center mb-16 relative">
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow" style={{ width: 400, height: 400, opacity: 0.08, background: `radial-gradient(circle, ${ACCENT} 0%, transparent 70%)` }} />
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight relative">
              Three Engines Driving Your{' '}
              <em className="font-serif italic font-normal bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(to right, ${ACCENT}, ${ACCENT_CA})` }}>Revenue Growth</em>
            </h2>
            <p className="mt-4 text-[#A1A1A8] max-w-md mx-auto text-[15px] leading-relaxed relative">
              Meridian transforms raw POS transaction data into intelligence you can act on today.
            </p>
          </ScrollReveal>

          <div ref={featuresRef} className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Revenue Intelligence */}
            <TiltCard className="gsap-feature-card h-full bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#2A2A30] transition-colors duration-300">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${ACCENT}15` }}>
                    <TrendingUp size={18} style={{ color: ACCENT }} />
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold">Revenue Intelligence</h3>
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed mb-4">
                  AI surfaces pricing gaps, upsell opportunities, and staffing inefficiencies with exact dollar amounts.
                </p>
                <div className="rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-4 font-mono text-sm">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[#A1A1A8] text-xs">Monthly opportunity</span>
                    <span className="font-semibold text-sm" style={{ color: ACCENT }}>$2,340</span>
                  </div>
                  <div className="space-y-2">
                    {[
                      { label: 'Bundle pricing', value: '$890', pct: 38 },
                      { label: 'Peak staffing', value: '$720', pct: 31 },
                      { label: 'Menu optimization', value: '$730', pct: 31 },
                    ].map(item => (
                      <div key={item.label}>
                        <div className="flex justify-between text-xs mb-1">
                          <span className="text-[#A1A1A8]">{item.label}</span>
                          <span className="text-[#F5F5F7]">{item.value}</span>
                        </div>
                        <div className="h-1 bg-[#1F1F23] rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width: `${item.pct}%`, backgroundColor: ACCENT }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </TiltCard>

            {/* 41-Agent AI Swarm */}
            <TiltCard className="gsap-feature-card h-full bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#2A2A30] transition-colors duration-300">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${ACCENT}15` }}>
                    <Bot size={18} style={{ color: ACCENT }} />
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold">41-Agent AI Swarm</h3>
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed mb-4">
                  Specialized AI agents work 24/7 on forecasting, anomaly detection, customer segmentation, and competitive pricing.
                </p>
                <div className="rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-4">
                  <div className="grid grid-cols-6 gap-1.5">
                    {dotStyles.map((ds, i) => (
                      <div
                        key={i}
                        className="w-full aspect-square rounded-full transition-all duration-1000"
                        style={{
                          backgroundColor: i < 12 ? ACCENT : i < 24 ? ACCENT_CA : '#1F1F23',
                          opacity: ds.opacity,
                          animation: i < 24 ? `pulse ${ds.animationDuration} ease-in-out infinite ${ds.animationDelay}` : 'none',
                        }}
                      />
                    ))}
                  </div>
                  <p className="text-[10px] text-[#A1A1A8] mt-3 font-mono">41 agents · 24/7 · real-time</p>
                </div>
              </TiltCard>

            {/* Phone Order Agent */}
            <TiltCard className="gsap-feature-card h-full bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#2A2A30] transition-colors duration-300">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${ACCENT}15` }}>
                    <Phone size={18} style={{ color: ACCENT }} />
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold">Phone Order Agent</h3>
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed mb-4">
                  AI voice agent takes phone orders in 600+ languages with voice cloning for your brand. Never miss a call.
                </p>
                <div className="rounded-lg bg-[#0A0A0B] border border-[#1F1F23] p-4 space-y-2">
                  {[
                    { from: 'customer', text: "Hi, I'd like a large latte and a blueberry muffin" },
                    { from: 'ai', text: "One large latte and blueberry muffin — that's $8.45. Anything else?" },
                    { from: 'customer', text: "That's all, thanks!" },
                  ].map((msg, i) => (
                    <div key={i} className={`flex ${msg.from === 'ai' ? 'justify-start' : 'justify-end'}`}>
                      <div
                        className="rounded-lg px-3 py-1.5 text-[11px] max-w-[85%]"
                        style={{
                          backgroundColor: msg.from === 'ai' ? `${ACCENT}15` : '#1F1F23',
                          color: msg.from === 'ai' ? ACCENT : '#A1A1A8',
                        }}
                      >
                        {msg.text}
                      </div>
                    </div>
                  ))}
                </div>
              </TiltCard>
          </div>
        </div>
      </section>

      {/* ─── HOW IT WORKS ─────────────────────────── */}
      <section className="py-24 border-t border-[#1F1F23]/40 relative overflow-hidden">
        <div className="absolute top-0 right-0 aurora-glow" style={{ width: 500, height: 500, opacity: 0.06, background: `radial-gradient(circle, ${ACCENT_CA} 0%, transparent 70%)` }} />
        <div className="max-w-content mx-auto px-6 relative">
          <ScrollReveal className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">
              Connect Your POS in{' '}
              <em className="font-serif italic font-normal" style={{ color: ACCENT_CA }}>Minutes</em>
            </h2>
            <p className="mt-4 text-[#A1A1A8] text-[15px]">Four steps. Under sixty seconds.</p>
          </ScrollReveal>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 max-w-4xl mx-auto">
            {[
              { step: '01', title: 'Connect', desc: 'One-click Square, Clover, or Toast OAuth. No API keys, no config.' },
              { step: '02', title: 'Analyze', desc: '41 AI agents process your entire transaction history instantly.' },
              { step: '03', title: 'Discover', desc: 'See specific dollar-denominated revenue opportunities.' },
              { step: '04', title: 'Capture', desc: 'Act on insights and start recovering hidden revenue today.' },
            ].map((s, i) => (
              <ScrollReveal key={s.step} delay={i * 0.1}>
                <div className="relative group text-left">
                  {i < 3 && (
                    <div className="hidden md:block absolute top-4 left-full w-6 h-px bg-[#1F1F23] z-0" />
                  )}
                  <span className="font-mono text-[11px] tracking-wider" style={{ color: ACCENT }}>{s.step}</span>
                  <h3 className="text-[#F5F5F7] font-semibold text-lg mt-2 mb-2">{s.title}</h3>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{s.desc}</p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </section>

      {/* ─── METRICS ──────────────────────────────── */}
      <section className="py-28 border-t border-[#1F1F23]/40 relative">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow" style={{ width: 700, height: 700, opacity: 0.08, background: `radial-gradient(circle, ${ACCENT} 0%, transparent 70%)` }} />
        <div className="max-w-content mx-auto px-6 relative">
          <ScrollReveal className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">
              Real Results from POS{' '}
              <em className="font-serif italic font-normal bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(to right, ${ACCENT}, ${ACCENT_CA})` }}>Analytics</em>
            </h2>
          </ScrollReveal>
          <div ref={statsRef} className="grid grid-cols-1 sm:grid-cols-3 gap-8 max-w-2xl mx-auto text-center">
            {[
              { end: 2340, prefix: '$', suffix: '/mo', label: 'Avg. revenue found per merchant' },
              { end: 94, suffix: '%', label: 'Forecast accuracy rate' },
              { end: 45, suffix: 's', label: 'Average setup time' },
            ].map((stat, i) => (
              <div key={stat.label} className="gsap-stat-card">
                <div className="text-4xl md:text-5xl font-bold text-[#F5F5F7]">
                  <CountUp end={stat.end} prefix={stat.prefix || ''} suffix={stat.suffix} duration={2200} />
                </div>
                <p className="text-[#A1A1A8] text-[13px] mt-2">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── TESTIMONIALS ─────────────────────────── */}
      <section className="py-24 border-t border-[#1F1F23]/40">
        <div className="max-w-content mx-auto px-6">
          <ScrollReveal className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-[#F5F5F7] tracking-tight">
              Trusted by Restaurant &amp; Retail{' '}
              <em className="font-serif italic font-normal" style={{ color: ACCENT_CA }}>Operators</em>
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

      {/* ─── SCHEDULE A QUOTE ─────────────────────── */}
      <ScheduleQuote accent={ACCENT} accentSecondary={ACCENT_CA} source="us-landing" />

      {/* ─── FAQ ──────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 py-16">
        <h2 className="text-2xl font-bold text-[#F5F5F7] mb-8">Frequently Asked Questions</h2>
        <div className="space-y-6">
          {[
            {
              q: 'What is Meridian Intelligence?',
              a: 'Meridian Intelligence is an AI-powered analytics platform that connects to your POS system — including Square, Toast, Clover, and 77 others — and generates revenue insights, anomaly alerts, and customer segmentation reports using a 41-agent AI swarm. Merchants see plain-English insights within minutes of connecting.',
            },
            {
              q: 'How much does Meridian cost?',
              a: "Pricing is tailored to your business — your POS, number of locations, and the features you need. Schedule a quote and a specialist will call you within 48 hours with a plan and price built for you. Your first month is free, with no long-term contracts.",
            },
            {
              q: 'Which POS systems does Meridian support?',
              a: 'Meridian supports 80+ POS systems including Square, Toast, Clover, Lightspeed, Shopify POS, Moneris (Canada), and TouchBistro. Most merchants connect in under 5 minutes using OAuth — no API keys needed.',
            },
            {
              q: 'Does Meridian work for Canadian businesses?',
              a: 'Yes. Meridian has a dedicated Canadian portal with CAD pricing, Canadian POS integrations including Moneris and Alice POS, and is built for PIPEDA and Quebec Law 25. Visit meridian.tips/canada for details.',
            },
            {
              q: 'How long does it take to set up Meridian?',
              a: 'Most businesses connect in under 10 minutes. Connect your POS via OAuth, and Meridian immediately starts importing your transaction history. First AI insights appear within 24 hours for businesses with 30+ days of history.',
            },
          ].map(({ q, a }) => (
            <details key={q} className="group">
              <summary className="cursor-pointer text-sm font-semibold text-[#F5F5F7] flex items-center justify-between py-3 border-b border-[#1F1F23]">
                {q}
                <ChevronRight size={16} className="text-[#A1A1A8] transition-transform group-open:rotate-90" />
              </summary>
              <p className="text-sm text-[#A1A1A8] leading-relaxed pt-3 pb-4">{a}</p>
            </details>
          ))}
        </div>
      </section>

      {/* ─── CTA ──────────────────────────────────── */}
      <section className="py-28 border-t border-[#1F1F23]/40 relative overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 aurora-glow" style={{ width: 500, height: 500, opacity: 0.1, background: `radial-gradient(circle, ${ACCENT} 0%, transparent 70%)` }} />
        <div className="max-w-content mx-auto px-6 text-center relative">
          <ScrollReveal>
            <div className="flex justify-center mb-8">
              <MeridianEmblem size={48} />
            </div>
            <h2 className="text-3xl md:text-5xl font-bold text-[#F5F5F7] tracking-tight text-balance max-w-2xl mx-auto leading-[1.1]">
              Stop guessing.
              <br />
              Start{' '}
              <em className="font-serif italic font-normal bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(to right, ${ACCENT}, ${ACCENT_CA})` }}>knowing.</em>
            </h2>
            <p className="mt-6 text-[#A1A1A8] text-[15px] max-w-md mx-auto leading-relaxed">
              Connect your POS and see exactly where your revenue is hiding. First month free — start seeing results in 60 seconds.
            </p>
            <div className="mt-10">
              <MagneticButton
                onClick={() => navigate('/us/onboard')}
                className="group px-8 py-3.5 text-[15px] font-medium text-white rounded-lg transition-all duration-300 inline-flex items-center gap-2 hover:brightness-110"
                style={{ backgroundColor: ACCENT, boxShadow: `0 0 40px ${ACCENT}35` }}
              >
                Start Today
                <ArrowRight size={16} className="transition-transform duration-300 group-hover:translate-x-0.5" />
              </MagneticButton>
            </div>
          </ScrollReveal>
        </div>
      </section>

      {/* ─── FOOTER ───────────────────────────────── */}
      <footer className="border-t border-[#1F1F23]/40 py-8">
        <div className="max-w-content mx-auto px-6">
          {/* Guides & resources */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-8 pb-8 mb-8 border-b border-[#1F1F23]/40 sm:grid-cols-4">
            <div>
              <h4 className="text-[12px] font-semibold text-[#F5F5F7] mb-3">Popular Guides</h4>
              <ul className="space-y-2 text-[12px] text-[#A1A1A8]/60">
                {[
                  { label: 'Restaurant Food Cost Guide', path: '/guides/restaurant-food-cost-guide' },
                  { label: 'Menu Pricing Strategy', path: '/guides/menu-pricing-strategy' },
                  { label: 'Reduce Restaurant Food Waste', path: '/guides/reduce-restaurant-food-waste' },
                  { label: 'Forecast Restaurant Sales', path: '/guides/forecast-restaurant-sales' },
                ].map(l => (
                  <li key={l.path}>
                    <a onClick={() => navigate(l.path)} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-[12px] font-semibold text-[#F5F5F7] mb-3">Resources</h4>
              <ul className="space-y-2 text-[12px] text-[#A1A1A8]/60">
                {[
                  { label: 'All Guides', path: '/guides' },
                  { label: 'Free Tools', path: '/tools/food-cost-calculator' },
                  { label: 'Blog', path: '/blog' },
                  { label: 'FAQ', path: '/faq' },
                ].map(l => (
                  <li key={l.path}>
                    <a onClick={() => navigate(l.path)} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-[12px] font-semibold text-[#F5F5F7] mb-3">Product</h4>
              <ul className="space-y-2 text-[12px] text-[#A1A1A8]/60">
                {[
                  { label: 'Live Demo', path: '/demo' },
                  { label: 'For Restaurants', path: '/for/restaurants' },
                  { label: 'For Coffee Shops', path: '/for/coffee-shops' },
                  { label: 'Integrations', path: '/integrations/square' },
                ].map(l => (
                  <li key={l.path}>
                    <a onClick={() => navigate(l.path)} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-[12px] font-semibold text-[#F5F5F7] mb-3 flex items-center gap-1.5">
                <span style={{ color: ACCENT_CA }}>🇨🇦</span> Meridian Canada
              </h4>
              <ul className="space-y-2 text-[12px] text-[#A1A1A8]/60">
                {[
                  { label: 'Canadian Portal', path: '/canada' },
                  { label: 'Careers', path: '/careers' },
                  { label: 'Customer Login', path: '/customer/login' },
                  { label: 'Start Today', path: '/us/onboard' },
                ].map(l => (
                  <li key={l.path}>
                    <a onClick={() => navigate(l.path)} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
            <div className="flex items-center gap-3">
              <MeridianLogo size={20} showWordmark showTagline={false} />
              <div className="flex items-center gap-1.5 text-[11px] text-[#A1A1A8]/50">
                <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ACCENT_CA }} />
                All systems operational
              </div>
            </div>
            <div className="flex flex-col items-center gap-3 sm:flex-row sm:gap-6">
              <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-4 text-[12px] text-[#A1A1A8]/60">
                <span className="flex items-center gap-1.5"><Shield size={12} /> Bank-level encryption</span>
                <span className="flex items-center gap-1.5"><Clock size={12} /> Real-time sync</span>
                <a onClick={() => navigate('/careers')} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">Careers</a>
                <a onClick={() => navigate('/us/portal/login')} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">Sales Portal</a>
                <a onClick={() => navigate('/customer/login')} className="hover:text-[#F5F5F7] cursor-pointer transition-colors">Customer Login</a>
              </div>
              <p className="text-[11px] text-[#A1A1A8]/30">
                © 2026{' '}
                <span className="font-semibold bg-clip-text text-transparent" style={{ backgroundImage: `linear-gradient(to right, ${ACCENT}, ${ACCENT_CA})` }}>
                  Meridian
                </span>
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
