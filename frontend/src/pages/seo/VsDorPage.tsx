import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  Footprints,
  Zap,
  Clock,
  ShieldAlert,
  AlertTriangle,
  BarChart3,
  Users,
  DollarSign,
  Camera,
  MessageSquare,
  Search,
  Plug,
  CheckCircle2,
  Eye,
  TrendingUp,
  MapPin,
} from 'lucide-react'
import SEO from '@/components/SEO'

/* -- FAQ Data ------------------------------------------------ */

const faqItems = [
  {
    q: 'Is Meridian as accurate as Dor for counting foot traffic?',
    a: 'Meridian uses camera-based AI that counts people entering, exiting, and moving between zones with 95%+ accuracy. Dor thermal sensors are also highly accurate for door counting, but they only measure a single entrance point. Meridian covers the entire floor and cross-references with POS data, so you get accuracy where it matters most: linking traffic to revenue.',
  },
  {
    q: 'Do I need to buy special hardware like Dor\'s thermal sensor?',
    a: 'No. Meridian works with any standard IP camera you already own or can purchase for $30-100. Dor requires a proprietary thermal sensor ($500+) mounted above each door. If you have multiple entrances, Dor\'s hardware costs multiply, while Meridian uses the cameras you likely already have for security.',
  },
  {
    q: 'Can I use Dor and Meridian together?',
    a: 'Technically yes, but most operators find it redundant. Meridian already counts foot traffic using your cameras and adds POS cross-referencing, zone heatmaps, and conversion analytics that Dor cannot provide. Running both means paying for Dor hardware and subscription for a subset of data Meridian already captures.',
  },
  {
    q: 'How hard is it to switch from Dor to Meridian?',
    a: 'There is no data migration needed. Meridian connects to your POS system via one-click OAuth and begins analyzing your existing IP camera feeds within minutes. Your historical POS data is automatically ingested. Most operators are fully live within 24 hours with zero downtime.',
  },
  {
    q: 'What is the total cost of Dor vs. Meridian for a 3-location business?',
    a: 'Dor: $299/month per location ($897/month) plus $500+ per sensor, plus 5+ hours per week manually correlating traffic with POS data. Meridian: $490/month per location ($1,470/month) but includes camera AI, POS analytics, anomaly detection, and forecasting with zero manual correlation. When you factor in the 5 hours per week of saved labor ($650/month at $30/hour), Meridian costs less overall.',
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

/* -- Head-to-Head Comparison --------------------------------- */

const comparisonRows = [
  {
    feature: 'What It Measures',
    dor: 'Door entries/exits',
    meridian: 'Foot traffic + POS transactions + dwell time + zones',
    winner: 'meridian',
  },
  {
    feature: 'POS Integration',
    dor: 'Basic — exports to CSV/API',
    meridian: 'Native — one-click OAuth with 75+ POS systems',
    winner: 'meridian',
  },
  {
    feature: 'Conversion Rate',
    dor: 'Manual calculation (traffic ÷ transactions)',
    meridian: 'Automatic — real-time, by hour, by zone, by staff shift',
    winner: 'meridian',
  },
  {
    feature: 'Revenue Per Visitor',
    dor: 'Not available',
    meridian: 'Automatic — revenue ÷ traffic, trending over time',
    winner: 'meridian',
  },
  {
    feature: 'Anomaly Detection',
    dor: 'None',
    meridian: 'AI-powered alerts on traffic, sales, and conversion anomalies',
    winner: 'meridian',
  },
  {
    feature: 'Dwell Time Analysis',
    dor: 'Not available',
    meridian: 'Zone-level dwell time with purchase correlation',
    winner: 'meridian',
  },
  {
    feature: 'Heatmaps',
    dor: 'Not available (door sensor only)',
    meridian: 'Full zone heatmaps from camera AI',
    winner: 'meridian',
  },
  {
    feature: 'Revenue Forecasting',
    dor: 'Not available',
    meridian: 'AI forecasting based on traffic + POS patterns',
    winner: 'meridian',
  },
  {
    feature: 'Hardware Required',
    dor: 'Proprietary thermal sensor ($500+)',
    meridian: 'Any existing IP camera ($0 if you have cameras)',
    winner: 'meridian',
  },
  {
    feature: 'Pricing',
    dor: '$299/mo per door + hardware',
    meridian: '$490/mo includes camera AI + POS analytics + forecasting',
    winner: 'meridian',
  },
]

/* -- Why Operators Choose Dor -------------------------------- */

const whyDor = [
  { icon: Footprints, label: 'Simple & Focused', detail: 'Does one thing well — counts people at the door' },
  { icon: Zap, label: 'Quick Install', detail: 'Stick a sensor above the door, get counts in minutes' },
  { icon: Users, label: 'Retail Industry Standard', detail: 'Used by many retail chains for benchmarking traffic' },
]

/* -- Where Dor Falls Short ----------------------------------- */

const dorFallsShort = [
  {
    icon: AlertTriangle,
    label: 'Counting without context',
    detail: 'Knowing 500 people walked in means nothing without knowing 340 bought something',
  },
  {
    icon: ShieldAlert,
    label: 'No POS cross-referencing',
    detail: 'You have to manually correlate traffic with sales in spreadsheets',
  },
  {
    icon: MapPin,
    label: 'Door only — no interior zones',
    detail: 'Can\'t see where people go inside, dwell time, or dead zones',
  },
  {
    icon: DollarSign,
    label: 'Expensive hardware per door',
    detail: 'Proprietary sensor per entrance adds up in multi-door or multi-location setups',
  },
]

/* -- Making the Switch Steps --------------------------------- */

const switchSteps = [
  {
    num: '01',
    icon: Camera,
    title: 'Connect Your Cameras',
    desc: 'Any IP camera you already own. No proprietary hardware to buy or install.',
  },
  {
    num: '02',
    icon: Plug,
    title: 'Connect Your POS',
    desc: 'One-click OAuth with Square, Toast, Clover, and 75+ systems.',
  },
  {
    num: '03',
    icon: CheckCircle2,
    title: 'Cross-Referenced in 24 Hours',
    desc: 'Conversion rates, revenue per visitor, zone heatmaps — all automatic. No spreadsheets needed.',
  },
]

/* -- Internal Links ------------------------------------------ */

const relatedPages = [
  { label: 'Camera Intelligence', to: '/features/camera-intelligence' },
  { label: 'What Is POS Analytics?', to: '/what-is-pos-analytics' },
  { label: 'Restaurants', to: '/for/restaurants' },
  { label: 'vs Foot Traffic Counters', to: '/vs/foot-traffic-counters' },
  { label: 'Foot Traffic Analytics Guide', to: '/guides/foot-traffic-analytics' },
]

/* -- Component ----------------------------------------------- */

export default function VsDorPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Meridian vs. Dor: Why Foot Traffic Counting Is Only Half the Story | Meridian"
        description="Dor counts people at the door. Meridian counts people AND cross-references with your POS data — giving you conversion rates, revenue per visitor, and zone profitability."
        path="/vs/dor"
        jsonLd={faqJsonLd}
      />

      {/* -- Hero -------------------------------------------- */}
      <section className="relative overflow-hidden pt-32 pb-20 px-6">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/8 via-[#0A0A0B] to-[#0A0A0B]" />
        <div className="relative max-w-4xl mx-auto text-center">
          <p className="text-[#17C5B0] text-sm font-medium tracking-widest uppercase mb-4">
            Comparison
          </p>
          <h1 className="text-4xl md:text-6xl font-bold leading-tight mb-6">
            Meridian vs. Dor:
            <br />
            <span className="text-[#17C5B0]">Counting Is Only Half the Story</span>
          </h1>
          <p className="text-lg md:text-xl text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Dor counts people at the door. Meridian counts people AND cross-references
            with your POS data — so you know what they bought.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all"
          >
            See the Full Picture — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* -- Why Operators Choose Dor / Where It Falls Short -- */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">The Foot Traffic Counter Trap</h2>
        <p className="text-[#A1A1A8] leading-relaxed mb-8">
          Dor is popular because it solves a real problem: knowing how many people walk
          through your door. But counting bodies is only step one. The real question is
          not "how many came in?" — it is "how many bought something, what did they buy,
          and where did they spend their time?"
        </p>

        {/* Why operators choose Dor */}
        <div className="mb-8">
          <p className="text-sm font-medium text-[#A1A1A8] uppercase tracking-wider mb-4">
            Why operators choose Dor
          </p>
          <div className="grid sm:grid-cols-3 gap-4">
            {whyDor.map((item) => (
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

        {/* Where Dor falls short */}
        <div>
          <p className="text-sm font-medium text-[#EF4444] uppercase tracking-wider mb-4">
            Where Dor falls short
          </p>
          <div className="grid sm:grid-cols-2 gap-4">
            {dorFallsShort.map((item) => (
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

      {/* -- Head-to-Head Comparison -------------------------- */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
            Head-to-Head Comparison
          </h2>
          <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-10">
            Ten categories where Dor and Meridian go head to head.
          </p>
          <div className="border border-[#1F1F23] rounded-lg overflow-x-auto">
            {/* Header */}
            <div className="grid grid-cols-[1.2fr_1.5fr_1.5fr] min-w-[600px] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Feature
              </div>
              <div className="px-5 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">
                Dor
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
                <div className="px-5 py-3 text-sm text-[#A1A1A8]">{row.dor}</div>
                <div className="px-5 py-3 text-sm font-medium text-[#17C5B0]">
                  {row.meridian}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* -- The Hidden Cost of "Just Counting" --------------- */}
      <section className="max-w-4xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold mb-6">
          The Hidden Cost of "Just Counting"
        </h2>
        <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8 mb-6">
          <div className="grid sm:grid-cols-3 gap-6 text-center mb-6">
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">5 hrs/week</div>
              <p className="text-sm text-[#A1A1A8] mt-1">
                spent manually correlating Dor data with POS exports
              </p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">$299/mo</div>
              <p className="text-sm text-[#A1A1A8] mt-1">
                for a sensor that only counts — no conversion, no revenue insight
              </p>
            </div>
            <div>
              <div className="text-3xl font-bold text-[#EF4444]">0</div>
              <p className="text-sm text-[#A1A1A8] mt-1">
                metrics Dor can produce without manual POS correlation
              </p>
            </div>
          </div>
          <div className="text-center border-t border-[#1F1F23] pt-6">
            <div className="text-4xl font-bold text-[#17C5B0]">$490/mo</div>
            <p className="text-sm text-[#A1A1A8] mt-2">
              for the full picture — camera AI + POS analytics + forecasting, zero spreadsheets
            </p>
          </div>
        </div>
        <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
          <p>
            Dor tells you 500 people walked in on Tuesday. Meridian tells you 500 people
            walked in, 340 bought something, the average ticket was $27.50, the back-left
            zone had 12 minutes of average dwell time but only a 22% purchase rate, and
            your Tuesday lunch conversion dropped 8% compared to last week.
          </p>
          <p>
            Every week that you run a foot traffic counter without POS cross-referencing,
            you are paying for data that creates more questions than answers. The spreadsheet
            gap between "people counted" and "revenue generated" is where real insight lives —
            and where Dor leaves you on your own.
          </p>
        </div>
      </section>

      {/* -- When Dor Still Works ----------------------------- */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-6">
            When Dor Still Works
          </h2>
          <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 md:p-8">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center shrink-0 mt-1">
                <MessageSquare className="w-5 h-5 text-[#1A8FD6]" />
              </div>
              <div className="space-y-3 text-[#A1A1A8] leading-relaxed">
                <p>
                  We will be straightforward. If you run a single-entrance retail store, you
                  only need to benchmark raw traffic volume against other locations in a
                  standardized format, and you have no interest in conversion rates, revenue
                  per visitor, or zone analytics — Dor does its job well.
                </p>
                <p>
                  Dor is also a reasonable fit for large retail chains that have already
                  standardized on thermal sensors across hundreds of locations and need
                  apples-to-apples traffic benchmarking with no additional analytics layer.
                </p>
                <p>
                  Meridian becomes essential when you want to go beyond counting — when you
                  need to understand{' '}
                  <span className="text-[#F5F5F7] font-medium">
                    why traffic converts or does not convert
                  </span>
                  , when you want{' '}
                  <span className="text-[#F5F5F7] font-medium">
                    revenue per visitor trending over time
                  </span>
                  , or when you are tired of spending hours each week in spreadsheets trying
                  to manually bridge the gap between your door counter and your POS system.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* -- Making the Switch -------------------------------- */}
      <section className="max-w-5xl mx-auto px-6 py-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-4">
          Making the Switch
        </h2>
        <p className="text-[#A1A1A8] text-center max-w-2xl mx-auto mb-12">
          No hardware to ship back. No data migration. Connect your cameras and POS,
          and Meridian handles the rest.
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

      {/* -- CTA --------------------------------------------- */}
      <section className="max-w-4xl mx-auto px-6 py-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-4">
          Count People. Know What They Bought.
        </h2>
        <p className="text-[#A1A1A8] mb-8 max-w-xl mx-auto">
          Camera AI + POS analytics in one platform. First month free.
        </p>
        <Link
          to="/demo"
          className="inline-flex items-center gap-2 px-10 py-4 rounded-lg bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] text-[#0A0A0B] font-semibold text-lg hover:brightness-110 transition-all"
        >
          Start Your Free Month <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* -- FAQ --------------------------------------------- */}
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

      {/* -- Internal Links ---------------------------------- */}
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
