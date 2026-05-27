import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Camera,
  Smartphone,
  ShieldAlert,
  AlertTriangle,
  DollarSign,
  MessageSquare,
  Plug,
  CheckCircle2,
  MapPin,
  Target,
  TrendingUp,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'How accurate is Placer.ai compared to actual camera counts?',
    a: 'Placer.ai uses mobile phone panel data and extrapolation models to estimate foot traffic. Independent comparisons show a typical 15-30% variance between Placer estimates and actual door counts. Meridian uses your own cameras to count every person who enters, achieving 95-98% accuracy with modern AI-powered people counting. For daily operational decisions, actual counts will always beat statistical estimates.',
  },
  {
    q: 'Can Meridian do competitive traffic analysis like Placer.ai?',
    a: 'Meridian does not estimate foot traffic at competitor locations — that is Placer.ai\'s strength. Meridian focuses on YOUR store: exact visitor counts, zone-level dwell time, POS-correlated conversion rates, and revenue per visitor. For competitive intelligence, some operators use Placer.ai for market-level trends and Meridian for their own operational data.',
  },
  {
    q: 'Can I use both Placer.ai and Meridian?',
    a: 'Yes, and some multi-location operators do. Placer.ai gives you estimated competitive and market-level traffic trends. Meridian gives you exact visitor counts, POS-linked conversion rates, and revenue per visitor for your own locations. They answer different questions: Placer.ai answers "how does traffic look across the market?" while Meridian answers "what is actually happening in my store right now?"',
  },
  {
    q: 'Is Meridian worth it for a single location?',
    a: 'Absolutely. Placer.ai is priced for enterprise chains and REITs at $1,000+/month. Meridian starts at $490/month and is designed for independent operators with one to twenty locations. You get camera-based visitor counting, POS integration, conversion rates, revenue per visitor, and zone-level analytics — all from day one at a single location.',
  },
  {
    q: 'How fresh is the data compared to Placer.ai?',
    a: 'Placer.ai data is typically delayed 24-48 hours as mobile panel data is aggregated and processed. Meridian provides real-time camera counts and live POS data. You can see how many people are in your store right now, what zone they are in, and what transactions are happening — not what happened two days ago.',
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
    feature: 'Data Source',
    placer: 'Mobile phone panel data (estimated)',
    meridian: 'Your cameras + your POS (actual)',
    winner: 'meridian',
  },
  {
    feature: 'Accuracy',
    placer: 'Estimated — extrapolated from sample panel',
    meridian: '95-98% — real counts from your camera feed',
    winner: 'meridian',
  },
  {
    feature: 'POS Integration',
    placer: 'None — traffic only',
    meridian: 'Native — full POS transaction correlation',
    winner: 'meridian',
  },
  {
    feature: 'Conversion Rate',
    placer: 'Not available (no POS data)',
    meridian: 'Automatic — real-time foot traffic / transactions',
    winner: 'meridian',
  },
  {
    feature: 'Revenue Per Visitor',
    placer: 'Not available',
    meridian: 'Automatic — cross-referenced with every sale',
    winner: 'meridian',
  },
  {
    feature: 'Granularity',
    placer: 'Neighborhood/store-level estimates',
    meridian: 'Zone-level within your store + individual transactions',
    winner: 'meridian',
  },
  {
    feature: 'Competitor Analysis',
    placer: 'Yes — compare traffic to nearby competitors',
    meridian: 'POS benchmarking against industry averages',
    winner: 'placer',
  },
  {
    feature: 'Real-Time',
    placer: 'Data delayed 24-48 hours',
    meridian: 'Real-time camera counts + live POS data',
    winner: 'meridian',
  },
  {
    feature: 'Dwell Time',
    placer: 'Estimated from phone signals',
    meridian: 'Measured from camera AI — actual zone-level dwell',
    winner: 'meridian',
  },
  {
    feature: 'Pricing',
    placer: '$1,000+/mo (enterprise contracts)',
    meridian: '$490/mo — camera AI + POS analytics included',
    winner: 'meridian',
  },
]

/* ── Why Operators Choose Placer.ai ──────────────────── */

const whyPlacer = [
  {
    icon: MapPin,
    label: 'Competitor Intelligence',
    detail: 'See estimated foot traffic at competing locations',
  },
  {
    icon: Smartphone,
    label: 'No Hardware Needed',
    detail: 'Works from mobile phone data — nothing to install',
  },
  {
    icon: TrendingUp,
    label: 'Market-Level Trends',
    detail: 'Broad view of neighborhood and regional traffic patterns',
  },
]

/* ── Where Placer.ai Falls Short ─────────────────────── */

