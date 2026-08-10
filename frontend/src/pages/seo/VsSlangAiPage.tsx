import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Clock,
  BarChart3,
  DollarSign,
  Building2,
  MessageSquare,
  Plug,
  CheckCircle2,
  Phone,
  PhoneCall,
  CalendarCheck,
  Link2,
  ClipboardX,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does Slang.ai take phone orders?',
    a: 'Not into your POS. Slang.ai handles ordering by texting the caller a link to order online — the guest hangs up and finishes the order alone on their phone. Meridian\'s AI phone agent takes the complete order conversationally on the call itself and injects it directly into your Square or Clover POS as a real order, then sends a pay-by-text link so the caller can pay from their phone.',
  },
  {
    q: 'How much does Slang.ai cost?',
    a: 'As of August 2026, Slang.ai\'s published pricing is $399/month per location for Core, $599/month per location for Premium, and custom pricing for Enterprise. Add-ons include Bilingual Support at $99/month and Private Events with Tripleseat integration at $199/month. Meridian is priced by quote — book a demo and the first month is free, with no contracts.',
  },
  {
    q: 'What is the difference between Meridian and Slang.ai?',
    a: 'Slang.ai is a reservations-first AI phone answering product: it manages reservations end-to-end through OpenTable, SevenRooms, Yelp, and Fishbowl, and hands ordering off to a texted link. Meridian is a restaurant intelligence platform: its AI phone agent takes the entire food order on the call and puts it in your POS, and the same platform includes POS analytics — anomaly detection, revenue forecasting, and multi-location dashboards.',
  },
  {
    q: 'Is Meridian a good Slang.ai alternative?',
    a: 'If phone orders are revenue for you, yes — Meridian completes the order on the call and lands it in Square or Clover, instead of texting the guest a link and hoping they finish. If your restaurant is reservation-heavy and rarely takes phone orders, Slang.ai\'s deep OpenTable and SevenRooms integrations are a genuine strength worth weighing.',
  },
  {
    q: 'Can I try Meridian\'s phone agent before buying?',
    a: 'Yes — no signup needed. Call +1 380 240 9535 in the US or +1 506 801 7904 in Canada and order a pizza. You\'ll hear the agent take the complete order conversationally, exactly the way it would for your callers.',
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
    feature: 'Phone Ordering',
    slang: 'Texts the caller a link to order online',
    meridian: 'Takes the complete order on the call, conversationally',
    winner: 'meridian',
  },
  {
    feature: 'POS Integration',
    slang: 'Reservation platforms (OpenTable, SevenRooms, Yelp, Fishbowl)',
    meridian: 'Order injected into Square or Clover as a real order',
    winner: 'meridian',
  },
  {
    feature: 'Reservations',
    slang: 'End-to-end, deep reservation-platform integrations',
    meridian: 'Order-first agent; analytics platform included',
    winner: 'slang',
  },
  {
    feature: 'Payment',
    slang: 'SMS confirmations and links sent to guests',
    meridian: 'Pay-by-text link after the order — caller pays from their phone',
    winner: 'meridian',
  },
  {
    feature: 'Analytics',
    slang: 'Call recordings, summaries, CSAT collection',
    meridian: 'Full POS analytics: anomaly detection + revenue forecasting',
    winner: 'meridian',
  },
  {
    feature: 'Multi-Location',
    slang: 'Priced per location ($399-599/mo each, as of Aug 2026)',
    meridian: 'Multi-location dashboards built in',
    winner: 'meridian',
  },
  {
    feature: 'Setup',
    slang: 'Under 30 minutes of staff time',
    meridian: 'One-click POS connect — minutes, not weeks',
    winner: 'meridian',
  },
  {
    feature: 'Pricing',
    slang: '$399-599/mo per location + add-ons (as of Aug 2026)',
    meridian: 'By quote — first month free, no contracts',
    winner: 'meridian',
  },
  {
    feature: 'Try It Live',
    slang: 'Not published',
    meridian: 'Call +1 380 240 9535 (US) and order a pizza',
    winner: 'meridian',
  },
]

/* ── "Why Operators Use Slang.ai" Reasons ──────────── */

const whySlangAi = [
  { icon: CalendarCheck, label: 'Reservations Done Right', detail: 'Manages reservations end-to-end through OpenTable, SevenRooms, Yelp, and Fishbowl' },
  { icon: Clock, label: 'Fast to Set Up', detail: 'Under 30 minutes of staff time to go live, per Slang.ai' },
  { icon: PhoneCall, label: 'Mature Answering Product', detail: '24/7 answering with call recordings, summaries, VIP routing, and CSAT collection' },
]

