import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Table2,
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
} from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ Data ──────────────────────────────────────── */

const faqItems = [
  {
    q: 'Is POS analytics really better than Excel for restaurants?',
    a: 'For real-time insights and anomaly detection, yes. Excel is powerful for custom one-off analysis, but it requires manual data entry and formula maintenance. POS analytics pulls data automatically, runs AI models continuously, and alerts you the moment something goes wrong — no formulas to build, no data to export.',
  },
  {
    q: 'How much time does POS analytics save vs. spreadsheets?',
    a: 'On average, restaurant and retail operators save 5-8 hours per week per location by switching from spreadsheet tracking to automated POS analytics. That time includes data export, manual entry, formula maintenance, formatting, and emailing reports to partners or managers.',
  },
  {
    q: 'Can I still export data to spreadsheets?',
    a: 'Yes. Most POS analytics tools, including Meridian, offer CSV and Excel export for any report or dataset. You get the best of both worlds: automated AI insights plus the flexibility to run custom analysis in spreadsheets when needed.',
  },
  {
    q: 'What if I have years of data in spreadsheets?',
    a: 'POS analytics pulls directly from your POS system, so all of your historical POS transaction data is automatically included from the moment you connect. Spreadsheet history can be imported separately if needed, but most operators find that the POS data is far more complete and accurate.',
  },
  {
    q: 'Is POS analytics worth it for a single location?',
    a: 'At $250/month vs. $650+ per month in spreadsheet labor (5 hours/week at $30/hour), it pays for itself immediately. Plus you get anomaly detection, forecasting, and customer segmentation that spreadsheets simply cannot provide — even with expert-level Excel skills.',
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
    feature: 'Data Entry',
    spreadsheet: 'Manual — hours per week',
    analytics: 'Automatic — real-time from POS',
    winner: 'analytics',
  },
  {
    feature: 'Accuracy',
    spreadsheet: 'Human error (5-15% error rate)',
    analytics: 'POS-verified (99.9% accurate)',
    winner: 'analytics',
  },
  {
    feature: 'Speed',
    spreadsheet: 'End of day or week',
    analytics: 'Real-time',
    winner: 'analytics',
  },
  {
    feature: 'Forecasting',
    spreadsheet: 'Manual formulas (if you know how)',
    analytics: 'AI/ML models trained on your data',
    winner: 'analytics',
  },
  {
    feature: 'Anomaly Detection',
    spreadsheet: 'Manual review — easy to miss',
    analytics: 'Automatic alerts in real time',
    winner: 'analytics',
  },
  {
    feature: 'Multi-Location',
    spreadsheet: 'Separate files per location',
    analytics: 'Unified dashboard across all sites',
    winner: 'analytics',
  },
  {
    feature: 'True Cost',
    spreadsheet: '"Free" (but 5+ hrs/wk x $30/hr = $7,800/yr)',
    analytics: '$250-500/month ($3,000-6,000/yr)',
    winner: 'analytics',
  },
  {
    feature: 'Scalability',
    spreadsheet: 'Breaks at 3+ locations',
    analytics: 'Unlimited locations',
    winner: 'analytics',
  },
  {
    feature: 'Collaboration',
    spreadsheet: 'Email attachments, version conflicts',
    analytics: 'Shared dashboard with role-based access',
    winner: 'analytics',
  },
  {
    feature: 'Insight Discovery',
    spreadsheet: 'Only what you think to look for',
    analytics: 'AI surfaces patterns you would miss',
    winner: 'analytics',
  },
]

/* ── "The Spreadsheet Trap" Reasons ────────────────── */

const whySpreadsheets = [
  { icon: Table2, label: 'Familiar', detail: 'Everyone knows Excel or Google Sheets' },
  { icon: DollarSign, label: 'Free', detail: 'No monthly subscription cost' },
  { icon: Zap, label: 'Flexible', detail: 'You can build anything you want' },
]

const whyTheyBreak = [
  { icon: AlertTriangle, label: 'Manual entry errors', detail: 'One typo can cascade through every formula' },
  { icon: Clock, label: 'Stale data', detail: 'By the time you update, the moment has passed' },
  { icon: ShieldAlert, label: 'No real-time alerts', detail: 'Theft and anomalies go undetected for days or weeks' },
  { icon: Building2, label: 'Doesn\'t scale', detail: 'Adding a second location doubles your spreadsheet work' },
]

