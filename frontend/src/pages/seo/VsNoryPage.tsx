import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Phone,
  PhoneOff,
  BarChart3,
  DollarSign,
  Building2,
  MessageSquare,
  Plug,
  CheckCircle2,
  Boxes,
  EyeOff,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does Nory answer restaurant phone calls or take phone orders?',
    a: 'No. Nory is a back-of-house operating system — its crew of AI assistants handles forecasting, scheduling, inventory ordering, invoicing, payroll, and compliance. None of them answer your phone. Meridian\'s AI phone agent answers every call 24/7, takes the complete order conversationally, and injects it directly into your Square or Clover POS as a real order.',
  },
  {
    q: 'How much does Nory cost?',
    a: 'Nory does not publish pricing — it is quote-based, arranged through their sales team. Meridian pricing is also by quote, but you can start with a first month free and no contracts, and you can test the phone agent live before ever talking to sales.',
  },
  {
    q: 'Does Meridian replace Nory?',
    a: 'Not for back-of-house operations. Nory goes deeper on inventory control, supplier ordering, invoice scanning, payroll, and staff scheduling than Meridian does — Meridian doesn\'t do those things. Meridian covers the revenue side: an AI phone agent that captures every phone order into your POS, plus POS analytics with anomaly detection, revenue forecasting, and multi-location dashboards. Some operators sensibly run both.',
  },
  {
    q: 'What are the best Nory alternatives?',
    a: 'It depends on which problem you\'re solving. For inventory, payroll, and scheduling depth, Nory\'s closest peers are other back-of-house restaurant operating systems. But if the problem is missed phone calls and lost phone orders, no back-office tool solves it — that\'s a front-of-house revenue problem, and it\'s what Meridian\'s phone agent plus POS analytics is built for.',
  },
  {
    q: 'Can I try Meridian before signing up?',
    a: 'Yes — live, right now. Call +1 380 240 9535 in the US or +1 506 801 7904 in Canada and order a pizza from the demo line. You\'ll experience exactly what your customers would: the agent answers, takes the complete order conversationally, and the order lands in a real POS.',
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
    feature: 'AI Phone Agent',
    nory: 'None — Nory does not answer calls',
    meridian: 'Answers every call, 24/7',
    winner: 'meridian',
  },
  {
    feature: 'Phone Orders into POS',
    nory: 'Not offered',
    meridian: 'Complete order taken conversationally, injected into Square or Clover as a real order',
    winner: 'meridian',
  },
  {
    feature: 'Pay-by-Text',
    nory: 'Not offered',
    meridian: 'Payment link texted after the order — caller pays from their phone',
    winner: 'meridian',
  },
  {
    feature: 'Demand Forecasting',
    nory: 'Core strength — claims up to 95% accuracy',
    meridian: 'AI revenue forecasting on your POS data',
    winner: 'nory',
  },
  {
    feature: 'Inventory & Ordering',
    nory: 'Deep — inventory control, supplier ordering, invoice scanning',
    meridian: 'Not offered — Nory\'s home turf',
    winner: 'nory',
  },
  {
    feature: 'Scheduling & Payroll',
    nory: 'Full scheduling, payroll, and staff performance tracking',
    meridian: 'Not offered',
    winner: 'nory',
  },
  {
    feature: 'Anomaly Detection',
    nory: 'P&L tracking and review',
    meridian: 'Real-time anomaly alerts on POS activity',
    winner: 'meridian',
  },
  {
    feature: 'Multi-Location View',
    nory: 'Proven with multi-site hospitality groups',
    meridian: 'Unified cross-location revenue dashboards',
    winner: 'tie',
  },
  {
    feature: 'POS Integrations',
    nory: 'Toast, Clover, Deliverect, Shift4, SumUp, Vita Mojo, Zonal',
    meridian: 'Square and Clover — with direct phone-order injection',
    winner: 'tie',
  },
  {
    feature: 'Try It Yourself',
    nory: 'Book a sales demo',
    meridian: 'Call the live agent right now: +1 380 240 9535',
    winner: 'meridian',
  },
]

