import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  UtensilsCrossed,
  Clock,
  Users,
  PieChart,
  BarChart3,
  ShieldAlert,
  CalendarClock,
  Target,
} from 'lucide-react'
import SEO from '@/components/SEO'

const faqItems = [
  {
    q: 'What analytics should a restaurant track?',
    a: 'The most impactful restaurant KPIs are revenue per labor hour (RPLH), food cost percentage, average ticket size, table turn time, and void rate. Meridian tracks all of these automatically from your POS data — no manual entry required.',
  },
  {
    q: 'How does Meridian connect to my restaurant POS?',
    a: 'Meridian uses secure OAuth connections for Square, Toast, Clover, Lightspeed, and 75+ other POS systems. Setup takes about 5 minutes — just authorize the connection and your data starts flowing. No API keys to copy, no IT team needed.',
  },
  {
    q: 'Can Meridian detect employee theft?',
    a: 'Yes. Meridian\'s anomaly detection engine flags unusual patterns including void spikes, abnormal refund rates, off-hours transactions, and discount abuse. You get real-time alerts so you can investigate immediately rather than discovering losses months later.',
  },
  {
    q: 'How much does restaurant analytics software cost?',
    a: 'Meridian starts at $250/month per location with your first month completely free. There are no long-term contracts, no setup fees, and no hidden charges. Most restaurants see ROI within the first two weeks through waste reduction and labor optimization alone.',
  },
  {
    q: 'Does Meridian work with Toast POS?',
    a: 'Absolutely. Meridian integrates natively with Toast, Square, Clover, Lightspeed, Shopify POS, and 75+ other point-of-sale systems. The Toast integration pulls transaction data, menu items, labor hours, and customer data automatically.',
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

const painPoints = [
  {
    icon: TrendingUp,
    title: 'Thin Margins, Zero Visibility',
    description:
      'Restaurant margins average 3-5%. Without real-time analytics, you cannot see where money leaks — food waste, over-staffing, or underperforming menu items.',
    color: '#EF4444',
  },
  {
    icon: BarChart3,
    title: 'Manual Spreadsheet Tracking',
    description:
      'Exporting CSVs, building pivot tables, and reconciling numbers across systems wastes 5-10 hours a week that should go toward running your restaurant.',
    color: '#F59E0B',
  },
  {
    icon: Users,
    title: 'Staffing by Gut Feel',
    description:
      'Without peak-hour data, you either over-staff (burning labor budget) or under-staff (losing customers). Both cost thousands monthly.',
    color: '#EF4444',
  },
]

const features = [
  {
    icon: TrendingUp,
    title: 'Revenue Forecasting',
    description: 'AI-powered daily and weekly revenue predictions based on historical trends, seasonality, and local events.',
  },
  {
    icon: AlertTriangle,
    title: 'Anomaly Detection',
    description: 'Instant alerts for unusual voids, refunds, off-hours activity, and revenue dips before they become costly.',
  },
  {
    icon: UtensilsCrossed,
    title: 'Menu Engineering Matrix',
    description: 'See which items are stars, plowhorses, puzzles, and dogs. Optimize your menu for margin and popularity.',
  },
  {
    icon: Clock,
    title: 'Peak Hours Analysis',
    description: 'Visualize revenue by hour and day to optimize staffing, prep schedules, and promotional timing.',
  },
  {
    icon: CalendarClock,
    title: 'Staff Scheduling Insights',
    description: 'Match labor to demand curves. Know exactly when you need more hands and when you can cut shifts.',
  },
  {
    icon: Target,
    title: 'Customer Segmentation',
    description: 'RFM analysis identifies your best customers, at-risk regulars, and one-time visitors so you can market smarter.',
  },
]

const steps = [
  {
    num: '01',
    title: 'Connect Your POS',
    description: 'Authorize Square, Toast, Clover, or any of 75+ POS systems in under 5 minutes. No API keys needed.',
  },
  {
    num: '02',
    title: 'AI Analyzes Your Data',
    description: 'Meridian ingests your transaction history and starts identifying patterns, anomalies, and opportunities.',
  },
  {
    num: '03',
    title: 'Get Actionable Insights',
    description: 'Revenue forecasts, menu recommendations, staffing alerts, and anomaly notifications — all from day one.',
  },
]

const siblingPages = [
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Auto Shops', to: '/for/auto-shops' },
  { label: 'Fast Food & QSR', to: '/for/fast-food' },
  { label: 'Smoke Shops', to: '/for/smoke-shops' },
]

export default function RestaurantsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Restaurant Analytics Software — AI-Powered POS Insights | Meridian"
        description="Connect your restaurant's POS and get instant AI-powered analytics. Revenue forecasts, anomaly detection, menu engineering, and staff optimization. First month free."
        path="/for/restaurants"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">For Restaurants</p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Restaurant Analytics Software
            <br />
            <span className="text-[#17C5B0]">AI-Powered POS Insights</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Connect your POS, stop guessing, and start making data-driven decisions that protect your margins and grow
            your restaurant.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            Start Your Free Month <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Pain Points ───────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Why Most Restaurants Fly Blind</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          The average restaurant closes within five years. The difference between survival and failure is visibility into
          your numbers.
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {painPoints.map((p) => (
            <div key={p.title} className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6">
              <div
                className="w-10 h-10 rounded-lg flex items-center justify-center mb-4"
                style={{ backgroundColor: `${p.color}15` }}
              >
                <p.icon className="w-5 h-5" style={{ color: p.color }} />
              </div>
              <h3 className="text-lg font-semibold mb-2">{p.title}</h3>
              <p className="text-[#A1A1A8] text-sm leading-relaxed">{p.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ──────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          Everything You Need to Run a Smarter Restaurant
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Meridian turns your POS data into revenue-driving insights automatically.
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f) => (
            <div key={f.title} className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6">
              <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center mb-4">
                <f.icon className="w-5 h-5 text-[#17C5B0]" />
              </div>
              <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
              <p className="text-[#A1A1A8] text-sm leading-relaxed">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ──────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-12">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((s) => (
            <div key={s.num} className="text-center">
              <div className="text-4xl font-bold text-[#17C5B0]/30 mb-3">{s.num}</div>
              <h3 className="text-lg font-semibold mb-2">{s.title}</h3>
              <p className="text-[#A1A1A8] text-sm leading-relaxed">{s.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── FAQ ───────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-12">Frequently Asked Questions</h2>
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
              <div className="px-6 pb-4 text-sm text-[#A1A1A8] leading-relaxed">{item.a}</div>
            </details>
          ))}
        </div>
      </section>

      {/* ── CTA ───────────────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">Ready to See What Your POS Data Is Hiding?</h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Join hundreds of restaurants using Meridian to protect margins, forecast revenue, and eliminate guesswork.
          Your first month is free.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Start Your Free Month <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* ── Internal Links ────────────────────────────── */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
        <p className="text-[#A1A1A8] text-sm mb-3">Explore more industries:</p>
        <div className="flex flex-wrap gap-3">
          {siblingPages.map((p) => (
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
