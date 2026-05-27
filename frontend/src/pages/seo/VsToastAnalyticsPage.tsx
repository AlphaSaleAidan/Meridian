import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Clock,
  ShieldAlert,
  BarChart3,
  Users,
  DollarSign,
  Building2,
  MessageSquare,
  Search,
  Plug,
  CheckCircle2,
  SlidersHorizontal,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Does Meridian replace Toast?',
    a: 'No. Meridian connects to Toast via API and enhances it. You keep Toast as your POS — Meridian adds AI analytics, anomaly detection, and cross-location insights that Toast\'s native reporting doesn\'t offer.',
  },
  {
    q: 'What can Meridian see that Toast can\'t?',
    a: 'Real-time anomaly detection (theft, comp abuse, void patterns), AI-powered revenue forecasting, customer segmentation across locations, and benchmarking against industry averages. Toast reports show you what happened — Meridian shows you what\'s about to happen.',
  },
  {
    q: 'How long does it take to connect Toast to Meridian?',
    a: 'Under 5 minutes. One-click OAuth authorization — no API keys, no IT department, no data migration. Your historical Toast data is ingested automatically.',
  },
  {
    q: 'Is it worth it for a single Toast location?',
    a: 'If you\'re doing over $500K/year, yes. The anomaly detection alone typically catches $3,000-8,000/year in preventable losses that Toast reports don\'t surface. For multi-location operators, the ROI is even higher.',
  },
  {
    q: 'Can I still use Toast\'s reports alongside Meridian?',
    a: 'Absolutely. Many operators use Toast for daily shift reports and Meridian for strategic decisions, forecasting, and cross-location analysis. They complement each other.',
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
    feature: 'Real-Time Alerts',
    toast: 'End-of-day reports',
    meridian: 'Instant anomaly alerts',
    winner: 'meridian',
  },
  {
    feature: 'Forecasting',
    toast: 'Basic trend lines',
    meridian: 'AI/ML revenue forecasting',
    winner: 'meridian',
  },
  {
    feature: 'Anomaly Detection',
    toast: 'Manual review of void reports',
    meridian: 'Auto-detects theft, comp abuse, void spikes',
    winner: 'meridian',
  },
  {
    feature: 'Multi-Location',
    toast: 'Separate reports per location',
    meridian: 'Unified dashboard, cross-location benchmarks',
    winner: 'meridian',
  },
  {
    feature: 'Customer Segmentation',
    toast: 'Limited to loyalty program',
    meridian: 'AI segments by behavior, spend, frequency',
    winner: 'meridian',
  },
  {
    feature: 'Labor Optimization',
    toast: 'Scheduled vs. actual hours',
    meridian: 'AI-optimized scheduling + labor cost forecasting',
    winner: 'meridian',
  },
  {
    feature: 'Menu Engineering',
    toast: 'Item sales mix report',
    meridian: 'Profit margin analysis + pricing recommendations',
    winner: 'meridian',
  },
  {
    feature: 'Competitor Benchmarks',
    toast: 'None',
    meridian: 'Industry and local market benchmarks',
    winner: 'meridian',
  },
  {
    feature: 'Custom Alerts',
    toast: 'Pre-set notification types',
    meridian: 'Fully configurable alert rules with AI thresholds',
    winner: 'meridian',
  },
  {
    feature: 'Data Depth',
    toast: '90-day default window',
    meridian: 'Unlimited history with trend analysis',
    winner: 'meridian',
  },
]

/* ── "Why Operators Use Toast Analytics" Reasons ─────── */

const whyToastAnalytics = [
  { icon: DollarSign, label: 'Already Included', detail: 'No extra cost — it\'s part of your Toast subscription' },
  { icon: BarChart3, label: 'Good Enough', detail: 'Daily sales summaries cover the basics' },
  { icon: Users, label: 'Familiar', detail: 'Your team already knows where to find reports' },
]