const whyTheyBreak = [
  { icon: Link2, label: 'Ordering ends in a texted link', detail: 'The guest hangs up with a link, not a placed order — finishing is up to them' },
  { icon: ClipboardX, label: 'No order lands in your POS', detail: 'Slang.ai doesn\'t state that it takes complete food orders into a POS' },
  { icon: DollarSign, label: 'Per-location pricing stacks', detail: '$399-599/mo per location, plus $99-199/mo add-ons (as of Aug 2026)' },
  { icon: BarChart3, label: 'Analytics stop at the phone', detail: 'Call summaries and CSAT — not POS-wide anomaly detection or forecasting' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'One-click connect for Square and Clover. Minutes, not weeks — no IT project.',
  },
  {
    num: '02',
    icon: Phone,
    title: 'Hear It Take a Real Order',
    desc: 'Call the live demo line — +1 380 240 9535 (US) or +1 506 801 7904 (Canada) — and order a pizza. That\'s the agent your callers will get.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Orders Land in Your POS',
    desc: 'Every call answered 24/7, the complete order injected into Square or Clover, and a pay-by-text link sent so the caller pays from their phone.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'vs SoundHound Smart Answering', to: '/vs/soundhound-smart-answering' },
  { label: 'vs Popmenu Answering', to: '/vs/popmenu-answering' },
  { label: 'vs Nory', to: '/vs/nory' },
  { label: 'vs Marty by Lavu', to: '/vs/marty-by-lavu' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Square Integration', to: '/integrations/square' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsSlangAiPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Slang.ai: Full Orders Into Your POS | Meridian"
        description="Slang.ai answers the phone and texts guests an ordering link. Meridian takes the entire order on the call and puts it in your POS. Here's the full comparison."
        path="/vs/slang-ai"
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
            Meridian vs. Slang.ai:
            <br />
            <span className="text-[#17C5B0]">The Call Should End With an Order in Your POS</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Slang.ai answers the phone and texts your guest a link. Meridian takes the whole order
            on the call and puts it straight into Square or Clover.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            Book a Demo — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── The Texted-Link Gap ───────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Texted-Link Gap</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-4">
          Slang.ai is a genuinely polished AI phone answering product for restaurants. It picks up
          24/7, manages reservations end-to-end through OpenTable, SevenRooms, Yelp, and Fishbowl,
          records and summarizes calls, routes VIP callers, and collects CSAT. If a question is
          beyond it, it forwards the call to a human or texts the guest a link.
        </p>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          But look closely at what happens when someone calls to place a food order. Slang.ai's
          ordering flow is link-based: it texts the caller a link to order online. The call ends,
          and the order hasn't been placed — the guest still has to open the link, rebuild their
          order in a web menu, and check out on their own. Meridian closes that gap: the agent takes
          the complete order conversationally on the call, injects it into your Square or Clover POS
          as a real order, and sends a pay-by-text link so the caller pays from their phone.
        </p>

        {/* Why owners use them */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators use Slang.ai
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whySlangAi.map((item) => (
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

        {/* Why they break */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where Slang.ai falls short for order-driven restaurants
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
            Nine categories where Slang.ai's answering service and Meridian's restaurant
            intelligence platform go head to head. Slang.ai details are from slang.ai as of
            August 2026.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Slang.ai
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.slang}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── What $399-599 a Month Buys ────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          What $399-599 a Month Buys — and What It Doesn't
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$399-599</div>
              <p className="text-sm text-[#A1A1A8] mt-1">per month, per location — Core to Premium (as of Aug 2026)</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">+$99-199</div>
              <p className="text-sm text-[#A1A1A8] mt-1">per month for each add-on: Bilingual Support, Private Events/Tripleseat</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">1 link</div>
              <p className="text-sm text-[#A1A1A8] mt-1">standing between the caller and a completed food order</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-2xl md:text-3xl font-bold text-[#EF4444]">
              You pay to answer the call — the order still depends on the guest finishing it alone
            </div>
            <p className="text-sm text-[#A1A1A8] mt-2">
              Answered is not the same as ordered. Only one of those shows up in your POS.
            </p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Slang.ai's pricing is straightforward and published: Core at $399/month per location,
            Premium at $599/month per location, Enterprise by custom quote, with Bilingual Support
            ($99/month) and Private Events with Tripleseat integration ($199/month) as add-ons — all
            as of August 2026. For a reservation-heavy restaurant, that buys a real capability:
            reservations handled end-to-end without a host tied to the phone.
          </p>
          <p>
            For a restaurant where the phone rings with orders, the math is different. A texted
            ordering link moves the work back to the guest at the exact moment they were ready to
            hand it to you. Meridian's agent finishes the job on the call: the complete order,
            taken conversationally, injected into Square or Clover as a real order, with a
            pay-by-text link so the caller pays from their phone. And because Meridian is a
            restaurant intelligence platform, the same subscription includes the analytics layer —
            anomaly detection, revenue forecasting, and multi-location dashboards on top of your
            POS data.
          </p>
        </div>
      </section>

      {/* ── When Slang.ai Still Makes Sense ───────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Slang.ai Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. If you run a{' '}
                  <span className="text-[#F5F5F7] font-medium">reservation-heavy full-service restaurant</span>{' '}
                  — where the phone rings with booking requests, not food orders — Slang.ai is a
                  strong, mature product. Its reservations automation is polished, and its deep
                  integrations with OpenTable, SevenRooms, Yelp, and Fishbowl mean bookings get
                  handled end-to-end without your host stand touching the phone.
                </p>
                <p>
                  VIP call routing, call recordings with summaries, CSAT collection, and a setup
                  process Slang.ai says takes under 30 minutes of staff time are all genuine
                  strengths. If reservations are your phone traffic, it does that job well.
                </p>
                <p>
                  The line is drawn at ordering. If callers want to place food orders — pizza,
                  takeout, delivery — Slang.ai hands them a texted link, and the order lives or
                  dies on whether the guest completes it. Meridian exists for exactly that call:
                  the order gets taken in full, on the phone, and lands in your POS before the
                  caller hangs up.
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
          Available in the US and Canada. One-click POS connect, first month free, no contracts.
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
          Hear the Difference Yourself
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Call +1 380 240 9535 (US) or +1 506 801 7904 (Canada) and order a pizza from the live
          demo line — then book a demo. First month free, no contracts.
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
