import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Phone, PhoneOutgoing, Menu, X } from 'lucide-react'

import SEO from '@/components/SEO'
import MeridianLogo from '@/components/MeridianLogo'
import GrainOverlay from '@/components/landing/GrainOverlay'
import ScheduleQuote from '@/components/landing/ScheduleQuote'
import CountUp from '@/components/landing/CountUp'
import { Marquee } from '@/components/ui/Marquee'
import LiveTranscript from './LiveTranscript'
import CostMath from './CostMath'
import FlowDiagram from './FlowDiagram'
import { VERTICALS, type Vertical } from './verticals'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * Landing v3 register — product theater on a lit dark terrain. Never a void:
 * every surface is grounded with layered radial light in the real brand
 * blues; ONE luminous event per screen (hero: the live call; outbound: the
 * dialing pulse; pricing: the Meridian row). Mechanics are drawn as
 * instruments, not written as prose. All numbers honest, all transcripts
 * real product behavior. No fabricated logos/testimonials.
 */
export default function LandingV2() {
  const [verticalKey, setVerticalKey] = useState(VERTICALS[0].key)
  const [menuOpen, setMenuOpen] = useState(false)
  const v = VERTICALS.find((x) => x.key === verticalKey) ?? VERTICALS[0]

  return (
    <div className="min-h-screen overflow-x-clip bg-[#05080F] text-[#F5F5F7]">
      <SEO
        title="Meridian — The phone agent that answers, books, and calls back"
        description="Meridian answers every call 24/7, takes orders and bookings straight into your POS, and dials your waitlist when a slot opens. From US$250/mo, $0.104/min true cost."
        path="/"
      />
      <GrainOverlay />

      {/* ─── Nav ─────────────────────────────────────────────── */}
      <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#05080F]/75 backdrop-blur-[20px]">
        <div className="mx-auto flex h-14 max-w-content items-center justify-between px-6">
          <Link to="/" aria-label="Meridian home">
            <MeridianLogo size={28} showWordmark showTagline={false} />
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-slate-400 md:flex">
            <a href="#how" className="transition-colors hover:text-white">How it works</a>
            <a href="#outbound" className="transition-colors hover:text-white">Outbound</a>
            <a href="#pricing" className="transition-colors hover:text-white">Pricing</a>
            <Link to="/careers" className="transition-colors hover:text-white">Become a rep</Link>
            <Link to="/login" className="transition-colors hover:text-white">Sign in</Link>
            <a
              href={`tel:${v.demoNumberE164 || VERTICALS[0].demoNumberE164}`}
              className="inline-flex items-center gap-2 rounded-full bg-[#1A8FD6] px-4 py-1.5 font-medium text-white shadow-[0_0_24px_rgba(26,143,214,0.45)] transition-all hover:bg-[#2da0e2] hover:shadow-[0_0_36px_rgba(26,143,214,0.6)]"
            >
              <Phone className="h-3.5 w-3.5 shrink-0" /> Call the agent
            </a>
          </nav>
          <button className="md:hidden" aria-label="Menu" onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {menuOpen && (
          <nav className="border-t border-white/[0.06] bg-[#05080F] px-6 py-4 md:hidden">
            <div className="flex flex-col gap-3 text-sm text-slate-300">
              <a href="#how" onClick={() => setMenuOpen(false)}>How it works</a>
              <a href="#outbound" onClick={() => setMenuOpen(false)}>Outbound</a>
              <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
              <Link to="/careers">Become a rep</Link>
              <Link to="/login">Sign in</Link>
            </div>
          </nav>
        )}
      </header>

      {/* ─── Hero — a real kitchen at rush, and the phone that answers it ── */}
      <section className="relative isolate">
        {/* Photographic ground: the pass at dinner rush. The video loop drops
            in over this still when ready; the still doubles as its poster. */}
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
          <img
            src="/landing2/hero-pass.webp"
            alt=""
            className="h-full w-full object-cover object-[70%_center]"
          />
          {/* Ambient loop over the still (which doubles as its poster). The
              seam is a 0.3s tail-to-head crossfade, RMS-verified. Reduced
              motion gets the still alone. */}
          <video
            className="absolute inset-0 h-full w-full object-cover object-[70%_center] motion-reduce:hidden"
            autoPlay
            muted
            loop
            playsInline
            poster="/landing2/hero-pass.webp"
          >
            <source src="/landing2/hero-loop.webm" type="video/webm" />
            <source src="/landing2/hero-loop.mp4" type="video/mp4" />
          </video>
          {/* scrims: readable text left, page ground below */}
          <div className="absolute inset-0"
               style={{ background: 'linear-gradient(90deg, rgba(5,8,15,0.92) 0%, rgba(5,8,15,0.72) 38%, rgba(5,8,15,0.25) 70%, rgba(5,8,15,0.45) 100%)' }} />
          <div className="absolute inset-0"
               style={{ background: 'linear-gradient(180deg, rgba(5,8,15,0.5) 0%, transparent 25%, transparent 55%, #05080F 96%)' }} />
        </div>

        <div className="mx-auto max-w-content px-6 pb-20 pt-32 md:pt-40">
          <div className="max-w-2xl">
            <p className="font-mono text-[11px] uppercase tracking-[0.3em] text-[#17C5B0]">
              Answers · Books · Calls back
            </p>
            <motion.h1
              key={v.key + '-h'}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease: EASE }}
              className="mt-4 font-serif text-5xl leading-[1.02] tracking-tight md:text-7xl"
            >
              {v.headline}
            </motion.h1>
            <motion.p
              key={v.key + '-s'}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, delay: 0.08, ease: EASE }}
              className="mt-5 max-w-xl text-lg text-slate-300"
            >
              {v.sub}
            </motion.p>

            <div className="mt-9 flex flex-col items-start gap-4 sm:flex-row sm:items-center">
              {v.demoNumberE164 ? (
                <a
                  href={`tel:${v.demoNumberE164}`}
                  className="group inline-flex w-full max-w-md items-center justify-center gap-3 rounded-full border border-[#1A8FD6]/40 bg-[#1A8FD6]/10 py-3.5 pl-5 pr-7 shadow-[0_0_48px_rgba(26,143,214,0.25)] backdrop-blur transition-all hover:border-[#1A8FD6]/70 hover:shadow-[0_0_64px_rgba(26,143,214,0.4)] sm:w-auto"
                >
                  <span className="relative flex h-2.5 w-2.5 shrink-0">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#17C5B0] opacity-70" />
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#17C5B0]" />
                  </span>
                  <span className="whitespace-nowrap font-mono text-lg font-semibold tracking-wider md:text-xl">{v.demoNumber}</span>
                </a>
              ) : (
                <a
                  href="#quote"
                  className="inline-flex items-center gap-2 rounded-full bg-[#1A8FD6] px-7 py-3.5 font-medium text-white shadow-[0_0_36px_rgba(26,143,214,0.4)] transition-all hover:bg-[#2da0e2]"
                >
                  {v.demoLabel} <ArrowRight className="h-4 w-4 shrink-0" />
                </a>
              )}
              <a
                href="#quote"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-slate-300 transition-colors hover:border-white/30 hover:text-white"
              >
                Book a 15-minute demo
              </a>
            </div>
            <p className="mt-3 font-mono text-[11px] uppercase tracking-widest text-slate-500">
              {v.demoNumberE164 ? `${v.demoLabel} — a real line, not a recording` : 'Live demo lines: restaurants & golf'}
            </p>
          </div>

          {/* Vertical switcher */}
          <div className="mt-16 flex flex-wrap gap-2" role="tablist" aria-label="Pick your trade">
            {VERTICALS.map((opt: Vertical) => (
              <button
                key={opt.key}
                role="tab"
                aria-selected={opt.key === verticalKey}
                onClick={() => setVerticalKey(opt.key)}
                className={
                  opt.key === verticalKey
                    ? 'rounded-full border border-[#17C5B0]/50 bg-[#17C5B0]/10 px-4 py-2 text-sm font-medium text-[#17C5B0] shadow-[0_0_20px_rgba(23,197,176,0.25)]'
                    : 'rounded-full border border-white/10 px-4 py-2 text-sm text-slate-400 transition-colors hover:border-white/25 hover:text-white'
                }
              >
                {opt.label}
              </button>
            ))}
          </div>

          <div className="mt-8">
            <AnimatePresence mode="wait">
              <motion.div
                key={v.key}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                transition={{ duration: 0.35, ease: EASE }}
              >
                <LiveTranscript lines={v.transcript} artifact={v.artifact} restartKey={v.key} />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
      </section>

      {/* ─── Problem strip — honest numbers with motion ──────── */}
      <section className="border-y border-white/[0.06] bg-[#070B14]">
        <div className="mx-auto grid max-w-content gap-8 px-6 py-12 text-center sm:grid-cols-3">
          {[
            { n: 30, suffix: '%', label: 'of calls go unanswered at peak — industry, not us' },
            { n: 0, prefix: '$', label: 'recovered by a voicemail box, ever' },
            { n: 1, suffix: ' ring', label: 'before Meridian picks up, every time' },
          ].map((s) => (
            <div key={s.label}>
              <div className="font-serif text-5xl text-white">
                <CountUp end={s.n} prefix={s.prefix ?? ''} suffix={s.suffix ?? ''} />
              </div>
              <div className="mx-auto mt-2 max-w-[240px] font-mono text-[11px] uppercase tracking-wider text-slate-500">
                {s.label}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── How it works — drawn as an instrument ───────────── */}
      <section id="how" className="relative isolate">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-[-15%] top-[10%] h-[560px] w-[560px] rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(26,143,214,0.12), transparent 70%)' }} />
        </div>
        <div className="mx-auto max-w-content px-6 py-24 md:py-28">
          <h2 className="max-w-3xl font-serif text-4xl tracking-tight md:text-5xl">
            The call becomes a row in your system, not a voicemail.
          </h2>
          <p className="mt-4 max-w-2xl text-slate-400">
            Watch the path: every call travels the same wire and ends as a paid
            ticket in your POS or a booking in Square — while the caller is
            still on the line.
          </p>
          <div className="mt-12">
            <FlowDiagram vertical={v} />
          </div>
        </div>
      </section>

      {/* ─── The real product — actual screens, actual dollars ── */}
      <section className="border-y border-white/[0.06] bg-[#070B14]">
        <div className="mx-auto max-w-content px-6 py-24 md:py-28">
          <div className="grid items-end gap-8 lg:grid-cols-[1.5fr,1fr]">
            <div>
              <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-slate-500">
                Not a mockup
              </span>
              <h2 className="mt-3 font-serif text-4xl tracking-tight md:text-5xl">
                These are screenshots, not renders.
              </h2>
            </div>
            <p className="text-slate-400 lg:pb-2">
              The same subscription reads your register: today's take against a
              normal day, what's still sellable tonight, and the three moves
              worth real dollars this week — priced in your numbers, not ours.
            </p>
          </div>

          <div className="mt-12 grid gap-6 lg:grid-cols-[1.6fr,1fr]">
            {/* The owner's morning screen */}
            <figure className="group relative overflow-hidden rounded-2xl border border-white/[0.09] bg-[#05080F] shadow-[0_24px_80px_rgba(0,0,0,0.5)]">
              <div className="flex items-center gap-1.5 border-b border-white/[0.07] px-4 py-2.5">
                <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                <span className="ml-3 font-mono text-[10px] text-slate-500">app.meridian.tips — Today</span>
              </div>
              <img src="/landing2/shot-dashboard.webp" alt="Meridian owner dashboard: booked revenue vs a normal day, covers, and three priced actions" loading="lazy"
                   className="w-full transition-transform duration-500 group-hover:scale-[1.015]" />
              <figcaption className="border-t border-white/[0.07] px-4 py-3 font-mono text-[11px] text-slate-500">
                "$672 still sellable today — 7 more slots would fit." It tells you, you don't dig.
              </figcaption>
            </figure>

            {/* The phone agent screen */}
            <figure className="group relative overflow-hidden rounded-2xl border border-white/[0.09] bg-[#05080F] shadow-[0_24px_80px_rgba(0,0,0,0.5)]">
              <div className="flex items-center gap-1.5 border-b border-white/[0.07] px-4 py-2.5">
                <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                <span className="h-2.5 w-2.5 rounded-full bg-white/10" />
                <span className="ml-3 font-mono text-[10px] text-slate-500">Phone Agent</span>
              </div>
              <img src="/landing2/shot-phone.webp" alt="Meridian phone agent screen: live call indicator, agent personalities, call and order counts" loading="lazy"
                   className="w-full object-cover object-top transition-transform duration-500 group-hover:scale-[1.015]" />
              <figcaption className="border-t border-white/[0.07] px-4 py-3 font-mono text-[11px] text-slate-500">
                Pick the voice that answers as yours — Vinny, Rosie, Jacques, Priya…
              </figcaption>
            </figure>
          </div>
        </div>
      </section>

      {/* ─── Outbound — the dialing pulse is the event ───────── */}
      <section id="outbound" className="relative isolate overflow-hidden border-y border-white/[0.06] bg-[#041A32]/40">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute right-[8%] top-1/2 h-[640px] w-[640px] -translate-y-1/2 rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(23,197,176,0.14), transparent 70%)' }} />
        </div>
        <div className="mx-auto max-w-content px-6 py-24 md:py-28">
          <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-[#17C5B0]">
            No one else does this
          </span>
          <h2 className="mt-3 max-w-2xl font-serif text-4xl tracking-tight md:text-5xl">
            It doesn't just answer your phone. It picks it up and dials.
          </h2>
          <div className="mt-12 grid items-center gap-10 lg:grid-cols-[1fr,1.1fr]">
            {/* The pulse instrument */}
            <div className="relative mx-auto aspect-square w-full max-w-[380px]">
              {[0, 1, 2].map((ring) => (
                <span
                  key={ring}
                  className="absolute inset-0 m-auto rounded-full border border-[#17C5B0]/30 motion-safe:animate-ping"
                  style={{
                    width: `${46 + ring * 27}%`,
                    height: `${46 + ring * 27}%`,
                    animationDuration: '3.2s',
                    animationDelay: `${ring * 1.05}s`,
                  }}
                />
              ))}
              <div className="absolute inset-0 m-auto flex h-[42%] w-[42%] items-center justify-center rounded-full border border-[#17C5B0]/50 bg-[#041A32] shadow-[0_0_60px_rgba(23,197,176,0.35)]">
                <PhoneOutgoing className="h-10 w-10 shrink-0 text-[#17C5B0]" />
              </div>
              {/* waitlist targets */}
              {[
                { top: '4%', left: '52%', label: 'J. Park · $840 lifetime' },
                { top: '58%', left: '2%', label: 'M. Osei · party of 4' },
                { top: '78%', left: '64%', label: 'T. Alvarez · regular' },
              ].map((t) => (
                <div key={t.label} className="absolute -translate-x-1/2 rounded-full border border-white/10 bg-[#05080F]/90 px-3 py-1 font-mono text-[10px] text-slate-400"
                     style={{ top: t.top, left: t.left }}>
                  {t.label}
                </div>
              ))}
            </div>
            <div className="space-y-6">
              <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-6">
                <h3 className="font-semibold text-white">A table opens, the waitlist rings</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                  A 7:30 cancellation at 7:05 is worth nothing on a clipboard.
                  Meridian calls the waitlist in order — biggest spender first,
                  no-shows last — and the slot is resold before your host
                  notices it opened.
                </p>
              </div>
              <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-6">
                <h3 className="font-semibold text-white">Every other answering AI is inbound-only</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                  Slang, Popmenu, SoundHound — they all wait for the phone to
                  ring. An agent that places calls is a different machine, and
                  it's the one that turns cancellations back into revenue.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Cost math — the Meridian row glows ──────────────── */}
      <section id="pricing" className="relative isolate">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-[20%] h-[520px] w-[900px] -translate-x-1/2 rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(26,143,214,0.10), transparent 70%)' }} />
        </div>
        <div className="mx-auto max-w-content px-6 py-24 md:py-28">
          <h2 className="font-serif text-4xl tracking-tight md:text-5xl">
            The price, next to everyone else's.
          </h2>
          <p className="mt-4 max-w-2xl text-slate-400">
            Nobody in this category prints their pricing beside their
            competitors'. We can, because the economics work: our measured cost
            is <span className="font-mono text-white">$0.104 a minute</span>, so
            we don't need overage fees or a sales call to tell you a number.
          </p>
          <div className="mt-12">
            <CostMath />
          </div>
        </div>
      </section>

      {/* ─── Integrations marquee ───────────────────────────── */}
      <section className="pb-16 md:pb-20">
        <div className="mx-auto max-w-content px-6">
          <p className="text-center font-mono text-[11px] uppercase tracking-[0.3em] text-slate-500">
            Plays well with the till you already own
          </p>
          <Marquee
            pauseOnHover
            className="mt-7 [--duration:40s] [mask-image:linear-gradient(to_right,transparent,#000_10%,#000_90%,transparent)]"
          >
            {['Square', 'Toast', 'Clover', 'Lightspeed', 'Stripe', 'OpenTable-ready', 'Telnyx', 'Vapi'].map((name) => (
              <span key={name} className="rounded-full border border-white/10 px-5 py-2 font-mono text-sm text-slate-400">
                {name}
              </span>
            ))}
          </Marquee>
        </div>
      </section>

      {/* ─── Friction strip ──────────────────────────────────── */}
      <section className="border-y border-white/[0.06] bg-[#070B14]">
        <div className="mx-auto grid max-w-content gap-6 px-6 py-10 text-center sm:grid-cols-3">
          {[
            ['Live in under an hour', 'connect your POS, pick a voice, forward the line'],
            ['Month to month', 'no contract, cancel from the dashboard'],
            ['Your number stays yours', 'we answer it; you can take it back any time'],
          ].map(([t, s]) => (
            <div key={t}>
              <div className="font-semibold text-white">{t}</div>
              <div className="mt-1 text-sm text-slate-500">{s}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Final CTA ───────────────────────────────────────── */}
      <section className="relative isolate">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-1/2 h-[480px] w-[820px] -translate-x-1/2 -translate-y-1/2 rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(26,143,214,0.16), transparent 70%)' }} />
        </div>
        <div className="mx-auto max-w-content px-6 py-24 text-center md:py-32">
          <h2 className="mx-auto max-w-2xl font-serif text-4xl tracking-tight md:text-6xl">
            Don't take a demo. Make a call.
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-slate-400">
            The agent is on a real line right now. Order something. Try to trip
            it up. Then imagine it answering your phone tonight at 6:45.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-4">
            <a
              href={`tel:${VERTICALS[0].demoNumberE164}`}
              className="inline-flex items-center gap-3 rounded-full bg-[#1A8FD6] py-3.5 pl-6 pr-7 font-medium text-white shadow-[0_0_48px_rgba(26,143,214,0.45)] transition-all hover:bg-[#2da0e2]"
            >
              <Phone className="h-4 w-4 shrink-0" />
              <span className="font-mono tracking-wide">{VERTICALS[0].demoNumber}</span>
            </a>
            <a
              href="#quote"
              className="inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-medium text-slate-300 transition-colors hover:border-white/30 hover:text-white"
            >
              Book a 15-minute demo <ArrowRight className="h-4 w-4 shrink-0" />
            </a>
          </div>
        </div>
      </section>

      {/* ─── Book a demo (quote form → /api/quote-request) ───── */}
      <ScheduleQuote accent="#1A8FD6" accentSecondary="#17C5B0" source="us-landing-v2" />

      {/* ─── Footer ──────────────────────────────────────────── */}
      <footer className="border-t border-white/[0.06]">
        <div className="mx-auto flex max-w-content flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-slate-500">
          <MeridianLogo size={22} showWordmark showTagline={false} />
          <nav className="flex flex-wrap gap-5">
            <Link to="/careers" className="transition-colors hover:text-white">Careers</Link>
            <a href="/privacy" className="transition-colors hover:text-white">Privacy</a>
            <a href="/terms" className="transition-colors hover:text-white">Terms</a>
            <Link to="/canada" className="transition-colors hover:text-white">Canada</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