const wherePlacerFallsShort = [
  {
    icon: AlertTriangle,
    label: 'Estimates, not actuals',
    detail:
      'Panel data extrapolation can\'t match actual camera counting at YOUR store',
  },
  {
    icon: ShieldAlert,
    label: 'No POS connection',
    detail:
      'You know roughly how many people visited, but never what they bought',
  },
  {
    icon: Target,
    label: 'No conversion metrics',
    detail:
      'Without POS data, conversion rate and revenue per visitor are impossible',
  },
  {
    icon: DollarSign,
    label: 'Enterprise pricing',
    detail:
      'Starting at $1,000+/mo — built for REITs and chains, not independent operators',
  },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Camera,
    title: 'Mount Your Cameras',
    desc: 'Use existing security cameras or add a $50-150 IP camera. Your data, your store, your accuracy.',
  },
  {
    num: '02',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'One-click OAuth. Square, Toast, Clover, and 75+ more.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Actual Numbers, Not Estimates',
    desc: 'Know exactly who walked in, where they went, how long they stayed, and what they bought.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'Camera Intelligence', to: '/camera-intelligence' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Best Restaurant Analytics Software', to: '/best-analytics-software' },
  { label: 'vs Dor', to: '/vs/dor' },
  { label: 'Foot Traffic Analytics Guide', to: '/foot-traffic-analytics' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsPlacerAiPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Placer.ai: Estimated Traffic vs. Your Actual Data | Meridian"
        description="Placer.ai estimates foot traffic from mobile panel data. Meridian counts actual visitors from your cameras and cross-references with your POS. Which one do you trust for daily decisions?"
        path="/vs/placer-ai"
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
            Meridian vs. Placer.ai:
            <br />
            <span className="text-[#17C5B0]">Estimated Traffic vs. Your Actual Data</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Placer estimates from panel data. Meridian knows from your cameras and your POS.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See Actual Data in Action <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Why Operators Choose Placer.ai ────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          Why Operators Choose Placer.ai
        </h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Placer.ai built its business on a compelling promise: see foot traffic at any location
          without installing anything. For real estate site selection and competitive
          intelligence at the market level, that promise has real value.
        </p>

        {/* Why owners use Placer */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            What draws operators to Placer.ai
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyPlacer.map((item) => (
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

        {/* Where Placer falls short */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where Placer.ai falls short for daily operations
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {wherePlacerFallsShort.map((item) => (
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
            Ten categories where estimated mobile panel data and actual camera + POS data go
            head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Placer.ai
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
                <div
                  className={`px-5 py-3 text-sm ${
                    row.winner === 'placer' ? 'font-medium text-[#1A8FD6]' : 'text-[#A1A1A8]'
                  }`}
                >
                  {row.placer}
                </div>
                <div
                  className={`px-5 py-3 text-sm ${
                    row.winner === 'meridian' ? 'font-medium text-[#17C5B0]' : 'text-[#A1A1A8]'
                  }`}
                >
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost: The Gap Between Estimated and Actual ── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost: The Gap Between Estimated and Actual
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">15-30%</div>
              <p className="text-sm text-[#A1A1A8] mt-1">
                typical variance between Placer estimates and actual camera counts
              </p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$1,000/mo</div>
              <p className="text-sm text-[#A1A1A8] mt-1">
                Placer's starting price for estimates
              </p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">Zero</div>
              <p className="text-sm text-[#A1A1A8] mt-1">
                POS metrics available from any mobile panel provider
              </p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">
              $490/mo for actuals
            </div>
            <p className="text-sm text-[#A1A1A8] mt-2">
              Camera AI + POS analytics — actual counts, actual purchases, actual conversion rates
            </p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Placer.ai's estimates are useful for market-level analysis — where are people
            going across a metro area, which shopping centers are gaining traffic, which
            neighborhoods are growing. But when you need to make staffing decisions for
            tomorrow, when you need to know if last Tuesday's promotion actually drove
            more buyers (not just more visitors), estimates are not enough.
          </p>
          <p>
            The gap between estimated and actual is where operational decisions go wrong.
            A 20% overestimate of foot traffic means your conversion rate looks worse
            than it is. A 20% underestimate means you are understaffing your busiest
            hours. And without POS correlation, you never know if traffic increases
            actually turned into revenue — or just noise.
          </p>
        </div>
      </section>

      {/* ── When Placer.ai Makes Sense ────────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Placer.ai Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. Placer.ai is a strong tool for the right use case. If
                  you are a{' '}
                  <span className="text-[#F5F5F7] font-medium">
                    real estate developer evaluating site selection
                  </span>
                  , a{' '}
                  <span className="text-[#F5F5F7] font-medium">
                    large chain running competitive intelligence across hundreds of locations
                  </span>
                  , or a{' '}
                  <span className="text-[#F5F5F7] font-medium">
                    multi-state operator tracking market-level trends
                  </span>
                  , Placer.ai delivers data you cannot get any other way.
                </p>
                <p>
                  But if your question is "how many people actually walked into MY store
                  today, how long did they stay, and what did they buy?" — that is not a
                  question mobile panel data can answer. That requires your cameras and
                  your POS. That is what Meridian does.
                </p>
                <p>
                  The question is not whether Placer.ai works. The question is whether
                  estimates are good enough for the decisions you need to make every day.
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
          Go from estimated traffic to actual visitor counts and POS-linked conversion
          rates in under an hour.
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
          Your Store. Your Data. Your Answers.
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Stop estimating. Start knowing. Connect cameras and POS in 10 minutes.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Start With Actual Data <ArrowRight className="w-5 h-5" />
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
