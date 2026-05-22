import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Receipt,
  ShoppingCart,
  UserCheck,
  Users,
  CreditCard,
  Package,
  Clock,
  PercentCircle,
  UtensilsCrossed,
  Coffee,
  Wrench,
  Store,
  Brain,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'What is POS analytics?',
    a: 'POS analytics is the process of collecting, analyzing, and interpreting data from your point-of-sale system to make better business decisions. It goes beyond basic sales reports to include forecasting, anomaly detection, customer segmentation, and AI-driven recommendations — turning raw transaction data into actionable business intelligence.',
  },
  {
    q: 'How is POS analytics different from POS reports?',
    a: 'POS reports show you what happened — yesterday\'s sales total, top items sold, employee hours. POS analytics shows you why it happened and what will happen next. It uses statistical models and AI to identify trends, detect anomalies, forecast revenue, and recommend specific actions to improve your business.',
  },
  {
    q: 'Do I need special software for POS analytics?',
    a: 'Your POS system likely includes basic reporting — sales summaries, item reports, and employee tracking. But dedicated analytics tools like Meridian unlock forecasting, anomaly detection, customer segmentation, and AI-powered insights that built-in POS reports simply cannot provide.',
  },
  {
    q: 'How much does POS analytics software cost?',
    a: 'Basic POS reports come free with your POS system. Dedicated analytics platforms range from $100-250/month for single-location tools to $500-1,000/month for enterprise AI-powered platforms with multi-location support, advanced forecasting, and anomaly detection. Meridian starts at $250/month with the first month free.',
  },
  {
    q: 'Can POS analytics work with my existing system?',
    a: 'Yes. Modern POS analytics platforms connect to 50+ POS systems via secure OAuth or API integrations. Meridian supports Square, Toast, Clover, Lightspeed, Shopify POS, and 75+ others. Setup takes under 5 minutes — no IT team or API keys required.',
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

/* ── "What Your POS Already Knows" Grid ────────────── */

const dataTypes = [
  {
    icon: Receipt,
    label: 'Transactions',
    insight: 'Revenue trends, daily/weekly patterns, year-over-year growth',
  },
  {
    icon: ShoppingCart,
    label: 'Items Sold',
    insight: 'Product mix, menu engineering, top performers vs. dead weight',
  },
  {
    icon: UserCheck,
    label: 'Employees',
    insight: 'Revenue per labor hour, shift performance, scheduling optimization',
  },
  {
    icon: Users,
    label: 'Customers',
    insight: 'Visit frequency, lifetime value, RFM segmentation, churn risk',
  },
  {
    icon: CreditCard,
    label: 'Payments',
    insight: 'Payment mix trends, average ticket size, processing cost analysis',
  },
  {
    icon: Package,
    label: 'Inventory',
    insight: 'Stock velocity, reorder forecasting, waste and shrinkage tracking',
  },
  {
    icon: Clock,
    label: 'Timestamps',
    insight: 'Peak hour identification, day-of-week patterns, seasonal trends',
  },
  {
    icon: PercentCircle,
    label: 'Discounts & Voids',
    insight: 'Promotion ROI, void anomaly detection, discount abuse alerts',
  },
]

/* ── Basic Reports vs. True Analytics Table ────────── */

const comparisonRows = [
  {
    basic: 'Yesterday\'s sales total',
    analytics: 'Revenue trend with 7-day forecast',
  },
  {
    basic: 'Top selling items',
    analytics: 'Menu engineering matrix (stars, plowhorses, puzzles, dogs)',
  },
  {
    basic: 'Employee hours',
    analytics: 'Revenue per labor hour by shift',
  },
  {
    basic: 'Customer count',
    analytics: 'RFM segmentation with churn prediction',
  },
  {
    basic: 'Void report',
    analytics: 'Anomaly detection with theft probability scoring',
  },
  {
    basic: 'Hourly sales',
    analytics: 'Peak hour optimization with staff scheduling',
  },
  {
    basic: 'Category totals',
    analytics: 'Cross-sell correlation and bundle recommendations',
  },
  {
    basic: 'Monthly summary',
    analytics: 'Trend analysis with seasonal adjustment',
  },
]

/* ── "Who Needs POS Analytics?" Cards ──────────────── */

const industries = [
  {
    icon: UtensilsCrossed,
    title: 'Restaurants',
    useCases: [
      'Menu engineering to optimize margins on every plate',
      'Labor cost forecasting to eliminate over-staffing',
      'Anomaly detection to catch theft and void abuse',
    ],
    link: '/for/restaurants',
  },
  {
    icon: Coffee,
    title: 'Coffee Shops',
    useCases: [
      'Peak hour analysis for barista scheduling',
      'Product mix insights to refine seasonal menus',
      'Customer loyalty segmentation for targeted promos',
    ],
    link: '/for/coffee-shops',
  },
  {
    icon: Wrench,
    title: 'Auto Shops',
    useCases: [
      'Service category revenue breakdown by technician',
      'Parts vs. labor margin analysis per job type',
      'Customer return-visit frequency and lifetime value',
    ],
    link: '/for/auto-shops',
  },
  {
    icon: Store,
    title: 'Retail',
    useCases: [
      'Inventory velocity tracking to reduce dead stock',
      'Basket analysis for cross-sell and upsell placement',
      'Seasonal demand forecasting for buying decisions',
    ],
    link: '/for/smoke-shops',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'POS Analytics vs. Spreadsheets', to: '/vs/spreadsheets' },
  { label: 'Square Integration', to: '/integrations/square' },
  { label: 'Toast Integration', to: '/integrations/toast' },
  { label: 'Clover Integration', to: '/integrations/clover' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
]

/* ── Component ─────────────────────────────────────── */

export default function WhatIsPosAnalyticsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="What Is POS Analytics? Everything You Need to Know | Meridian"
        description="POS analytics transforms your point-of-sale data into actionable business intelligence. Learn what it is, how it works, and why every restaurant and retail store needs it."
        path="/what-is-pos-analytics"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#1A8FD6]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#1A8FD6] text-sm font-medium tracking-widest uppercase mb-4">
            The Definitive Guide
          </p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            What Is POS Analytics?
            <br />
            <span className="text-[#17C5B0]">Everything You Need to Know</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Your point-of-sale system captures thousands of data points every day.
            POS analytics turns those numbers into decisions that grow your business.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See Your POS Data in Action <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── What POS Analytics Actually Is ────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          What POS Analytics Actually Is
        </h2>
        <div className="space-y-4 text-[#A1A1A8] leading-relaxed">
          <p>
            POS analytics is the practice of turning transaction data from your point-of-sale system
            into business intelligence. Every sale, void, discount, and customer interaction your POS
            records becomes raw material for understanding how your business actually works.
          </p>
          <p>
            It is not just "how much did we sell today." True POS analytics answers harder questions:
            <span className="text-[#F5F5F7] font-medium"> why</span> did sales dip on Tuesday,
            <span className="text-[#F5F5F7] font-medium"> who</span> are your most valuable customers,
            <span className="text-[#F5F5F7] font-medium"> when</span> should you schedule an extra
            employee, and <span className="text-[#F5F5F7] font-medium">what</span> should you do next
            to grow revenue.
          </p>
          <p>
            The difference between a POS report and POS analytics is the difference between a
            rearview mirror and a GPS. One shows where you have been. The other shows where you
            should go.
          </p>
        </div>
      </section>

      {/* ── What Your POS Already Knows ───────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            What Your POS Already Knows
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
            Your POS captures eight categories of data every single day. Here is what each one
            unlocks when you apply analytics.
          </p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {dataTypes.map((d) => (
              <div
                key={d.label}
                className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5 hover:border-[#17C5B0]/30 transition-colors"
              >
                <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center mb-4">
                  <d.icon className="w-5 h-5 text-[#17C5B0]" />
                </div>
                <h3 className="text-base font-semibold mb-2">{d.label}</h3>
                <p className="text-sm text-[#A1A1A8] leading-relaxed">{d.insight}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Basic Reports vs. True Analytics ──────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          Basic POS Reports vs. True Analytics
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-10">
          Every POS system includes basic reports. Here is what you are missing without
          dedicated analytics.
        </p>
        <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-2 bg-[#111113] border-b border-[#1F1F23]">
            <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
              Basic POS Report
            </div>
            <div className="px-5 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider">
              POS Analytics Insight
            </div>
          </div>
          {/* Rows */}
          {comparisonRows.map((row, i) => (
            <div
              key={i}
              className={`grid grid-cols-2 ${
                i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'
              } ${i < comparisonRows.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}
            >
              <div className="px-5 py-3 text-[#A1A1A8] text-sm">{row.basic}</div>
              <div className="px-5 py-3 text-sm font-medium">{row.analytics}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Who Needs POS Analytics? ──────────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            Who Needs POS Analytics?
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
            Any business with a point-of-sale system benefits from analytics. Here are the
            industries seeing the biggest impact.
          </p>
          <div className="grid sm:grid-cols-2 gap-6">
            {industries.map((ind) => (
              <Link
                key={ind.title}
                to={ind.link}
                className="group bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#17C5B0]/40 transition-colors"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
                    <ind.icon className="w-5 h-5 text-[#17C5B0]" />
                  </div>
                  <h3 className="text-lg font-semibold group-hover:text-[#17C5B0] transition-colors">
                    {ind.title}
                  </h3>
                </div>
                <ul className="space-y-2">
                  {ind.useCases.map((uc) => (
                    <li key={uc} className="flex items-start gap-2 text-sm text-[#A1A1A8]">
                      <ChevronRight className="w-3 h-3 text-[#17C5B0] mt-1 shrink-0" />
                      {uc}
                    </li>
                  ))}
                </ul>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ── How AI Changes POS Analytics ──────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <div className="flex items-start gap-4 mb-6">
          <div className="w-12 h-12 rounded-xl bg-[#1A8FD6]/10 flex items-center justify-center shrink-0">
            <Brain className="w-6 h-6 text-[#1A8FD6]" />
          </div>
          <div>
            <h2 className="text-2xl md:text-3xl font-bold mb-2">
              How AI Changes POS Analytics
            </h2>
            <p className="text-[#A1A1A8] text-sm">
              Machine learning finds patterns humans miss.
            </p>
          </div>
        </div>
        <div className="space-y-4 text-[#A1A1A8] leading-relaxed">
          <p>
            Traditional analytics relies on humans knowing what questions to ask. AI-powered
            POS analytics flips this model: the system surfaces insights you never thought to
            look for.
          </p>
          <div className="grid sm:grid-cols-3 gap-4 mt-6">
            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
              <h3 className="text-sm font-semibold text-[#F5F5F7] mb-2">Anomaly Detection</h3>
              <p className="text-sm text-[#A1A1A8]">
                AI monitors every transaction and flags unusual patterns — void spikes, revenue
                dips, off-hours activity — before they become costly.
              </p>
            </div>
            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
              <h3 className="text-sm font-semibold text-[#F5F5F7] mb-2">Forecasting</h3>
              <p className="text-sm text-[#A1A1A8]">
                Machine learning models trained on your data predict revenue, demand, and
                staffing needs 7, 30, and 90 days out with increasing accuracy.
              </p>
            </div>
            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
              <h3 className="text-sm font-semibold text-[#F5F5F7] mb-2">Segmentation</h3>
              <p className="text-sm text-[#A1A1A8]">
                AI clusters customers by behavior — recency, frequency, monetary value — to
                identify champions, at-risk regulars, and one-time visitors automatically.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          See What Your POS Data Really Says
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS in under 5 minutes. Get AI-powered insights within the hour.
          First month free, no contracts.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Get Your Free Month <ArrowRight className="w-5 h-5" />
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
