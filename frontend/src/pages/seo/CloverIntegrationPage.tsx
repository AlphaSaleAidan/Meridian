import { Link } from 'react-router-dom'
import {
  ChevronRight,
  ArrowRight,
  BarChart3,
  TrendingUp,
  AlertTriangle,
  Users,
  Package,
  UserCheck,
  ShieldCheck,
  Zap,
  Clock,
  Database,
} from 'lucide-react'
import SEO from '@/components/SEO'

const dataPoints = [
  { point: 'Transactions', usage: 'Revenue trend modeling, hourly heatmaps, anomaly detection' },
  { point: 'Inventory', usage: 'Stock velocity tracking, reorder point forecasting, dead-stock alerts' },
  { point: 'Orders', usage: 'Order volume forecasting, basket-size analysis, peak-hour modeling' },
  { point: 'Employees', usage: 'Staff-to-revenue ratio, shift performance scoring, scheduling optimization' },
  { point: 'Customers', usage: 'RFM segmentation, lifetime value scoring, churn prediction' },
  { point: 'Refunds', usage: 'Refund trend analysis, root-cause flagging, fraud pattern detection' },
  { point: 'Discounts', usage: 'Promotion ROI tracking, discount frequency analysis, abuse detection' },
  { point: 'Tips', usage: 'Employee tipping trends, tip-to-sales benchmarks' },
  { point: 'Tax Data', usage: 'Tax liability forecasting, rate-change impact modeling' },
  { point: 'Payment Methods', usage: 'Payment mix trends, processing cost optimization' },
]

const insights = [
  { icon: TrendingUp, title: 'Revenue Forecasting', desc: 'AI-generated 7/30/90-day predictions with confidence intervals, built from your actual Clover sales data.' },
  { icon: AlertTriangle, title: 'Anomaly Detection', desc: 'Instant alerts when transactions, refunds, or voids deviate from your established patterns.' },
  { icon: Users, title: 'Customer Segmentation', desc: 'RFM analysis segments your customers into actionable tiers — champions, at-risk, and lapsed.' },
  { icon: Package, title: 'Product Optimization', desc: 'See which products drive margin, which need repricing, and which are candidates for removal.' },
  { icon: UserCheck, title: 'Staff Optimization', desc: 'Revenue per labor hour by employee, shift performance scoring, and overstaffing detection.' },
  { icon: BarChart3, title: 'Plain-English Insights', desc: 'No complex dashboards. Meridian explains what changed, why it matters, and what action to take.' },
]

const comparison = [
  { feature: 'Sales Dashboard', clover: true, meridian: true },
  { feature: 'Basic Reports', clover: true, meridian: true },
  { feature: 'Inventory Tracking', clover: true, meridian: true },
  { feature: '7/30/90-Day Forecasting', clover: false, meridian: true },
  { feature: 'AI Anomaly Detection', clover: false, meridian: true },
  { feature: 'RFM Customer Segmentation', clover: false, meridian: true },
  { feature: 'Product Optimization Matrix', clover: false, meridian: true },
  { feature: 'Staff Revenue Optimization', clover: false, meridian: true },
  { feature: 'AI Insights in Plain English', clover: false, meridian: true },
  { feature: 'Multi-Location Roll-Up', clover: false, meridian: true },
]

