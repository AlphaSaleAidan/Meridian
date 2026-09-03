import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowRight, Phone, PhoneOutgoing, Menu, X,
  BarChart3, CalendarCheck, MessageSquareText,
} from 'lucide-react'

import SEO from '@/components/SEO'
import MeridianLogo from '@/components/MeridianLogo'
import ScheduleQuote from '@/components/landing/ScheduleQuote'
import LiveTranscript from './LiveTranscript'
import CostMath from './CostMath'
import { VERTICALS, type Vertical } from './verticals'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * Landing v2 — light ground, evidence-led. The register merchants already
 * trust (Square whitespace, Toast warmth), not the dark "AI vendor" look.
 * One signature: the live call and the artifact it creates. One accent.
 * Everything on this page is checkable: real transcripts of real behavior,
 * real demo lines, real economics. No fabricated logos or testimonials.
 */
export default function LandingV2() {
  const [verticalKey, setVerticalKey] = useState(VERTICALS[0].key)
  const [menuOpen, setMenuOpen] = useState(false)
  const v = VERTICALS.find((x) => x.key === verticalKey) ?? VERTICALS[0]

  return (
    <div className="min-h-screen bg-[#FAFAF7] text-slate-900 overflow-x-clip">
      <SEO
        title="Meridian — The phone agent that answers, books, and calls back"
        description="Meridian answers every call 24/7, takes orders and bookings straight into your POS, and dials your waitlist when a slot opens. From US$250/mo, $0.104/min true cost."
        path="/"
      />

      {/* ─── Nav ─────────────────────────────────────────────── */}
      <header className="fixed inset-x-0 top-0 z-50 border-b border-[#E8E6E0]/80 bg-[#FAFAF7]/85 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-content items-center justify-between px-6">
          <Link to="/" aria-label="Meridian home">
            <MeridianLogo size={28} showWordmark showTagline={false} />
          </Link>
          <nav className="hidden items-center gap-7 text-sm text-slate-600 md:flex">
            <a href="#how" className="hover:text-slate-900">How it works</a>
            <a href="#outbound" className="hover:text-slate-900">Outbound</a>
            <a href="#pricing" className="hover:text-slate-900">Pricing</a>
            <Link to="/careers" className="hover:text-slate-900">Become a rep</Link>
            <Link to="/login" className="hover:text-slate-900">Sign in</Link>
            <a
              href={`tel:${v.demoNumberE164 || VERTICALS[0].demoNumberE164}`}
              className="inline-flex items-center gap-2 rounded-full bg-[#1A8FD6] px-4 py-1.5 font-medium text-white transition-colors hover:bg-[#1574B8]"
            >
              <Phone className="h-3.5 w-3.5 shrink-0" /> Call the agent
            </a>
          </nav>
          <button
            className="md:hidden"
            aria-label="Menu"
            onClick={() => setMenuOpen((o) => !o)}
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {menuOpen && (
          <nav className="border-t border-[#E8E6E0] bg-[#FAFAF7] px-6 py-4 md:hidden">
            <div className="flex flex-col gap-3 text-sm">
              <a href="#how" onClick={() => setMenuOpen(false)}>How it works</a>
              <a href="#outbound" onClick={() => setMenuOpen(false)}>Outbound</a>
              <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
              <Link to="/careers">Become a rep</Link>
              <Link to="/login">Sign in</Link>
            </div>
          </nav>
        )}
      </header>

      {/* ─── Hero ────────────────────────────────────────────── */}
      <section className="mx-auto max-w-content px-6 pb-16 pt-28 md:pb-24 md:pt-36">
        <div className="max-w-3xl">
          <motion.h1
            key={v.key + '-h'}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: EASE }}
            className="font-serif text-5xl leading-[1.05] tracking-tight md:text-7xl"
          >
            {v.headline}
          </motion.h1>
          <motion.p
            key={v.key + '-s'}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.08, ease: EASE }}
            className="mt-5 max-w-xl text-lg text-slate-600"
          >
            {v.sub}
          </motion.p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            {v.demoNumberE164 ? (
              <a
                href={`tel:${v.demoNumberE164}`}
                className="group inline-flex items-center gap-3 rounded-full bg-[#0B1120] py-3 pl-5 pr-6 text-white transition-transform hover:scale-[1.02]"
              >
                <span className="relative flex h-2.5 w-2.5 shrink-0">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#17C5B0] opacity-60" />
                  <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[#17C5B0]" />
                </span>
                <span className="text-sm text-slate-300">{v.demoLabel}</span>
                <span className="font-mono font-semibold tracking-wide">{v.demoNumber}</span>
              </a>
            ) : (
              <a
                href="#demo"
                className="inline-flex items-center gap-2 rounded-full bg-[#0B1120] px-6 py-3 font-medium text-white transition-transform hover:scale-[1.02]"
              >
                {v.demoLabel} <ArrowRight className="h-4 w-4 shrink-0" />
              </a>
            )}
            <a
              href="#demo"
              className="inline-flex items-center gap-2 rounded-full border border-[#E8E6E0] bg-white px-5 py-3 text-sm font-medium text-slate-700 hover:border-slate-300"
            >
              Book a 15-minute demo
            </a>
          </div>
          <p className="mt-3 text-xs text-slate-400">
            That's a real line answered by the actual agent — not a recording.
          </p>
        </div>

        {/* Vertical switcher — swaps the whole page's evidence in place */}
        <div className="mt-14 flex flex-wrap gap-2" role="tablist" aria-label="Pick your trade">
          {VERTICALS.map((opt: Vertical) => (
            <button
              key={opt.key}
              role="tab"
              aria-selected={opt.key === verticalKey}
              onClick={() => setVerticalKey(opt.key)}
              className={
                opt.key === verticalKey
                  ? 'rounded-full bg-[#0B1120] px-4 py-2 text-sm font-medium text-white'
                  : 'rounded-full border border-[#E8E6E0] bg-white px-4 py-2 text-sm text-slate-600 hover:border-slate-300'
              }
            >
              {opt.label}
            </button>
          ))}
        </div>

        <div className="mt-6">
          <AnimatePresence mode="wait">
            <motion.div
              key={v.key}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.35, ease: EASE }}
            >
              <LiveTranscript lines={v.transcript} artifact={v.artifact} restartKey={v.key} />
            </motion.div>
          </AnimatePresence>
        </div>
      </section>

      {/* ─── The problem, once, sharply ──────────────────────── */}
      <section className="border-y border-[#E8E6E0] bg-white">
        <div className="mx-auto max-w-content px-6 py-10">
          <p className="mx-auto max-w-2xl text-center text-lg text-slate-600">
            Around <span className="font-semibold text-slate-900">a third of calls go unanswered at peak</span>.
            Those callers don't call back — they call the next place.
            Every other section of this page is about what happens when they get an answer.
          </p>
        </div>
      </section>

      {/* ─── How it works: call → artifact ───────────────────── */}
      <section id="how" className="mx-auto max-w-content px-6 py-20 md:py-28">
        <h2 className="font-serif text-4xl tracking-tight md:text-5xl">
          The call becomes a <span className="text-[#1A8FD6]">row in your system</span>, not a voicemail.
        </h2>
        <p className="mt-4 max-w-2xl text-slate-600">
          No app to check, no message pad. Orders land in your POS as paid tickets.
          Bookings land in Square Appointments under the customer's name.
          You watched it happen in the demo above — that's the whole product.
        </p>
        <div className="mt-10 grid gap-5 md:grid-cols-3">
          {[
            {
              icon: MessageSquareText,
              title: 'Answers like your best host',
              body: 'Knows the menu, the hours, the 86 list, and your prices — because it reads your POS, not a script.',
            },
            {
              icon: CalendarCheck,
              title: 'Books straight into Square',
              body: 'Real availability, real bookings, deposits by text. Your staff see it where they already look.',
            },
            {
              icon: BarChart3,
              title: 'Reads the register too',
              body: 'The same subscription includes POS analytics — margins, forecasts, and what to fix this week.',
            },
          ].map((f) => (
            <div key={f.title} className="rounded-2xl border border-[#E8E6E0] bg-white p-6">
              <f.icon className="h-5 w-5 shrink-0 text-[#1A8FD6]" />
              <h3 className="mt-3 font-semibold">{f.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Outbound: the ownable claim ─────────────────────── */}
      <section id="outbound" className="border-y border-[#E8E6E0] bg-[#0B1120] text-white">
        <div className="mx-auto max-w-content px-6 py-20 md:py-28">
          <span className="font-mono text-xs uppercase tracking-widest text-[#17C5B0]">
            No one else does this
          </span>
          <h2 className="mt-3 max-w-2xl font-serif text-4xl tracking-tight md:text-5xl">
            It doesn't just answer your phone. It picks it up and dials.
          </h2>
          <div className="mt-10 grid gap-5 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <PhoneOutgoing className="h-5 w-5 shrink-0 text-[#17C5B0]" />
              <h3 className="mt-3 font-semibold">A table opens, the waitlist rings</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                A 7:30 cancellation at 7:05 is worth nothing on a clipboard. Meridian
                calls the waitlist in order — biggest spender first — and the slot is
                resold before your host notices it opened.
              </p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
              <Phone className="h-5 w-5 shrink-0 text-[#17C5B0]" />
              <h3 className="mt-3 font-semibold">Every answering AI is inbound-only</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-400">
                Slang, Popmenu, SoundHound — they all wait for the phone to ring.
                An agent that places calls is a different machine, and it's the one
                that turns cancellations back into revenue.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─── Cost math ───────────────────────────────────────── */}
      <section id="pricing" className="mx-auto max-w-content px-6 py-20 md:py-28">
        <h2 className="font-serif text-4xl tracking-tight md:text-5xl">
          The price, next to everyone else's.
        </h2>
        <p className="mt-4 max-w-2xl text-slate-600">
          Nobody in this category prints their pricing next to their competitors'.
          We can, because the economics work: our measured cost is{' '}
          <span className="font-mono text-slate-900">$0.104 a minute</span>, so we
          don't need overage fees or a sales call to tell you a number.
        </p>
        <div className="mt-10">
          <CostMath />
        </div>
      </section>

      {/* ─── Friction killers ────────────────────────────────── */}
      <section className="border-y border-[#E8E6E0] bg-white">
        <div className="mx-auto grid max-w-content gap-6 px-6 py-10 text-center sm:grid-cols-3">
          {[
            ['Live in under an hour', 'connect your POS, pick a voice, forward the line'],
            ['Month to month', 'no contract, cancel from the dashboard'],
            ['Your number stays yours', 'we answer it; you can take it back any time'],
          ].map(([t, s]) => (
            <div key={t}>
              <div className="font-semibold text-slate-900">{t}</div>
              <div className="mt-1 text-sm text-slate-500">{s}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Final CTA ───────────────────────────────────────── */}
      <section className="mx-auto max-w-content px-6 py-20 text-center md:py-28">
        <h2 className="mx-auto max-w-2xl font-serif text-4xl tracking-tight md:text-5xl">
          Don't take a demo. Make a call.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-slate-600">
          The agent is on a real line right now. Order something. Try to trip it up.
          Then imagine it answering your phone tonight at 6:45.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
          <a
            href={`tel:${VERTICALS[0].demoNumberE164}`}
            className="inline-flex items-center gap-3 rounded-full bg-[#1A8FD6] py-3 pl-5 pr-6 font-medium text-white transition-colors hover:bg-[#1574B8]"
          >
            <Phone className="h-4 w-4 shrink-0" />
            <span className="font-mono tracking-wide">{VERTICALS[0].demoNumber}</span>
          </a>
          <a
            href="#demo"
            className="inline-flex items-center gap-2 rounded-full border border-[#E8E6E0] bg-white px-5 py-3 text-sm font-medium text-slate-700 hover:border-slate-300"
          >
            Book a 15-minute demo <ArrowRight className="h-4 w-4 shrink-0" />
          </a>
        </div>
      </section>

      {/* ─── Book a demo (quote form → /api/quote-request) ───── */}
      {/* ScheduleQuote is the shared dark-page component (old landing +
          Canada use it) — hosting it on ink keeps its light-on-dark text
          legible without forking it. Restyle for light ground later. */}
      <section id="demo" className="border-t border-[#E8E6E0] bg-[#0B1120]">
        <ScheduleQuote accent="#1A8FD6" accentSecondary="#17C5B0" source="us-landing-v2" />
      </section>

      {/* ─── Footer ──────────────────────────────────────────── */}
      <footer className="border-t border-[#E8E6E0] bg-[#FAFAF7]">
        <div className="mx-auto flex max-w-content flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-slate-500">
          <MeridianLogo size={22} showWordmark showTagline={false} />
          <nav className="flex flex-wrap gap-5">
            <Link to="/careers" className="hover:text-slate-900">Careers</Link>
            <a href="/privacy" className="hover:text-slate-900">Privacy</a>
            <a href="/terms" className="hover:text-slate-900">Terms</a>
            <Link to="/canada" className="hover:text-slate-900">Canada</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
