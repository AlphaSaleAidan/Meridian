import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Camera,
  ShieldCheck,
  Eye,
  EyeOff,
  Wifi,
  Thermometer,
  Hand,
  Activity,
  TrendingUp,
  DollarSign,
  Users,
  Clock,
  MapPin,
  BarChart3,
  Plug,
  Zap,
  CheckCircle2,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Do I need to replace my existing counters?',
    a: 'No. You can run Meridian alongside existing systems. But most operators find that once they have camera AI + POS cross-referencing, standalone counters become redundant.',
  },
  {
    q: 'Is camera counting as accurate as thermal sensors?',
    a: 'More accurate. Camera-based AI counting achieves 95-98% accuracy vs 85-90% for thermal sensors. It also handles groups, distinguishes entries from exits, and works across multiple zones — not just the door.',
  },
  {
    q: 'What if I already have Dor / RetailNext / another counter?',
    a: "You can keep them running. Meridian adds the POS correlation layer that standalone counters can't provide. Most operators phase out the standalone counter within 3 months because Meridian covers counting + analytics.",
  },
  {
    q: 'How much does it cost?',
    a: 'Camera intelligence is included in the Premium plan at $490/month — which also includes POS analytics, anomaly detection, forecasting, and customer segmentation. Compare that to $299/mo for Dor (counting only) or $1,000+/mo for Placer.ai (estimated counts, no POS).',
  },
  {
    q: 'What makes Meridian different from other camera analytics?',
    a: "Cross-referencing. Other camera analytics tools count people. Meridian counts people AND connects that data to your POS transactions in real time. That gives you conversion rates, revenue per visitor, and zone-level profitability — metrics that don't exist without both data sources.",
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

/* ── Counting Methods Comparison ─────────────────────── */

const countingMethods = [
  {
    method: 'Manual (Clicker)',
    icon: Hand,
    accuracy: '60-70%',
    cost: 'Free',
    posIntegration: 'None',
    conversionRate: 'No',
    revenuePerVisitor: 'No',
    highlight: false,
  },
  {
    method: 'Infrared Beam',
    icon: Activity,
    accuracy: '80-85%',
    cost: '$200-500 hardware',
    posIntegration: 'None',
    conversionRate: 'No',
    revenuePerVisitor: 'No',
    highlight: false,
  },
  {
    method: 'Thermal Sensor (Dor, etc.)',
    icon: Thermometer,
    accuracy: '85-90%',
    cost: '$500+ hardware + $299/mo',
    posIntegration: 'Basic CSV export',
    conversionRate: 'Manual only',
    revenuePerVisitor: 'No',
    highlight: false,
  },
  {
    method: 'Wi-Fi / Bluetooth Probing',
    icon: Wifi,
    accuracy: '70-80%',
    cost: '$50-200/mo',
    posIntegration: 'None',
    conversionRate: 'No',
    revenuePerVisitor: 'No',
    highlight: false,
  },
  {
    method: 'Camera AI (standalone)',
    icon: Eye,
    accuracy: '95-98%',
    cost: '$0-50/mo',
    posIntegration: 'Varies',
    conversionRate: 'Manual only',
    revenuePerVisitor: 'No',
    highlight: false,
  },
  {
    method: 'Meridian Camera Intelligence',
    icon: Camera,
    accuracy: '95-98%',
    cost: 'Included in $490/mo plan',
    posIntegration: 'Native (75+ POS)',
    conversionRate: 'Automatic + real-time',
    revenuePerVisitor: 'Automatic + real-time',
    highlight: true,
  },
]

/* ── Cross-Referencing Gap ───────────────────────────── */

const countersGive = [
  '500 people walked in today',
  'Tuesday is your busiest day',
  'Traffic is up 12% this month',
]

const crossRefGives = [
  '500 people walked in, 340 bought something, average spend was $18.50, revenue per visitor was $12.58',
  'Tuesday has 500 visitors but 58% conversion. Wednesday has 380 visitors but 74% conversion — Wednesday is more profitable per visitor',
  'Traffic is up 12% but conversion dropped 8%, net revenue per visitor is actually down. Your traffic increase is hiding a service problem.',
]

/* ── Case Study Cards ────────────────────────────────── */

const caseStudies = [
  {
    title: 'The Lunch Rush That Wasn’t',
    body: 'A QSR saw 400 visitors between 11am-1pm. Conversion rate: 61%. That means 156 people walked in, looked at the line, and left. After adjusting staffing and adding an express ordering lane, conversion hit 78% — adding $2,100/week without a single new visitor.',
    stat: '+$2,100/wk',
    icon: Clock,
  },
  {
    title: 'The Dead Zone',
    body: 'Camera heatmaps showed the back dining area drew 8% of foot traffic. POS cross-reference revealed it generated 3% of revenue. Revenue per square foot: $4/day vs $48/day at the counter. The operator converted it to a grab-and-go display — revenue per square foot jumped to $31/day.',
    stat: '$4 → $31/sqft',
    icon: MapPin,
  },
  {
    title: 'The Staff Gap',
    body: 'Shift A converted 72% of foot traffic. Shift B converted 54% with similar traffic volume. The difference: $840/week. Camera + POS data pinpointed that Shift B had 23% longer greeting-to-order time. Training fixed it in two weeks.',
    stat: '+$840/wk',
    icon: Users,
  },
]

/* ── Privacy Cards ───────────────────────────────────── */

const privacyCards = [
  {
    icon: EyeOff,
    title: 'Anonymous Counting Only',
    desc: 'Meridian counts bodies, not faces. No facial recognition, no biometric data, no individual tracking. Every person is a number, never an identity.',
  },
  {
    icon: ShieldCheck,
    title: 'PIPEDA & CCPA Compliant',
    desc: 'Built for privacy regulations from day one. No personally identifiable information is collected, stored, or transmitted at any point in the pipeline.',
  },
  {
    icon: Activity,
    title: 'Data Stays on Your Network',
    desc: 'Camera feeds are processed locally. Only anonymized aggregate counts and zone-level metrics are sent to the Meridian dashboard — never raw footage.',
  },
]

/* ── Making the Switch Steps ─────────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Camera,
    title: 'Connect Your Cameras',
    desc: 'Point existing security cameras at entry zones and key areas. No new hardware required — Meridian works with IP cameras you already own.',
  },
  {
    num: '02',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'Authorize Square, Toast, Clover, or any of 75+ POS systems. One-click OAuth, under 5 minutes.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Cross-Referenced Intelligence in 24 Hours',
    desc: 'Conversion rates, revenue per visitor, zone profitability, and staff performance metrics — all delivered automatically within a day.',
  },
]

/* ── Internal Links ──────────────────────────────────── */

const relatedPages = [
  { label: 'Camera Intelligence', to: '/camera-intelligence' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Foot Traffic Analytics Guide', to: '/blog/restaurant-foot-traffic-analytics-guide' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsFootTrafficCountersPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Foot Traffic Counters: Why Counting People Isn't Enough | Meridian"
        description="Infrared, thermal, Wi-Fi — they all count people. None of them know what those people bought. Meridian cross-references camera AI with your POS to turn foot traffic into revenue intelligence."
        path="/vs/foot-traffic-counters"
        jsonLd={faqJsonLd}
      />

      {/* ── Section 1: Hero ──────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">
            Category Comparison
          </p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Foot Traffic Counters vs. Revenue Intelligence:
            <br />
            <span className="text-[#17C5B0]">The Number That Actually Matters</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Every counter tells you how many. None of them tell you why it matters.
            Meridian is the first to cross-reference camera AI with POS data.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See Cross-Referenced Intelligence — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Section 2: The Counting Methods ──────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            The Counting Methods
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-10">
            Six ways to count foot traffic. Only one connects that count to what actually happened at the register.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.4fr_0.8fr_1fr_0.9fr_0.9fr_0.9fr] min-w-[900px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Method
              </div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Accuracy
              </div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Cost
              </div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                POS Integration
              </div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Conversion Rate
              </div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Revenue / Visitor
              </div>
            </div>
            {/* Rows */}
            {countingMethods.map((row, i) => (
              <div
                key={row.method}
                className={`grid grid-cols-[1.4fr_0.8fr_1fr_0.9fr_0.9fr_0.9fr] min-w-[900px] ${
                  row.highlight
                    ? 'bg-[#17C5B0]/5 border-l-2 border-l-[#17C5B0]'
                    : i % 2 === 0
                    ? 'bg-[#0A0A0B]'
                    : 'bg-[#111113]/50'
                } ${i < countingMethods.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}
              >
                <div className={`px-4 py-3 text-sm font-medium flex items-center gap-2 ${row.highlight ? 'text-[#17C5B0]' : ''}`}>
                  <row.icon className={`w-4 h-4 shrink-0 ${row.highlight ? 'text-[#17C5B0]' : 'text-[#A1A1A8]'}`} />
                  {row.method}
                </div>
                <div className={`px-4 py-3 text-sm ${row.highlight ? 'text-[#17C5B0] font-medium' : 'text-[#A1A1A8]'}`}>
                  {row.accuracy}
                </div>
                <div className={`px-4 py-3 text-sm ${row.highlight ? 'text-[#17C5B0] font-medium' : 'text-[#A1A1A8]'}`}>
                  {row.cost}
                </div>
                <div className={`px-4 py-3 text-sm ${row.highlight ? 'text-[#17C5B0] font-medium' : 'text-[#A1A1A8]'}`}>
                  {row.posIntegration}
                </div>
                <div className={`px-4 py-3 text-sm ${row.highlight ? 'text-[#17C5B0] font-medium' : 'text-[#A1A1A8]'}`}>
                  {row.conversionRate}
                </div>
                <div className={`px-4 py-3 text-sm ${row.highlight ? 'text-[#17C5B0] font-medium' : 'text-[#A1A1A8]'}`}>
                  {row.revenuePerVisitor}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 3: The Cross-Referencing Gap ─────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          The Number That Changes Everything
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Counting people is step one. Knowing what those people did is where revenue intelligence begins.
        </p>
        <div className="grid md:grid-cols-2 gap-6">
          {/* Left: What Counters Give You */}
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-lg bg-[#A1A1A8]/10 flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-[#A1A1A8]" />
              </div>
              <h3 className="text-lg font-semibold text-[#A1A1A8]">What Counters Give You</h3>
            </div>
            <div className="space-y-4">
              {countersGive.map((item, i) => (
                <div
                  key={i}
                  className="bg-[#0A0A0B] border border-[#1F1F23] rounded-lg p-4"
                >
                  <p className="text-sm text-[#A1A1A8] leading-relaxed italic">
                    &ldquo;{item}&rdquo;
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Right: What Cross-Referencing Gives You */}
          <div className="bg-[#0D1F1D] border border-[#17C5B0]/20 rounded-xl p-6 md:p-8">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-9 h-9 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                <TrendingUp className="w-4 h-4 text-[#17C5B0]" />
              </div>
              <h3 className="text-lg font-semibold text-[#17C5B0]">What Cross-Referencing Gives You</h3>
            </div>
            <div className="space-y-4">
              {crossRefGives.map((item, i) => (
                <div
                  key={i}
                  className="bg-[#0A0A0B]/60 border border-[#17C5B0]/10 rounded-lg p-4"
                >
                  <p className="text-sm text-[#F5F5F7] leading-relaxed">
                    &ldquo;{item}&rdquo;
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 4: Real Examples ─────────────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            What Operators Discover When They Cross-Reference
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
            The insights that only exist when camera AI meets POS data.
          </p>
          <div className="grid md:grid-cols-3 gap-6">
            {caseStudies.map((study) => (
              <div
                key={study.title}
                className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 flex flex-col"
              >
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                    <study.icon className="w-5 h-5 text-[#17C5B0]" />
                  </div>
                  <span className="text-sm font-bold text-[#17C5B0] bg-[#17C5B0]/10 px-3 py-1 rounded-full">
                    {study.stat}
                  </span>
                </div>
                <h3 className="text-lg font-semibold mb-3">{study.title}</h3>
                <p className="text-sm text-[#A1A1A8] leading-relaxed flex-1">
                  {study.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Section 5: Privacy First ─────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          No Facial Recognition. No Individual Tracking. Just Counts.
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Camera intelligence without the privacy concerns. Designed for compliance from the ground up.
        </p>
        <div className="grid sm:grid-cols-3 gap-6">
          {privacyCards.map((card) => (
            <div
              key={card.title}
              className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6"
            >
              <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center mb-4">
                <card.icon className="w-5 h-5 text-[#17C5B0]" />
              </div>
              <h3 className="text-base font-semibold mb-2">{card.title}</h3>
              <p className="text-sm text-[#A1A1A8] leading-relaxed">{card.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Section 6: Making the Switch ─────────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            Making the Switch
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
            No new hardware. No complex installation. Cross-referenced intelligence in 24 hours.
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
        </div>
      </section>

      {/* ── Section 7: CTA ───────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Stop Counting. Start Knowing.
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Camera AI + POS analytics. The metrics that matter. First month free.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Start Your Free Month <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* ── Section 8: FAQ ───────────────────────────────── */}
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

      {/* ── Section 9: Internal Links ────────────────────── */}
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
