import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Wrench,
  Clock,
  TrendingUp,
  BarChart3,
  Users,
  Package,
  CalendarClock,
  ShieldCheck,
  DollarSign,
} from 'lucide-react'
import SEO from '@/components/SEO'

const faqItems = [
  {
    q: 'What metrics should an auto repair shop track?',
    a: 'The most important KPIs for auto shops are average repair order (ARO) value, technician efficiency rate, parts-to-labor ratio, customer return rate, and revenue per bay per day. Meridian tracks all of these automatically from your POS and shop management system.',
  },
  {
    q: 'How does Meridian connect to my shop management system?',
    a: 'Meridian integrates with Square, Clover, Lightspeed, and other POS systems used by auto shops via secure OAuth. Setup takes about 5 minutes. If you use specialized shop management software, we can also ingest CSV exports on a scheduled basis.',
  },
  {
    q: 'Can Meridian help with technician scheduling?',
    a: 'Yes. Meridian analyzes appointment patterns, service duration history, and seasonal trends to recommend optimal scheduling. You will see which time slots are underbooked, which techs are overloaded, and where you can fit more high-margin jobs.',
  },
  {
    q: 'How much does auto shop analytics cost?',
    a: 'Meridian starts at $250/month per location with the first month free. No long-term contracts. Most shops see ROI within weeks through better scheduling, reduced idle time, and identifying their most profitable service categories.',
  },
  {
    q: 'Does Meridian work for multi-location auto shops?',
    a: 'Absolutely. Meridian provides cross-location dashboards to compare bay utilization, technician productivity, revenue per service type, and customer retention across all your shops. Identify your top and bottom performers at a glance.',
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
    icon: DollarSign,
    title: 'No Visibility Into Service Profitability',
    description:
      'You know oil changes bring people in, but are they profitable? Without service-level margin tracking, you cannot tell which jobs actually make money.',
    color: '#EF4444',
  },
  {
    icon: CalendarClock,
    title: 'Scheduling Inefficiency',
    description:
      'Bays sit empty on Tuesdays while Mondays are triple-booked. Without data-driven scheduling, you lose revenue to idle time and rush-hour bottlenecks.',
    color: '#F59E0B',
  },
  {
    icon: Users,
    title: 'Customer Retention Is a Mystery',
    description:
      'A customer comes in for brake work and never returns. Without retention analytics, you have no idea who is at risk of leaving or why.',
    color: '#EF4444',
  },
]

const features = [
  {
    icon: DollarSign,
    title: 'Service Profitability Tracking',
    description: 'See margin by service type — oil changes, brake jobs, diagnostics, tires. Know which services to promote and which to reprice.',
  },
  {
    icon: Wrench,
    title: 'Technician Productivity',
    description: 'Track hours billed vs. hours worked, jobs per day, and average repair order by tech. Coach with data.',
  },
  {
    icon: CalendarClock,
    title: 'Appointment Forecasting',
    description: 'AI predicts demand by day and service type so you can staff and schedule bays for maximum throughput.',
  },
  {
    icon: Users,
    title: 'Customer Retention Analytics',
    description: 'RFM segmentation identifies loyal customers, at-risk clients, and lost ones. Trigger re-engagement campaigns automatically.',
  },
  {
    icon: Package,
    title: 'Parts Inventory Intelligence',
    description: 'Predict parts needs based on upcoming appointments and historical usage. Reduce stockouts and overstock.',
  },
  {
    icon: TrendingUp,
    title: 'Revenue Trend Analysis',
    description: 'Track revenue by week, month, and season. See growth trends and forecast future performance with AI models.',
  },
]

const steps = [
  {
    num: '01',
    title: 'Connect Your POS',
    description: 'Authorize Square, Clover, Lightspeed, or any of 75+ systems. Takes under 5 minutes, no API keys needed.',
  },
  {
    num: '02',
    title: 'AI Analyzes Your Data',
    description: 'Meridian ingests your transaction and appointment history to build a model of your shop\'s patterns and opportunities.',
  },
  {
    num: '03',
    title: 'Get Actionable Insights',
    description: 'Service profitability breakdowns, scheduling recommendations, retention alerts, and revenue forecasts from day one.',
  },
]

const siblingPages = [
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Fast Food & QSR', to: '/for/fast-food' },
  { label: 'Smoke Shops', to: '/for/smoke-shops' },
]

export default function AutoShopsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Auto Shop Management Software — AI Analytics for Repair Shops | Meridian"
        description="Track your most profitable services, optimize technician scheduling, and forecast revenue with AI. Works with your existing POS. First month free."
        path="/for/auto-shops"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#1A8FD6]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#1A8FD6] text-sm font-medium tracking-widest uppercase mb-4">For Auto Shops</p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Auto Shop Management Software
            <br />
            <span className="text-[#17C5B0]">AI Analytics for Repair Shops</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Stop guessing which services make money. Meridian connects to your POS and shows you exactly where to focus
            for maximum profitability.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Why Most Auto Shops Leave Money on the Table</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          The difference between a struggling shop and a thriving one is not more customers — it is knowing which
          services, techs, and time slots drive profit.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Built for the Way Auto Shops Work</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Meridian understands appointment-based, service-heavy businesses and delivers insights tailored to your workflow.
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
        <h2 className="text-2xl md:text-3xl font-bold mb-4">Run a Smarter Shop, Starting Today</h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS and see which services, techs, and time slots drive your bottom line. First month is on us.
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
