import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Zap,
  Clock,
  TrendingUp,
  BarChart3,
  Users,
  Trash2,
  Timer,
  UtensilsCrossed,
  Gauge,
} from 'lucide-react'
import SEO from '@/components/SEO'

const faqItems = [
  {
    q: 'What analytics matter most for fast food and QSR?',
    a: 'The critical QSR KPIs are speed of service (order-to-handoff time), order accuracy rate, transactions per labor hour, average ticket size, and food waste percentage. Meridian tracks all of these from your POS data automatically.',
  },
  {
    q: 'Can Meridian track drive-through performance?',
    a: 'Yes. Meridian analyzes order volume patterns, peak window timing, and transaction throughput to help you identify drive-through bottlenecks. While we do not install hardware timers, we surface POS-based speed and volume data that reveals where your line slows down.',
  },
  {
    q: 'How does Meridian help reduce food waste?',
    a: 'Meridian uses AI to forecast demand by hour, day, and season. By matching prep quantities to predicted demand, restaurants typically reduce waste by 15-30% in the first month. You also get alerts when actual sales deviate from forecasts so you can adjust in real time.',
  },
  {
    q: 'Does Meridian work with QSR franchise POS systems?',
    a: 'Yes. Meridian integrates with Square, Toast, Clover, Lightspeed, and 75+ other POS systems commonly used in fast food and QSR. If your franchise uses a proprietary system, we can also ingest data via scheduled CSV exports.',
  },
  {
    q: 'How much does QSR analytics software cost?',
    a: 'Meridian starts at $250/month per location with the first month free. No long-term contracts or setup fees. For multi-location QSR operators, volume pricing is available — contact us for a custom quote.',
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
    icon: Timer,
    title: 'Drive-Through Bottlenecks Are Invisible',
    description:
      'You know the line backs up at noon, but you cannot see where orders stall. Without timing analytics, you are losing customers who drive past.',
    color: '#EF4444',
  },
  {
    icon: Trash2,
    title: 'Food Waste From Bad Forecasting',
    description:
      'Over-prepping for a slow Tuesday or running out on a busy Friday — without demand forecasting, you waste food or lose sales. Both cost real money.',
    color: '#F59E0B',
  },
  {
    icon: Users,
    title: 'Labor Scheduling by Gut Feel',
    description:
      'Too many crew members during a slow shift, not enough during a rush. Without peak-period analytics, your labor cost eats into already-thin QSR margins.',
    color: '#EF4444',
  },
]

const features = [
  {
    icon: TrendingUp,
    title: 'Order Volume Forecasting',
    description: 'AI predicts hourly and daily order counts so you can prep the right amount and staff the right number of people.',
  },
  {
    icon: BarChart3,
    title: 'Peak Period Analytics',
    description: 'Visualize your rush patterns by hour, day, and season. Know exactly when demand spikes and plan accordingly.',
  },
  {
    icon: Gauge,
    title: 'Speed of Service Tracking',
    description: 'Monitor transaction throughput and identify bottleneck periods. Optimize your line for faster order completion.',
  },
  {
    icon: Trash2,
    title: 'Waste Reduction',
    description: 'Match prep quantities to AI forecasts. Get real-time alerts when actual sales deviate so you can adjust before waste happens.',
  },
  {
    icon: Users,
    title: 'Labor Optimization',
    description: 'Map staffing to demand curves. Know exactly when to add crew and when to cut — down to the half-hour.',
  },
  {
    icon: UtensilsCrossed,
    title: 'Menu Performance',
    description: 'See which items drive volume, which drive margin, and which do neither. Optimize your menu board and combos with data.',
  },
]

const steps = [
  {
    num: '01',
    title: 'Connect Your POS',
    description: 'Authorize Square, Toast, Clover, or any of 75+ POS systems. No API keys, no IT team needed.',
  },
  {
    num: '02',
    title: 'AI Analyzes Your Data',
    description: 'Meridian processes your transaction history to model demand patterns, speed metrics, and cost structures.',
  },
  {
    num: '03',
    title: 'Get Actionable Insights',
    description: 'Demand forecasts, waste reduction alerts, labor recommendations, and menu insights — operational from day one.',
  },
]

const siblingPages = [
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Auto Shops', to: '/for/auto-shops' },
  { label: 'Smoke Shops', to: '/for/smoke-shops' },
]

export default function FastFoodPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Fast Food Analytics Software — Speed Meets Intelligence | Meridian"
        description="AI-powered analytics for fast food and QSR. Optimize drive-through timing, track order accuracy, forecast rush periods. Works with Square, Toast, Clover."
        path="/for/fast-food"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">For Fast Food & QSR</p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Fast Food Analytics Software
            <br />
            <span className="text-[#17C5B0]">Speed Meets Intelligence</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            In QSR, seconds matter. Meridian turns your POS data into demand forecasts, waste reduction, and labor
            optimization — so every shift runs at peak efficiency.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">The Hidden Costs of Running Blind</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Fast food runs on volume and speed. Without analytics, small inefficiencies multiply across hundreds of daily
          transactions into massive losses.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Analytics Built for QSR Speed</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Meridian is designed for high-volume, speed-critical operations where every minute of efficiency translates to
          real dollars.
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
        <h2 className="text-2xl md:text-3xl font-bold mb-4">Faster Service, Lower Waste, Higher Margins</h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS and let AI optimize your QSR operations. First month free, no contracts, no setup fees.
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