const faqs = [
  {
    q: 'What reports does Clover provide?',
    a: 'Clover Dashboard offers basic sales summaries, transaction history, inventory counts, and employee shift tracking. These are useful for daily operations but are backward-looking. Meridian adds predictive forecasting, anomaly detection, customer segmentation, and product optimization on top of your existing Clover data.',
  },
  {
    q: 'How does Meridian connect to Clover?',
    a: 'Through Clover\'s REST API with OAuth authorization. You log in to your Clover account, authorize Meridian, and your historical data begins importing immediately. No developer setup or API keys needed. The process takes under 5 minutes.',
  },
  {
    q: 'Does Meridian work with all Clover devices?',
    a: 'Yes. Meridian pulls data at the API level, so it works with Clover Station, Clover Mini, Clover Flex, and Clover Go. Any transaction processed through your Clover account is included.',
  },
  {
    q: 'Can I use Meridian with Clover\'s third-party apps?',
    a: 'Meridian operates independently of Clover\'s app marketplace. It connects directly to your Clover data and does not interfere with any other apps you have installed. You can run both side by side.',
  },
  {
    q: 'How much does Meridian cost for Clover users?',
    a: 'Same as all plans: $250/mo Standard, $490/mo Premium, $980/mo Command. Every plan includes your first month free. No contracts, cancel anytime.',
  },
]

const steps = [
  { num: 1, icon: ShieldCheck, title: 'Authorize', desc: 'Click "Connect Clover" and log in with your Clover merchant account. OAuth handles everything — no API keys.' },
  { num: 2, icon: Database, title: 'Import', desc: 'Meridian pulls your historical transaction, inventory, and customer data. Most imports finish within 30 minutes.' },
  { num: 3, icon: Zap, title: 'Insights', desc: 'AI analyzes your Clover data and delivers forecasts, anomaly alerts, and optimization recommendations.' },
]

export default function CloverIntegrationPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Clover POS Analytics — Smart Insights for Clover Merchants | Meridian"
        description="Transform your Clover POS data into actionable AI insights. Revenue forecasts, anomaly alerts, and customer intelligence. Connect in minutes."
        path="/integrations/clover"
        jsonLd={{
          '@type': 'SoftwareApplication',
          name: 'Meridian Intelligence for Clover POS',
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
            <span className="text-[#F5F5F7] font-semibold text-lg">Clover</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6">
            Clover POS Analytics — Smart Insights for Clover Merchants
          </h1>
          <p className="text-lg text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Your Clover POS captures every sale, every customer, every product. Meridian turns that data
            into revenue forecasts, anomaly alerts, and product intelligence — in plain English.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            Connect Your Clover — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* What Meridian Pulls */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">What Meridian Pulls from Clover</h2>
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
          <p className="text-[#A1A1A8] mb-10 text-center">Six layers of intelligence on top of your Clover data.</p>
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
          <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">Clover Alone vs. With Meridian</h2>
          <p className="text-[#A1A1A8] mb-8 text-center">Everything Clover gives you, plus everything it doesn't.</p>
          <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
            <div className="grid grid-cols-[2fr_1fr_1fr] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">Feature</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider text-center">Clover</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider text-center">Meridian</div>
            </div>
            {comparison.map((row, i) => (
              <div key={row.feature} className={`grid grid-cols-[2fr_1fr_1fr] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'} ${i < comparison.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}>
                <div className="px-4 py-3 font-medium">{row.feature}</div>
                <div className="px-4 py-3 text-center">{row.clover ? <span className="text-[#17C5B0]">&#10003;</span> : <span className="text-[#A1A1A8]">—</span>}</div>
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
          <h2 className="text-2xl md:text-3xl font-bold mb-4">Ready to unlock your Clover data?</h2>
          <p className="text-[#A1A1A8] mb-8">Connect in under 5 minutes. See insights within the hour. First month free.</p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            Connect Your Clover — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* Other Integrations */}
      <section className="py-12 px-6 border-t border-[#1F1F23]">
        <div className="max-w-4xl mx-auto text-center">
          <p className="text-sm text-[#A1A1A8] mb-3">Other integrations:</p>
          <div className="flex items-center justify-center gap-6">
            <Link to="/integrations/square" className="text-sm text-[#F5F5F7] hover:text-[#17C5B0] transition-colors flex items-center gap-1">
              Square POS <ChevronRight className="w-3 h-3" />
            </Link>
            <Link to="/integrations/toast" className="text-sm text-[#F5F5F7] hover:text-[#17C5B0] transition-colors flex items-center gap-1">
              Toast POS <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
