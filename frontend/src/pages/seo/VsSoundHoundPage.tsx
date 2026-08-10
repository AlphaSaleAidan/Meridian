import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  ShieldAlert,
  Building2,
  MessageSquare,
  Plug,
  Phone,
  Mic,
  Layers,
  CreditCard,
  PhoneCall,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does SoundHound Smart Answering take phone orders?',
    a: 'Smart Answering is SoundHound\'s FAQ and answering tier — it handles common guest inquiries like hours, location, menu items, and order status. Full conversational phone ordering is a separate SoundHound product (Dynamic Interaction) aimed at enterprise brands. Meridian\'s phone agent takes the complete order on the call and injects it directly into your Square or Clover POS as a real order, with a pay-by-text link sent to the caller.',
  },
  {
    q: 'How much does SoundHound Smart Answering cost?',
    a: 'SoundHound does not publish restaurant pricing. Third-party reports (as of August 2026) put its restaurant voice AI at roughly $249-$499 per month for a single location, with volume discounts for multi-location groups — but exact pricing is quoted by sales. Meridian pricing is by quote, with the first month free and no contracts.',
  },
  {
    q: 'Is SoundHound a good fit for an independent restaurant?',
    a: 'SoundHound has serious voice-AI pedigree and its restaurant stack is built for larger chains and enterprise deployments. Third-party reviewers note it is often not the fit for 1-3 location operators — pricing and deployment run through a sales process rather than self-serve. Meridian is built the other way around: independents connect their Square or Clover themselves in minutes.',
  },
  {
    q: 'What are the alternatives to SoundHound Smart Answering?',
    a: 'For independents who want more than answered FAQs, Meridian is an AI phone agent that takes the complete order into your POS, sends a pay-by-text link, and includes a POS analytics layer with anomaly detection and revenue forecasting. You can hear it live before signing anything: call +1 380 240 9535 in the US or +1 506 801 7904 in Canada and order a pizza.',
  },
  {
    q: 'Does Meridian replace my POS?',
    a: 'No. Meridian connects to your existing Square or Clover POS with one-click connect, in minutes. The phone agent injects orders directly into that POS as real orders, and the analytics layer — anomaly detection, revenue forecasting, multi-location dashboards — runs on top of your existing data.',
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
    soundhound: 'Answers FAQs (hours, menu, order status); full ordering is a separate enterprise product',
    meridian: 'Takes the complete order conversationally, 24/7',
    winner: 'meridian',
  },
  {
    feature: 'POS Injection',
    soundhound: 'Integrates with POS systems (specific list not public)',
    meridian: 'Order lands in Square or Clover as a real order',
    winner: 'meridian',
  },
  {
    feature: 'Payment Collection',
    soundhound: 'Not part of the Smart Answering tier',
    meridian: 'Pay-by-text link after the order; caller pays from their phone',
    winner: 'meridian',
  },
  {
    feature: 'Pricing',
    soundhound: '~$249-$499/mo single location (reported; quoted by sales)',
    meridian: 'By quote — first month free, no contracts',
    winner: 'meridian',
  },
  {
    feature: 'Getting Started',
    soundhound: 'Sales process; enterprise-style deployment',
    meridian: 'Self-serve one-click POS connect — minutes, not weeks',
    winner: 'meridian',
  },
  {
    feature: 'Built For',
    soundhound: 'Larger restaurant chains and enterprise brands',
    meridian: 'Independents and small multi-location groups',
    winner: 'meridian',
  },
  {
    feature: 'Analytics Included',
    soundhound: 'Not the focus of the answering tier',
    meridian: 'Anomaly detection, revenue forecasting, multi-location dashboards',
    winner: 'meridian',
  },
  {
    feature: 'Try It Before Buying',
    soundhound: 'Demo arranged through sales',
    meridian: 'Live demo line: +1 380 240 9535 (US), +1 506 801 7904 (Canada)',
    winner: 'meridian',
  },
  {
    feature: 'Contracts',
    soundhound: 'Not published',
    meridian: 'No contracts; first month free',
    winner: 'meridian',
  },
]

/* ── "Why Operators Consider SoundHound" Reasons ───── */

const whySoundHound = [
  { icon: Mic, label: 'Voice-AI Pedigree', detail: 'SoundHound has been building voice technology for over a decade' },
  { icon: Building2, label: 'Enterprise Scale', detail: 'Strong fit for large chains that need enterprise-scale deployment' },
  { icon: Layers, label: 'Broad Platform', detail: 'A multi-industry voice platform, not just a restaurant tool' },
]

