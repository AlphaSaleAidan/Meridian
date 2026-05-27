import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  ShieldAlert,
  AlertTriangle,
  BarChart3,
  Users,
  DollarSign,
  Building2,
  MessageSquare,
  Search,
  Plug,
  CheckCircle2,
  Package,
  TrendingUp,
  ShoppingCart,
  Brain,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Is Meridian a replacement for MarketMan?',
    a: 'They solve different problems. MarketMan is inventory management — purchase orders, recipe costing, stock counts. Meridian is AI-powered analytics — revenue forecasting, anomaly detection, customer intelligence. Many operators use both.',
  },
  {
    q: 'Can I use both Meridian and MarketMan?',
    a: 'Absolutely. MarketMan handles your food cost and inventory workflows. Meridian handles revenue analytics, anomaly detection, labor optimization, and customer segmentation. Together they give you complete operational intelligence.',
  },
  {
    q: 'What does Meridian do that MarketMan doesn\'t?',
    a: 'Revenue forecasting, real-time anomaly detection (theft, void spikes, discount abuse), customer segmentation and churn prediction, labor cost optimization, and cross-location benchmarking. MarketMan focuses on what goes into making food — Meridian focuses on what happens after it\'s sold.',
  },
  {
    q: 'How does pricing compare?',
    a: 'MarketMan ranges from $200–400/month depending on features and locations. Meridian starts at $250/month. If you need inventory management, you\'ll want MarketMan. If you need analytics and AI insights, Meridian. For complete coverage, both together still costs less than Restaurant365.',
  },
  {
    q: 'Does Meridian track food cost?',
    a: 'Meridian can surface food cost trends from your POS data (COGS ratios, menu item margins), but it doesn\'t do purchase order management, recipe costing, or stock counts. That\'s where MarketMan excels. Meridian shows you the revenue side — what\'s selling, what\'s profitable, and what\'s suspicious.',
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
    feature: 'Primary Focus',
    marketman: 'Inventory and food cost management',
    meridian: 'Revenue analytics and AI insights',
    winner: 'neutral',
  },
  {
    feature: 'Anomaly Detection',
    marketman: 'Inventory variance alerts',
    meridian: 'AI-powered theft, void, and discount abuse detection',
    winner: 'meridian',
  },
  {
    feature: 'Revenue Forecasting',
    marketman: 'None',
    meridian: 'AI/ML daily, weekly, and monthly forecasts',
    winner: 'meridian',
  },
  {
    feature: 'Customer Intelligence',
    marketman: 'None',
    meridian: 'Segmentation, churn prediction, LTV scoring',
    winner: 'meridian',
  },
  {
    feature: 'Inventory Management',
    marketman: 'Full PO, recipe costing, stock counts',
    meridian: 'COGS trends from POS data (not full inventory)',
    winner: 'marketman',
  },
  {
    feature: 'Labor Analytics',
    marketman: 'None',
    meridian: 'Labor cost optimization + scheduling recommendations',
    winner: 'meridian',
  },
  {
    feature: 'Recipe Costing',
    marketman: 'Detailed recipe-level cost tracking',
    meridian: 'Menu item margin analysis from sales data',
    winner: 'marketman',
  },
  {
    feature: 'Real-Time Alerts',
    marketman: 'Low stock and variance alerts',
    meridian: 'Configurable alerts for any metric or anomaly',
    winner: 'meridian',
  },
  {
    feature: 'Cross-Location',
    marketman: 'Multi-location inventory',
    meridian: 'Cross-location benchmarking, ranking, and comparison',
    winner: 'meridian',
  },
  {
    feature: 'Supplier Management',
    marketman: 'Full vendor/PO management',
    meridian: 'None — focused on revenue-side analytics',
    winner: 'marketman',
  },
]

/* ── Why Operators Choose MarketMan ───────────────── */

const whyMarketMan = [
  { icon: Package, label: 'Best-in-Class Inventory', detail: 'Industry-leading purchase orders, recipe costing, and stock management' },
  { icon: DollarSign, label: 'Food Cost Control', detail: 'Real-time tracking of actual vs. theoretical food cost' },
  { icon: ShoppingCart, label: 'Supplier Integration', detail: 'Direct ordering from vendors, invoice scanning, AP management' },
]

