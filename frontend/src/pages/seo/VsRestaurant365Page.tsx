import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Zap,
  Clock,
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
  Layers,
  BrainCircuit,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Is Meridian a replacement for Restaurant365?',
    a: 'Not exactly. R365 is an all-in-one platform (accounting, inventory, scheduling, analytics). Meridian is focused exclusively on AI-powered analytics and insights. If you need everything in one system, R365 is comprehensive. If you want smarter analytics at a fraction of the cost, Meridian is the answer.',
  },
  {
    q: 'How does pricing compare?',
    a: "R365 starts at $400-600/month per location for their full suite. Meridian's analytics starts at $250/month. If you only need analytics and insights — not accounting or HR — Meridian delivers more intelligence at lower cost.",
  },
  {
    q: 'Can I use Meridian alongside R365?',
    a: 'Yes. Many operators use R365 for back-office operations (accounting, AP/AR, scheduling) and Meridian for real-time analytics, anomaly detection, and AI insights. They connect to the same POS data.',
  },
  {
    q: 'What does Meridian do better than R365?',
    a: "AI-native anomaly detection, real-time alerting, predictive forecasting, and customer segmentation. R365 has reporting, but Meridian's AI layer finds patterns and anomalies that traditional reporting misses.",
  },
  {
    q: "How long is R365's implementation vs Meridian?",
    a: 'R365 typically takes 4-8 weeks for full implementation with training. Meridian connects to your POS in 5 minutes and delivers insights within 24 hours. No implementation project needed.',
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
    feature: 'Setup Time',
    competitor: '4-8 weeks implementation',
    meridian: '5 minutes — connect POS and go',
    winner: 'meridian',
  },
  {
    feature: 'Monthly Cost',
    competitor: '$400-600+/mo per location',
    meridian: '$250/mo — analytics only',
    winner: 'meridian',
  },
  {
    feature: 'AI/ML Analytics',
    competitor: 'Basic reporting and dashboards',
    meridian: 'AI-native — anomaly detection, forecasting, segmentation',
    winner: 'meridian',
  },
  {
    feature: 'Anomaly Detection',
    competitor: 'Manual report review',
    meridian: 'Real-time AI alerts for theft, voids, comp abuse',
    winner: 'meridian',
  },
  {
    feature: 'Implementation',
    competitor: 'Dedicated onboarding team, weeks of training',
    meridian: 'Self-service, insights in 24 hours',
    winner: 'meridian',
  },
  {
    feature: 'Scope',
    competitor: 'All-in-one (accounting, HR, inventory, analytics)',
    meridian: 'Focused — analytics and intelligence only',
    winner: 'tie',
  },
  {
    feature: 'Contract',
    competitor: 'Annual contract required',
    meridian: 'Month-to-month, cancel anytime',
    winner: 'meridian',
  },
  {
    feature: 'Real-Time Alerts',
    competitor: 'Scheduled report delivery',
    meridian: 'Instant SMS/email alerts on anomalies',
    winner: 'meridian',
  },
  {
    feature: 'Customer Intelligence',
    competitor: 'Basic customer data',
    meridian: 'AI segmentation, churn prediction, LTV scoring',
    winner: 'meridian',
  },
  {
    feature: 'Learning Curve',
    competitor: 'Steep — weeks to train staff',
    meridian: 'Minimal — intuitive dashboard, no training needed',
    winner: 'meridian',
  },
]

/* ── "Why Operators Choose R365" ─────────────────── */

const whyR365 = [
  { icon: Layers, label: 'All-in-One', detail: 'Accounting, HR, inventory, and analytics in one platform' },
  { icon: Building2, label: 'Enterprise Grade', detail: 'Built for multi-unit operators with 10+ locations' },
  { icon: BarChart3, label: 'Industry Specific', detail: 'Designed specifically for restaurant operations' },
]

