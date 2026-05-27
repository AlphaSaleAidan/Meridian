import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronRight, Calculator, RotateCcw } from 'lucide-react'
import SEO from '@/components/SEO'

function num(v: string): number { const n = parseFloat(v); return isNaN(n) ? 0 : n }
function pct(n: number): string { return n.toFixed(1) + '%' }
function usd(n: number): string { return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }

const faqItems = [
  { q: 'What is prime cost in a restaurant?', a: 'Prime cost is the sum of your total food and beverage costs (COGS) plus your total labor costs, including wages, salaries, payroll taxes, and benefits. It is the single most important profitability metric in the restaurant industry because it typically accounts for 55-65% of total revenue. If your prime cost exceeds 65%, your restaurant is almost certainly struggling to generate meaningful profit.' },
  { q: 'What is a good prime cost percentage?', a: 'Target prime cost varies by concept: Full service 55-65%, Fast casual 55-62%, QSR 55-60%, Coffee shops 50-58%, Bars 45-55%. The key is that prime cost below 60% gives you room for rent, utilities, marketing, and profit. Above 65% means you are likely losing money or barely breaking even.' },
  { q: 'How do I lower my prime cost?', a: 'You have two levers — food cost and labor cost. On the food side: reduce waste, renegotiate vendor pricing, engineer your menu to promote high-margin items, and implement strict portioning. On the labor side: match staffing to sales patterns using POS data, cross-train employees, stagger shift start times, and reduce hours on consistently slow shifts.' },
  { q: 'How often should I calculate prime cost?', a: 'Weekly is ideal. Monthly is the minimum acceptable frequency. At $1M annual revenue, every percentage point of prime cost equals $10,000 per year — so catching a problem one week earlier saves roughly $200. Automated tools like Meridian calculate prime cost in real time from your POS data.' },
  { q: 'Is prime cost more important than food cost alone?', a: 'Yes. A restaurant with 28% food cost and 38% labor has a 66% prime cost and is likely unprofitable. A restaurant with 35% food cost and 26% labor has a 61% prime cost and is healthier. Looking at food cost in isolation can be misleading — prime cost tells the complete story.' },
]

