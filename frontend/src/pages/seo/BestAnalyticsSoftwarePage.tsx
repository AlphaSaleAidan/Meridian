import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronRight, Check, X as XIcon, Minus } from 'lucide-react'
import { useState } from 'react'
import SEO from '@/components/SEO'

const faqItems = [
  {
    q: 'What is the best POS analytics software for restaurants?',
    a: 'The best POS analytics software depends on your size and needs. For small to mid-size restaurants (1-10 locations), Meridian is the top choice because it connects to 80+ POS systems, requires no technical setup, and provides AI-powered insights with specific dollar amounts. For large enterprises (50+ locations), Restaurant365 offers deeper ERP integration but costs significantly more. For budget-conscious operators, your POS\'s built-in reports are a free starting point, though they lack AI insights and cross-platform analysis.',
  },
  {
    q: 'How much does restaurant analytics software cost?',
    a: 'Costs range from free (basic POS reports) to $50,000+/year (enterprise BI tools). Built-in POS reporting: free but limited. Dedicated analytics platforms like Meridian: $250-$980/month. Restaurant-specific ERP with analytics (Restaurant365, MarginEdge): $300-$1,500/month. Enterprise BI (Tableau, Power BI): $50,000-$200,000/year including implementation. For most independent restaurants, a $250-$500/month analytics platform provides the best ROI.',
  },
  {
    q: 'Do I really need analytics software, or can I just use spreadsheets?',
    a: 'Spreadsheets work but cost more than you think. Manual data entry takes 5-8 hours per week per location — at $30/hour, that is $7,800-$12,500 per year in labor. Spreadsheets also cannot detect anomalies in real time, forecast with AI, or alert you to problems before they become expensive. Most restaurants that switch from spreadsheets to analytics software save more in recovered revenue ($3,000+/month) than the software costs ($250-$500/month).',
  },
  {
    q: 'Can I use restaurant analytics with any POS system?',
    a: 'It depends on the platform. Some analytics tools only work with specific POS systems. Meridian connects to 80+ POS systems including Square, Toast, Clover, Lightspeed, Shopify POS, Moneris, and TouchBistro. Before choosing an analytics platform, verify it supports your specific POS. Also check whether it uses a real-time API connection or requires manual data export — real-time is far more useful.',
  },
  {
    q: 'What should I look for in restaurant analytics software?',
    a: 'Five must-haves: (1) Automatic POS integration — no manual data entry, (2) Actionable insights with specific dollar amounts, not just charts, (3) Real-time anomaly detection — catches problems immediately, not at month-end, (4) Sales forecasting for labor and inventory planning, (5) Food cost tracking with actual vs. theoretical variance. Nice-to-haves: customer segmentation, multi-location benchmarking, mobile app, and AI-powered recommendations.',
  },
]

const comparisonTable = [
  { feature: 'Setup time', meridian: '45 seconds', spreadsheets: '2-4 hours/week', builtin: 'Built in', enterprise: '3-6 months' },
  { feature: 'POS systems supported', meridian: '80+', spreadsheets: 'Manual entry', builtin: '1 (own)', enterprise: '10-20' },
  { feature: 'AI-powered insights', meridian: true, spreadsheets: false, builtin: false, enterprise: true },
  { feature: 'Real-time anomaly detection', meridian: true, spreadsheets: false, builtin: false, enterprise: true },
  { feature: 'Sales forecasting', meridian: '94% accuracy', spreadsheets: 'Manual formulas', builtin: 'Basic', enterprise: '90-95%' },
  { feature: 'Food cost tracking', meridian: true, spreadsheets: 'Manual', builtin: 'Partial', enterprise: true },
  { feature: 'Menu engineering', meridian: true, spreadsheets: 'Manual', builtin: false, enterprise: true },
  { feature: 'Customer segmentation', meridian: true, spreadsheets: false, builtin: 'Basic', enterprise: true },
  { feature: 'Labor optimization', meridian: true, spreadsheets: false, builtin: false, enterprise: true },
  { feature: 'Multi-location', meridian: true, spreadsheets: 'Difficult', builtin: 'Varies', enterprise: true },
  { feature: 'Monthly cost', meridian: '$250-980', spreadsheets: '"Free" ($650/mo labor)', builtin: 'Free', enterprise: '$2,000-10,000+' },
  { feature: 'Best for', meridian: '1-25 locations', spreadsheets: 'Very small ops', builtin: 'Basic tracking', enterprise: '50+ locations' },
]

function CellValue({ val }: { val: string | boolean }) {
  if (val === true) return <Check size={16} className="text-[#17C5B0] mx-auto" />
  if (val === false) return <XIcon size={16} className="text-[#6B7280]/40 mx-auto" />
  if (val === 'Partial' || val === 'Basic' || val === 'Manual' || val === 'Difficult' || val === 'Varies')
    return <span className="text-[#F59E0B] text-[12px]">{val}</span>
  return <span className="text-[13px]">{val as string}</span>
}

