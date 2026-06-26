import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, ChevronRight, ArrowRight, Search } from 'lucide-react'
import SEO from '@/components/SEO'

interface FAQ { q: string; a: string; related?: string }

const categories: { title: string; id: string; items: FAQ[] }[] = [
  {
    title: 'Getting Started',
    id: 'getting-started',
    items: [
      { q: 'What is Meridian Intelligence?', a: 'Meridian Intelligence is an AI-powered analytics platform that connects to your POS system (Square, Toast, Clover, and 77 others) and generates revenue insights, anomaly alerts, and customer segmentation reports. Merchants see plain-English insights within minutes of connecting their POS — no data entry, no spreadsheets, no dashboards to learn.', related: '/what-is-pos-analytics' },
      { q: 'How long does setup take?', a: 'Most businesses connect in under 45 seconds. Select your POS, authorize via OAuth (one click for Square, Toast, and Clover), and Meridian immediately starts importing your transaction history. First insights appear within minutes. No API keys, no configuration files, no IT support needed.' },
      { q: 'Which POS systems does Meridian support?', a: 'Meridian supports 80+ POS systems including Square, Toast, Clover, Lightspeed, Shopify POS, Moneris (Canada), Alice POS, and TouchBistro. We add new integrations monthly. If your POS is not listed, contact us — we can typically add it within 2 weeks.' },
      { q: 'Do I need to change my POS to use Meridian?', a: 'No. Meridian connects to your existing POS system. You do not need to switch POS providers, install any hardware, or change any workflows. Meridian reads your transaction data through secure API connections — it never modifies your POS settings or data.' },
      { q: 'Is there a free trial?', a: 'Yes — your first month is completely free on any plan. No credit card required to start. You can connect your POS, explore your data, and see the full insights before deciding whether to continue. Cancel anytime with no penalties.' },
    ],
  },
  {
    title: 'Pricing & Plans',
    id: 'pricing',
    items: [
      { q: 'How much does Meridian cost?', a: 'Standard Plan: $250 USD/month ($339 CAD). Premium Plan: $490 USD/month ($675 CAD) — adds camera intelligence and customer segmentation. Command Plan: $980 USD/month ($1,350 CAD) — multi-location support and dedicated account manager. All plans include a free first month.' },
      { q: 'What is the ROI of Meridian?', a: 'The average merchant recovers $3,229/month in previously hidden revenue through pricing adjustments, waste reduction, and labor optimization. On the Standard plan ($250/month), that is a 13x return on investment. Most merchants see measurable results within the first 2-4 weeks.' },
      { q: 'Are there any contracts or commitments?', a: 'No. Meridian is month-to-month with no contracts, no setup fees, and no cancellation penalties. You can upgrade, downgrade, or cancel at any time from your account settings.' },
      { q: 'Is there a discount for multiple locations?', a: 'Yes. The Command Plan includes multi-location support with consolidated reporting. Contact us for custom pricing on 5+ locations — we offer volume discounts that scale with your business.' },
    ],
  },
  {
    title: 'Food Cost & Waste',
    id: 'food-cost',
    items: [
      { q: 'How do I calculate food cost percentage?', a: 'Food cost percentage = (Beginning Inventory + Purchases - Ending Inventory) / Food Sales × 100. For example: ($5,000 + $3,000 - $4,500) / $12,000 = 29.2%. Target 28-35% for most restaurant types. Meridian calculates this automatically from your POS data in real time.', related: '/guides/restaurant-food-cost-guide' },
      { q: 'What should my food cost percentage be?', a: 'It depends on your concept. Full service: 28-35%. Fast casual: 25-32%. QSR: 25-30%. Pizza: 20-28%. Coffee shops: 18-25%. Fine dining: 30-38%. The more important metric is prime cost (food + labor), which should stay below 60-65% of total revenue.', related: '/guides/restaurant-food-cost-guide' },
      { q: 'How much food waste is normal for a restaurant?', a: 'The industry average is 4-10% of total food purchased, translating to $20,000-$50,000 per year for a typical restaurant. Well-managed restaurants with tracking and forecasting reduce waste to under 2%. The first step is measuring — most operators dramatically underestimate their waste.', related: '/guides/reduce-restaurant-food-waste' },
      { q: 'How can I reduce food waste?', a: 'Start with your top 10 highest-cost ingredients — track waste on just those for two weeks. Use POS sales history to set prep quantities instead of guessing (reduces waste by 20-40%). Implement FIFO inventory rotation. Cross-utilize ingredients across multiple menu items. Run daily specials with items approaching expiration.', related: '/guides/reduce-restaurant-food-waste' },
      { q: 'What is the difference between actual and theoretical food cost?', a: 'Theoretical food cost is what your food cost should be based on recipe costs and sales mix. Actual food cost is what you really spent. The gap (variance) reveals waste, theft, over-portioning, and pricing errors. A healthy variance is under 2%. If yours exceeds 3%, start with portion audits on your five highest-cost items.' },
    ],
  },
  {
    title: 'Revenue & Pricing',
    id: 'revenue-pricing',
    items: [
      { q: 'How should I price my menu items?', a: 'Start with the food cost multiplier: divide recipe cost by target food cost percentage (e.g., $4.50 / 0.30 = $15.00). Then adjust based on competition (audit 5 closest competitors), perceived value, and demand. Use psychology: remove dollar signs, use .95 endings, place high-margin items in visual hot spots on your menu.', related: '/guides/menu-pricing-strategy' },
      { q: 'How often should I raise menu prices?', a: 'Every 6-8 months with increases of 2-3%. Food costs rise 3-5% per year on average. Small, frequent increases are barely noticed by customers. A 10% jump after two years causes sticker shock. Use POS data to identify which items have the most price elasticity — raise those first.', related: '/guides/menu-pricing-strategy' },
      { q: 'What is menu engineering?', a: 'Menu engineering categorizes every item by profitability (contribution margin) and popularity (sales volume). Stars (high profit, high sales) — promote. Plowhorses (low profit, high sales) — raise price or reduce cost. Puzzles (high profit, low sales) — improve placement. Dogs (low profit, low sales) — remove. Run this quarterly with POS data.', related: '/guides/menu-pricing-strategy' },
      { q: 'How do I increase my average ticket size?', a: 'Train servers to recommend specific items (not generic upsells). Place high-margin items in menu hot spots. Add premium tiers to popular items. Focus on beverage attachment (75-85% margin). Use bundling. A $2 increase per ticket on 100 daily transactions adds $730/month in revenue with zero marketing cost.', related: '/guides/increase-average-ticket-size' },
      { q: 'Why is my restaurant busy but not making money?', a: 'Revenue is not profit. The most common causes: food cost over 35%, labor scheduled by habit not demand, menu items priced below cost, excessive waste/comps, and no real-time financial visibility. A restaurant doing $1.2M/year at 3% margin makes only $36,000. Focus on prime cost (food + labor under 65%).', related: '/guides/why-restaurant-not-profitable' },
    ],
  },
  {
    title: 'Labor & Staffing',
    id: 'labor-staffing',
    items: [
      { q: 'What should my labor cost percentage be?', a: 'Full service: 30-35% (including benefits and payroll taxes). Fast casual: 25-30%. QSR: 20-28%. More important than the percentage alone is prime cost (food + labor combined), which should stay below 60-65% of revenue.', related: '/guides/restaurant-staffing-optimization' },
      { q: 'How do I know if I am overstaffed?', a: 'Calculate revenue per labor hour (RPLH) for each shift. Full service should target $35-50 RPLH. If Monday lunch generates $800 with $400 in labor, your RPLH is $20 — that shift is dramatically overstaffed. Pull this data for every shift for 4 weeks to find the pattern.', related: '/guides/restaurant-staffing-optimization' },
      { q: 'How much does overstaffing cost?', a: 'One extra person per shift at $15/hour for 6 hours across 7 days costs $546/week or $28,400/year. Most restaurants have 2-3 overstaffed shifts per week, meaning $15,000-$40,000 in annual excess labor cost. Data-driven scheduling eliminates this by matching staff to sales patterns.' },
      { q: 'How should I schedule restaurant staff?', a: 'Use POS hourly sales data to build staffing templates for each day. Divide expected shift revenue by target RPLH to determine headcount. Stagger start times by 30 minutes instead of bringing the whole crew in at once. Cross-train employees for flexibility during slow periods.', related: '/guides/restaurant-staffing-optimization' },
    ],
  },
  {
    title: 'Forecasting & Operations',
    id: 'forecasting',
    items: [
      { q: 'How do I forecast restaurant sales?', a: 'Start with a 4-week rolling average from your POS data for each day of the week (75-85% accuracy). Factor in weather (rain reduces traffic 10-30%), local events (20-40% impact), and holidays. AI-powered forecasting achieves 90-95% accuracy by analyzing all variables simultaneously. Meridian\'s AI model hits 94%.', related: '/guides/forecast-restaurant-sales' },
      { q: 'How does weather affect restaurant sales?', a: 'Rain reduces foot traffic by 10-30%. Extreme cold reduces dine-in by 15-25% but may increase delivery. Warm pleasant weather boosts patio dining by 30-50%. Major weather events can reduce sales by 40-60%. Track weather alongside your POS data for 3 months to discover your specific sensitivity.' },
      { q: 'What POS reports should I check daily?', a: 'Three daily: (1) Total revenue vs. forecast or same-day last week, (2) Labor cost percentage for the day, (3) Void and comp summary. Weekly: sales mix analysis, food cost percentage, average ticket by daypart. Monthly: full P&L, year-over-year comparison, customer retention.', related: '/guides/pos-data-business-decisions' },
      { q: 'What is prime cost?', a: 'Prime cost = total food/beverage cost + total labor cost (wages, benefits, payroll taxes). It is the single most important restaurant profitability metric, typically 55-65% of revenue. If prime cost exceeds 65%, the restaurant will struggle to profit regardless of revenue. Every 1% reduction on $1M revenue = $10,000 saved.' },
    ],
  },
  {
    title: 'Profitability',
    id: 'profitability',
    items: [
      { q: 'What profit margin should a restaurant expect?', a: 'Industry average is 3-5% net profit margin. Well-managed restaurants achieve 10-15%. Fast casual: 6-12%. Fine dining: 1-5% (higher absolute dollars). QSR: 6-12%. A 10%+ margin is excellent. Work backwards from your target margin to set food, labor, and overhead budgets.', related: '/blog/how-to-know-if-restaurant-is-profitable' },
      { q: 'How do I know if my restaurant is profitable?', a: 'Track seven metrics: food cost percentage (28-35%), labor cost percentage (25-35%), prime cost (under 65%), revenue per labor hour ($35-50), average ticket size, void/comp rate (under 2%), and net profit margin (target 10%+). If you cannot state these numbers right now, that is the first problem to solve.', related: '/blog/how-to-know-if-restaurant-is-profitable' },
      { q: 'How can I improve my restaurant profitability?', a: 'Quick wins: (1) Raise prices on underpriced high-volume items, (2) Cut prep quantities based on POS sales data to reduce waste, (3) Reduce staffing on overstaffed shifts. Structural improvements: menu engineering to remove Dogs, vendor renegotiation on top 20 items, cross-training for labor flexibility. Most restaurants see 5-15% improvement within 60 days.', related: '/guides/why-restaurant-not-profitable' },
      { q: 'What are the biggest expenses in a restaurant?', a: 'Food and beverage: 28-35% of revenue. Labor (wages, benefits, payroll taxes): 25-35%. Occupancy (rent, insurance, utilities): 8-15%. Marketing: 3-6%. Everything else: 5-10%. Together, food and labor (prime cost) account for 55-65% — controlling these two categories is the key to profitability.', related: '/guides/lower-restaurant-expenses' },
    ],
  },
  {
    title: 'Canada-Specific',
    id: 'canada',
    items: [
      { q: 'Does Meridian work for Canadian businesses?', a: 'Yes. Meridian has a dedicated Canadian portal at meridian.tips/canada with Canadian POS support (Moneris, Alice POS, Lightspeed), CAD pricing (starting at CA$339/month), and a platform built around PIPEDA and Quebec Law 25 — privacy-by-design, explicit consent, documented retention, and encryption.' },
      { q: 'What is PIPEDA and does Meridian comply?', a: 'PIPEDA (Personal Information Protection and Electronic Documents Act) is Canada\'s federal privacy law governing how private-sector organizations collect, use, and disclose personal information. Meridian is fully PIPEDA compliant — we obtain proper consent, limit data collection to what is necessary, and protect all data with bank-level encryption.' },
      { q: 'Does Meridian comply with Quebec Law 25?', a: 'Yes. Quebec\'s Law 25 (Bill 64) is Canada\'s strictest provincial privacy legislation, requiring explicit consent, data portability, and privacy impact assessments. Meridian meets all Law 25 requirements including consent management, data minimization, and the right to data deletion.' },
      { q: 'How does Meridian handle Canadian data and privacy?', a: 'Meridian is built around Canadian privacy law — PIPEDA and Quebec Law 25. That means privacy-by-design, explicit (opt-in) consent handling for Quebec, documented data retention, role-based access controls, and encryption in transit and at rest. Meridian\'s infrastructure runs on major cloud providers in US regions, and we are transparent about that with appropriate contractual cross-border data-transfer safeguards in place. Meridian never sees raw payment card numbers.' },
    ],
  },
  {
    title: 'Security & Privacy',
    id: 'security',
    items: [
      { q: 'Is my POS data secure with Meridian?', a: 'Yes. Meridian uses bank-level AES-256 encryption for data at rest and TLS 1.3 for data in transit. We are read-only — we never modify your POS data, process payments, or access financial account information. All connections use OAuth with minimal scope permissions.' },
      { q: 'Does Meridian access my payment card data?', a: 'No. Meridian never sees, stores, or processes credit card numbers. We receive anonymized transaction summaries from your POS — item names, quantities, timestamps, and totals. Actual payment card data stays with your POS provider and payment processor.' },
      { q: 'Can Meridian modify my POS settings or data?', a: 'No. Meridian has read-only access to your POS. We pull transaction history and product catalog data but cannot modify prices, create orders, update inventory, or change any POS configuration. You can revoke access at any time from your POS provider\'s settings.' },
    ],
  },
]