const whyTheyBreak = [
  { icon: PhoneCall, label: 'Answering is not ordering', detail: 'Smart Answering handles FAQs — full phone ordering is a separate enterprise product (Dynamic Interaction)' },
  { icon: ShieldAlert, label: 'Sales-quoted everything', detail: 'No published pricing, no self-serve signup — every step runs through a sales process' },
  { icon: Building2, label: 'Built for chains', detail: 'Third-party reviewers note it is often not the fit for 1-3 location operators' },
  { icon: Plug, label: 'POS list not public', detail: 'It integrates with POS systems, but the specific list is not published — you find out in the sales call' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'One-click connect for Square or Clover. Self-serve, in minutes — no sales call required to get started.',
  },
  {
    num: '02',
    icon: Phone,
    title: 'The Phone Agent Goes Live',
    desc: 'Meridian answers every call 24/7, takes the complete order conversationally, and injects it into your POS as a real order.',
  },
  {
    num: '03',
    icon: CreditCard,
    title: 'Callers Pay by Text',
    desc: 'After the order, the caller gets a pay-by-text link and pays from their phone. Analytics on every order flows into your dashboard.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'vs Slang.ai', to: '/vs/slang-ai' },
  { label: 'vs Popmenu Answering', to: '/vs/popmenu-answering' },
  { label: 'vs Nory', to: '/vs/nory' },
  { label: 'vs Marty by Lavu', to: '/vs/marty-by-lavu' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Square Integration', to: '/integrations/square' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsSoundHoundPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. SoundHound: Built for Independents | Meridian"
        description="SoundHound Smart Answering answers guest FAQs and is built for chains, quoted by sales. Meridian is self-serve for independents — complete phone orders straight into Square or Clover."
        path="/vs/soundhound-smart-answering"
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
            Meridian vs. SoundHound Smart Answering:
            <br />
            <span className="text-[#17C5B0]">Enterprise Answering vs. Self-Serve Ordering</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            SoundHound's restaurant stack is built for chains and quoted by sales. Meridian is
            self-serve for independents — and the phone agent takes the whole order, not just the
            question.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            Hear It Take a Real Order — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── The Smart Answering Question ──────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          What Smart Answering Actually Does
        </h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-4">
          SoundHound Smart Answering is a voice AI for inbound business calls: it answers the
          phone and handles common guest inquiries — hours, location, menu items, order status.
          For a busy restaurant, that alone removes a real chunk of interruptions. And SoundHound
          is not a startup experimenting with voice: the company has been building voice
          technology for over a decade and runs a broad, multi-industry platform.
        </p>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          The catch is who it was built for — and where answering stops. SoundHound's restaurant
          products target larger chains and enterprise brands, with pricing quoted by sales
          (third-party reports put single-location restaurant voice AI at roughly $249-$499 per
          month as of August 2026, but there is no published price). And Smart Answering is the
          FAQ tier: full conversational phone ordering lives in a separate SoundHound product,
          Dynamic Interaction, aimed at enterprise brands. If you run one to three locations and
          the phone rings with orders — not just questions — that distinction matters.
        </p>

        {/* Why operators consider it */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators consider SoundHound
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whySoundHound.map((item) => (
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
            Why it breaks down for independents
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
            Nine categories where SoundHound Smart Answering and Meridian's phone agent go head
            to head. SoundHound facts are third-party reported as of August 2026; where nothing
            is published, we say so.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                SoundHound Smart Answering
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.soundhound}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Enterprise Gap ────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Enterprise Gap
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$249-$499</div>
              <p className="text-sm text-[#A1A1A8] mt-1">reported monthly range for a single location (third-party reported; quoted by sales)</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">2 products</div>
              <p className="text-sm text-[#A1A1A8] mt-1">answering (Smart Answering) and full phone ordering (Dynamic Interaction) are separate tiers</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">0</div>
              <p className="text-sm text-[#A1A1A8] mt-1">published prices or self-serve signup — every answer comes from a sales call</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-2xl md:text-3xl font-bold text-[#EF4444]">= A chain-scale sales motion for an independent's problem</div>
            <p className="text-sm text-[#A1A1A8] mt-2">The technology is real — the packaging assumes you have a procurement team</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            None of this is a knock on the technology. SoundHound's voice stack is genuinely
            strong, and for a 200-location brand that wants a vendor to run an enterprise-scale
            deployment across reservation systems, POS systems, and event software, the sales-led
            model is the point. Third-party reviewers consistently frame it that way: built for
            chains, and often not the fit for 1-3 location operators.
          </p>
          <p>
            But an independent pizzeria's phone problem is not a procurement problem. The phone
            rings at 6:40pm on a Friday, whoever is closest picks it up or nobody does, and the
            caller wants to place an order — not ask when you close. An answering tier that
            handles the FAQ and hands off the order is solving the smaller half of that call.
            Meridian's phone agent answers every call 24/7, takes the complete order
            conversationally, injects it into your Square or Clover as a real order, and sends
            the caller a pay-by-text link so they pay from their phone. No sales call to find out
            whether your POS is on the list — you connect it yourself in minutes.
          </p>
        </div>
      </section>

      {/* ── When SoundHound Still Makes Sense ─────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When SoundHound Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. SoundHound has been in voice technology for over a decade —
                  that pedigree is real, and it shows. If you are a{' '}
                  <span className="text-[#F5F5F7] font-medium">large restaurant chain</span> that
                  needs enterprise-scale deployment, a vendor relationship with a sales and
                  support organization behind it, and a{' '}
                  <span className="text-[#F5F5F7] font-medium">broad multi-industry platform</span>{' '}
                  that extends beyond restaurants, SoundHound is a serious contender — and its
                  separate Dynamic Interaction product exists precisely for enterprise brands
                  that want full voice ordering at that scale.
                </p>
                <p>
                  Where the calculus flips is at independent scale. If you run one to three
                  locations, your POS is Square or Clover, and the calls you are missing are
                  orders rather than questions, you are paying an enterprise sales motion for an
                  answering tier — while the ordering tier sits in a different product bracket
                  entirely.
                </p>
                <p>
                  The question is not whether SoundHound's voice AI works. It is whether an
                  FAQ-answering tier, priced by sales for chain deployments, is the right shape
                  for a phone that rings with orders.
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
          No sales cycle, no deployment project. Connect your POS yourself and the phone agent is
          taking complete orders in minutes — in the US and Canada.
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
          Don't Take Our Word for It — Call the Demo Line
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Hear Meridian take a complete pizza order right now: +1 380 240 9535 in the US, or
          +1 506 801 7904 in Canada. Then connect your Square or Clover in minutes. First month
          free, no contracts.
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