const jsonLd = [
  { '@type': 'WebApplication', name: 'Restaurant Prime Cost Calculator', applicationCategory: 'BusinessApplication', description: 'Free online prime cost calculator for restaurants. Calculate prime cost percentage and see how your food and labor costs compare to industry benchmarks.', url: 'https://meridian.tips/tools/prime-cost-calculator', offers: { '@type': 'Offer', price: '0', priceCurrency: 'USD' }, provider: { '@type': 'Organization', name: 'Meridian Intelligence', url: 'https://meridian.tips' } },
  { '@type': 'FAQPage', mainEntity: faqItems.map(item => ({ '@type': 'Question', name: item.q, acceptedAnswer: { '@type': 'Answer', text: item.a } })) },
  { '@type': 'BreadcrumbList', itemListElement: [{ '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips' }, { '@type': 'ListItem', position: 2, name: 'Tools', item: 'https://meridian.tips/tools' }, { '@type': 'ListItem', position: 3, name: 'Prime Cost Calculator', item: 'https://meridian.tips/tools/prime-cost-calculator' }] },
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

export default function PrimeCostCalculatorPage() {
  const [foodCost, setFoodCost] = useState('')
  const [bevCost, setBevCost] = useState('')
  const [wages, setWages] = useState('')
  const [benefits, setBenefits] = useState('')
  const [payrollTax, setPayrollTax] = useState('')
  const [totalRevenue, setTotalRevenue] = useState('')
  const [annualRevenue, setAnnualRevenue] = useState('')

  const food = num(foodCost)
  const bev = num(bevCost)
  const wage = num(wages)
  const ben = num(benefits)
  const tax = num(payrollTax)
  const rev = num(totalRevenue)
  const annual = num(annualRevenue)

  const cogs = food + bev
  const totalLabor = wage + ben + tax
  const primeCost = cogs + totalLabor
  const cogsPct = rev > 0 ? (cogs / rev) * 100 : 0
  const laborPct = rev > 0 ? (totalLabor / rev) * 100 : 0
  const primePct = rev > 0 ? (primeCost / rev) * 100 : 0
  const hasResult = rev > 0 && primeCost > 0

  const remaining = rev > 0 ? rev - primeCost : 0
  const remainingPct = rev > 0 ? (remaining / rev) * 100 : 0

  const targetPrime = 60
  const overTarget = primePct - targetPrime
  const annualSavings = annual > 0 && overTarget > 0 ? (overTarget / 100) * annual : 0

  let healthLabel = ''
  let healthColor = '#17C5B0'
  if (hasResult) {
    if (primePct <= 58) { healthLabel = 'Excellent'; healthColor = '#17C5B0' }
    else if (primePct <= 63) { healthLabel = 'Healthy'; healthColor = '#17C5B0' }
    else if (primePct <= 68) { healthLabel = 'High — needs attention'; healthColor = '#F59E0B' }
    else { healthLabel = 'Critical — take action now'; healthColor = '#EF4444' }
  }

  function reset() { setFoodCost(''); setBevCost(''); setWages(''); setBenefits(''); setPayrollTax(''); setTotalRevenue(''); setAnnualRevenue('') }

  return (
    <>
      <SEO title="Free Restaurant Prime Cost Calculator — Food + Labor | Meridian" description="Calculate your restaurant prime cost (food + labor as a percentage of revenue). Free calculator with industry benchmarks and savings projections." path="/tools/prime-cost-calculator" jsonLd={jsonLd} />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <ChevronRight size={12} />
            <Link to="/tools/food-cost-calculator" className="hover:text-[#A1A1A8]">Tools</Link>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">Prime Cost Calculator</span>
          </nav>
        </div>

        <header className="max-w-3xl mx-auto px-4 sm:px-6 pb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center">
              <Calculator size={20} className="text-[#1A8FD6]" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Prime Cost Calculator</h1>
              <p className="text-[13px] text-[#6B7280]">The #1 restaurant profitability metric</p>
            </div>
          </div>
          <p className="text-[#A1A1A8] text-[15px] leading-relaxed">
            Prime cost = food &amp; beverage costs + total labor. It is the single most important number in your restaurant. Enter your numbers for any period (weekly recommended) and see how you compare.
          </p>
        </header>

        <main className="max-w-3xl mx-auto px-4 sm:px-6 pb-16">
          <div className="rounded-xl border border-[#1F1F23] bg-[#111113] p-5 sm:p-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold">Enter Your Numbers</h2>
              <button onClick={reset} className="flex items-center gap-1.5 text-[12px] text-[#6B7280] hover:text-[#A1A1A8] transition-colors"><RotateCcw size={12} /> Reset</button>
            </div>

            <p className="text-[13px] text-[#A1A1A8] mb-3">Cost of Goods Sold (COGS)</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              {[
                { label: 'Food Cost ($)', value: foodCost, set: setFoodCost, hint: 'Total food purchases minus inventory change' },
                { label: 'Beverage Cost ($)', value: bevCost, set: setBevCost, hint: 'Alcohol, soft drinks, coffee (optional)' },
              ].map(f => (
                <div key={f.label}>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">{f.label}</label>
                  <input type="number" value={f.value} onChange={e => f.set(e.target.value)} placeholder="0" className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors" />
                  <p className="text-[11px] text-[#6B7280] mt-1">{f.hint}</p>
                </div>
              ))}
            </div>

            <p className="text-[13px] text-[#A1A1A8] mb-3">Labor Costs</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
              {[
                { label: 'Wages & Salaries ($)', value: wages, set: setWages, hint: 'All employee pay for the period' },
                { label: 'Benefits ($)', value: benefits, set: setBenefits, hint: 'Health insurance, PTO, etc.' },
                { label: 'Payroll Taxes ($)', value: payrollTax, set: setPayrollTax, hint: 'Employer-side payroll taxes' },
              ].map(f => (
                <div key={f.label}>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">{f.label}</label>
                  <input type="number" value={f.value} onChange={e => f.set(e.target.value)} placeholder="0" className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors" />
                  <p className="text-[11px] text-[#6B7280] mt-1">{f.hint}</p>
                </div>
              ))}
            </div>

            <p className="text-[13px] text-[#A1A1A8] mb-3">Revenue</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              {[
                { label: 'Total Revenue ($)', value: totalRevenue, set: setTotalRevenue, hint: 'Total sales for this period' },
                { label: 'Annual Revenue ($)', value: annualRevenue, set: setAnnualRevenue, hint: 'Optional — for annual savings calculation' },
              ].map(f => (
                <div key={f.label}>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">{f.label}</label>
                  <input type="number" value={f.value} onChange={e => f.set(e.target.value)} placeholder="0" className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors" />
                  <p className="text-[11px] text-[#6B7280] mt-1">{f.hint}</p>
                </div>
              ))}
            </div>

            {hasResult && (
              <div className="border-t border-[#1F1F23] pt-6 mt-4">
                <h3 className="text-lg font-semibold mb-4">Your Results</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                  <ResultCard label="Prime Cost %" value={pct(primePct)} sub={healthLabel} color={healthColor} />
                  <ResultCard label="COGS %" value={pct(cogsPct)} sub={usd(cogs)} />
                  <ResultCard label="Labor %" value={pct(laborPct)} sub={usd(totalLabor)} />
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                  <ResultCard label="Prime Cost $" value={usd(primeCost)} />
                  <ResultCard label="Remaining" value={usd(remaining)} sub={pct(remainingPct) + ' for rent, overhead, profit'} color={remainingPct >= 35 ? '#17C5B0' : '#F59E0B'} />
                  {annualSavings > 0 && <ResultCard label="Annual Savings" value={usd(annualSavings)} sub="if you hit 60% prime cost" color="#1A8FD6" />}
                </div>

                {/* Breakdown bar */}
                <div className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] p-4 mt-4">
                  <p className="text-[13px] text-[#A1A1A8] mb-3">Revenue breakdown:</p>
                  <div className="h-8 rounded-full overflow-hidden flex">
                    <div style={{ width: `${cogsPct}%`, backgroundColor: '#1A8FD6' }} className="flex items-center justify-center text-[10px] font-mono text-white min-w-[40px]">
                      {cogsPct > 8 && `COGS ${pct(cogsPct)}`}
                    </div>
                    <div style={{ width: `${laborPct}%`, backgroundColor: '#7C3AED' }} className="flex items-center justify-center text-[10px] font-mono text-white min-w-[40px]">
                      {laborPct > 8 && `Labor ${pct(laborPct)}`}
                    </div>
                    <div style={{ width: `${Math.max(remainingPct, 0)}%`, backgroundColor: '#17C5B0' }} className="flex items-center justify-center text-[10px] font-mono text-white min-w-[40px]">
                      {remainingPct > 8 && `${pct(remainingPct)}`}
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-3 text-[11px]">
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-[#1A8FD6]" /> Food & Bev</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-[#7C3AED]" /> Labor</span>
                    <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded bg-[#17C5B0]" /> Overhead + Profit</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          <section className="mt-12">
            <h2 className="text-xl font-bold mb-4">How Prime Cost Is Calculated</h2>
            <div className="rounded-lg border border-[#1F1F23] bg-[#111113] p-5 font-mono text-center text-[14px] text-[#A1A1A8] mb-4">
              Prime Cost = (Food Cost + Beverage Cost) + (Wages + Benefits + Payroll Tax)
            </div>
            <div className="rounded-lg border border-[#1F1F23] bg-[#111113] p-5 font-mono text-center text-[14px] text-[#A1A1A8] mb-4">
              Prime Cost % = Prime Cost ÷ Total Revenue × 100
            </div>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              Prime cost captures the two largest expense categories in any restaurant: what you spend on ingredients and what you spend on people. Together these typically account for 55-65% of total revenue. The remaining 35-45% must cover rent, utilities, marketing, equipment, insurance, and profit.
            </p>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75]">
              Every percentage point of prime cost on $1M in annual revenue equals $10,000. A restaurant that reduces prime cost from 66% to 61% on $1M in revenue adds $50,000 to the bottom line — often the difference between losing money and generating a healthy profit.
            </p>
          </section>

          <section className="mt-10">
            <h2 className="text-xl font-bold mb-4">Prime Cost Benchmarks by Restaurant Type</h2>
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <table className="w-full min-w-[480px] text-[13px] border border-[#1F1F23] rounded-lg overflow-hidden">
                <thead><tr className="bg-[#111113] border-b border-[#1F1F23]">
                  <th className="text-left p-3 text-[#A1A1A8] font-medium">Concept</th>
                  <th className="text-center p-3 text-[#A1A1A8] font-medium">Food Cost</th>
                  <th className="text-center p-3 text-[#A1A1A8] font-medium">Labor Cost</th>
                  <th className="text-center p-3 text-[#17C5B0] font-semibold">Prime Cost</th>
                </tr></thead>
                <tbody>
                  {[
                    { type: 'Fine Dining', food: '30-38%', labor: '30-35%', prime: '60-68%' },
                    { type: 'Full Service', food: '28-35%', labor: '28-33%', prime: '55-65%' },
                    { type: 'Fast Casual', food: '25-32%', labor: '25-30%', prime: '55-62%' },
                    { type: 'Quick Service', food: '25-30%', labor: '20-28%', prime: '55-60%' },
                    { type: 'Pizza', food: '20-28%', labor: '25-30%', prime: '50-60%' },
                    { type: 'Coffee Shop', food: '18-25%', labor: '28-35%', prime: '50-58%' },
                    { type: 'Bar / Nightclub', food: '20-25%', labor: '22-30%', prime: '45-55%' },
                  ].map((r, i) => (
                    <tr key={r.type} className={`border-b border-[#1F1F23] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'}`}>
                      <td className="p-3 text-[#F5F5F7] font-medium">{r.type}</td>
                      <td className="p-3 text-center text-[#A1A1A8] font-mono">{r.food}</td>
                      <td className="p-3 text-center text-[#A1A1A8] font-mono">{r.labor}</td>
                      <td className="p-3 text-center text-[#17C5B0] font-mono font-semibold">{r.prime}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-12">
            <h2 className="text-xl font-bold mb-6">Frequently Asked Questions</h2>
            <div className="space-y-3">{faqItems.map((faq, i) => <FAQ key={i} q={faq.q} a={faq.a} />)}</div>
          </section>

          <section className="mt-10">
            <h3 className="text-lg font-semibold mb-4">Related Tools & Resources</h3>
            <div className="flex flex-wrap gap-2">
              {[
                { to: '/tools/food-cost-calculator', label: 'Food Cost Calculator' },
                { to: '/tools/menu-pricing-calculator', label: 'Menu Pricing Calculator' },
                { to: '/guides/restaurant-food-cost-guide', label: 'Food Cost Guide' },
                { to: '/guides/lower-restaurant-expenses', label: 'Lower Operating Costs' },
                { to: '/guides/restaurant-staffing-optimization', label: 'Staffing Optimization' },
              ].map(link => (
                <Link key={link.to} to={link.to} className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-[#1F1F23] text-[13px] text-[#A1A1A8] hover:text-[#F5F5F7] hover:border-[#2A2A30] transition-colors">
                  {link.label} <ChevronRight size={12} />
                </Link>
              ))}
            </div>
          </section>
        </main>

        <section className="py-16 border-t border-[#1F1F23]/40 relative">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full opacity-[0.06]" style={{ background: 'radial-gradient(circle, #1A8FD6 0%, transparent 70%)' }} />
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center relative">
            <h2 className="text-2xl font-bold">Track prime cost automatically — every day.</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">Meridian connects to your POS and calculates prime cost in real time. Get alerts when it exceeds your target — before it costs you thousands.</p>
            <Link to="/onboard" className="mt-6 inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors">
              Get Started Free <ArrowRight size={15} />
            </Link>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <Link to="/tools/food-cost-calculator" className="hover:text-[#A1A1A8]">Food Cost Calculator</Link>
            <Link to="/tools/menu-pricing-calculator" className="hover:text-[#A1A1A8]">Menu Pricing Calculator</Link>
            <Link to="/guides" className="hover:text-[#A1A1A8]">Guides</Link>
            <Link to="/faq" className="hover:text-[#A1A1A8]">FAQ</Link>
          </div>
        </footer>
      </div>
    </>
  )
}
