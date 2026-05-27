import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronRight, Calculator, RotateCcw } from 'lucide-react'
import SEO from '@/components/SEO'

function num(v: string): number {
  const n = parseFloat(v)
  return isNaN(n) ? 0 : n
}

function pct(n: number): string {
  return n.toFixed(1) + '%'
}

function usd(n: number): string {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const faqItems = [
  { q: 'What is food cost percentage?', a: 'Food cost percentage measures how much of your food revenue goes toward purchasing food ingredients. It is calculated as: (Beginning Inventory + Purchases - Ending Inventory) / Food Sales × 100. Most restaurants should target 28-35%, though the ideal range depends on your concept — fine dining runs 30-38% while pizza and coffee shops can hit 20-28%.' },
  { q: 'How often should I calculate food cost?', a: 'Weekly at minimum. High-volume restaurants benefit from daily tracking. Monthly is too infrequent — problems compound for 30 days before you discover them. Automated POS analytics tools like Meridian calculate food cost in real time, eliminating the need for manual calculation entirely.' },
  { q: 'What is prime cost?', a: 'Prime cost is food and beverage cost plus total labor cost (wages, benefits, payroll taxes). It is the single most important profitability metric for restaurants, typically accounting for 55-65% of total revenue. If prime cost exceeds 65%, your restaurant will struggle to be profitable regardless of revenue level.' },
  { q: 'What is a good food cost for a restaurant?', a: 'Target food cost by concept: Full service 28-35%, Fast casual 25-32%, QSR 25-30%, Pizza 20-28%, Coffee shops 18-25%, Fine dining 30-38%. The key metric is not food cost alone but prime cost (food + labor), which should stay below 60-65% of revenue.' },
  { q: 'Why is my food cost so high?', a: 'Common causes: over-portioning (staff serving more than recipes call for), waste and spoilage from poor inventory management, theft or unrecorded consumption, menu prices that haven\'t kept up with ingredient cost increases, and recipes that were never accurately costed. Start by comparing actual vs. theoretical food cost to find the gap.' },
]

const jsonLd = [
  {
    '@type': 'WebApplication',
    name: 'Restaurant Food Cost Calculator',
    applicationCategory: 'BusinessApplication',
    description: 'Free online food cost calculator for restaurants. Calculate food cost percentage, prime cost, and annual savings from optimizing your food costs.',
    url: 'https://meridian.tips/tools/food-cost-calculator',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' },
    provider: { '@type': 'Organization', name: 'Meridian Intelligence', url: 'https://meridian.tips' },
  },
  {
    '@type': 'FAQPage',
    mainEntity: faqItems.map(item => ({
      '@type': 'Question', name: item.q,
      acceptedAnswer: { '@type': 'Answer', text: item.a },
    })),
  },
  {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips' },
      { '@type': 'ListItem', position: 2, name: 'Tools', item: 'https://meridian.tips/tools' },
      { '@type': 'ListItem', position: 3, name: 'Food Cost Calculator', item: 'https://meridian.tips/tools/food-cost-calculator' },
    ],
  },
]

