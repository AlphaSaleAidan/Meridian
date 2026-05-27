import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Zap,
  ShieldAlert,
  AlertTriangle,
  BarChart3,
  DollarSign,
  Building2,
  MessageSquare,
  Search,
  Plug,
  CheckCircle2,
  Monitor,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does Meridian work with all Clover plans?',
    a: 'Yes. Meridian connects via Clover\'s API and works with all Clover plans — Station, Mini, Flex, and Go. Your plan level doesn\'t affect what Meridian can analyze.',
  },
  {
    q: 'What does Meridian catch that Clover misses?',
    a: 'Real-time anomaly detection (void spikes, refund abuse, unauthorized discounts), predictive revenue forecasting, customer segmentation, and cross-location benchmarking. Clover shows transaction data — Meridian finds the patterns hiding in it.',
  },
  {
    q: 'How long to connect Clover?',
    a: 'Under 5 minutes. OAuth authorization through Clover\'s app marketplace. No API keys needed, no IT support required.',
  },
  {
    q: 'Can I still use Clover\'s reports?',
    a: 'Yes. Meridian runs alongside Clover. Use Clover for daily shift summaries and Meridian for strategic decisions, forecasting, and anomaly detection.',
  },
  {
    q: 'Is Meridian worth it for one Clover location?',
    a: 'For locations doing $300K+/year, typically yes. Anomaly detection alone catches $2,000-6,000/year in losses that Clover reports don\'t surface.',
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
    feature: 'Real-Time Monitoring',
    clover: 'End-of-shift reports',
    meridian: 'Live dashboards with instant alerts',
    winner: 'meridian',
  },
  {
    feature: 'Anomaly Detection',
    clover: 'None',
    meridian: 'AI-powered void, theft, and discount abuse detection',
    winner: 'meridian',
  },
  {
    feature: 'Revenue Forecasting',
    clover: 'None',
    meridian: 'ML-powered daily, weekly, monthly forecasts',
    winner: 'meridian',
  },
  {
    feature: 'Multi-Location',
    clover: 'Clover Dashboard (basic)',
    meridian: 'Cross-location benchmarking and ranking',
    winner: 'meridian',
  },
  {
    feature: 'Customer Intelligence',
    clover: 'Basic customer list',
    meridian: 'AI segmentation, churn risk, LTV scoring',
    winner: 'meridian',
  },
  {
    feature: 'Inventory Insights',
    clover: 'Stock counts and alerts',
    meridian: 'Demand forecasting + waste reduction',
    winner: 'meridian',
  },
  {
    feature: 'Labor Analysis',
    clover: 'Clock-in/out reports',
    meridian: 'Labor cost optimization + coverage recommendations',
    winner: 'meridian',
  },
  {
    feature: 'Menu Performance',
    clover: 'Item sales totals',
    meridian: 'Margin analysis + dynamic pricing suggestions',
    winner: 'meridian',
  },
  {
    feature: 'Custom Alerts',
    clover: 'Low stock alerts only',
    meridian: 'Configurable alerts for any metric or anomaly',
    winner: 'meridian',
  },
  {
    feature: 'Reporting Depth',
    clover: 'Pre-built report templates',
    meridian: 'Custom KPIs + unlimited drill-down',
    winner: 'meridian',
  },
]

/* ── "Why Clover Reporting" Reasons ──────────────────── */

const whyClover = [
  { icon: DollarSign, label: 'Bundled Free', detail: 'Reports come with every Clover plan' },
  { icon: Zap, label: 'Simple', detail: 'Easy to understand at a glance' },
  { icon: Monitor, label: 'Hardware Integrated', detail: 'Data shows right on your Clover device' },
]

