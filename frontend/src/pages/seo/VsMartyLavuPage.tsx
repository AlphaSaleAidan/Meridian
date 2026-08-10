import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Lock,
  PhoneOff,
  Phone,
  Building2,
  MessageSquare,
  Search,
  Plug,
  Sunrise,
  Bot,
  EyeOff,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'What is Marty by Lavu?',
    a: 'Marty is the AI analytics and intelligence layer built into Lavu POS — Lavu describes it as a "digital general manager." It delivers morning briefings, a daily digest of sales trends, labor spend, and inventory status, real-time labor alerts, food-cost tracking, and a single dashboard for multi-location operators. It also includes six AI agents that Lavu says can act on your behalf: smart promotions, pricing fixes, schedule building, waste prevention, team coaching, and margin guarding.',
  },
  {
    q: 'Do I need Lavu POS to use Marty?',
    a: 'Yes. Marty is built into Lavu POS — it is not sold as a standalone product that connects to other systems. If you run Square, Clover, or any other point of sale, getting Marty means switching your entire POS to Lavu. Meridian takes the opposite approach: it connects on top of the POS you already run.',
  },
  {
    q: 'Does Marty by Lavu answer the phone or take phone orders?',
    a: 'No. Marty is an analytics and operations intelligence layer — answering calls and taking phone orders is not part of the product. Meridian includes an AI phone agent that answers every call 24/7, takes the complete order conversationally, injects it into your Square or Clover POS as a real order, and sends the caller a pay-by-text link.',
  },
  {
    q: 'How much does Marty by Lavu cost?',
    a: 'Lavu does not publish Marty pricing separately from Lavu POS — Marty comes as part of the Lavu platform, so its cost is bundled into what you pay for the POS itself. Meridian is priced by quote, with the first month free and no contracts.',
  },
  {
    q: 'What is the best Marty by Lavu alternative for Square or Clover?',
    a: 'If you run Square or Clover and want Marty-style intelligence — anomaly detection, revenue forecasting, multi-location dashboards — without changing your POS, Meridian connects in minutes with a one-click POS connect. It also adds something no POS-bundled AI offers: an AI phone agent that answers every call and puts complete orders directly into your POS. You can try it live by calling +1 380 240 9535 (US) or +1 506 801 7904 (Canada).',
  },
]

const faqJsonLd = {
  '@type': 'FAQPage',
  mainEntity: faqItems.map((item) => ({
    '@type': 'Question',
    name: item.q,
    acceptedAnswer: {
      '@type': 'Answer',
      text: item.a,
    },
  })),
}

/* ── Head-to-Head Comparison ───────────────────────── */

const comparisonRows = [
  {
    feature: 'Works With Your POS',
    marty: 'Lavu POS only — built in',
    meridian: 'Sits on top of Square and Clover',
    winner: 'meridian',
  },
  {
    feature: 'Switching Required',
    marty: 'Must adopt (or switch to) Lavu POS',
    meridian: 'Keep your existing POS — one-click connect',
    winner: 'meridian',
  },
  {
    feature: 'Daily Intelligence',
    marty: 'Morning briefings + daily digest',
    meridian: 'AI analytics with anomaly detection',
    winner: 'tie',
  },
  {
    feature: 'Forecasting',
    marty: 'Sales trends in the daily digest',
    meridian: 'AI revenue forecasting',
    winner: 'meridian',
  },
  {
    feature: 'Multi-Location',
    marty: 'Single dashboard across locations',
    meridian: 'Unified multi-location dashboards',
    winner: 'tie',
  },
  {
    feature: 'Answers the Phone',
    marty: 'Not part of the product',
    meridian: 'AI phone agent answers every call, 24/7',
    winner: 'meridian',
  },
  {
    feature: 'Phone Orders Into POS',
    marty: 'Not part of the product',
    meridian: 'Complete orders injected into Square/Clover',
    winner: 'meridian',
  },
  {
    feature: 'Payment Collection',
    marty: 'Not part of the product',
    meridian: 'Pay-by-text link — caller pays from their phone',
    winner: 'meridian',
  },
  {
    feature: 'Pricing Transparency',
    marty: 'Not published separately from Lavu POS',
    meridian: 'By quote — first month free, no contracts',
    winner: 'meridian',
  },
  {
    feature: 'Time to Live',
    marty: 'Tied to a full POS install/switch',
    meridian: 'Minutes, not weeks',
    winner: 'meridian',
  },
]

/* ── "Why Operators Like Marty" Reasons ──────────────── */

const whyMarty = [
  { icon: Plug, label: 'Zero Integration on Lavu', detail: 'If you already run Lavu POS, Marty is right there — nothing to connect' },
  { icon: Sunrise, label: 'Briefing & Digest UX', detail: 'Morning briefings and a daily digest are a genuinely useful pattern' },
  { icon: Bot, label: 'Agents That Act', detail: 'Six AI agents (in Lavu\'s description) go beyond reports — promotions, pricing, schedules' },
]

