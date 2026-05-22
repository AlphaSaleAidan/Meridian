import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Coffee,
  Clock,
  TrendingUp,
  BarChart3,
  Users,
  Heart,
  Package,
  DollarSign,
} from 'lucide-react'
import SEO from '@/components/SEO'

const faqItems = [
  {
    q: 'What metrics should a coffee shop track?',
    a: 'The most important cafe KPIs are revenue per labor hour, average ticket size, drinks sold per hour, peak-hour conversion rate, and customer visit frequency. Meridian tracks all of these automatically from your POS data with zero manual work.',
  },
  {
    q: 'How much does coffee shop analytics cost?',
    a: 'Meridian starts at $250/month per location with your first month free. No contracts, no setup fees. Most cafes recover the cost within two weeks through better staffing and reduced waste alone.',
  },
  {
    q: 'How fast is setup for a cafe?',
    a: 'About 5 minutes. Authorize your POS connection via OAuth (Square, Toast, Clover, or others), and Meridian immediately begins analyzing your historical data. You will see your first insights before your next espresso shot.',
  },
  {
    q: 'Does Meridian work with Square POS?',
    a: 'Yes. Meridian has a native Square integration that pulls transactions, item-level sales, customer data, and labor hours automatically. It also works with Toast, Clover, Lightspeed, Shopify POS, and 75+ other systems.',
  },
  {
    q: 'Can Meridian help manage multiple cafe locations?',
    a: 'Absolutely. Meridian provides cross-location dashboards so you can compare revenue, product mix, staffing efficiency, and customer patterns across all your cafes in one place. Spot your best and worst performers instantly.',
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
    title: 'No Visibility Into Drink Margins',
    description:
      'A latte costs $1.20 to make but sells for $5.50 — or does it? Without item-level margin tracking, you cannot tell which drinks actually drive profit.',
    color: '#EF4444',
  },
  {
    icon: Clock,
    title: 'Inconsistent Rush-Hour Staffing',
    description:
      'Your morning rush shifts every season. Without peak-hour analytics, you end up with three baristas when you need five — or five when you need three.',
    color: '#F59E0B',
  },
  {
    icon: Heart,
    title: 'Loyalty Programs With No Data',
    description:
      'You run a punch-card or app-based loyalty program but have no idea which customers are slipping away or which promotions actually bring people back.',
    color: '#EF4444',
  },
]

const features = [
  {
    icon: Clock,
    title: 'Revenue Per Hour Tracking',
    description: 'See exactly how much each hour generates so you can optimize open/close times and shift schedules.',
  },
  {
    icon: Coffee,
    title: 'Product Mix Analysis',
    description: 'Know which drinks are stars and which are dead weight. Optimize your menu board for margin and speed.',
  },
  {
    icon: TrendingUp,
    title: 'Peak Hours Optimization',
    description: 'AI identifies your true rush patterns — by day, by season, by weather — so you staff perfectly every time.',
  },
  {
    icon: Users,
    title: 'Barista Performance',
    description: 'Track transactions per hour, average ticket, and upsell rates by employee. Coach with data, not guesses.',
  },
  {
    icon: BarChart3,
    title: 'Customer Frequency',
    description: 'RFM segmentation shows who visits daily, who is at risk of churning, and who you have already lost.',
  },
  {
    icon: Package,
    title: 'Inventory Forecasting',
    description: 'Predict milk, bean, and supply needs based on sales velocity. Reduce waste and avoid 86-ing your best seller.',
  },
]

const steps = [
  {
    num: '01',
    title: 'Connect Your POS',
    description: 'Authorize Square, Toast, Clover, or any of 75+ POS systems. Takes under 5 minutes, no API keys.',
  },
  {
    num: '02',
    title: 'AI Analyzes Your Data',
    description: 'Meridian ingests your sales history and identifies patterns in product mix, rush timing, and customer behavior.',
  },
  {
    num: '03',
    title: 'Get Actionable Insights',
    description: 'Revenue forecasts, staffing recommendations, product performance, and anomaly alerts — all from day one.',
  },
]

const siblingPages = [
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Auto Shops', to: '/for/auto-shops' },
  { label: 'Fast Food & QSR', to: '/for/fast-food' },
  { label: 'Smoke Shops', to: '/for/smoke-shops' },
]

export default function CoffeeShopsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Coffee Shop Analytics — Track What Matters for Your Cafe | Meridian"
        description="AI analytics built for coffee shops and cafes. Track revenue per hour, best-selling drinks, peak rush patterns, and barista performance. Works with Square and Toast."
        path="/for/coffee-shops"
        jsonLd={faqJsonLd}
      />

      {/* ── Hero ──────────────────────────────────────── */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">For Coffee Shops</p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Coffee Shop Analytics
            <br />
            <span className="text-[#17C5B0]">Track What Matters for Your Cafe</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            From espresso margins to rush-hour staffing, Meridian gives you the numbers you need to run a more
            profitable cafe.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">The Blind Spots Killing Cafe Profits</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Coffee shops operate on speed and volume. Without analytics, small inefficiencies compound into thousands in
          lost revenue every month.
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
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">Analytics Built for Cafes</h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          Meridian understands the cafe business model — high volume, tight margins, and speed-dependent revenue.
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
        <h2 className="text-2xl md:text-3xl font-bold mb-4">Your Cafe Deserves Better Than Guesswork</h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS and see what your data has been trying to tell you. First month free, no contracts.
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
