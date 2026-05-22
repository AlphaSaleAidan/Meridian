import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Flame,
  DollarSign,
  TrendingUp,
  BarChart3,
  Users,
  Package,
  ShieldCheck,
  AlertTriangle,
  Search,
  Eye,
} from 'lucide-react'
import SEO from '@/components/SEO'

const faqItems = [
  {
    q: 'What analytics should a smoke shop track?',
    a: 'The most important metrics for smoke shops are gross margin by product category, inventory turnover rate, shrinkage percentage, average transaction value, and customer visit frequency. Meridian tracks all of these automatically from your POS data.',
  },
  {
    q: 'Can Meridian help with compliance tracking?',
    a: 'Meridian flags age-verification gaps, tracks sales by regulated product category, and generates audit-ready reports. While it does not replace your compliance software, it adds a data layer that catches patterns compliance-only tools miss — like unusual volume spikes on restricted items.',
  },
  {
    q: 'How does Meridian detect theft and shrinkage?',
    a: 'Meridian\'s anomaly detection engine monitors void rates, refund patterns, discount usage, inventory-to-sales ratios, and off-hours transactions. When any metric deviates from your baseline, you get an immediate alert with the specific details to investigate.',
  },
  {
    q: 'Does Meridian work with my smoke shop POS?',
    a: 'Yes. Meridian integrates with Square, Clover, Lightspeed, Shopify POS, and 75+ other point-of-sale systems commonly used in specialty retail. Setup takes about 5 minutes via secure OAuth — no API keys or IT work required.',
  },
  {
    q: 'How much does smoke shop analytics cost?',
    a: 'Meridian starts at $250/month per location with the first month completely free. No long-term contracts, no setup fees. Most specialty retailers see ROI within the first month through shrinkage reduction and margin optimization alone.',
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
    icon: Package,
    title: 'High SKU Count, No Margin Visibility',
    description:
      'Hundreds of products across glass, vape, accessories, and tobacco — but you cannot tell which categories actually drive profit versus just taking up shelf space.',
    color: '#EF4444',
  },
  {
    icon: ShieldCheck,
    title: 'Compliance Tracking Headaches',
    description:
      'Regulated products require meticulous tracking. Without analytics, you rely on manual logs that miss patterns and leave you vulnerable during audits.',
    color: '#F59E0B',
  },
  {
    icon: Eye,
    title: 'Theft and Shrinkage',
    description:
      'High-value, small-size inventory makes smoke shops a target. Without anomaly detection, shrinkage eats into margins for months before you notice.',
    color: '#EF4444',
  },
]

const features = [
  {
    icon: DollarSign,
    title: 'Product Margin Analysis',
    description: 'See true margin by product, brand, and category. Know which items deserve prime shelf space and which to discontinue.',
  },
  {
    icon: Package,
    title: 'Inventory Optimization',
    description: 'AI-driven reorder points and velocity tracking. Reduce deadstock, prevent stockouts on your best sellers.',
  },
  {
    icon: ShieldCheck,
    title: 'Compliance Tracking',
    description: 'Monitor regulated product sales, flag anomalies, and generate audit-ready reports. Stay ahead of inspections.',
  },
  {
    icon: AlertTriangle,
    title: 'Shrinkage Detection',
    description: 'Real-time alerts on unusual voids, refunds, discount abuse, and inventory-to-sales mismatches. Catch theft early.',
  },
  {
    icon: Users,
    title: 'Customer Segmentation',
    description: 'RFM analysis identifies your regulars, occasional visitors, and churned customers. Target promotions where they matter.',
  },
  {
    icon: TrendingUp,
    title: 'Trend Forecasting',
    description: 'Predict demand for trending products before they peak. Stock up on winners and exit losers before they become deadstock.',
  },
]

const steps = [
  {
    num: '01',
    title: 'Connect Your POS',
    description: 'Authorize Square, Clover, Lightspeed, Shopify, or any of 75+ systems. Under 5 minutes, no API keys.',
  },
  {
    num: '02',
    title: 'AI Analyzes Your Data',
    description: 'Meridian ingests your transaction and inventory history to build a model of margins, velocity, and customer behavior.',
  },
  {
    num: '03',
    title: 'Get Actionable Insights',
    description: 'Margin breakdowns, shrinkage alerts, compliance reports, and inventory recommendations — all from day one.',
  },
]

const siblingPages = [
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Auto Shops', to: '/for/auto-shops' },
  { label: 'Fast Food & QSR', to: '/for/fast-food' },
]

export default function SmokeShopsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Smoke Shop Analytics — Inventory and Compliance Intelligence | Meridian"
        description="AI analytics for smoke shops and specialty retail. Track product margins, optimize inventory, and stay compliant. Works with your existing POS system."
        path="/for/smoke-shops"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">For Smoke Shops</p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Smoke Shop Analytics
            <br />
            <span className="text-[#17C5B0]">Inventory and Compliance Intelligence</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Hundreds of SKUs, thin margins, compliance pressure. Meridian turns your POS data into margin clarity,
            shrinkage alerts, and inventory intelligence.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Why Smoke Shops Struggle Without Analytics</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Specialty retail is uniquely challenging — high SKU counts, regulated products, and theft risk. Without data,
          you are managing blind.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Built for Specialty Retail Complexity</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Meridian understands the unique challenges of smoke shops — from high SKU counts to compliance requirements.
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
        <h2 className="text-2xl md:text-3xl font-bold mb-4">Take Control of Your Margins and Inventory</h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS and get instant visibility into what is selling, what is shrinking, and where your margins
          really stand. First month free.
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