const whyTheyBreak = [
  { icon: ShieldAlert, label: 'No anomaly detection', detail: 'Theft and comp abuse goes unnoticed until month-end' },
  { icon: Building2, label: 'No cross-location insights', detail: 'Each location is a silo — no benchmarking' },
  { icon: Clock, label: 'Reactive, not predictive', detail: 'Reports tell you what happened, not what\'s coming' },
  { icon: SlidersHorizontal, label: 'Limited customization', detail: 'Pre-built reports can\'t be tailored to your specific KPIs' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Toast',
    desc: 'One-click OAuth authorization. No API keys, no IT, under 5 minutes.',
  },
  {
    num: '02',
    icon: Search,
    title: 'AI Analyzes Your Data',
    desc: 'Meridian ingests your complete Toast transaction history and identifies patterns, anomalies, and opportunities.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Get Insights in 24 Hours',
    desc: 'Forecasts, alerts, and segmentation — delivered automatically on top of your existing Toast setup.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Toast Integration', to: '/integrations/toast' },
  { label: 'vs Spreadsheets', to: '/vs/spreadsheets' },
  { label: 'Square Integration', to: '/integrations/square' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsToastAnalyticsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Toast Analytics: What Toast's Reports Don't Show You | Meridian"
        description="Toast's built-in reports cover the basics. Here's what you're missing — and why operators with 3+ locations are switching to dedicated POS analytics."
        path="/vs/toast-analytics"
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
            Meridian vs. Toast Analytics:
            <br />
            <span className="text-[#17C5B0]">What Toast's Reports Don't Show You</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Toast's built-in reports cover the basics. Here's what you're missing.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See What You're Missing — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── The Toast Analytics Trap ──────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Toast Analytics Trap</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Toast's built-in reporting is convenient — it's already there, your team knows it, and it
          covers the basics. But every operator who scales beyond two or three locations hits the
          same ceiling.
        </p>

        {/* Why owners use them */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators use Toast's built-in analytics
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyToastAnalytics.map((item) => (
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
            Why Toast analytics breaks down
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
            Ten categories where Toast's built-in reporting and Meridian's dedicated analytics go
            head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Toast Analytics
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.toast}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost of "Included" ────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost of "Included"
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$3K-8K</div>
              <p className="text-sm text-[#A1A1A8] mt-1">per year in undetected losses (theft, comp abuse, voids)</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">90 days</div>
              <p className="text-sm text-[#A1A1A8] mt-1">default data window — trends beyond that are invisible</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">0</div>
              <p className="text-sm text-[#A1A1A8] mt-1">cross-location benchmarks or industry comparisons</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">= Blind spots that cost more than any subscription</div>
            <p className="text-sm text-[#A1A1A8] mt-2">Toast's reports are free — but what they don't show you isn't</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Toast's included analytics cover daily sales, labor percentages, and product mix. That's
            enough to know what happened yesterday. It's not enough to know what's about to happen
            tomorrow — or to catch the patterns that are quietly costing you thousands.
          </p>
          <p>
            A void pattern running undetected across three locations for a single quarter can cost
            $10,000-25,000. A missed shift in customer behavior can erode margins for months before
            it shows up in a standard sales report. Toast cannot alert you to either.
          </p>
        </div>
      </section>

      {/* ── When Toast Analytics Still Makes Sense ────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Toast Analytics Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. If you run a single location doing under $500K per year and
                  your primary need is checking yesterday's sales and labor costs, Toast's built-in
                  reports do that job just fine.
                </p>
                <p>
                  Dedicated POS analytics becomes essential when you need to{' '}
                  <span className="text-[#F5F5F7] font-medium">manage multiple locations from one view</span>,
                  when you want{' '}
                  <span className="text-[#F5F5F7] font-medium">proactive alerts instead of reactive reports</span>,
                  or when you suspect you're losing money to patterns that Toast's standard reports
                  cannot surface.
                </p>
                <p>
                  The question is not whether Toast's analytics work. The question is whether
                  "good enough" reporting is costing you more than a tool that shows you what
                  you're actually missing.
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
          Keep Toast as your POS. Add Meridian as your analytics layer. No disruption, no migration.
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
          See What Toast Can't Show You
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your Toast account in under 5 minutes. First month free, no contracts.
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
