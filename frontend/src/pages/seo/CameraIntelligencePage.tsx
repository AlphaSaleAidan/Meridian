import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ChevronDown,
  ArrowRight,
  Camera,
  Eye,
  EyeOff,
  ShoppingBag,
  TrendingUp,
  Clock,
  MapPin,
  Users,
  DollarSign,
  UserCheck,
  Shield,
  Lock,
  Server,
  Wifi,
  Brain,
  BarChart3,
  Gauge,
  Coffee,
  UtensilsCrossed,
  Store,
  Wrench,
  Layers,
  Zap,
} from 'lucide-react'
import SEO from '@/components/SEO'

const ACCENT = '#17C5B0'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Do I need to buy new cameras?',
    a: "Most operators don't. Any IP camera with 720p+ resolution works. If you have existing security cameras, those are usually sufficient. A single new IP camera costs $50-150 if needed.",
  },
  {
    q: 'Is this legal in Canada?',
    a: "Yes. Under PIPEDA, aggregate counting without facial recognition or individual tracking is permitted with proper signage. Meridian's default mode is fully anonymous — no biometric data is stored.",
  },
  {
    q: 'How accurate is the counting?',
    a: '95-98% accuracy under normal conditions, using state-of-the-art computer vision. That exceeds infrared beam counters (80-85%), Wi-Fi probing (70-80%), and manual counting (60-70%).',
  },
  {
    q: 'What POS systems does this work with?',
    a: 'Square, Toast, Clover, Lightspeed, Revel, TouchBistro, and 75+ others. One-click OAuth connection — no API keys, no IT department needed.',
  },
  {
    q: 'What makes this different from other foot traffic solutions?',
    a: "Most foot traffic tools just count people. Meridian is the first platform to cross-reference camera counts with actual POS transaction data — giving you conversion rates, revenue per visitor, and zone-level profitability. Counting is step one. Knowing what they bought is what changes your business.",
  },
  {
    q: 'How much does camera intelligence cost?',
    a: 'Camera intelligence is included in the Premium plan at $490/month. The Standard plan at $250/month includes POS analytics without camera features.',
  },
]

const jsonLd = [
  {
    '@type': 'SoftwareApplication',
    name: 'Meridian Camera Intelligence',
    applicationCategory: 'BusinessApplication',
    description:
      'The first analytics platform to cross-reference camera AI with POS transaction data. Count foot traffic, measure dwell time, and know exactly who bought — all from your existing cameras.',
    url: 'https://meridian.tips/features/camera-intelligence',
    offers: { '@type': 'Offer', price: '490', priceCurrency: 'USD' },
    provider: {
      '@type': 'Organization',
      name: 'Meridian Intelligence',
      url: 'https://meridian.tips',
    },
    operatingSystem: 'Cloud-based',
  },
  {
    '@type': 'FAQPage',
    mainEntity: faqItems.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  },
  {
    '@type': 'BreadcrumbList',
    itemListElement: [
      {
        '@type': 'ListItem',
        position: 1,
        name: 'Home',
        item: 'https://meridian.tips',
      },
      {
        '@type': 'ListItem',
        position: 2,
        name: 'Features',
        item: 'https://meridian.tips/features',
      },
      {
        '@type': 'ListItem',
        position: 3,
        name: 'Camera Intelligence',
        item: 'https://meridian.tips/features/camera-intelligence',
      },
    ],
  },
]

/* ── Cross-Reference Metrics ─────────────────────── */

const crossRefMetrics = [
  {
    icon: Gauge,
    title: 'Conversion Rate by Hour',
    desc: 'Know that 340 people walked in between 11am-1pm, 238 made a purchase. Your lunch conversion is 70%. On Tuesdays it drops to 58%. Now you know where to focus.',
  },
  {
    icon: DollarSign,
    title: 'Revenue Per Visitor',
    desc: 'Your average transaction is $18.50 but your revenue per visitor is $12.95. That $5.55 gap represents people who walked in and left. Close it and you add $1,900/day.',
  },
  {
    icon: Clock,
    title: 'Dwell Time → Purchase Correlation',
    desc: 'Customers who browse for 4+ minutes convert at 2.1x the rate of those under 2 minutes. Optimize your layout, signage, and greeting to increase dwell time.',
  },
  {
    icon: MapPin,
    title: 'Zone Profitability',
    desc: 'Camera heatmaps show the back seating zone gets 8% of traffic but your POS shows it generates 3% of revenue. Revenue per square foot: $4/day vs $48/day at the counter.',
  },
  {
    icon: TrendingUp,
    title: 'Walk-Away Analysis',
    desc: "34% of your foot traffic leaves without buying. Camera timestamps + POS gaps identify exactly when and how long they stayed before walking out. That's not a traffic problem — it's a conversion problem.",
  },
  {
    icon: UserCheck,
    title: 'Staff Performance by Traffic',
    desc: 'Cross-reference which staff are on shift during high-traffic hours with actual conversion rates. One shift converts at 72%, another at 54% with similar traffic. The difference is $840/week.',
  },
]