/* ── "Why Operators Use Nory" Reasons ──────────────── */

const whyNory = [
  { icon: Boxes, label: 'Back-of-House Depth', detail: 'Inventory control, supplier ordering, invoice scanning, payroll — genuinely deep operations tooling' },
  { icon: BarChart3, label: 'Forecasting Pedigree', detail: 'Demand forecasting is Nory\'s core — they claim up to 95% accuracy' },
  { icon: Building2, label: 'Proven with Groups', detail: 'Strong track record with UK and Ireland multi-site hospitality groups; $37M Series B, US expansion in 2026' },
]

const whereNoryStops = [
  { icon: PhoneOff, label: 'The phone still rings unanswered', detail: 'Nory\'s AI crew forecasts, schedules, and orders stock — none of them pick up your phone' },
  { icon: DollarSign, label: 'Optimizes cost, not revenue capture', detail: 'Its claims — cut food waste 50%, cut labour 25%, save 100+ admin hours a month (Nory\'s own numbers) — are all about the back office' },
  { icon: Phone, label: 'No path from a phone call to a POS order', detail: 'A caller who can\'t get through doesn\'t become a ticket in any system Nory touches' },
  { icon: EyeOff, label: 'Pricing not published', detail: 'Quote-based only — you can\'t evaluate cost, or the product, without a sales cycle' },
]