function FAQ({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="border border-[#1F1F23] rounded-lg overflow-hidden">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between p-5 text-left hover:bg-[#111113] transition-colors">
        <span className="text-[#F5F5F7] font-medium text-[15px] pr-4">{q}</span>
        <ChevronDown size={18} className={`text-[#6B7280] flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && <div className="px-5 pb-5 text-[#A1A1A8] text-[14px] leading-relaxed border-t border-[#1F1F23] pt-4">{a}</div>}
    </div>
  )
}

function ResultCard({ label, value, sub, color = '#17C5B0' }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="rounded-lg border border-[#1F1F23] bg-[#111113] p-4 text-center">
      <p className="text-[12px] text-[#A1A1A8] mb-1">{label}</p>
      <p className="text-2xl font-bold font-mono" style={{ color }}>{value}</p>
      {sub && <p className="text-[11px] text-[#6B7280] mt-1">{sub}</p>}
    </div>
  )
}

export default function FoodCostCalculatorPage() {
  const [beginInv, setBeginInv] = useState('')
  const [purchases, setPurchases] = useState('')
  const [endInv, setEndInv] = useState('')
  const [foodSales, setFoodSales] = useState('')
  const [laborCost, setLaborCost] = useState('')
  const [annualRevenue, setAnnualRevenue] = useState('')

  const beg = num(beginInv)
  const pur = num(purchases)
  const end = num(endInv)
  const sales = num(foodSales)
  const labor = num(laborCost)
  const annual = num(annualRevenue)

  const cogs = beg + pur - end
  const foodCostPct = sales > 0 ? (cogs / sales) * 100 : 0
  const laborPct = sales > 0 ? (labor / sales) * 100 : 0
  const primeCostPct = foodCostPct + laborPct
  const hasResult = sales > 0 && cogs > 0

  const targetFoodCost = 30
  const variance = foodCostPct - targetFoodCost
  const annualSavings = annual > 0 && variance > 0 ? (variance / 100) * annual : 0

  let healthLabel = ''
  let healthColor = '#17C5B0'
  if (hasResult) {
    if (foodCostPct <= 30) { healthLabel = 'Excellent'; healthColor = '#17C5B0' }
    else if (foodCostPct <= 35) { healthLabel = 'Healthy'; healthColor = '#17C5B0' }
    else if (foodCostPct <= 40) { healthLabel = 'High — review needed'; healthColor = '#F59E0B' }
    else { healthLabel = 'Critical — take action'; healthColor = '#EF4444' }
  }

  function reset() {
    setBeginInv(''); setPurchases(''); setEndInv(''); setFoodSales(''); setLaborCost(''); setAnnualRevenue('')
  }

  return (
    <>
      <SEO
        title="Free Restaurant Food Cost Calculator — Calculate Food Cost Percentage | Meridian"
        description="Calculate your restaurant food cost percentage, prime cost, and potential savings. Free online calculator with benchmarks by restaurant type."
        path="/tools/food-cost-calculator"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">Food Cost Calculator</span>
          </nav>
        </div>

        <header className="max-w-3xl mx-auto px-4 sm:px-6 pb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
              <Calculator size={20} className="text-[#17C5B0]" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Food Cost Calculator</h1>
              <p className="text-[13px] text-[#6B7280]">Free tool for restaurant owners</p>
            </div>
          </div>
          <p className="text-[#A1A1A8] text-[15px] leading-relaxed">
            Enter your numbers for any period (weekly recommended). See your food cost percentage, prime cost, and how much you could save by hitting industry benchmarks.
          </p>
        </header>

        <main className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          {/* Calculator */}
          <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 sm:p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Enter Your Numbers</h2>
              <button onClick={reset} className="flex items-center gap-1.5 text-[12px] text-[#6B7280] hover:text-[#A1A1A8] transition-colors">
                <RotateCcw size={12} /> Reset
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              {[
                { label: 'Beginning Inventory ($)', value: beginInv, set: setBeginInv, hint: 'Value of food on hand at start of period' },
                { label: 'Purchases ($)', value: purchases, set: setPurchases, hint: 'Total food purchased during period' },
                { label: 'Ending Inventory ($)', value: endInv, set: setEndInv, hint: 'Value of food on hand at end of period' },
                { label: 'Food Sales ($)', value: foodSales, set: setFoodSales, hint: 'Total food revenue during period' },
              ].map(field => (
                <div key={field.label}>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">{field.label}</label>
                  <input
                    type="number"
                    value={field.value}
                    onChange={e => field.set(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                  />
                  <p className="text-[11px] text-[#6B7280] mt-1">{field.hint}</p>
                </div>
              ))}
            </div>

            <div className="border-t border-[#1F1F23] pt-4 mb-4">
              <p className="text-[13px] text-[#A1A1A8] mb-3">Optional — for prime cost and annual savings</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">Labor Cost ($)</label>
                  <input
                    type="number"
                    value={laborCost}
                    onChange={e => setLaborCost(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                  />
                  <p className="text-[11px] text-[#6B7280] mt-1">Total labor for same period (wages + benefits)</p>
                </div>
                <div>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">Annual Revenue ($)</label>
                  <input
                    type="number"
                    value={annualRevenue}
                    onChange={e => setAnnualRevenue(e.target.value)}
                    placeholder="0"
                    className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                  />
                  <p className="text-[11px] text-[#6B7280] mt-1">For calculating annual savings potential</p>
                </div>
              </div>
            </div>

            {/* Results */}
            {hasResult && (
              <div className="border-t border-[#1F1F23] pt-6 mt-6">
                <h3 className="text-lg font-semibold mb-4">Your Results</h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                  <ResultCard label="Food Cost %" value={pct(foodCostPct)} sub={healthLabel} color={healthColor} />
                  <ResultCard label="Cost of Goods" value={usd(cogs)} sub="(food used)" />
                  {labor > 0 && <ResultCard label="Prime Cost %" value={pct(primeCostPct)} sub={primeCostPct <= 65 ? 'Healthy' : 'Above target'} color={primeCostPct <= 65 ? '#17C5B0' : '#F59E0B'} />}
                  {annualSavings > 0 && <ResultCard label="Annual Savings" value={usd(annualSavings)} sub="if you hit 30% food cost" color="#1A8FD6" />}
                </div>

                {/* Benchmark comparison */}
                <div className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] p-4 mt-4">
                  <p className="text-[13px] text-[#A1A1A8] mb-3">How you compare to benchmarks:</p>
                  <div className="space-y-2">
                    {[
                      { label: 'Your food cost', value: foodCostPct },
                      { label: 'Full service target', value: 32, benchmark: true },
                      { label: 'Fast casual target', value: 28, benchmark: true },
                      { label: 'QSR target', value: 27, benchmark: true },
                    ].map(row => (
                      <div key={row.label} className="flex items-center gap-3">
                        <span className="text-[12px] text-[#A1A1A8] w-36 flex-shrink-0">{row.label}</span>
                        <div className="flex-1 h-4 bg-[#1F1F23] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all duration-500"
                            style={{
                              width: `${Math.min(row.value / 50 * 100, 100)}%`,
                              backgroundColor: row.benchmark ? '#6B7280' : healthColor,
                            }}
                          />
                        </div>
                        <span className="text-[12px] font-mono w-12 text-right" style={{ color: row.benchmark ? '#6B7280' : healthColor }}>
                          {pct(row.value)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Formula explanation */}
          <section className="mt-12">
            <h2 className="text-xl font-bold mb-4">How Food Cost Percentage Is Calculated</h2>
            <div className="rounded-lg border border-[#1F1F23] bg-[#111113] p-5 font-mono text-center text-[14px] text-[#A1A1A8] mb-4">
              Food Cost % = (Beginning Inventory + Purchases − Ending Inventory) ÷ Food Sales × 100
            </div>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              This formula calculates the percentage of your food revenue that goes toward purchasing food ingredients. The result tells you how efficiently you are converting food purchases into revenue.
            </p>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              For example, if you start the week with $5,000 in food inventory, purchase $3,000, end the week with $4,500, and generate $12,000 in food sales: ($5,000 + $3,000 - $4,500) / $12,000 × 100 = <strong className="text-[#17C5B0]">29.2%</strong>. This is a healthy food cost for most restaurant concepts.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold mb-4">Food Cost Benchmarks by Restaurant Type</h2>
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <table className="w-full min-w-[400px] text-[13px] border border-[#1F1F23] rounded-lg overflow-hidden">
                <thead><tr className="bg-[#111113] border-b border-[#1F1F23]">
                  <th className="text-left p-3 text-[#A1A1A8] font-medium">Concept</th>
                  <th className="text-center p-3 text-[#A1A1A8] font-medium">Target Food Cost</th>
                  <th className="text-center p-3 text-[#A1A1A8] font-medium">Target Prime Cost</th>
                </tr></thead>
                <tbody>
                  {[
                    { type: 'Fine Dining', food: '30-38%', prime: '60-68%' },
                    { type: 'Full Service', food: '28-35%', prime: '55-65%' },
                    { type: 'Fast Casual', food: '25-32%', prime: '55-62%' },
                    { type: 'Quick Service (QSR)', food: '25-30%', prime: '55-60%' },
                    { type: 'Pizza', food: '20-28%', prime: '50-60%' },
                    { type: 'Coffee Shop', food: '18-25%', prime: '50-58%' },
                    { type: 'Bar / Nightclub', food: '20-25%', prime: '45-55%' },
                  ].map((row, i) => (
                    <tr key={row.type} className={`border-b border-[#1F1F23] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'}`}>
                      <td className="p-3 text-[#F5F5F7] font-medium">{row.type}</td>
                      <td className="p-3 text-center text-[#17C5B0] font-mono">{row.food}</td>
                      <td className="p-3 text-center text-[#A1A1A8] font-mono">{row.prime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* FAQ */}
          <section className="mt-12">
            <h2 className="text-xl font-bold mb-6">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {faqItems.map((faq, i) => <FAQ key={i} q={faq.q} a={faq.a} />)}
            </div>
          </section>

          {/* Related */}
          <section className="mt-10">
            <h3 className="text-lg font-semibold mb-4">Related Resources</h3>
            <div className="flex flex-wrap gap-2">
              {[
                { to: '/guides/restaurant-food-cost-guide', label: 'Food Cost Guide' },
                { to: '/guides/reduce-restaurant-food-waste', label: 'Reduce Food Waste' },
                { to: '/guides/menu-pricing-strategy', label: 'Menu Pricing Strategy' },
                { to: '/guides/why-restaurant-not-profitable', label: 'Why Your Restaurant Isn\'t Profitable' },
                { to: '/faq', label: 'All FAQs' },
              ].map(link => (
                <Link key={link.to} to={link.to} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
                  {link.label} <ChevronRight size={12} />
                </Link>
              ))}
            </div>
          </section>
        </main>

        {/* CTA */}
        <section className="py-16 border-t border-[#1F1F23]/40 relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-[0.06]" style={{ background: 'radial-gradient(circle, #1A8FD6 0%, transparent 70%)' }} />
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl font-bold">Track food cost automatically — in real time.</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">Stop calculating manually. Meridian connects to your POS and tracks food cost continuously with alerts when it exceeds your target.</p>
            <Link to="/onboard" className="mt-6 inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              Get Started Free <ArrowRight size={15} />
            </Link>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <Link to="/guides" className="hover:text-[#A1A1A8]">Guides</Link>
            <Link to="/faq" className="hover:text-[#A1A1A8]">FAQ</Link>
            <Link to="/blog" className="hover:text-[#A1A1A8]">Blog</Link>
          </div>
        </footer>
      </div>
    </>
  )
}
