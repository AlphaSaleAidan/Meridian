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
  { point: 'Orders', usage: 'Order volume forecasting, peak-hour modeling, prep time optimization' },
  { point: 'Menu Items', usage: 'Menu engineering matrix — stars, plowhorses, puzzles, dogs' },
  { point: 'Modifiers', usage: 'Upsell analysis, modifier attach-rate tracking' },
  { point: 'Revenue', usage: '7/30/90-day revenue forecasting with confidence intervals' },
  { point: 'Labor Hours', usage: 'Labor-to-revenue ratio, optimal scheduling recommendations' },
  { point: 'Voids & Comps', usage: 'Void pattern detection, comp abuse alerts, shrinkage tracking' },
  { point: 'Refunds', usage: 'Refund trend analysis, root-cause flagging' },
  { point: 'Guest Counts', usage: 'Per-guest spend analysis, covers forecasting' },
  { point: 'Tip Data', usage: 'Server performance scoring, tip-to-sales benchmarking' },
  { point: 'Dayparts', usage: 'Daypart profitability analysis, menu mix by time slot' },
]

const insights = [
  { icon: TrendingUp, title: 'Revenue Forecasting', desc: 'AI-generated 7/30/90-day revenue predictions so you can plan labor and inventory ahead of demand.' },
  { icon: AlertTriangle, title: 'Anomaly Alerts', desc: 'Real-time flags when voids, comps, refunds, or sales deviate from your restaurant\'s baseline.' },
  { icon: Users, title: 'Guest Intelligence', desc: 'RFM segmentation turns guest data into loyalty tiers — champions, regulars, at-risk, and lapsed.' },
  { icon: Utensils, title: 'Menu Engineering', desc: 'Profitability-weighted menu matrix shows which items to promote, reprice, or retire.' },
  { icon: UserCheck, title: 'Labor Optimization', desc: 'See revenue per labor hour by shift, identify overstaffed windows, and optimize schedules.' },
  { icon: BarChart3, title: 'Plain-English Insights', desc: 'No pivot tables. Meridian tells you exactly what changed, why, and what to do about it.' },
]

const comparison = [
  { feature: 'Sales Summary', toast: true, meridian: true },
  { feature: 'Labor Reports', toast: true, meridian: true },
  { feature: 'Toast Pulse Alerts', toast: true, meridian: true },
  { feature: '7/30/90-Day Forecasting', toast: false, meridian: true },
  { feature: 'AI Anomaly Detection', toast: false, meridian: true },
  { feature: 'RFM Guest Segmentation', toast: false, meridian: true },
  { feature: 'Menu Engineering Matrix', toast: false, meridian: true },
  { feature: 'Labor-to-Revenue Optimization', toast: false, meridian: true },
  { feature: 'AI Insights in Plain English', toast: false, meridian: true },
  { feature: 'Multi-Location Roll-Up', toast: false, meridian: true },
]

const faqs = [
  {
    q: 'How does Toast Pulse compare to Meridian?',
    a: 'Toast Pulse sends basic alerts on daily sales and labor. It is reactive — it tells you what happened. Meridian is predictive — it tells you what will happen and what to do about it. Meridian adds forecasting, anomaly detection, customer segmentation, and menu engineering that Toast Pulse does not offer.',
  },
  {
    q: 'How does Meridian connect to Toast?',
    a: 'Through Toast\'s Partner API. You authorize Meridian in a few clicks, and your historical data imports automatically. No developer setup, no API keys to manage. The connection takes under 5 minutes.',
  },
  {
    q: 'How long does the initial data import take?',
    a: 'Most Toast restaurants see their full historical data imported within 30 to 60 minutes. Meridian starts generating insights as soon as the first batch of data arrives.',
  },
  {
    q: 'Does Meridian work with Toast Go handheld devices?',
    a: 'Yes. Meridian pulls data from your Toast account at the API level, which includes all transactions processed through Toast Go terminals, Toast Flex, and Toast Kiosk.',
  },
  {
    q: 'How much does Meridian cost for Toast users?',
    a: 'Same as all plans: $250/mo Standard, $490/mo Premium, $980/mo Command. Every plan includes your first month free. No contracts, cancel anytime.',
  },
]