const whereR365FallsShort = [
  { icon: DollarSign, label: 'Expensive for growing brands', detail: '$400-600/mo per location adds up fast for 2-5 locations' },
  { icon: Clock, label: 'Slow to deploy', detail: '4-8 week implementation means months before you see value' },
  { icon: AlertTriangle, label: 'Reporting, not intelligence', detail: "Dashboards show data but don't predict or alert" },
  { icon: ShieldAlert, label: 'Over-engineered for analytics', detail: "You're paying for accounting and HR even if you just need insights" },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'Works with Square, Toast, Clover, and 75+ systems. One-click OAuth, under 5 minutes.',
  },
  {
    num: '02',
    icon: BrainCircuit,
    title: 'AI Analyzes Immediately',
    desc: 'No implementation project. Meridian ingests your data and starts finding patterns within hours.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Insights in 24 Hours',
    desc: 'Forecasts, anomaly alerts, customer segmentation — all running without a single training session.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Best Restaurant Analytics Software', to: '/best-restaurant-analytics-software' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'vs Spreadsheets', to: '/vs/spreadsheets' },
  { label: 'vs Toast Analytics', to: '/vs/toast-analytics' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsRestaurant365Page() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Restaurant365: Lean AI Analytics vs. Enterprise Suite | Meridian"
        description="R365 is a powerful all-in-one platform — but it's built for enterprise. Here's why growing restaurants are choosing focused AI analytics over bloated suites."
        path="/vs/restaurant365"
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
            Meridian vs. Restaurant365:
            <br />
            <span className="text-[#17C5B0]">Lean AI Analytics vs. Enterprise Suite</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            R365 does everything. Meridian does analytics better.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See the Difference — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Problem Section ──────────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Enterprise Suite Problem</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Restaurant365 is a powerful platform — accounting, HR, inventory, and analytics under one roof.
          But for growing brands that just need smarter analytics, the all-in-one model comes with
          all-in-one complexity and all-in-one pricing.
        </p>

        {/* Why operators choose R365 */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators choose R365
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyR365.map((item) => (
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

        {/* Where R365 falls short */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where R365 falls short
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {whereR365FallsShort.map((item) => (
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
            Ten categories where Restaurant365 and Meridian go head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Restaurant365
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.competitor}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost of Enterprise ─────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost of Enterprise
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-4 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$8,000-15,000</div>
              <p className="text-sm text-[#A1A1A8] mt-1">typical R365 implementation cost</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">6 weeks</div>
              <p className="text-sm text-[#A1A1A8] mt-1">average time-to-value</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$600+/mo</div>
              <p className="text-sm text-[#A1A1A8] mt-1">R365 analytics-equivalent cost</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#17C5B0]">$250/mo</div>
              <p className="text-sm text-[#A1A1A8] mt-1">Meridian all-in price</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">$4,200+ saved per year</div>
            <p className="text-sm text-[#A1A1A8] mt-2">on analytics alone — before counting implementation fees</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            R365's enterprise pricing makes sense when you need the full suite — accounting, AP/AR,
            payroll, inventory, and analytics. But if you already have an accountant or use QuickBooks,
            you are paying for modules you will never open.
          </p>
          <p>
            The implementation cost alone can exceed a full year of Meridian. And while your team
            spends weeks in training sessions, your competitors are already getting AI insights
            from their POS data.
          </p>
        </div>
      </section>

      {/* ── When R365 Still Makes Sense ───────────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When R365 Still Makes Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. If you operate 10+ locations, need consolidated accounting
                  across every unit, manage complex payroll and scheduling for hundreds of employees,
                  and want everything under one login — Restaurant365 is a strong choice.
                </p>
                <p>
                  R365 shines when you need a{' '}
                  <span className="text-[#F5F5F7] font-medium">single source of truth for back-office operations</span>{' '}
                  at enterprise scale. The platform is deep, the integrations are mature, and the
                  accounting module is genuinely best-in-class for restaurants.
                </p>
                <p>
                  But if your primary need is{' '}
                  <span className="text-[#F5F5F7] font-medium">understanding your data, spotting problems early, and making better decisions</span>,
                  you do not need an enterprise suite. You need an AI analytics layer that is
                  purpose-built for intelligence — and that is exactly what Meridian delivers.
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
          No implementation project. No weeks of training. Just connect your POS and let AI do the rest.
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
          Enterprise Intelligence Without Enterprise Complexity
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS in 5 minutes. Get AI insights in 24 hours. First month free.
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