/* ── "Making the Switch" Steps ─────────────────────── */

const switchSteps = [
  {
    num: '01',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'Authorize Square, Toast, Clover, or any of 75+ systems. One-click OAuth, no API keys, under 5 minutes.',
  },
  {
    num: '02',
    icon: Search,
    title: 'AI Analyzes Your History',
    desc: 'Meridian ingests your complete transaction history and begins identifying patterns, anomalies, and opportunities.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Get Insights in 24 Hours',
    desc: 'Revenue forecasts, anomaly alerts, and customer segmentation — delivered automatically. No spreadsheet migration needed.',
  },
]

/* ── Internal Links ────────────────────────────────── */

const relatedPages = [
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'Coffee Shops', to: '/for/coffee-shops' },
  { label: 'Square Integration', to: '/integrations/square' },
  { label: 'Toast Integration', to: '/integrations/toast' },
  { label: 'Clover Integration', to: '/integrations/clover' },
]

/* ── Component ─────────────────────────────────────── */

export default function VsSpreadsheetsPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="POS Analytics vs. Spreadsheets: Why Manual Tracking Fails | Meridian"
        description="Still tracking restaurant performance in Excel? Here's why spreadsheet-based analysis misses critical insights and costs you 5+ hours per week."
        path="/vs/spreadsheets"
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
            POS Analytics vs. Spreadsheets:
            <br />
            <span className="text-[#17C5B0]">Why Manual Tracking Fails</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            The spreadsheet was never designed to run a restaurant.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See the Difference — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── The Spreadsheet Trap ──────────────────────── */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Spreadsheet Trap</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Smart operators still use spreadsheets because they feel free, familiar, and flexible.
          But every spreadsheet-based tracking system eventually hits the same wall.
        </p>

        {/* Why owners use them */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators start with spreadsheets
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whySpreadsheets.map((item) => (
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
            Why spreadsheets eventually break
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
            Ten categories where spreadsheets and POS analytics go head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Spreadsheets
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider">
                POS Analytics
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.spreadsheet}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.analytics}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── The Hidden Cost of "Free" ─────────────────── */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost of "Free"
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">5 hrs</div>
              <p className="text-sm text-[#A1A1A8] mt-1">per week on data entry and reporting</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">x 52</div>
              <p className="text-sm text-[#A1A1A8] mt-1">weeks per year</p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">x $30</div>
              <p className="text-sm text-[#A1A1A8] mt-1">per hour (your time or a manager's)</p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#EF4444]">= $7,800/year</div>
            <p className="text-sm text-[#A1A1A8] mt-2">in labor alone for a "free" spreadsheet</p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            That $7,800 only accounts for the time spent building and maintaining spreadsheets.
            It does not include the cost of delayed decisions, missed anomalies, or employee theft
            going undetected for weeks because nobody checked the void report.
          </p>
          <p>
            A single undetected theft pattern that runs for three months can cost a restaurant
            $5,000-15,000. A missed trend in customer churn can cost even more. The spreadsheet
            cannot alert you to either.
          </p>
        </div>
      </section>

      {/* ── When Spreadsheets Still Make Sense ─────────── */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Spreadsheets Still Make Sense
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be honest. If you run a single location doing under $500K per year, you
                  enjoy the process of building your own reports, and you do not manage more than a
                  handful of employees — spreadsheets can work fine.
                </p>
                <p>
                  POS analytics becomes essential when you need to{' '}
                  <span className="text-[#F5F5F7] font-medium">scale beyond one location</span>,
                  when you want to{' '}
                  <span className="text-[#F5F5F7] font-medium">stop working IN the business</span>{' '}
                  and start working on it, or when you are losing money to problems that only
                  real-time monitoring can catch.
                </p>
                <p>
                  The question is not whether spreadsheets work. The question is whether your time
                  is better spent entering data into cells or making decisions that grow your business.
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
          No spreadsheet migration needed. POS analytics pulls directly from your transaction data.
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
          Stop Tracking, Start Knowing
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Connect your POS in under 5 minutes. Let AI do the analysis. Get your first insights
          within 24 hours. First month free, no contracts.
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