const allFaqs = categories.flatMap(c => c.items)

const jsonLd = [
  {
    '@type': 'FAQPage',
    mainEntity: allFaqs.map(item => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  },
  {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips' },
      { '@type': 'ListItem', position: 2, name: 'FAQ', item: 'https://meridian.tips/faq' },
    ],
  },
]

function FAQItem({ faq }: { faq: FAQ }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-4 sm:p-5 text-left hover:bg-[#111113] transition-colors">
        <span className="text-[#F5F5F7] font-medium text-[14px] sm:text-[15px] pr-4">{faq.q}</span>
        <ChevronDown size={18} className={`text-[#6B7280] flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="px-4 sm:px-5 pb-4 sm:pb-5 border-t border-[#1F1F23] pt-4">
          <p className="text-[#A1A1A8] text-[14px] leading-relaxed">{faq.a}</p>
          {faq.related && (
            <Link to={faq.related} className="inline-flex items-center gap-1.5 mt-3 text-[12px] text-[#1A8FD6] font-medium hover:underline">
              Learn more <ChevronRight size={12} />
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

export default function FAQHubPage() {
  const [search, setSearch] = useState('')
  const lowerSearch = search.toLowerCase()

  const filtered = search.length < 2
    ? categories
    : categories.map(cat => ({
        ...cat,
        items: cat.items.filter(
          faq => faq.q.toLowerCase().includes(lowerSearch) || faq.a.toLowerCase().includes(lowerSearch)
        ),
      })).filter(cat => cat.items.length > 0)

  return (
    <>
      <SEO
        title="FAQ — Restaurant POS Analytics Questions Answered | Meridian"
        description="Answers to common questions about restaurant profitability, food cost, menu pricing, sales forecasting, staffing, and POS analytics. Backed by industry data."
        path="/faq"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        <header className="max-w-3xl mx-auto px-4 sm:px-6 pt-28 pb-8 text-center">
          <h1 className="text-3xl sm:text-4xl font-bold tracking-tight">
            Frequently Asked{' '}
            <span className="bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] bg-clip-text text-transparent">Questions</span>
          </h1>
          <p className="mt-4 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">
            Everything restaurant and retail owners ask about POS analytics, food cost, pricing, and profitability.
          </p>
          <div className="mt-6 relative max-w-md mx-auto">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#6B7280]" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search questions..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-[#1F1F23] bg-[#111113] text-[14px] text-[#F5F5F7] placeholder-[#6B7280] focus:outline-none focus:border-[#1A8FD6] transition-colors"
            />
          </div>
        </header>

        {/* Category quick nav */}
        <nav className="max-w-3xl mx-auto px-4 sm:px-6 pb-8">
          <div className="flex flex-wrap gap-2 justify-center">
            {categories.map(cat => (
              <a
                key={cat.id}
                href={`#${cat.id}`}
                className="px-3 py-1.5 rounded-full border border-[#1F1F23] text-[12px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors"
              >
                {cat.title}
              </a>
            ))}
          </div>
        </nav>

        <main className="max-w-3xl mx-auto px-4 sm:px-6 pb-20 space-y-10">
          {filtered.map(cat => (
            <section key={cat.id} id={cat.id}>
              <h2 className="text-lg font-semibold text-[#F5F5F7] mb-4 flex items-center gap-2 scroll-mt-20">
                <span className="w-2 h-2 rounded-full bg-[#17C5B0]" />
                {cat.title}
                <span className="text-[12px] text-[#6B7280] font-normal">({cat.items.length})</span>
              </h2>
              <div className="space-y-2">
                {cat.items.map((faq, i) => <FAQItem key={i} faq={faq} />)}
              </div>
            </section>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-[#6B7280]">
              <p className="text-lg">No questions match "{search}"</p>
              <button onClick={() => setSearch('')} className="mt-3 text-[#1A8FD6] text-sm hover:underline">Clear search</button>
            </div>
          )}
        </main>

        <section className="py-16 border-t border-[#1F1F23]/40">
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">Still have questions?</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px]">See Meridian in action with live demo data — no signup required.</p>
            <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
              <Link to="/demo" className="inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
                See Live Demo <ArrowRight size={15} />
              </Link>
              <Link to="/guides" className="px-6 py-3 text-[14px] font-medium text-[#A1A1A8] border border-[#1F1F23] rounded-lg hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
                Read Our Guides
              </Link>
            </div>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <Link to="/guides" className="hover:text-[#A1A1A8]">Guides</Link>
            <Link to="/blog" className="hover:text-[#A1A1A8]">Blog</Link>
            <Link to="/onboard" className="hover:text-[#A1A1A8]">Get Started</Link>
          </div>
        </footer>
      </div>
    </>
  )
}
