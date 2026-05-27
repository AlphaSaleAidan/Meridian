import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  ShieldAlert,
  DollarSign,
  Building2,
  MessageSquare,
  Search,
  Plug,
  CheckCircle2,
  TrendingUp,
  Eye,
  Layers,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does Meridian replace Square?',
    a: 'No. Meridian connects to Square and adds AI analytics on top. You keep Square as your POS — Meridian adds forecasting, anomaly detection, and multi-location intelligence.',
  },
  {
    q: "What does Meridian see that Square doesn't?",
    a: "AI-powered anomaly detection (theft, void spikes, comp abuse), predictive revenue forecasting, customer behavior segmentation, cross-location benchmarking, and automated alerts. Square shows raw numbers — Meridian tells you what they mean.",
  },
  {
    q: 'How do I connect Square to Meridian?',
    a: "One-click OAuth in Square's app marketplace. No API keys, no developer setup. Takes under 3 minutes and your full transaction history is imported automatically.",
  },
  {
    q: "I only have one Square location — is it worth it?",
    a: "If you're doing over $400K/year, the anomaly detection and labor optimization typically save 3-5x the monthly cost. For multi-location, the cross-location insights alone justify it.",
  },
  {
    q: 'Will this slow down my Square terminal?',
    a: "Not at all. Meridian reads data from Square's API in the background. Zero impact on your POS terminal performance or checkout speed.",
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
    feature: 'Reporting',
    square: 'Pre-built sales & inventory reports',
    meridian: 'AI-generated insights + custom reports',
    winner: 'meridian',
  },
  {
    feature: 'Anomaly Detection',
    square: 'None — manual review only',
    meridian: 'Real-time alerts for voids, theft, comp abuse',
    winner: 'meridian',
  },
  {
    feature: 'Forecasting',
    square: 'None',
    meridian: 'AI/ML revenue + demand forecasting',
    winner: 'meridian',
  },
  {
    feature: 'Multi-Location',
    square: 'Basic multi-location overview',
    meridian: 'Cross-location benchmarking + ranking',
    winner: 'meridian',
  },
  {
    feature: 'Customer Insights',
    square: 'Purchase history per customer',
    meridian: 'AI segmentation, churn prediction, LTV scoring',
    winner: 'meridian',
  },
  {
    feature: 'Labor Analytics',
    square: 'Timecard reports',
    meridian: 'Labor cost optimization + scheduling recommendations',
    winner: 'meridian',
  },
  {
    feature: 'Menu/Product Analysis',
    square: 'Top sellers by quantity',
    meridian: 'Profit margin analysis + pricing optimization',
    winner: 'meridian',
  },
  {
    feature: 'Alerts',
    square: 'Daily summary email',
    meridian: 'Real-time configurable alerts (SMS, email, dashboard)',
    winner: 'meridian',
  },
  {
    feature: 'Industry Benchmarks',
    square: 'None',
    meridian: 'Compare your metrics to industry and local averages',
    winner: 'meridian',
  },
  {
    feature: 'Data Retention',
    square: 'Limited export history',
    meridian: 'Unlimited history with year-over-year trends',
    winner: 'meridian',
  },
]

/* ── Why Operators Use Square Dashboard ───────────── */

const whySquare = [
  { icon: DollarSign, label: 'Free with Square', detail: 'Included in your Square subscription at no extra charge' },
  { icon: Layers, label: 'Clean Interface', detail: 'Simple, well-designed reports that are easy to read' },
  { icon: Plug, label: 'Integrated', detail: 'Data flows directly from your POS without setup' },
]

const whySquareFallsShort = [
  { icon: TrendingUp, label: 'No predictive analytics', detail: "You see what sold — not what will sell tomorrow" },
  { icon: ShieldAlert, label: 'No anomaly alerts', detail: 'Theft and fraud patterns go unnoticed for weeks' },
  { icon: Eye, label: 'Surface-level insights', detail: "Totals and averages, but no 'why' behind the numbers" },
  { icon: Building2, label: 'Limited for multi-location', detail: 'No cross-store benchmarking or performance ranking' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Square',
    desc: "One-click OAuth from Square's app marketplace. Under 3 minutes, zero technical setup.",
  },
  {
    num: '02',
    icon: Search,
    title: 'Meridian Learns Your Business',
    desc: 'AI analyzes your complete Square transaction history — products, customers, patterns, anomalies.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Insights in 24 Hours',
    desc: 'Revenue forecasts, anomaly alerts, customer segmentation — all running automatically alongside Square.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Square Integration', to: '/integrations/square' },
  { label: 'vs Spreadsheets', to: '/vs/spreadsheets' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsSquareAnalyticsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Square Dashboard: Beyond Basic Sales Reports | Meridian"
        description="Square Dashboard shows you sales totals. Meridian shows you why they're changing — and what to do about it. See the gap between basic and intelligent analytics."
        path="/vs/square-analytics"
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
            Meridian vs. Square Dashboard:
            <br />
            <span className="text-[#17C5B0]">Beyond Basic Sales Reports</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Square Dashboard shows you sales totals. Meridian shows you why they are changing
            &mdash; and what to do about it.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See What Square Dashboard Can't <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Why Operators Rely on Square Dashboard ────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">Why operators rely on Square Dashboard</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Square Dashboard is a solid starting point. It is free, clean, and connected directly to
          your POS. For many operators, it is the first analytics tool they ever use.
        </p>

        {/* Why owners use it */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators start with Square Dashboard
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whySquare.map((item) => (
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

        {/* Why it falls short */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Why Square's analytics fall short
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {whySquareFallsShort.map((item) => (
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
            Ten categories where Square Dashboard and Meridian go head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Square Dashboard
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.square}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost ───────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          What Are You Missing?
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$4,200/yr</div>
              <p className="text-sm text-[#A1A1A8] mt-1">average losses from undetected anomalies</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">15%</div>
              <p className="text-sm text-[#A1A1A8] mt-1">revenue improvement from AI-optimized menu pricing</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">8 hrs/wk</div>
              <p className="text-sm text-[#A1A1A8] mt-1">saved vs manual report analysis</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">= Invisible Opportunity Cost</div>
            <p className="text-sm text-[#A1A1A8] mt-2">that Square Dashboard cannot show you</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Square Dashboard tells you what happened. It does not tell you what you missed. Undetected
            void patterns, comp abuse, and cash discrepancies cost the average restaurant over $4,200
            per year &mdash; losses that only surface with AI-powered anomaly detection.
          </p>
          <p>
            Add in the revenue left on the table from static menu pricing and the management hours
            burned on manual report building, and the true cost of relying on basic dashboards
            becomes impossible to ignore.
          </p>
        </div>
      </section>

      {/* ── When Square Dashboard Still Works ────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Square Dashboard Still Works
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. If you run a single location doing under $400K per year, you
                  have a small team you trust completely, and you only need to know daily sales
                  totals &mdash; Square Dashboard handles that just fine.
                </p>
                <p>
                  Meridian becomes essential when you need to{' '}
                  <span className="text-[#F5F5F7] font-medium">understand why numbers change</span>,
                  when you want to{' '}
                  <span className="text-[#F5F5F7] font-medium">catch problems before they cost you money</span>,
                  or when you are scaling to multiple locations and need cross-store intelligence
                  that Square simply does not offer.
                </p>
                <p>
                  The question is not whether Square Dashboard works. The question is whether basic
                  sales reports give you enough to compete in a market where margins shrink every year.
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
          Keep Square as your POS. Add Meridian as your analytics brain. No migration, no disruption.
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
          See What Square Dashboard Can't
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect Square in under 3 minutes. First month free, no contracts.
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