const whereFallsShort = [
  { icon: BarChart3, label: 'No revenue analytics', detail: 'Tracks what you buy, not what you sell or why' },
  { icon: ShieldAlert, label: 'No anomaly detection on sales', detail: 'Can\'t detect theft patterns, void abuse, or discount fraud' },
  { icon: Users, label: 'No customer intelligence', detail: 'Doesn\'t segment customers or predict churn' },
  { icon: TrendingUp, label: 'No predictive forecasting', detail: 'Can\'t forecast revenue, demand, or staffing needs' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'Meridian connects to Square, Toast, Clover, and 75+ POS systems. 5 minutes, one-click OAuth.',
  },
  {
    num: '02',
    icon: CheckCircle2,
    title: 'Keep MarketMan Running',
    desc: 'No disruption to your inventory workflows. Meridian reads from your POS alongside MarketMan.',
  },
  {
    num: '03',
    icon: Brain,
    title: 'Get Revenue Intelligence',
    desc: 'AI-powered insights, anomaly alerts, and forecasting — filling the gap MarketMan doesn\'t cover.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'vs Spreadsheets', to: '/vs/spreadsheets' },
  { label: 'vs Restaurant365', to: '/vs/restaurant365' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsMarketManPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. MarketMan: Inventory Tracking vs. AI-Powered Analytics | Meridian"
        description="MarketMan excels at inventory. But inventory is just one piece. See how AI analytics covers revenue, anomalies, customers, and forecasting that MarketMan can't."
        path="/vs/marketman"
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
            Meridian vs. MarketMan:
            <br />
            <span className="text-[#17C5B0]">Inventory Tracking vs. AI-Powered Analytics</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            MarketMan tells you what you bought. Meridian tells you what you earned, what you lost, and what happens next.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See the Difference — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── The MarketMan Problem ────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Inventory-Only Blind Spot</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          MarketMan is excellent at what it does: managing inventory, tracking food cost, and
          streamlining supplier workflows. But inventory is only half the picture. What happens
          after the food leaves the kitchen is where revenue is made, lost, or stolen.
        </p>

        {/* Why owners use MarketMan */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators choose MarketMan
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyMarketMan.map((item) => (
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

        {/* Where it falls short */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where MarketMan falls short for analytics
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {whereFallsShort.map((item) => (
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
            Ten categories where MarketMan and Meridian go head to head. Different tools, different strengths.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                MarketMan
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
                <div className={`px-5 py-3 text-sm ${row.winner === 'marketman' ? 'font-medium text-[#F5F5F7]' : 'text-[#A1A1A8]'}`}>
                  {row.marketman}
                </div>
                <div className={`px-5 py-3 text-sm ${row.winner === 'meridian' ? 'font-medium text-[#17C5B0]' : row.winner === 'neutral' ? 'text-[#F5F5F7]' : 'text-[#A1A1A8]'}`}>
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost of Blind Spots ────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost of Blind Spots
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">68%</div>
              <p className="text-sm text-[#A1A1A8] mt-1">of operators say they lack visibility into sales anomalies</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$5,200/yr</div>
              <p className="text-sm text-[#A1A1A8] mt-1">average revenue lost to undetected POS fraud</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">0</div>
              <p className="text-sm text-[#A1A1A8] mt-1">the number of revenue forecasting features in inventory tools</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">Inventory tools see half the picture</div>
            <p className="text-sm text-[#A1A1A8] mt-2">What happens after the food is sold matters just as much as what goes into making it</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            MarketMan watches the supply side: what you order, what it costs, and how much you have
            in stock. But it cannot tell you when a bartender is giving away free drinks, when a
            manager is voiding transactions after close, or when a location is trending 12% below
            forecast.
          </p>
          <p>
            Inventory variance alerts catch some problems, but they only surface when physical counts
            don't match expected counts. By then, the damage has been done. Revenue-side anomaly
            detection catches problems in real time, before they show up as shrinkage.
          </p>
        </div>
      </section>

      {/* ── When MarketMan Makes Sense ───────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When MarketMan Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  If your primary challenge is food cost control, supplier management, and inventory
                  tracking, MarketMan is a great tool. It does those things better than most
                  alternatives, and it integrates well with major POS systems.
                </p>
                <p>
                  MarketMan is the right choice when you need to{' '}
                  <span className="text-[#F5F5F7] font-medium">reduce food waste</span>, manage{' '}
                  <span className="text-[#F5F5F7] font-medium">recipe costing at scale</span>, or
                  streamline{' '}
                  <span className="text-[#F5F5F7] font-medium">vendor purchasing across locations</span>.
                  These are critical back-of-house operations that Meridian does not replace.
                </p>
                <p>
                  The question is not MarketMan or Meridian. The question is whether inventory
                  management alone gives you the visibility you need. If you also need revenue
                  intelligence, anomaly detection, customer insights, and AI-powered forecasting,
                  Meridian fills the gap.
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
          Adding Meridian doesn't mean leaving MarketMan. They run side by side with zero disruption.
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
          Complete the Picture
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          MarketMan handles inventory. Meridian handles everything else. Connect your POS in 5 minutes.
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
