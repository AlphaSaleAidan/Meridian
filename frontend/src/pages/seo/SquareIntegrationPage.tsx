import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Users,
  Utensils,
  UserCheck,
  ShieldCheck,
  Zap,
  Clock,
  Database,
} from 'lucide-react'
import SEO from '@/components/SEO'

const dataPoints = [
  { point: 'Transactions', usage: 'Revenue trend modeling, anomaly detection, hourly heatmaps' },
  { point: 'Items Sold', usage: 'Menu engineering matrix, product mix optimization' },
  { point: 'Categories', usage: 'Category-level margin analysis, cross-sell insights' },
  { point: 'Refunds & Voids', usage: 'Fraud pattern detection, shrinkage alerts' },
  { point: 'Tips', usage: 'Staff performance scoring, tipping trend analysis' },
  { point: 'Discounts', usage: 'Promotion ROI tracking, discount abuse detection' },
  { point: 'Customer Profiles', usage: 'RFM segmentation, lifetime value scoring' },
  { point: 'Employee Data', usage: 'Staff-to-revenue correlation, scheduling optimization' },
  { point: 'Inventory', usage: 'Stock velocity tracking, reorder point forecasting' },
  { point: 'Payment Methods', usage: 'Payment mix trends, processing cost optimization' },
]

const insights = [
  { icon: TrendingUp, title: '7/30/90-Day Forecasts', desc: 'AI-generated revenue predictions so you can plan labor, inventory, and marketing with confidence.' },
  { icon: AlertTriangle, title: 'Anomaly Detection', desc: 'Instant alerts when sales, refunds, or voids deviate from your normal patterns.' },
  { icon: Users, title: 'Customer Segmentation', desc: 'RFM analysis groups your customers into actionable tiers — champions, at-risk, lost.' },
  { icon: Utensils, title: 'Menu Engineering', desc: 'Identify stars, plowhorses, puzzles, and dogs across your menu with margin-weighted analysis.' },
  { icon: UserCheck, title: 'Staff Optimization', desc: 'See which employees drive the most revenue per hour and when you are over- or under-staffed.' },
  { icon: BarChart3, title: 'Plain-English Insights', desc: 'No dashboards to decipher. Meridian tells you what changed, why it matters, and what to do.' },
]

const comparison = [
  { feature: 'Sales Summary', square: true, meridian: true },
  { feature: 'Item Reports', square: true, meridian: true },
  { feature: 'Employee Hours', square: true, meridian: true },
  { feature: '7/30/90-Day Forecasting', square: false, meridian: true },
  { feature: 'Anomaly Detection & Alerts', square: false, meridian: true },
  { feature: 'RFM Customer Segmentation', square: false, meridian: true },
  { feature: 'Menu Engineering Matrix', square: false, meridian: true },
  { feature: 'Staff Revenue Optimization', square: false, meridian: true },
  { feature: 'AI Insights in Plain English', square: false, meridian: true },
  { feature: 'Multi-Location Roll-Up', square: false, meridian: true },
]

const faqs = [
  {
    q: 'What analytics does Square provide?',
    a: 'Square offers sales summaries, item reports, and employee tracking. These are useful for day-to-day operations, but they are backward-looking. Meridian adds AI-powered forecasting, anomaly detection, and customer segmentation on top of your existing Square data — turning historical numbers into forward-looking strategy.',
  },
  {
    q: 'How does Meridian connect to Square?',
    a: 'One-click OAuth connection. No API keys needed, no developer setup. The entire process takes under 5 minutes. Once connected, your historical data imports automatically and Meridian begins generating insights within the hour.',
  },
  {
    q: 'Will Meridian slow down my Square POS?',
    a: 'No. Meridian reads data through Square\'s API in the background. It never touches your live POS terminal. Your checkout experience stays exactly the same — we operate entirely on the data layer.',
  },
  {
    q: 'Can I use Meridian with Square for Restaurants?',
    a: 'Yes, both Square POS and Square for Restaurants are fully supported. Restaurant-specific features like menu engineering, course tracking, and table turn analysis are available out of the box.',
  },
  {
    q: 'How much does Meridian cost for Square users?',
    a: 'Same as all plans: $250/mo Standard, $490/mo Premium, $980/mo Command. Every plan includes your first month free so you can see the value before you pay. No contracts, cancel anytime.',
  },
]

const steps = [
  { num: 1, icon: ShieldCheck, title: 'Authorize', desc: 'Click "Connect Square" and log in with your Square account. One-click OAuth — no API keys needed.' },
  { num: 2, icon: Database, title: 'Import', desc: 'Meridian pulls your historical transaction data. Most imports complete within 30 minutes.' },
  { num: 3, icon: Zap, title: 'Insights', desc: 'AI analyzes your data and surfaces forecasts, anomalies, and recommendations immediately.' },
]