const whyItBreaks = [
  { icon: ShieldAlert, label: 'No anomaly detection', detail: 'Suspicious patterns go unnoticed until cash is gone' },
  { icon: BarChart3, label: 'No forecasting', detail: 'You can\'t predict tomorrow\'s revenue or staffing needs' },
  { icon: Building2, label: 'Fragmented multi-location', detail: 'Each device has its own view — no unified intelligence' },
  { icon: AlertTriangle, label: 'Static reports', detail: 'You can view data but can\'t ask custom questions' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Authorize on Clover',
    desc: 'One-click setup through the Clover App Market. Under 5 minutes.',
  },
  {
    num: '02',
    icon: Search,
    title: 'AI Ingests Your History',
    desc: 'Meridian pulls your complete Clover transaction history and starts finding patterns.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Insights by Tomorrow',
    desc: 'Forecasts, anomaly alerts, and customer intelligence — running automatically.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Clover Integration', to: '/integrations/clover' },
  { label: 'vs Spreadsheets', to: '/vs/spreadsheets' },
  { label: 'vs Toast Analytics', to: '/vs/toast-analytics' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsCloverAnalyticsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Clover Reporting: The Analytics Gap Your POS Won't Close | Meridian"
        description="Clover's built-in reports cover basics. Meridian adds AI-powered insights, anomaly detection, and predictive analytics that Clover can't provide."
        path="/vs/clover-analytics"
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
            Meridian vs. Clover Reporting:
            <br />
            <span className="text-[#17C5B0]">The Analytics Gap Your POS Won't Close</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Clover tracks transactions. Meridian finds what they mean.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            Close the Gap — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── The Clover Reporting Problem ─────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Clover Reporting Problem</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Clover's built-in reports handle the basics: daily sales summaries, item counts, and
          employee clock-ins. Operators rely on them because they are free, simple, and already
          on the device. But the moment you need to predict, detect, or compare — the reports
          go silent.
        </p>

        {/* Why owners use them */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators use Clover's built-in reporting
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyClover.map((item) => (
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
            Why Clover reporting breaks down
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {whyItBreaks.map((item) => (
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
            Ten categories where Clover's built-in reports and Meridian's AI analytics go head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Clover Reporting
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider">
                Meridian Analytics
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.clover}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost of Missed Anomalies ──────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost of Missed Anomalies
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$3,500/yr</div>
              <p className="text-sm text-[#A1A1A8] mt-1">average undetected losses per location</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#17C5B0]">4.2x</div>
              <p className="text-sm text-[#A1A1A8] mt-1">ROI for operators using AI analytics</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#17C5B0]">23 min</div>
              <p className="text-sm text-[#A1A1A8] mt-1">average time from anomaly to alert with Meridian</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-lg text-[#A1A1A8]">
              Clover's time from anomaly to detection:{' '}
              <span className="text-[#EF4444] font-bold text-2xl">days or never</span>
            </div>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Clover reports show you what happened. They cannot tell you when something is wrong.
            A void spike at 11 PM, a refund pattern from a single employee, unauthorized discounts
            applied to friends-and-family orders — these anomalies hide in plain sight inside
            standard sales summaries.
          </p>
          <p>
            Without real-time anomaly detection, operators discover losses during quarterly reviews
            or inventory counts — weeks or months after the damage is done. Meridian flags anomalies
            within minutes, giving you time to act before a pattern becomes a problem.
          </p>
        </div>
      </section>

      {/* ── When Clover Reporting Still Works ─────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Clover Reporting Still Works
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  If you run a single location with a small team, do under $300K per year, and your
                  main need is a quick end-of-day sales summary — Clover's built-in reports handle
                  that well. They are fast, free, and right on your device.
                </p>
                <p>
                  Meridian becomes essential when you need to{' '}
                  <span className="text-[#F5F5F7] font-medium">detect problems before they cost you money</span>,
                  when you want{' '}
                  <span className="text-[#F5F5F7] font-medium">forecasting to plan labor and inventory</span>,
                  or when you manage multiple locations and need a unified view instead of checking
                  each Clover device separately.
                </p>
                <p>
                  Clover is a great POS. Its reports just were not built to be an analytics platform.
                  Meridian fills the gap without replacing anything you already use.
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
          Meridian layers on top of Clover. No hardware changes, no data migration, no disruption.
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
          Close the Analytics Gap
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your Clover in under 5 minutes. First month free.
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