/* ── How It Works Steps ──────────────────────────── */

const howItWorks = [
  {
    step: '1',
    icon: Camera,
    title: 'Connect Your Cameras',
    desc: 'Works with any IP camera you already have — 720p+, ceiling-mounted, pointed at entries/zones. No new hardware required for most operators.',
  },
  {
    step: '2',
    icon: Brain,
    title: 'AI Counts Anonymously',
    desc: 'Computer vision counts people entering, exiting, and moving through zones. No facial recognition, no biometric storage. Fully PIPEDA and CCPA compliant.',
  },
  {
    step: '3',
    icon: Wifi,
    title: 'POS Data Syncs Automatically',
    desc: 'Meridian pulls transactions from Square, Toast, Clover, or 75+ systems via one-click OAuth. Camera counts and POS sales are time-synced to the minute.',
  },
  {
    step: '4',
    icon: BarChart3,
    title: 'Cross-Referenced Dashboard',
    desc: 'Conversion rates, revenue per visitor, zone heatmaps overlaid with sales data — all updating in real time. Anomaly alerts fire when the numbers diverge.',
  },
]

/* ── Privacy Cards ───────────────────────────────── */

const privacyCards = [
  {
    icon: EyeOff,
    title: 'Anonymous Counting Only',
    desc: 'We count people, not faces. No facial recognition, no biometric data, no individual tracking. Just aggregate counts by zone and time.',
  },
  {
    icon: Shield,
    title: 'Compliance Built In',
    desc: 'PIPEDA (Canada), CCPA (California), GDPR-ready. Configurable compliance modes: anonymous, opt-in identity, or disabled per camera.',
  },
  {
    icon: Lock,
    title: 'You Own Your Data',
    desc: 'Camera analysis runs on compressed video. Raw footage never leaves your network. Only aggregate metrics (counts, dwell times, heatmaps) are synced to the dashboard.',
  },
]

/* ── Industry Cards ──────────────────────────────── */

const industryCards = [
  {
    icon: UtensilsCrossed,
    title: 'Restaurants & QSR',
    desc: 'Know your lunch rush conversion rate, not just your lunch rush revenue.',
  },
  {
    icon: Coffee,
    title: 'Coffee Shops',
    desc: 'See how many people enter, see the line, and leave — then fix the bottleneck.',
  },
  {
    icon: Store,
    title: 'Retail & Smoke Shops',
    desc: 'Dwell time heatmaps show which displays drive purchases vs. which are dead zones.',
  },
  {
    icon: Wrench,
    title: 'Auto Shops',
    desc: 'Service bay occupancy + ticket data = revenue per bay per hour.',
  },
]

/* ── FAQ Component ───────────────────────────────── */