export default function SquareIntegrationPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Square POS Analytics — AI Insights from Your Square Data | Meridian"
        description="Connect your Square POS to Meridian for instant AI-powered analytics. Revenue forecasts, anomaly detection, and customer insights beyond Square's built-in reports."
        path="/integrations/square"
        jsonLd={{
          '@type': 'SoftwareApplication',
          name: 'Meridian Intelligence for Square POS',
          applicationCategory: 'BusinessApplication',
          operatingSystem: 'Web',
          offers: { '@type': 'Offer', price: '250', priceCurrency: 'USD' },
        }}
      />

      {/* Hero */}
      <section className="relative pt-28 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#17C5B0]/5 to-transparent pointer-events-none" />
        <div className="max-w-4xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-3 mb-6 px-4 py-2 rounded-full border border-[#1F1F23] bg-[#111113]">
            <span className="text-[#17C5B0] font-semibold text-lg">Meridian</span>
            <span className="text-[#A1A1A8]">+</span>
            <span className="text-[#F5F5F7] font-semibold text-lg">Square</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6">
            Square POS Analytics — Get AI Insights from Your Square Data
          </h1>
          <p className="text-lg text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Your Square POS captures every transaction. Meridian turns that data into revenue forecasts,
            anomaly alerts, and customer intelligence — in plain English.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            Connect Your Square — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* What Meridian Pulls */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">What Meridian Pulls from Square</h2>
          <p className="text-[#A1A1A8] mb-8">Every data point becomes an insight.</p>
          <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
            <div className="grid grid-cols-[1fr_2fr] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">Data Point</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">What Meridian Does With It</div>
            </div>
            {dataPoints.map((d, i) => (
              <div key={d.point} className={`grid grid-cols-[1fr_2fr] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'} ${i < dataPoints.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}>
                <div className="px-4 py-3 font-medium">{d.point}</div>
                <div className="px-4 py-3 text-[#A1A1A8]">{d.usage}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* What You Get */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-5xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">What You Get</h2>
          <p className="text-[#A1A1A8] mb-10 text-center">Six layers of intelligence on top of your Square data.</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {insights.map((item) => (
              <div key={item.title} className="p-5 rounded-lg border border-[#1F1F23] bg-[#111113] hover:border-[#17C5B0]/30 transition-colors">
                <item.icon className="w-8 h-8 text-[#17C5B0] mb-3" />
                <h3 className="font-semibold mb-1">{item.title}</h3>
                <p className="text-sm text-[#A1A1A8]">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How to Connect */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">How to Connect</h2>
          <p className="text-[#A1A1A8] mb-10 text-center">Three steps. Under five minutes.</p>
          <div className="grid md:grid-cols-3 gap-6">
            {steps.map((s) => (
              <div key={s.num} className="relative p-6 rounded-lg border border-[#1F1F23] bg-[#111113] text-center">
                <div className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-[#17C5B0]/10 text-[#17C5B0] font-bold text-lg mb-4">
                  {s.num}
                </div>
                <s.icon className="w-8 h-8 text-[#17C5B0] mx-auto mb-3" />
                <h3 className="font-semibold mb-1">{s.title}</h3>
                <p className="text-sm text-[#A1A1A8]">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Comparison */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">Square Alone vs. With Meridian</h2>
          <p className="text-[#A1A1A8] mb-8 text-center">Everything Square gives you, plus everything it doesn't.</p>
          <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
            <div className="grid grid-cols-[2fr_1fr_1fr] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">Feature</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider text-center">Square</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider text-center">Meridian</div>
            </div>
            {comparison.map((row, i) => (
              <div key={row.feature} className={`grid grid-cols-[2fr_1fr_1fr] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'} ${i < comparison.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}>
                <div className="px-4 py-3 font-medium">{row.feature}</div>
                <div className="px-4 py-3 text-center">{row.square ? <span className="text-[#17C5B0]">&#10003;</span> : <span className="text-[#A1A1A8]">—</span>}</div>
                <div className="px-4 py-3 text-center"><span className="text-[#17C5B0]">&#10003;</span></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-20 px-6">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-8 text-center">Frequently Asked Questions</h2>
          <div className="space-y-3">
            {faqs.map((faq) => (
              <details key={faq.q} className="group border border-[#1F1F23] rounded-lg bg-[#111113] overflow-hidden">
                <summary className="flex items-center justify-between px-5 py-4 cursor-pointer font-medium hover:text-[#17C5B0] transition-colors list-none">
                  {faq.q}
                  <ChevronRight className="w-4 h-4 text-[#A1A1A8] group-open:rotate-90 transition-transform shrink-0 ml-3" />
                </summary>
                <div className="px-5 pb-4 text-sm text-[#A1A1A8] leading-relaxed">{faq.a}</div>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-20 px-6 bg-[#111113]/30">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl md:text-3xl font-bold mb-4">Ready to unlock your Square data?</h2>
          <p className="text-[#A1A1A8] mb-8">Connect in under 5 minutes. See insights within the hour. First month free.</p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            Connect Your Square — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Other Integrations */}
      <section className="py-12 px-6 border-t border-[#1F1F23]">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-[#A1A1A8] mb-3">Other integrations:</p>
          <div className="flex items-center justify-center gap-6">
            <Link to="/integrations/toast" className="text-sm text-[#F5F5F7] hover:text-[#17C5B0] transition-colors flex items-center gap-1">
              Toast POS <ChevronRight className="w-3 h-3" />
            </Link>
            <Link to="/integrations/clover" className="text-sm text-[#F5F5F7] hover:text-[#17C5B0] transition-colors flex items-center gap-1">
              Clover POS <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
