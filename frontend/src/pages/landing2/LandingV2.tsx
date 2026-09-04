import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowRight, Phone, MessageSquareText, Menu, X, Check, Minus, Cctv } from 'lucide-react'

import SEO from '@/components/SEO'
import MeridianLogo from '@/components/MeridianLogo'
import ScheduleQuote from '@/components/landing/ScheduleQuote'
import { BorderBeam } from '@/components/ui/BorderBeam'
import PopCard from './PopCard'
import LiveTranscript from './LiveTranscript'
import CostMath from './CostMath'
import { VERTICALS, type Vertical } from './verticals'

const EASE = [0.16, 1, 0.3, 1] as const

/**
 * Landing v5 — a deliberate structural clone of the register winning this
 * category (Certus): warm paper ground, heavy sans headlines, white cards
 * with soft shadows, a floating pill nav, and a photographed hand holding
 * the REAL product with honest stat chips floating around it. Meridian's
 * accent blue replaces their red; every number and screen is real.
 */
export default function LandingV2() {
  const [verticalKey, setVerticalKey] = useState(VERTICALS[0].key)
  const [menuOpen, setMenuOpen] = useState(false)
  const v = VERTICALS.find((x) => x.key === verticalKey) ?? VERTICALS[0]

  return (
    <div className="min-h-screen overflow-x-clip bg-[#FBF8F3] font-sans text-[#171A20]">
      <SEO
        title="Meridian — The phone agent that answers, books, and calls back"
        description="Meridian answers every call 24/7, takes orders and bookings straight into your POS, and texts your waitlist the moment a slot opens. Cameras, bookings, and POS analytics in one subscription from US$250/mo."
        path="/"
      />

      {/* ─── Floating pill nav ───────────────────────────────── */}
      <header className="fixed inset-x-0 top-4 z-50 px-4">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between rounded-2xl border border-[#EAE5DC] bg-white/95 px-5 shadow-[0_8px_30px_rgba(23,26,32,0.08)] backdrop-blur">
          <Link to="/" aria-label="Meridian home">
            <MeridianLogo size={26} showWordmark showTagline={false} />
          </Link>
          <nav className="hidden items-center gap-6 text-[15px] font-medium text-[#5B6069] md:flex">
            <a href="#how" className="transition-colors hover:text-[#171A20]">How it works</a>
            <a href="#pricing" className="transition-colors hover:text-[#171A20]">Pricing</a>
            <Link to="/careers" className="transition-colors hover:text-[#171A20]">Careers</Link>
            <Link to="/login" className="transition-colors hover:text-[#171A20]">Sign in</Link>
            <a
              href={`tel:${v.demoNumberE164 || VERTICALS[0].demoNumberE164}`}
              className="inline-flex items-center gap-2 rounded-xl bg-[#1A8FD6] px-4 py-2 font-semibold text-white transition-colors hover:bg-[#1574B8]"
            >
              <Phone className="h-3.5 w-3.5 shrink-0" /> Hear it live
            </a>
          </nav>
          <button className="md:hidden" aria-label="Menu" onClick={() => setMenuOpen((o) => !o)}>
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
        {menuOpen && (
          <div className="mx-auto mt-2 max-w-5xl rounded-2xl border border-[#EAE5DC] bg-white p-5 shadow-lg md:hidden">
            <div className="flex flex-col gap-3 text-[15px] font-medium text-[#5B6069]">
              <a href="#how" onClick={() => setMenuOpen(false)}>How it works</a>
              <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
              <Link to="/careers">Careers</Link>
              <Link to="/login">Sign in</Link>
              <a href={`tel:${VERTICALS[0].demoNumberE164}`} className="font-semibold text-[#1A8FD6]">
                Hear it live — {VERTICALS[0].demoNumber}
              </a>
            </div>
          </div>
        )}
      </header>

      {/* ─── Hero — copy left, the product in a real hand right ── */}
      <section className="relative isolate overflow-hidden">
        <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute right-[-12%] top-[-8%] h-[560px] w-[560px] rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(26,143,214,0.14), transparent 70%)' }} />
          <div className="absolute left-[-10%] top-[45%] h-[420px] w-[420px] rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(23,197,176,0.10), transparent 70%)' }} />
          <div className="absolute bottom-[-30%] left-[35%] h-[480px] w-[480px] rounded-full"
               style={{ background: 'radial-gradient(closest-side, rgba(240,180,41,0.08), transparent 70%)' }} />
        </div>
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 pb-10 pt-32 md:pt-36 lg:grid-cols-[1.1fr,1fr] lg:gap-6">
        <div>
          <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">
            AI phone agent for {v.label.toLowerCase()}
          </p>
          <motion.h1
            key={v.key + '-h'}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, ease: EASE }}
            className="mt-4 text-5xl font-extrabold leading-[1.04] tracking-tight md:text-6xl"
          >
            {v.headline}
          </motion.h1>
          <motion.p
            key={v.key + '-s'}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.55, delay: 0.06, ease: EASE }}
            className="mt-5 max-w-lg text-lg leading-relaxed text-[#5B6069]"
          >
            {v.sub}
          </motion.p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            {v.demoNumberE164 ? (
              <a
                href={`tel:${v.demoNumberE164}`}
                className="inline-flex items-center gap-2.5 rounded-xl bg-[#1A8FD6] px-6 py-3.5 font-semibold text-white shadow-[0_10px_24px_rgba(26,143,214,0.35)] transition-all hover:-translate-y-0.5 hover:bg-[#1574B8]"
              >
                Hear it live <ArrowRight className="h-4 w-4 shrink-0" />
              </a>
            ) : (
              <a
                href="#quote"
                className="inline-flex items-center gap-2.5 rounded-xl bg-[#1A8FD6] px-6 py-3.5 font-semibold text-white shadow-[0_10px_24px_rgba(26,143,214,0.35)] transition-all hover:-translate-y-0.5 hover:bg-[#1574B8]"
              >
                {v.demoLabel} <ArrowRight className="h-4 w-4 shrink-0" />
              </a>
            )}
            <a
              href="#pricing"
              className="inline-flex items-center gap-2 rounded-xl border border-[#EAE5DC] bg-white px-5 py-3.5 font-semibold text-[#171A20] shadow-sm transition-colors hover:border-[#d8d2c6]"
            >
              Calculate lost orders
            </a>
          </div>
          {v.demoNumberE164 && (
            <p className="mt-3 font-mono text-sm text-[#5B6069]">
              {v.demoLabel}: <a className="font-semibold text-[#171A20] underline decoration-[#1A8FD6]/40 underline-offset-4" href={`tel:${v.demoNumberE164}`}>{v.demoNumber}</a> — a real line, not a recording
            </p>
          )}

          {/* Vertical switcher */}
          <div className="mt-9 flex flex-wrap gap-2" role="tablist" aria-label="Pick your trade">
            {VERTICALS.map((opt: Vertical) => (
              <button
                key={opt.key}
                role="tab"
                aria-selected={opt.key === verticalKey}
                onClick={() => setVerticalKey(opt.key)}
                className={
                  opt.key === verticalKey
                    ? 'rounded-full bg-[#171A20] px-4 py-2 text-sm font-semibold text-white'
                    : 'rounded-full border border-[#EAE5DC] bg-white px-4 py-2 text-sm font-medium text-[#5B6069] transition-colors hover:border-[#d8d2c6]'
                }
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Integrations strip (honest — wordmarks, no fake customer logos) */}
          <div className="mt-9">
            <p className="text-[11px] font-bold uppercase tracking-widest text-[#9BA0A8]">
              Works with the till you already own
            </p>
            <div className="mt-2.5 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-[15px] font-semibold text-[#9BA0A8]">
              {['Square', 'Toast', 'Clover', 'Lightspeed', 'Stripe', 'OpenTable-ready'].map((n) => (
                <span key={n}>{n}</span>
              ))}
            </div>
          </div>
        </div>

        {/* The product, in a hand, with honest floating chips */}
        <div className="relative mx-auto w-full max-w-[430px]">
          <img
            src="/landing2/hero-hand.webp"
            alt="A hand holding a phone running Meridian: today's booked revenue and three priced actions on screen"
            className="w-full"
          />
          {[
            { txt: '< 1 ring pickup', cls: 'left-[-4%] top-[16%]', delay: '0s' },
            { txt: '+$4,080/mo actions on screen', cls: 'right-[-6%] top-[38%]', delay: '1.1s' },
            { txt: 'Camera: spill spotted · dealt with', cls: 'left-[-4%] bottom-[18%]', delay: '2.2s' },
          ].map((c) => (
            <span
              key={c.txt}
              className={`absolute ${c.cls} animate-float rounded-xl border border-[#EAE5DC] bg-white px-3.5 py-2 text-[13px] font-semibold shadow-[0_10px_24px_rgba(23,26,32,0.12)]`}
              style={{ animationDelay: c.delay }}
            >
              {c.txt}
            </span>
          ))}
        </div>
      </div>
      </section>

      {/* ─── Metrics strip ───────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-12">
        <PopCard className="grid gap-4 p-8 sm:grid-cols-3">
          {[
            ['~30%', 'of calls go unanswered at peak — industry, not us'],
            ['1 ring', 'before Meridian picks up, every time'],
            ['0 faces', 'cameras record what happened — never who'],
          ].map(([n, l]) => (
            <div key={l} className="text-center sm:text-left">
              <div className="text-4xl font-extrabold tracking-tight text-[#1A8FD6]">{n}</div>
              <div className="mt-1 text-sm leading-snug text-[#5B6069]">{l}</div>
            </div>
          ))}
        </PopCard>
      </section>

      {/* ─── Listen: the live transcript ─────────────────────── */}
      <section id="how" className="relative bg-gradient-to-b from-[#EFF6FC] to-transparent"><div className="mx-auto max-w-6xl px-6 py-14">
        <div className="max-w-2xl">
          <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">Hear it work</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
            The call becomes a row in your POS, not a voicemail.
          </h2>
          <p className="mt-4 text-lg text-[#5B6069]">
            A real conversation, and the artifact it leaves behind — while the
            caller is still on the line.
          </p>
        </div>
        <div className="mt-10">
          <AnimatePresence mode="wait">
            <motion.div
              key={v.key}
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3, ease: EASE }}
            >
              <LiveTranscript lines={v.transcript} artifact={v.artifact} restartKey={v.key} />
            </motion.div>
          </AnimatePresence>
        </div>
      </div></section>

      {/* ─── Real screenshots ────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid items-end gap-6 lg:grid-cols-[1.4fr,1fr]">
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">Not a mockup</p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
              These are screenshots, not renders.
            </h2>
          </div>
          <p className="text-lg text-[#5B6069] lg:pb-1">
            The same subscription reads your register: today's take, what's
            still sellable tonight, and the three moves worth real dollars this
            week.
          </p>
        </div>
        <div className="mt-10 grid gap-6 lg:grid-cols-[1.6fr,1fr]">
          <PopCard className="!shadow-[0_18px_50px_rgba(23,26,32,0.10)]">
            <div className="flex items-center gap-1.5 border-b border-[#EAE5DC] px-4 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="ml-3 font-mono text-[11px] text-[#9BA0A8]">app.meridian.tips — Today</span>
            </div>
            <img src="/landing2/shot-dashboard.webp" loading="lazy"
                 alt="Meridian owner dashboard: booked revenue vs a normal day, covers, and three priced actions" className="w-full" />
            <figcaption className="border-t border-[#EAE5DC] px-4 py-3 text-sm text-[#5B6069]">
              "$672 still sellable today — 7 more slots would fit." It tells you; you don't dig.
            </figcaption>
          </PopCard>
          <PopCard className="flex flex-col !shadow-[0_18px_50px_rgba(23,26,32,0.10)]">
            <div className="flex items-center gap-1.5 border-b border-[#EAE5DC] px-4 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="ml-3 font-mono text-[11px] text-[#9BA0A8]">Phone Agent</span>
            </div>
            <img src="/landing2/shot-phone.webp" loading="lazy"
                 alt="Meridian phone agent screen: live call indicator, voice personalities, call and order counts" className="min-h-0 w-full flex-1 object-cover object-top" />
            <figcaption className="border-t border-[#EAE5DC] px-4 py-3 text-sm text-[#5B6069]">
              Pick the voice that answers as yours — Vinny, Rosie, Jacques, Priya…
            </figcaption>
          </PopCard>
        </div>
      </section>

      {/* ─── The trades — QP-style photo bento ───────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="max-w-2xl">
          <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">Every trade</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
            One brain. Every trade's phone.
          </h2>
          <p className="mt-4 text-lg text-[#5B6069]">
            Meridian is set up differently for each one — the vocabulary, the
            booking noun, the screens. Pick yours and the demo opens the way
            your portal would.
          </p>
        </div>
        <div className="mt-10 grid auto-rows-[190px] gap-4 md:grid-cols-6">
          {[
            { img: '/landing2/hero-pass.webp', label: 'Restaurants', line: 'Orders land in the POS while the caller is still on the line.', span: 'md:col-span-3 md:row-span-2', big: true },
            { img: '/landing2/niche-golf.webp', label: 'Golf courses', line: 'Foursomes on the tee sheet, carts included.', span: 'md:col-span-3' },
            { img: '/landing2/niche-barber.webp', label: 'Barbershops & salons', line: 'Chairs booked into Square, deposits texted.', span: 'md:col-span-2' },
            { img: '/landing2/niche-smoke.webp', label: 'Smoke shops', line: '', span: 'md:col-span-1' },
            { img: '/landing2/niche-detail.webp', label: 'Auto detailing', line: 'Bays scheduled, payment links per job.', span: 'md:col-span-2' },
            { img: '/landing2/niche-medspa.webp', label: 'Med spas', line: 'Consults booked, reminders sent.', span: 'md:col-span-2' },
            { img: '/landing2/niche-coffee.webp', label: 'Coffee shops', line: 'The morning rush, answered.', span: 'md:col-span-2' },
          ].map((t) => (
            <div
              key={t.label}
              className={`group relative overflow-hidden rounded-[22px] border border-[#EAE5DC] shadow-[0_8px_30px_rgba(23,26,32,0.08)] ${t.span}`}
            >
              <img
                src={t.img}
                alt={`${t.label} — a Meridian trade`}
                loading="lazy"
                className="absolute inset-0 h-full w-full object-cover transition-transform duration-500 motion-safe:group-hover:scale-[1.04]"
              />
              <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/25 to-transparent" />
              <div className={`absolute bottom-0 p-5 text-white ${t.big ? 'md:p-6' : ''}`}>
                <div className={`font-extrabold tracking-tight ${t.big ? 'text-3xl' : 'text-xl'}`}>{t.label}</div>
                {t.line && <p className="mt-1 max-w-sm text-sm text-white/75">{t.line}</p>}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ─── Camera Intelligence — it watches the room, too ──── */}
      <section className="bg-gradient-to-b from-transparent via-[#E9F7F4] to-transparent"><div className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid items-center gap-10 lg:grid-cols-[1fr,1.35fr]">
          <div>
            <p className="inline-flex items-center gap-2 text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">
              <Cctv className="h-4 w-4 shrink-0" /> Camera intelligence
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
              It watches the room, too.
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-[#5B6069]">
              Plug in the cameras you already have. Meridian counts walk-ins,
              occupancy, and queue time — and flags the moments that cost you:
              a spill nobody's mopped, a host stand empty with two parties
              waiting, a phone out behind the bar mid-service.
            </p>
            <ul className="mt-6 space-y-3">
              {[
                'Walk-ins, walk-outs, occupancy, and queue wait — live',
                'Spills, unattended counters, after-hours motion flagged with confidence scores',
                'One tap: "Dealt with" or "Not a real one" — it learns your floor',
              ].map((t) => (
                <li key={t} className="flex items-start gap-2.5 text-[15px] text-[#171A20]">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#1A8FD6]" /> {t}
                </li>
              ))}
            </ul>
            <p className="mt-6 rounded-xl border border-[#EAE5DC] bg-white px-4 py-3 text-sm font-medium text-[#5B6069]">
              Nobody is identified. The cameras record <span className="font-semibold text-[#171A20]">what happened</span> — never who.
            </p>
          </div>
          <PopCard className="relative">
            <div className="flex items-center gap-1.5 border-b border-[#EAE5DC] px-4 py-2.5">
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#EAE5DC]" />
              <span className="ml-3 font-mono text-[11px] text-[#9BA0A8]">Camera Intelligence — What the cameras saw</span>
            </div>
            <img src="/landing2/shot-camera.webp" loading="lazy"
                 alt="Meridian Camera Intelligence: walk-in counts, queue wait, and flagged events like a spill on the floor and an unattended host stand"
                 className="w-full" />
            <BorderBeam size={160} duration={9} colorFrom="#1A8FD6" colorTo="#17C5B0" />
          </PopCard>
        </div>
      </div></section>

      {/* ─── Feature comparison — where Meridian stands alone ── */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="max-w-2xl">
          <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">Side by side</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
            Every answering AI answers. Then the list gets short.
          </h2>
        </div>
        <PopCard className="mt-10 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-[15px]">
            <thead>
              <tr className="border-b border-[#EAE5DC] font-mono text-xs uppercase tracking-wider text-[#9BA0A8]">
                <th className="px-5 py-4 font-medium"></th>
                <th className="px-5 py-4 font-bold text-[#1A8FD6]">Meridian</th>
                <th className="px-5 py-4 font-medium">Slang.ai</th>
                <th className="px-5 py-4 font-medium">Popmenu AI</th>
                <th className="px-5 py-4 font-medium">SoundHound</th>
              </tr>
            </thead>
            <tbody>
              {[
                ['Answers every call, 24/7', true, true, true, true],
                ['Takes orders straight into your POS', true, false, false, false],
                ['Books into Square Appointments', true, false, false, false],
                ['Works your waitlist automatically when a slot opens', true, false, false, false],
                ['Camera intelligence on your floor', true, false, false, false],
                ['POS analytics in the same subscription', true, false, false, false],
                ['Price printed on the website', true, false, false, false],
              ].map(([label, ...cols]) => (
                <tr key={label as string} className="border-b border-[#EAE5DC] last:border-0">
                  <td className="px-5 py-3.5 font-medium text-[#171A20]">{label}</td>
                  {(cols as boolean[]).map((ok, i) => (
                    <td key={i} className={i === 0 ? 'bg-[#1A8FD6]/[0.06] px-5 py-3.5' : 'px-5 py-3.5'}>
                      {ok
                        ? <Check className={`h-5 w-5 shrink-0 ${i === 0 ? 'text-[#1A8FD6]' : 'text-[#9BA0A8]'}`} />
                        : <Minus className="h-5 w-5 shrink-0 text-[#D8D2C6]" />}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="border-t border-[#EAE5DC] px-5 py-3 text-xs text-[#9BA0A8]">
            Competitor capabilities as publicly described on their own sites, Sept 2026.
          </p>
        </PopCard>
      </section>

      {/* ─── Outbound — the claim nobody else can make ───────── */}
      <section className="mx-auto max-w-6xl px-6 py-14">
        <div className="grid items-center gap-10 rounded-2xl border border-[#EAE5DC] bg-white p-8 shadow-[0_8px_30px_rgba(23,26,32,0.06)] md:p-12 lg:grid-cols-[1fr,1.2fr]">
          <div className="relative mx-auto aspect-square w-full max-w-[300px]">
            {[0, 1, 2].map((ring) => (
              <span
                key={ring}
                className="absolute inset-0 m-auto rounded-full border border-[#1A8FD6]/25 motion-safe:animate-ping"
                style={{ width: `${46 + ring * 27}%`, height: `${46 + ring * 27}%`, animationDuration: '3.2s', animationDelay: `${ring * 1.05}s` }}
              />
            ))}
            <div className="absolute inset-0 m-auto flex h-[42%] w-[42%] items-center justify-center rounded-full bg-[#1A8FD6] shadow-[0_16px_40px_rgba(26,143,214,0.35)]">
              <MessageSquareText className="h-9 w-9 shrink-0 text-white" />
            </div>
          </div>
          <div>
            <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">
              No one else does this
            </p>
            <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
              It doesn't just answer. It texts your waitlist the second a table opens.
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-[#5B6069]">
              A 7:30 cancellation at 7:05 is worth nothing on a clipboard.
              Meridian offers the freed slot to your waitlist by text, in
              order — biggest spender first, no-shows last — and it's resold
              before your host notices it opened. Slang, Popmenu, SoundHound:
              they only answer.
            </p>
          </div>
        </div>
      </section>

      {/* ─── Pricing + ROI ───────────────────────────────────── */}
      <section id="pricing" className="bg-gradient-to-b from-[#FDF4E7] to-transparent"><div className="mx-auto max-w-6xl px-6 py-14">
        <div className="max-w-2xl">
          <p className="text-[13px] font-bold uppercase tracking-wide text-[#1A8FD6]">Priced in the open</p>
          <h2 className="mt-3 text-4xl font-extrabold tracking-tight md:text-5xl">
            The price, next to everyone else's.
          </h2>
          <p className="mt-4 text-lg text-[#5B6069]">
            From US$250 a month, month to month, no overage games — and we
            don't need a sales call to tell you a number.
          </p>
        </div>
        <div className="mt-10">
          <CostMath />
        </div>
      </div></section>

      {/* ─── Friction killers ────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-10">
        <div className="grid gap-6 text-center sm:grid-cols-3">
          {[
            ['Live in under an hour', 'connect your POS, pick a voice, forward the line'],
            ['Month to month', 'no contract, cancel from the dashboard'],
            ['Your number stays yours', 'we answer it; take it back any time'],
          ].map(([t, s]) => (
            <PopCard key={t} className="p-6">
              <div className="font-bold">{t}</div>
              <div className="mt-1 text-sm text-[#5B6069]">{s}</div>
            </PopCard>
          ))}
        </div>
      </section>

      {/* ─── Final CTA ───────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-16 text-center">
        <h2 className="mx-auto max-w-2xl text-4xl font-extrabold tracking-tight md:text-5xl">
          Don't take a demo. Make a call.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-lg text-[#5B6069]">
          The agent is on a real line right now. Order something. Try to trip it
          up. Then imagine it answering your phone tonight at 6:45.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <a
            href={`tel:${VERTICALS[0].demoNumberE164}`}
            className="inline-flex items-center gap-2.5 rounded-xl bg-[#1A8FD6] px-6 py-3.5 font-semibold text-white shadow-[0_10px_24px_rgba(26,143,214,0.35)] transition-all hover:-translate-y-0.5 hover:bg-[#1574B8]"
          >
            <Phone className="h-4 w-4 shrink-0" />
            <span className="font-mono tracking-wide">{VERTICALS[0].demoNumber}</span>
          </a>
          <a
            href="#quote"
            className="inline-flex items-center gap-2 rounded-xl border border-[#EAE5DC] bg-white px-5 py-3.5 font-semibold text-[#171A20] shadow-sm transition-colors hover:border-[#d8d2c6]"
          >
            Book a 15-minute demo <ArrowRight className="h-4 w-4 shrink-0" />
          </a>
        </div>
      </section>

      {/* ─── Quote form (shared dark component — contrast band) ── */}
      <section id="quote" className="bg-[#0B1120]">
        <ScheduleQuote accent="#1A8FD6" accentSecondary="#17C5B0" source="us-landing-v2" />
      </section>

      {/* ─── Footer ──────────────────────────────────────────── */}
      <footer className="border-t border-[#EAE5DC] bg-[#FBF8F3]">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-[#5B6069]">
          <MeridianLogo size={22} showWordmark showTagline={false} />
          <nav className="flex flex-wrap gap-5">
            <Link to="/careers" className="hover:text-[#171A20]">Careers</Link>
            <a href="/privacy" className="hover:text-[#171A20]">Privacy</a>
            <a href="/terms" className="hover:text-[#171A20]">Terms</a>
            <Link to="/canada" className="hover:text-[#171A20]">Canada</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