/* ── "Adding Meridian" Steps ───────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'One-click connection to Square or Clover. Minutes, not weeks — no IT project, no data migration.',
  },
  {
    num: '02',
    icon: Phone,
    title: 'Phone Agent Goes Live',
    desc: 'The AI agent starts answering every call 24/7, taking complete orders conversationally and injecting them straight into your POS, with a pay-by-text link to close the sale.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Analytics Switch On',
    desc: 'Anomaly detection, revenue forecasting, and multi-location dashboards run automatically on your POS data — the revenue side of the house, covered.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'vs Slang.ai', to: '/vs/slang-ai' },
  { label: 'vs SoundHound Smart Answering', to: '/vs/soundhound-smart-answering' },
  { label: 'vs Popmenu Answering', to: '/vs/popmenu-answering' },
  { label: 'vs Marty by Lavu', to: '/vs/marty-by-lavu' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Square Integration', to: '/integrations/square' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsNoryPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Nory: Who Answers the Phone? | Meridian"
        description="Nory runs your back office — forecasting, inventory, payroll. But it doesn't answer your phone. Meridian's AI agent captures every phone order into your POS."
        path="/vs/nory"
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
            Meridian vs. Nory:
            <br />
            <span className="text-[#17C5B0]">Who Answers the Phone?</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Nory optimizes your back office. Meridian captures revenue at the front — starting with
            every phone call you're currently missing.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            Hear the Agent Live — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Two Different Problems ─────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">Two Different Problems</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-4">
          Nory calls itself an AI restaurant operating system, and for the back of house that's a
          fair description. Founded in Ireland by Conor Sheridan and backed by a $37M Series B,
          it gives hospitality groups a crew of AI assistants for demand forecasting, staff
          scheduling, inventory control and supplier ordering, invoice scanning, payroll, and
          compliance. It expanded to the US in 2026 after building a strong base with UK and
          Ireland hospitality groups.
        </p>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Meridian solves a different problem. It's a restaurant intelligence platform — an AI
          phone agent plus POS analytics in one — built around the revenue that walks in through
          your front door and, more often than operators realize, rings in on your phone line.
          Nory helps you spend less running the restaurant. Meridian helps you capture more of
          the revenue trying to reach it. Those are not the same job, and it's worth being clear
          about which one you're hiring a platform to do.
        </p>

        {/* Why operators use Nory */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators use Nory
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyNory.map((item) => (
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

        {/* Where it stops */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where Nory stops
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {whereNoryStops.map((item) => (
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
            Ten categories, honestly scored. Nory wins several of them — the question is which
            categories your P&amp;L actually needs won.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Nory
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.nory}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Front Door Nory Doesn't Cover ─────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Front Door Nory Doesn't Cover
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">0</div>
              <p className="text-sm text-[#A1A1A8] mt-1">phone calls answered by Nory's crew of AI assistants</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">Not published</div>
              <p className="text-sm text-[#A1A1A8] mt-1">Nory's pricing — quote-based, via their sales team</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">100+ hrs/mo</div>
              <p className="text-sm text-[#A1A1A8] mt-1">admin time Nory says it saves — their claim, and all of it back-office</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">A missed call is a missed order</div>
            <p className="text-sm text-[#A1A1A8] mt-2">No waste reduction or scheduling efficiency gets that revenue back</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Nory's headline claims are real efficiency claims: reduce food waste by up to 50%, cut
            labour costs by 25%, save more than 100 admin hours per month. Those are Nory's own
            numbers, and if they hold for your operation, they're meaningful. But notice what every
            one of them has in common — they shrink cost. None of them adds a single order.
          </p>
          <p>
            The phone is where restaurants leak revenue in real time. Every call that hits
            voicemail during a Friday rush, every caller who hangs up after six rings and dials
            the next place on the list, is an order lost today — not a cost to trim next quarter.
            Meridian's AI phone agent answers every one of those calls, 24/7, takes the complete
            order conversationally, injects it into your Square or Clover POS as a real order,
            and texts the caller a payment link so they pay from their phone. Then the analytics
            layer — anomaly detection, revenue forecasting, multi-location dashboards — tells you
            what that revenue is doing and where it's headed.
          </p>
          <p>
            You don't have to take that on faith. The agent is live right now: call{' '}
            <span className="text-[#F5F5F7] font-medium">+1 380 240 9535</span> in the US or{' '}
            <span className="text-[#F5F5F7] font-medium">+1 506 801 7904</span> in Canada and
            order a pizza. That's the whole pitch, demonstrated in one phone call — something a
            quote-based back-office platform simply can't show you.
          </p>
        </div>
      </section>

      {/* ── When Nory Still Makes Sense ───────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Nory Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest: for back-of-house operations, Nory is the deeper tool, and
                  it isn't close. If your pain is{' '}
                  <span className="text-[#F5F5F7] font-medium">inventory control, supplier ordering, invoice scanning, payroll, and staff scheduling</span>{' '}
                  across a multi-site group, Nory does things Meridian simply doesn't do, with a
                  forecasting pedigree and a track record with UK and Ireland hospitality groups
                  to back it up.
                </p>
                <p>
                  These platforms don't actually compete for the same budget line. Nory manages
                  the cost side of your P&amp;L; Meridian captures and analyzes the revenue side.
                  Some operators would sensibly{' '}
                  <span className="text-[#F5F5F7] font-medium">run both</span> — Nory keeping the
                  back office tight, Meridian making sure no phone order ever goes unanswered and
                  the revenue data gets watched by something smarter than a weekly report.
                </p>
                <p>
                  The honest question is sequencing. If your kitchen is leaking waste and your
                  rotas are chaos, start with Nory. If your phone line is leaking orders every
                  single day, no amount of back-office efficiency fixes that — start with the
                  phone.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Adding Meridian ───────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          Adding Meridian
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Whether or not Nory runs your back office, Meridian bolts onto the revenue side in
          minutes — no disruption, no migration. Available in the US and Canada.
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
          Stop Losing the Orders That Call You
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Call the live demo line — +1 380 240 9535 (US) or +1 506 801 7904 (Canada) — then
          connect your POS in minutes. First month free, no contracts.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Start Your Free Month <ArrowRight className="w-5 h-5" />
        </Link>
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