function FAQ({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between p-5 text-left hover:bg-[#111113] transition-colors"
      >
        <span className="text-[#F5F5F7] font-medium text-[15px] pr-4">{q}</span>
        <ChevronDown
          size={18}
          className={`text-[#6B7280] flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
        />
      </button>
      <div className={`grid transition-all duration-200 ease-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div className="overflow-hidden">
          <div className="px-5 pb-5 text-[#A1A1A8] text-[14px] leading-relaxed border-t border-[#1F1F23] pt-4">
            {a}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Page Component ──────────────────────────────── */

export default function CameraIntelligencePage() {
  return (
    <>
      <SEO
        title="Camera Intelligence + POS Cross-Referencing: See What Others Can't | Meridian"
        description="Meridian is the first analytics platform to cross-reference camera AI with POS data. Count foot traffic, measure dwell time, and know exactly who bought — all from your existing cameras."
        path="/features/camera-intelligence"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        {/* Breadcrumb */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">
              Home
            </Link>
            <ChevronRight size={12} />
            <span className="text-[#6B7280]">Features</span>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">Camera Intelligence</span>
          </nav>
        </div>

        {/* Hero */}
        <header className="max-w-4xl mx-auto px-4 sm:px-6 pb-16 text-center">
          <div className="flex justify-center mb-4">
            <span
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[12px] font-semibold tracking-wide uppercase"
              style={{ backgroundColor: `${ACCENT}15`, color: ACCENT }}
            >
              <Zap size={12} />
              First in Industry
            </span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-bold tracking-tight mb-4 leading-tight">
            Camera Intelligence Meets POS Data{' '}
            <span className="block mt-1" style={{ color: ACCENT }}>
              For the First Time
            </span>
          </h1>
          <p className="text-[#A1A1A8] text-[16px] sm:text-[17px] leading-relaxed max-w-2xl mx-auto mb-8">
            Other platforms count people OR analyze sales. Meridian is the first to cross-reference
            both — giving you conversion rates, revenue per visitor, and zone-level profitability
            that no one else can.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white rounded-lg transition-colors"
            style={{ backgroundColor: ACCENT }}
            onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#14b09d')}
            onMouseOut={(e) => (e.currentTarget.style.backgroundColor = ACCENT)}
          >
            See It in Action — First Month Free <ArrowRight size={15} />
          </Link>
        </header>

        <main className="max-w-4xl mx-auto px-4 sm:px-6 pb-16">
          {/* ── The Problem ──────────────────────────── */}
          <section className="mb-20">
            <h2 className="text-2xl font-bold mb-3 text-center">
              The Blind Spots Every Operator Has
            </h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              Camera-only and POS-only analytics each tell half the story. Cross-referencing tells
              the whole story.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Camera-Only */}
              <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#1F1F23]">
                    <Eye size={18} className="text-[#6B7280]" />
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold text-[15px]">
                    Camera-Only Analytics
                  </h3>
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed">
                  Foot traffic counters tell you how many people walked in. They cannot tell you
                  which ones bought, what they bought, or whether your busiest hour is also your most
                  profitable.
                </p>
              </div>

              {/* POS-Only */}
              <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#1F1F23]">
                    <ShoppingBag size={18} className="text-[#6B7280]" />
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold text-[15px]">POS-Only Analytics</h3>
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed">
                  Transaction data tells you what sold. It cannot tell you how many people walked in
                  and left without buying, where they spent time in your space, or why your conversion
                  rate dropped.
                </p>
              </div>

              {/* Cross-Referenced — highlighted */}
              <div
                className="rounded-xl p-6"
                style={{
                  border: `1px solid ${ACCENT}40`,
                  backgroundColor: `${ACCENT}08`,
                }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center"
                    style={{ backgroundColor: `${ACCENT}20` }}
                  >
                    <Layers size={18} style={{ color: ACCENT }} />
                  </div>
                  <h3 className="font-semibold text-[15px]" style={{ color: ACCENT }}>
                    Cross-Referenced Intelligence
                  </h3>
                </div>
                <p className="text-[#A1A1A8] text-[13px] leading-relaxed">
                  When you connect both, you unlock metrics that neither system can produce alone:
                  conversion rate by hour, revenue per visitor, dwell-to-purchase correlation, and
                  zone profitability.
                </p>
              </div>
            </div>
          </section>

          {/* ── What Cross-Referencing Unlocks ────────── */}
          <section className="mb-20">
            <h2 className="text-2xl font-bold mb-3 text-center">
              Metrics That Don't Exist Without Both Data Sources
            </h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              These six metrics require both camera counts and POS transactions. No single system can
              produce them.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {crossRefMetrics.map((metric) => (
                <div
                  key={metric.title}
                  className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 hover:border-[#2A2A30] transition-colors"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${ACCENT}15` }}
                    >
                      <metric.icon size={18} style={{ color: ACCENT }} />
                    </div>
                    <h3 className="text-[#F5F5F7] font-semibold text-[15px]">{metric.title}</h3>
                  </div>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{metric.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* ── How It Works ─────────────────────────── */}
          <section className="mb-20">
            <h2 className="text-2xl font-bold mb-3 text-center">
              From Camera Feed to Revenue Insight in 24 Hours
            </h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              Four steps. No new hardware for most operators. No IT department needed.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {howItWorks.map((item) => (
                <div
                  key={item.step}
                  className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 text-center"
                >
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center mx-auto mb-3"
                    style={{ backgroundColor: `${ACCENT}15` }}
                  >
                    <item.icon size={20} style={{ color: ACCENT }} />
                  </div>
                  <div
                    className="text-[11px] font-bold uppercase tracking-wider mb-2"
                    style={{ color: ACCENT }}
                  >
                    Step {item.step}
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold text-[15px] mb-2">{item.title}</h3>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* ── Privacy First ────────────────────────── */}
          <section className="mb-20">
            <div className="text-center mb-8">
              <div className="flex justify-center mb-4">
                <div
                  className="w-12 h-12 rounded-xl flex items-center justify-center"
                  style={{ backgroundColor: `${ACCENT}15` }}
                >
                  <Shield size={24} style={{ color: ACCENT }} />
                </div>
              </div>
              <h2 className="text-2xl font-bold mb-2">Privacy-First by Design</h2>
              <p className="text-[#A1A1A8] text-[15px]">
                Camera intelligence without surveillance.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {privacyCards.map((card) => (
                <div
                  key={card.title}
                  className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 hover:border-[#2A2A30] transition-colors"
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center"
                      style={{ backgroundColor: `${ACCENT}15` }}
                    >
                      <card.icon size={18} style={{ color: ACCENT }} />
                    </div>
                    <h3 className="text-[#F5F5F7] font-semibold text-[15px]">{card.title}</h3>
                  </div>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{card.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* ── Who Uses This ────────────────────────── */}
          <section className="mb-20">
            <h2 className="text-2xl font-bold mb-3 text-center">
              Built for Operators Who Want the Full Picture
            </h2>
            <p className="text-[#A1A1A8] text-[15px] text-center max-w-xl mx-auto mb-8">
              Camera intelligence works for any business with foot traffic and a point of sale.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {industryCards.map((card) => (
                <div
                  key={card.title}
                  className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 hover:border-[#2A2A30] transition-colors"
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center mb-3"
                    style={{ backgroundColor: `${ACCENT}15` }}
                  >
                    <card.icon size={18} style={{ color: ACCENT }} />
                  </div>
                  <h3 className="text-[#F5F5F7] font-semibold text-[15px] mb-2">{card.title}</h3>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{card.desc}</p>
                </div>
              ))}
            </div>
          </section>

          {/* ── FAQ ──────────────────────────────────── */}
          <section className="mb-16">
            <h2 className="text-xl font-bold mb-6">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {faqItems.map((faq, i) => (
                <FAQ key={i} q={faq.q} a={faq.a} />
              ))}
            </div>
          </section>

          {/* ── Internal Links ───────────────────────── */}
          <section className="mb-10">
            <h3 className="text-lg font-semibold mb-4">Related Resources</h3>
            <div className="flex flex-wrap gap-2">
              {[
                {
                  to: '/blog/restaurant-foot-traffic-analytics-guide',
                  label: 'Foot Traffic Analytics Guide',
                },
                { to: '/what-is-pos-analytics', label: 'What Is POS Analytics?' },
                { to: '/for/restaurants', label: 'Restaurants' },
                { to: '/for/coffee-shops', label: 'Coffee Shops' },
                { to: '/vs/spreadsheets', label: 'vs Spreadsheets' },
                { to: '/vs/toast-analytics', label: 'vs Toast Analytics' },
              ].map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors"
                >
                  {link.label} <ChevronRight size={12} />
                </Link>
              ))}
            </div>
          </section>
        </main>

        {/* ── Bottom CTA ─────────────────────────────── */}
        <section className="py-16 border-t border-[#1F1F23]/40 relative">
          <div
            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-[0.06]"
            style={{ background: `radial-gradient(circle, ${ACCENT} 0%, transparent 70%)` }}
          />
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl font-bold">Stop Guessing. Start Cross-Referencing.</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">
              Connect your POS and cameras in under 10 minutes. Get cross-referenced intelligence
              within 24 hours. First month free.
            </p>
            <Link
              to="/demo"
              className="mt-6 inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white rounded-lg transition-colors"
              style={{ backgroundColor: ACCENT }}
              onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#14b09d')}
              onMouseOut={(e) => (e.currentTarget.style.backgroundColor = ACCENT)}
            >
              See It in Action — First Month Free <ArrowRight size={15} />
            </Link>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">
              Home
            </Link>
            <Link to="/guides" className="hover:text-[#A1A1A8]">
              Guides
            </Link>
            <Link to="/faq" className="hover:text-[#A1A1A8]">
              FAQ
            </Link>
            <Link to="/blog" className="hover:text-[#A1A1A8]">
              Blog
            </Link>
          </div>
        </footer>
      </div>
    </>
  )
}