const whyTheyBreak = [
  { icon: Lock, label: 'Locked to one POS', detail: 'Marty only exists inside Lavu — leave Lavu and the intelligence goes with it' },
  { icon: PhoneOff, label: 'The phone still rings unanswered', detail: 'Marty analyzes your business; it does not answer calls or take phone orders' },
  { icon: EyeOff, label: 'No standalone pricing', detail: 'Marty\'s cost is bundled into Lavu POS — you can\'t evaluate it on its own' },
  { icon: Building2, label: 'Backwards migration path', detail: 'Getting analytics by replacing your entire POS is the most disruptive route possible' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'One-click connect for Square or Clover. Minutes, not weeks — no POS migration, no retraining, no new hardware.',
  },
  {
    num: '02',
    icon: Search,
    title: 'AI Analyzes Your Data',
    desc: 'Meridian layers anomaly detection, revenue forecasting, and multi-location dashboards on top of the POS you already run.',
  },
  {
    num: '03',
    icon: Phone,
    title: 'Every Call Gets Answered',
    desc: 'The AI phone agent picks up 24/7, takes the complete order conversationally, injects it into your POS, and sends a pay-by-text link.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'vs Slang.ai', to: '/vs/slang-ai' },
  { label: 'vs SoundHound Smart Answering', to: '/vs/soundhound-smart-answering' },
  { label: 'vs Popmenu Answering', to: '/vs/popmenu-answering' },
  { label: 'vs Nory', to: '/vs/nory' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Square Integration', to: '/integrations/square' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsMartyLavuPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Marty by Lavu: Keep Your POS | Meridian"
        description="Marty's AI is locked inside Lavu POS. Meridian adds the same class of intelligence on top of Square or Clover — plus an AI phone agent that answers every call."
        path="/vs/marty-by-lavu"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">
            Comparison
          </p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Meridian vs. Marty by Lavu:
            <br />
            <span className="text-[#17C5B0]">Intelligence Shouldn't Require a POS Switch</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Marty is a smart "digital general manager" — but only if Lavu is your point of sale.
            Meridian sits on top of the POS you already run, and answers your phone too.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            Keep Your POS — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── What Marty Actually Is ────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">What Marty by Lavu Actually Is</h2>
        <div className="space-y-4 text-[#A1A1A8] leading-relaxed mb-8">
          <p>
            Marty is the AI intelligence layer built into Lavu POS. Lavu positions it as a
            "digital general manager": it opens your day with a morning briefing summarizing
            performance, sends a daily digest covering sales trends, labor spend, and inventory
            status, fires real-time labor alerts when overtime or overstaffing creeps in, tracks
            food cost by combining sales and inventory data, and rolls multiple locations into a
            single dashboard.
          </p>
          <p>
            Lavu also describes six AI agents inside Marty that act rather than just report:
            smart promotions for empty hours, pricing and margin fixes, schedule building, waste
            prevention, team coaching, and margin guarding. That agentic direction is genuinely
            ahead of most POS-bundled reporting.
          </p>
          <p>
            There is one structural catch, and it changes everything about the comparison:{' '}
            <span className="text-[#F5F5F7] font-medium">
              Marty is built into Lavu POS. Using Marty means using — or switching to — Lavu as
              your point of sale.
            </span>{' '}
            The intelligence is not a product you can bolt onto Square or Clover. It is a feature
            of a POS you would have to adopt first.
          </p>
        </div>

        {/* Why owners like it */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why Lavu operators like Marty
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyMarty.map((item) => (
              <div
                key={item.label}
                className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5"
              >
                <item.icon className="w-5 h-5 text-[#A1A1A8] mb-3" />
                <h3 className="text-base font-semibold mb-1">{item.label}</h3>
                <p className="text-sm text-[#A1A1A8]">{item.detail}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Why it breaks down */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Why Marty breaks down for everyone else
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {whyTheyBreak.map((item) => (
              <div
                key={item.label}
                className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 flex items-start gap-4"
              >
                <div className="w-9 h-9 rounded-lg bg-[#EF4444]/10 flex items-center justify-center shrink-0">
                  <item.icon className="w-4 h-4 text-[#EF4444]" />
                </div>
                <div>
                  <h3 className="text-base font-semibold mb-1">{item.label}</h3>
                  <p className="text-sm text-[#A1A1A8]">{item.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Head-to-Head Comparison ───────────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            Head-to-Head Comparison
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-10">
            Ten categories where a POS-bundled AI and a POS-independent intelligence platform go
            head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Marty by Lavu
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider">
                Meridian
              </div>
            </div>
            {/* Rows */}
            {comparisonRows.map((row, i) => (
              <div
                key={row.feature}
                className={`grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] ${
                  i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'
                } ${i < comparisonRows.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}
              >
                <div className="px-5 py-3 font-medium text-sm">{row.feature}</div>
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.marty}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Cost of POS-Locked Intelligence ───────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Cost of POS-Locked Intelligence
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">Your POS</div>
              <p className="text-sm text-[#A1A1A8] mt-1">must become Lavu before Marty's briefings ever reach you</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">Its price</div>
              <p className="text-sm text-[#A1A1A8] mt-1">is not published separately — bundled into the Lavu platform</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">Your phone</div>
              <p className="text-sm text-[#A1A1A8] mt-1">still rings unanswered — call handling isn't part of Marty</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-3xl md:text-4xl font-bold text-[#EF4444]">= Switching your POS to get a dashboard</div>
            <p className="text-sm text-[#A1A1A8] mt-2">The analytics may be good — the migration path is backwards</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            A POS switch is the single most disruptive change a restaurant can make: new hardware,
            new menu programming, staff retraining, and days of operational risk. Doing all of
            that to gain an analytics layer inverts the decision — the point of sale should be
            chosen for how it runs your line, not for the dashboard bundled with it.
          </p>
          <p>
            Meridian takes the opposite architecture. It sits on top of the POS you already run —
            Square and Clover today — and adds the same class of intelligence Marty offers:
            anomaly detection, AI revenue forecasting, and multi-location dashboards. Connection
            is one click, and onboarding takes minutes, not weeks.
          </p>
          <p>
            Then it adds the piece no POS-bundled AI has: an AI phone agent that answers every
            call 24/7, takes the complete order conversationally, and injects it directly into
            your POS as a real order — not a text-a-link handoff. The caller gets a pay-by-text
            link and pays from their phone. You can hear it yourself right now: call{' '}
            <span className="text-[#F5F5F7] font-medium">+1 380 240 9535</span> in the US or{' '}
            <span className="text-[#F5F5F7] font-medium">+1 506 801 7904</span> in Canada and
            order a pizza from the live demo line.
          </p>
        </div>
      </section>

      {/* ── When Marty Still Makes Sense ──────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Marty by Lavu Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. If you{' '}
                  <span className="text-[#F5F5F7] font-medium">already run Lavu POS</span>, Marty
                  is a real asset: it is built in, there is zero integration work, and the
                  morning-briefing and daily-digest experience is a genuinely useful way to
                  consume your numbers. Its six AI agents — as Lavu describes them — act on
                  promotions, pricing, schedules, waste, coaching, and margins rather than just
                  reporting, which puts it ahead of passive POS dashboards.
                </p>
                <p>
                  If you were choosing a new POS from scratch and Lavu fits your service model,
                  getting Marty in the bundle is a legitimate point in Lavu's favor.
                </p>
                <p>
                  The comparison changes if you run{' '}
                  <span className="text-[#F5F5F7] font-medium">Square or Clover and are happy with it</span>.
                  Then Marty's price of admission is replacing your entire point of sale — and
                  even after that migration, your phone still goes unanswered during a rush.
                  Meridian delivers the intelligence layer without touching your POS, and turns
                  every missed call into a completed, paid order inside it.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Making the Switch ─────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          Making the Switch
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Keep the POS you already run. Add Meridian as the intelligence and phone layer on top —
          available in the US and Canada.
        </p>
        <div className="grid md:grid-cols-3 gap-8">
          {switchSteps.map((s) => (
            <div key={s.num} className="text-center">
              <div className="text-4xl font-bold text-[#17C5B0]/30 mb-3">{s.num}</div>
              <div className="w-12 h-12 rounded-xl bg-[#17C5B0]/10 flex items-center justify-center mx-auto mb-4">
                <s.icon className="w-6 h-6 text-[#17C5B0]" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{s.title}</h3>
              <p className="text-[#A1A1A8] text-sm leading-relaxed">{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Get the Intelligence Without the POS Migration
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          One-click POS connect for Square and Clover. AI analytics plus a phone agent that
          answers every call. First month free, no contracts.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Start Your Free Month <ArrowRight className="w-5 h-5" />
        </Link>
        <p className="text-sm text-[#A1A1A8] mt-6">
          Or hear the phone agent live: <span className="text-[#F5F5F7] font-medium">+1 380 240 9535</span> (US)
          {' '}&middot;{' '}
          <span className="text-[#F5F5F7] font-medium">+1 506 801 7904</span> (Canada)
        </p>
      </section>

      {/* ── FAQ ───────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-12">
          Frequently Asked Questions
        </h2>
        <div className="space-y-3">
          {faqItems.map((item) => (
            <details
              key={item.q}
              className="group bg-[#111113] border border-[#1F1F23] rounded-xl overflow-hidden"
            >
              <summary className="flex items-center justify-between cursor-pointer px-6 py-4 text-[15px] font-medium list-none">
                {item.q}
                <ChevronRight className="w-4 h-4 text-[#A1A1A8] transition-transform group-open:rotate-90 shrink-0 ml-4" />
              </summary>
              <div className="px-6 pb-4 text-sm text-[#A1A1A8] leading-relaxed">
                {item.a}
              </div>
            </details>
          ))}
        </div>
      </section>

      {/* ── Internal Links ────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
        <p className="text-[#A1A1A8] text-sm mb-3">Keep reading:</p>
        <div className="flex flex-wrap gap-3">
          {relatedPages.map((p) => (
            <Link
              key={p.to}
              to={p.to}
              className="inline-flex items-center gap-1 px-4 py-2 rounded-lg border border-[#1F1F23] text-sm text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#17C5B0]/40 transition-colors"
            >
              {p.label} <ChevronRight className="w-3 h-3" />
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