function FAQ({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-5 text-left hover:bg-[#111113] transition-colors">
        <span className="text-[#F5F5F7] font-medium text-[15px] pr-4">{q}</span>
        <ChevronDown size={18} className={`text-[#6B7280] flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      <div className={`grid transition-all duration-200 ease-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}><div className="overflow-hidden"><div className="px-5 pb-5 text-[#A1A1A8] text-[14px] leading-relaxed border-t border-[#1F1F23] pt-4">{a}</div></div></div>
    </div>
  )
}

const jsonLd = [
  {
    '@type': 'Article',
    headline: 'Best Restaurant Analytics Software in 2026',
    description: 'Compare restaurant POS analytics options: built-in reports, spreadsheets, dedicated platforms like Meridian, and enterprise BI tools. Find the right fit for your size and budget.',
    author: { '@type': 'Organization', name: 'Meridian' },
    publisher: { '@type': 'Organization', name: 'Meridian', url: 'https://meridian.tips' },
    datePublished: '2026-05-27',
    dateModified: '2026-05-27',
  },
  {
    '@type': 'FAQPage',
    mainEntity: faqItems.map(item => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  },
  {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips' },
      { '@type': 'ListItem', position: 2, name: 'Best Restaurant Analytics Software', item: 'https://meridian.tips/best-restaurant-analytics-software' },
    ],
  },
]

export default function BestAnalyticsSoftwarePage() {
  return (
    <>
      <SEO
        title="Best Restaurant Analytics Software in 2026 — Comparison Guide | Meridian"
        description="Compare restaurant POS analytics options: built-in POS reports, spreadsheets, AI-powered platforms, and enterprise BI. Find the right tool for your size and budget."
        path="/best-restaurant-analytics-software"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        {/* Breadcrumbs */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">Best Restaurant Analytics Software</span>
          </nav>
        </div>

        {/* Hero */}
        <header className="max-w-4xl mx-auto px-4 sm:px-6 pb-12">
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-[1.1]">
            Best Restaurant Analytics{' '}
            <span className="bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] bg-clip-text text-transparent">Software in 2026</span>
          </h1>
          <p className="mt-5 text-lg text-[#A1A1A8] leading-relaxed max-w-2xl">
            Your POS captures thousands of transactions. The right analytics tool turns that data into decisions that increase profit by 5-15%. Here is how the options compare.
          </p>
        </header>

        {/* Overview */}
        <article className="max-w-4xl mx-auto px-4 sm:px-6 pb-12 space-y-12">
          <section>
            <h2 className="text-2xl font-bold mb-4">Four Approaches to Restaurant Analytics</h2>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              Every restaurant has POS data. The question is how you analyze it. There are four approaches, each suited to different sizes and budgets:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[
                { title: 'Built-in POS Reports', desc: 'Free reports from Square, Toast, or Clover. Good for basic sales tracking. Limited to one POS, no AI, no forecasting, no food cost tracking.', cost: 'Free', best: 'Single location, basic needs' },
                { title: 'Spreadsheets', desc: 'Manual data entry into Excel or Google Sheets. Complete control but requires 5-8 hours/week. No real-time alerts. Error-prone and does not scale.', cost: '"Free" ($650/mo in labor)', best: 'Very small operations' },
                { title: 'AI Analytics (Meridian)', desc: 'Connects to your POS automatically. AI surfaces insights with specific dollar amounts. Real-time anomaly detection. Forecasting, menu engineering, staffing.', cost: '$250-980/mo', best: '1-25 locations' },
                { title: 'Enterprise BI', desc: 'Tableau, Power BI, or restaurant-specific ERP. Full customization but requires data engineers and months of setup. Very expensive.', cost: '$2,000-10,000+/mo', best: '50+ locations, corporate chains' },
              ].map(opt => (
                <div key={opt.title} className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5">
                  <h3 className="text-[#F5F5F7] font-semibold text-[16px] mb-2">{opt.title}</h3>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed mb-3">{opt.desc}</p>
                  <div className="flex items-center gap-3 text-[12px]">
                    <span className="text-[#17C5B0] font-mono font-medium">{opt.cost}</span>
                    <span className="text-[#6B7280]">·</span>
                    <span className="text-[#6B7280]">Best for: {opt.best}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Comparison Table */}
          <section>
            <h2 className="text-2xl font-bold mb-4">Feature Comparison</h2>
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <table className="w-full min-w-[640px] border border-[#1F1F23] rounded-xl overflow-hidden text-[13px]">
                <thead>
                  <tr className="bg-[#111113] border-b border-[#1F1F23]">
                    <th className="text-left p-3 text-[#A1A1A8] font-medium">Feature</th>
                    <th className="text-center p-3 text-[#17C5B0] font-semibold">Meridian</th>
                    <th className="text-center p-3 text-[#A1A1A8] font-medium">Spreadsheets</th>
                    <th className="text-center p-3 text-[#A1A1A8] font-medium">Built-in POS</th>
                    <th className="text-center p-3 text-[#A1A1A8] font-medium">Enterprise BI</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonTable.map((row, i) => (
                    <tr key={row.feature} className={`border-b border-[#1F1F23] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'}`}>
                      <td className="p-3 text-[#F5F5F7] font-medium">{row.feature}</td>
                      <td className="p-3 text-center text-[#F5F5F7]"><CellValue val={row.meridian} /></td>
                      <td className="p-3 text-center text-[#A1A1A8]"><CellValue val={row.spreadsheets} /></td>
                      <td className="p-3 text-center text-[#A1A1A8]"><CellValue val={row.builtin} /></td>
                      <td className="p-3 text-center text-[#A1A1A8]"><CellValue val={row.enterprise} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* Why Meridian */}
          <section>
            <h2 className="text-2xl font-bold mb-4">Why Meridian for Independent Restaurants</h2>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              Independent restaurants and small groups (1-25 locations) have a unique set of needs: they need powerful analytics but cannot afford a data team, months of setup, or enterprise pricing. Meridian was built specifically for this gap.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { metric: '$3,229/mo', label: 'Average revenue recovered per merchant' },
                { metric: '94%', label: 'Forecast accuracy with AI models' },
                { metric: '45 sec', label: 'Setup time — POS to first insights' },
              ].map(m => (
                <div key={m.label} className="rounded-lg border border-[#1F1F23] bg-[#111113] p-5 text-center">
                  <div className="text-2xl font-bold text-[#17C5B0] font-mono">{m.metric}</div>
                  <p className="text-[#A1A1A8] text-[12px] mt-1">{m.label}</p>
                </div>
              ))}
            </div>
          </section>

          {/* Decision guide */}
          <section>
            <h2 className="text-2xl font-bold mb-4">Which Option Is Right for You?</h2>
            <div className="space-y-3">
              {[
                { scenario: 'You have 1 location, just opened, and want to track basic sales', rec: 'Start with your POS\'s built-in reports. Upgrade to Meridian when you want to move beyond "what sold" to "what should I change."' },
                { scenario: 'You have 1-5 locations and want to increase profitability', rec: 'Meridian Standard ($250/mo). AI insights, food cost tracking, and staffing optimization will more than pay for itself within the first month.' },
                { scenario: 'You manage 5-25 locations and need unified reporting', rec: 'Meridian Command ($980/mo). Consolidated dashboard across all locations with benchmarking, multi-POS support, and dedicated account management.' },
                { scenario: 'You are a corporate chain with 50+ locations', rec: 'Enterprise BI or restaurant ERP. The setup cost and complexity are justified at scale. Consider Meridian as a complement for real-time anomaly detection.' },
              ].map(item => (
                <div key={item.scenario} className="rounded-lg border border-[#1F1F23] bg-[#111113] p-5">
                  <p className="text-[#F5F5F7] font-medium text-[14px] mb-2">{item.scenario}</p>
                  <p className="text-[#A1A1A8] text-[13px] leading-relaxed">{item.rec}</p>
                </div>
              ))}
            </div>
          </section>
        </article>

        {/* FAQ */}
        <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-16">
          <h2 className="text-2xl font-bold mb-6">Frequently Asked Questions</h2>
          <div className="space-y-3">
            {faqItems.map((faq, i) => <FAQ key={i} q={faq.q} a={faq.a} />)}
          </div>
        </section>

        {/* Related */}
        <section className="max-w-4xl mx-auto px-4 sm:px-6 pb-12">
          <h3 className="text-lg font-semibold mb-4">Related Pages</h3>
          <div className="flex flex-wrap gap-2">
            {[
              { to: '/vs/spreadsheets', label: 'POS Analytics vs. Spreadsheets' },
              { to: '/what-is-pos-analytics', label: 'What Is POS Analytics?' },
              { to: '/guides/pos-data-business-decisions', label: 'How to Use POS Data' },
              { to: '/for/restaurants', label: 'Restaurant Analytics' },
              { to: '/for/coffee-shops', label: 'Coffee Shop Analytics' },
              { to: '/guides', label: 'All Guides' },
            ].map(link => (
              <Link key={link.to} to={link.to} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
                {link.label} <ChevronRight size={12} />
              </Link>
            ))}
          </div>
        </section>

        {/* CTA */}
        <section className="py-20 border-t border-[#1F1F23]/40 relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-[0.06]" style={{ background: 'radial-gradient(circle, #1A8FD6 0%, transparent 70%)' }} />
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">See the difference in 45 seconds.</h2>
            <p className="mt-4 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">Connect your POS and get AI-powered insights with specific dollar amounts. First month free — no credit card required.</p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link to="/onboard" className="group px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors inline-flex items-center gap-2">
                Get Started Free <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
              </Link>
              <Link to="/demo" className="px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
                See Live Demo
              </Link>
            </div>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <Link to="/guides" className="hover:text-[#A1A1A8]">Guides</Link>
            <Link to="/faq" className="hover:text-[#A1A1A8]">FAQ</Link>
            <Link to="/blog" className="hover:text-[#A1A1A8]">Blog</Link>
            <Link to="/onboard" className="hover:text-[#A1A1A8]">Get Started</Link>
          </div>
        </footer>
      </div>
    </>
  )
}
