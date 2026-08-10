import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Phone,
  MessageSquare,
  Link2,
  DollarSign,
  Globe,
  Layers,
  Mic,
  Plug,
  CheckCircle2,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does Popmenu AI Answering take phone orders?',
    a: 'Not directly. Popmenu\'s AI Answering fields calls 24/7, answers common questions (hours, parking, allergens), and texts the caller a link to Popmenu\'s online ordering or reservations mid-call. The guest then finishes the order themselves on a website. Meridian\'s phone agent takes the complete order conversationally during the call and injects it into your Square or Clover POS as a real order — the caller never has to switch to a website.',
  },
  {
    q: 'How much does Popmenu AI Answering cost?',
    a: 'AI Answering is an add-on priced by Popmenu\'s sales team on top of a base plan. Popmenu\'s published base plans are Starter $179/mo, Essentials $299/mo, and Premier $499/mo (as of August 2026), with roughly 10% off when prepaid annually. Third-party reports put the AI Answering add-on at around $150-$349/mo (reported; quoted by sales). There is no free trial. Meridian pricing is by quote, with the first month free and no contracts.',
  },
  {
    q: 'Can I get Popmenu AI Answering without the Popmenu platform?',
    a: 'No. AI Answering is not a standalone product — it requires Popmenu\'s broader marketing platform (website, menus, marketing suite) as its base. Meridian\'s phone agent is standalone: it connects directly to your existing Square or Clover POS with no platform bundle required.',
  },
  {
    q: 'What is the best Popmenu AI Answering alternative for phone orders?',
    a: 'If your goal is capturing phone orders — not just answering questions — Meridian is built for exactly that. Its AI phone agent answers every call 24/7, takes the full order in conversation, injects it into Square or Clover as a real order, and sends the caller a pay-by-text link. It also includes a POS analytics layer with anomaly detection, revenue forecasting, and multi-location dashboards.',
  },
  {
    q: 'Can I try Meridian\'s phone agent before signing up?',
    a: 'Yes — live, right now. Call +1 380 240 9535 in the US or +1 506 801 7904 in Canada and order a pizza. You\'ll experience the full flow a real caller gets: the agent takes the complete order in conversation and follows up with a pay-by-text link.',
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
    feature: 'Phone Orders',
    popmenu: 'Texts the caller an ordering link mid-call',
    meridian: 'Takes the complete order in the call',
    winner: 'meridian',
  },
  {
    feature: 'POS Integration',
    popmenu: 'Order happens later on Popmenu\'s web flow',
    meridian: 'Order injected directly into Square or Clover',
    winner: 'meridian',
  },
  {
    feature: 'Payment',
    popmenu: 'Guest pays on the website they\'re linked to',
    meridian: 'Pay-by-text link right after the order',
    winner: 'meridian',
  },
  {
    feature: 'Standalone Product',
    popmenu: 'No — requires the Popmenu marketing platform',
    meridian: 'Yes — no platform bundle required',
    winner: 'meridian',
  },
  {
    feature: '24/7 Call Answering',
    popmenu: 'Yes, in a customizable voice',
    meridian: 'Yes, every call answered',
    winner: 'tie',
  },
  {
    feature: 'Voice Customization',
    popmenu: 'Custom voice and greetings',
    meridian: 'Conversational AI agent',
    winner: 'popmenu',
  },
  {
    feature: 'Analytics',
    popmenu: 'Call monitoring via the Popmenu for Owners app',
    meridian: 'Anomaly detection, forecasting, multi-location dashboards',
    winner: 'meridian',
  },
  {
    feature: 'Pricing Transparency',
    popmenu: 'Add-on quoted by sales, atop $179-$499/mo plans',
    meridian: 'By quote — first month free, no contracts',
    winner: 'meridian',
  },
  {
    feature: 'Free Trial',
    popmenu: 'None',
    meridian: 'First month free',
    winner: 'meridian',
  },
  {
    feature: 'Try Before You Buy',
    popmenu: 'Sales demo',
    meridian: 'Live demo line — call and order a pizza',
    winner: 'meridian',
  },
]