const steps = [
  { num: 1, icon: ShieldCheck, title: 'Authorize', desc: 'Click "Connect Toast" and log in with your Toast credentials. Meridian uses Toast\'s Partner API — no keys to copy.' },
  { num: 2, icon: Database, title: 'Import', desc: 'Historical orders, labor, and menu data flow in automatically. Most imports finish within the hour.' },
  { num: 3, icon: Zap, title: 'Insights', desc: 'Meridian\'s AI analyzes your restaurant data and delivers forecasts, alerts, and recommendations.' },
]

export default function ToastIntegrationPage() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="Toast POS Analytics — AI-Powered Insights for Toast Restaurants | Meridian"
        description="Unlock the full potential of your Toast POS data with Meridian's AI analytics. Revenue forecasting, menu engineering, and anomaly detection beyond Toast's reports."
        path="/integrations/toast"
        jsonLd={{
          '@type': 'SoftwareApplication',
          name: 'Meridian Intelligence for Toast POS',
          applicationCategory: 'BusinessApplication',
          operatingSystem: 'Web',
          offers: { '@type': 'Offer', price: '250', priceCurrency: 'USD' },
        }}
      />

      {/* Hero */}
      <section className="relative pt-28 pb-20 px-6 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-[#1A8FD6]/5 to-transparent pointer-events-none" />
        <div className="max-w-4xl mx-auto text-center relative">
          <div className="inline-flex items-center gap-3 mb-6 px-4 py-2 rounded-full border border-[#1F1F23] bg-[#111113]">
            <span className="text-[#17C5B0] font-semibold text-lg">Meridian</span>
            <span className="text-[#A1A1A8]">+</span>
            <span className="text-[#F5F5F7] font-semibold text-lg">Toast</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-6">
            Toast POS Analytics — AI-Powered Insights for Toast Restaurants
          </h1>
          <p className="text-lg text-[#A1A1A8] max-w-2xl mx-auto mb-8">
            Your Toast POS records every order, every shift, every modifier. Meridian turns that data
            into revenue forecasts, labor optimization, and menu intelligence — in plain English.
          </p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            Connect Your Toast — First Month Free <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* What Meridian Pulls */}
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl md:text-3xl font-bold mb-2">What Meridian Pulls from Toast</h2>
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
          <p className="text-[#A1A1A8] mb-10 text-center">Six layers of intelligence on top of your Toast data.</p>
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
          <h2 className="text-2xl md:text-3xl font-bold mb-2 text-center">Toast Alone vs. With Meridian</h2>
          <p className="text-[#A1A1A8] mb-8 text-center">Everything Toast gives you, plus everything it doesn't.</p>
          <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
            <div className="grid grid-cols-[2fr_1fr_1fr] bg-[#111113] border-b border-[#1F1F23]">
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider">Feature</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#A1A1A8] uppercase tracking-wider text-center">Toast</div>
              <div className="px-4 py-3 font-semibold text-sm text-[#17C5B0] uppercase tracking-wider text-center">Meridian</div>
            </div>
            {comparison.map((row, i) => (
              <div key={row.feature} className={`grid grid-cols-[2fr_1fr_1fr] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'} ${i < comparison.length - 1 ? 'border-b border-[#1F1F23]' : ''}`}>
                <div className="px-4 py-3 font-medium">{row.feature}</div>
                <div className="px-4 py-3 text-center">{row.toast ? <span className="text-[#17C5B0]">&#10003;</span> : <span className="text-[#A1A1A8]">—</span>}</div>
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
          <h2 className="text-2xl md:text-3xl font-bold mb-4">Ready to unlock your Toast data?</h2>
          <p className="text-[#A1A1A8] mb-8">Connect in under 5 minutes. See insights within the hour. First month free.</p>
          <Link
            to="/demo"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold hover:bg-[#17C5B0]/90 transition-colors"
          >
            Connect Your Toast — First Month Free <ArrowRight className="w-4 h-4" />
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
            <Link to="/integrations/clover" className="text-sm text-[#F5F5F7] hover:text-[#17C5B0] transition-colors flex items-center gap-1">
              Clover POS <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  )
}