/* ── "Why Operators Use Popmenu" Reasons ───────────── */

const whyPopmenu = [
  { icon: Globe, label: 'Full Marketing Suite', detail: 'Strong websites, photo-rich menus, and remarketing in one platform' },
  { icon: Mic, label: 'Custom Voice', detail: 'Customizable greetings and voice options for the answering line' },
  { icon: Layers, label: 'One Vendor', detail: 'If you already want the platform, the answering add-on slots in naturally' },
]

const whyTheyBreak = [
  { icon: Link2, label: 'A link is not an order', detail: 'The AI texts guests a link — the caller still has to finish the order themselves on a website' },
  { icon: Plug, label: 'No POS order injection', detail: 'The call itself never places an order in your Square or Clover POS' },
  { icon: Layers, label: 'Platform required', detail: 'You must buy a $179-$499/mo base plan (as of August 2026) before the answering add-on' },
  { icon: DollarSign, label: 'Opaque add-on pricing', detail: 'Sales-quoted; third parties report roughly $150-$349/mo — and there\'s no free trial' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Square or Clover',
    desc: 'One-click POS connect. Minutes, not weeks — no website rebuild, no platform migration.',
  },
  {
    num: '02',
    icon: Phone,
    title: 'The Agent Answers Every Call',
    desc: '24/7 coverage. The AI takes the complete order conversationally and injects it into your POS as a real order.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Caller Pays by Text',
    desc: 'A pay-by-text link lands on the guest\'s phone right after the order. No website detour, no abandoned carts.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'vs Slang.ai', to: '/vs/slang-ai' },
  { label: 'vs SoundHound Smart Answering', to: '/vs/soundhound-smart-answering' },
  { label: 'vs Nory', to: '/vs/nory' },
  { label: 'vs Marty by Lavu', to: '/vs/marty-by-lavu' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Square Integration', to: '/integrations/square' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsPopmenuAnsweringPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Popmenu AI Answering: Orders, Not Links | Meridian"
        description="Popmenu's AI answers questions and texts callers an ordering link. Meridian's agent takes the whole order in the call and puts it in your Square or Clover POS."
        path="/vs/popmenu-answering"
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
            Meridian vs. Popmenu AI Answering:
            <br />
            <span className="text-[#17C5B0]">Take the Order — Don't Text a Link</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Popmenu's AI answers the phone and texts your guest a link to order online. Meridian's
            agent takes the entire order in the call and puts it straight into your POS.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See the Difference — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
          <p className="text-sm text-[#A1A1A8] mt-4">
            Or hear it yourself: call <span className="text-[#F5F5F7] font-medium">+1 380 240 9535</span> (US)
            or <span className="text-[#F5F5F7] font-medium">+1 506 801 7904</span> (Canada) and order a pizza.
          </p>
        </div>
      </section>

      {/* ── The Link-Instead-of-Order Trap ────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">Answering the Phone Isn't the Same as Taking the Order</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-4">
          Popmenu built its name on restaurant marketing — websites, interactive photo menus,
          remarketing — and its AI Answering add-on extends that platform to the phone line. It
          fields calls 24/7 in a custom voice, answers common questions about hours, parking, and
          allergens, and texts guests a link to order or reserve mid-call. Owners monitor it all
          through the Popmenu for Owners app.
        </p>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          That's genuinely useful if what you want is a marketing platform with a phone-answering
          layer. But look closely at what happens to the actual order: the AI doesn't take it. It
          hands the caller a link and hopes they finish the transaction on a website. Every hungry
          caller who wanted to just say their order out loud now has to hang up, open a browser,
          navigate a menu, and check out on their own.
        </p>

        {/* Why owners use it */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators choose Popmenu AI Answering
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyPopmenu.map((item) => (
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

        {/* Why it breaks */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where Popmenu AI Answering falls short
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
            Ten categories where Popmenu's AI Answering add-on and Meridian's AI phone agent go
            head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Popmenu AI Answering
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.popmenu}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
          <p className="text-xs text-[#A1A1A8] text-center mt-4">
            Popmenu base-plan pricing from Popmenu's published pricing as of August 2026. AI
            Answering add-on pricing is not published; the $150-$349/mo range is reported by third
            parties and quoted by sales.
          </p>
        </div>
      </section>

      {/* ── The Real Price of the Add-On ──────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Real Price of an "Add-On"
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$179-$499</div>
              <p className="text-sm text-[#A1A1A8] mt-1">per month for the required base plan (as of August 2026)</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">+ sales quote</div>
              <p className="text-sm text-[#A1A1A8] mt-1">for the AI Answering add-on itself (reported ~$150-$349/mo)</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">0</div>
              <p className="text-sm text-[#A1A1A8] mt-1">orders placed in your POS by the call itself</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-3xl md:text-4xl font-bold text-[#EF4444]">= Two subscriptions to answer the phone — and the caller still orders on a website</div>
            <p className="text-sm text-[#A1A1A8] mt-2">The answering product can't be bought alone, and it can't complete an order alone either</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Because AI Answering is an add-on, the entry price is never just the add-on. You need
            a Popmenu base plan — Starter at $179/mo, Essentials at $299/mo, or Premier at $499/mo
            as of August 2026 (roughly 10% off if prepaid annually) — before the answering product
            is even on the table. The add-on itself is priced by the sales team; third-party
            reports place it around $150-$349/mo. There is no free trial to sanity-check any of it.
          </p>
          <p>
            Meridian inverts that model. The phone agent is standalone: it connects to the Square
            or Clover POS you already run, in minutes, with one-click connect. It takes the whole
            order in the call, injects it into your POS as a real order, and sends the caller a
            pay-by-text link. First month free, no contracts, and you can test the entire
            experience right now by calling the live demo line and ordering a pizza.
          </p>
        </div>
      </section>

      {/* ── When Popmenu Still Makes Sense ────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Popmenu AI Answering Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. Popmenu's core marketing suite is genuinely strong — polished
                  websites, interactive menus with photos, and remarketing tools that many
                  restaurants get real value from. If you already want that full platform, adding
                  AI Answering on top is a natural fit: one vendor, one dashboard, and a
                  customizable voice greeting your guests.
                </p>
                <p>
                  It also fits if your phone problem is mostly{' '}
                  <span className="text-[#F5F5F7] font-medium">questions, not orders</span> — hours,
                  parking, allergens, private events. An AI that answers those and nudges guests
                  toward your online ordering link handles that job.
                </p>
                <p>
                  But if the reason your phone matters is{' '}
                  <span className="text-[#F5F5F7] font-medium">revenue — callers who want to place an order right now</span> —
                  then a text-me-a-link flow leaves the hardest part to the guest. Meridian exists
                  for that moment: the order gets taken in the call, lands in your Square or Clover
                  POS, and gets paid by text. No website detour, no platform bundle.
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
          No platform migration, no website rebuild. Meridian connects to the POS you already have
          and starts answering calls — in the US and Canada.
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
        <p className="text-[#A1A1A8] text-sm text-center mt-10 max-w-2xl mx-auto">
          And because Meridian is an intelligence platform, not just a phone line, the same
          subscription includes POS analytics: anomaly detection, revenue forecasting, and
          multi-location dashboards on top of your Square or Clover data.
        </p>
      </section>

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Hear a Complete Phone Order, Live
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Call <span className="text-[#F5F5F7] font-medium">+1 380 240 9535</span> (US) or{' '}
          <span className="text-[#F5F5F7] font-medium">+1 506 801 7904</span> (Canada) and order a
          pizza from the demo line. Then connect your Square or Clover in minutes. First month
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
