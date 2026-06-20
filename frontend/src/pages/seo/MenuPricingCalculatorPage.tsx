import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, ChevronDown, ChevronRight, Calculator, RotateCcw, TrendingUp, DollarSign } from 'lucide-react'
import SEO from '@/components/SEO'

function num(v: string): number {
  const n = parseFloat(v)
  return isNaN(n) ? 0 : n
}

function pct(n: number): string {
  return n.toFixed(1) + '%'
}

function usd(n: number): string {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function usdInt(n: number): string {
  return '$' + n.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

const faqItems = [
  { q: 'How do I calculate the right price for a menu item?', a: 'Divide your recipe cost per serving by your target food cost percentage (as a decimal). For example, if a dish costs $4.50 to make and you want a 30% food cost, the menu price should be $4.50 / 0.30 = $15.00. This food cost multiplier method is the standard in the restaurant industry, though you should also consider competitor pricing, perceived value, and your overall menu mix.' },
  { q: 'What food cost percentage should I target?', a: 'It depends on your concept. Fine dining typically targets 28-32%, casual dining 28-35%, fast casual 25-30%, QSR 25-32%, pizza 20-28%, and coffee/beverage operations 12-20%. Your overall menu should blend to your target — it is fine to have some items at 40% food cost if others are at 20%, as long as the mix hits your target.' },
  { q: 'How often should I raise menu prices?', a: 'Most successful restaurants raise prices 2-3% every 6-8 months. Small, frequent increases are far less noticeable to customers than large jumps. Track your food costs monthly — when ingredient costs rise faster than your prices, it is time for an adjustment. Waiting too long forces larger increases that customers notice and resist.' },
  { q: 'Should I price based on food cost or competition?', a: 'Use both. Start with food cost to set your floor price — you cannot sustainably sell below your cost target. Then adjust based on competition and perceived value. If competitors charge significantly more for a similar item, you have room to increase. If you are already above market, look for ways to reduce recipe cost or add perceived value through presentation and quality.' },
  { q: 'What is menu engineering and how does it help pricing?', a: 'Menu engineering categorizes every item by profitability and popularity into four groups: Stars (high profit, high popularity — promote these), Plowhorses (low profit, high popularity — raise prices or cut costs), Puzzles (high profit, low popularity — reposition on menu), and Dogs (low profit, low popularity — consider removing). This analysis reveals which items to feature, reprice, rework, or cut from your menu.' },
]

const jsonLd = [
  {
    '@type': 'WebApplication',
    name: 'Menu Pricing Calculator',
    applicationCategory: 'BusinessApplication',
    description: 'Free menu pricing calculator for restaurant owners. Calculate optimal menu prices using food cost percentage targets, compare pricing scenarios, and see industry benchmarks.',
    url: 'https://meridian.tips/tools/menu-pricing-calculator',
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
      { '@type': 'ListItem', position: 3, name: 'Menu Pricing Calculator', item: 'https://meridian.tips/tools/menu-pricing-calculator' },
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
      <div className={`grid transition-all duration-200 ease-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}><div className="overflow-hidden"><div className="px-5 pb-5 text-[#A1A1A8] text-[14px] leading-relaxed border-t border-[#1F1F23] pt-4">{a}</div></div></div>
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

function foodCostColor(pctVal: number): string {
  if (pctVal <= 30) return '#17C5B0'
  if (pctVal <= 33) return '#F59E0B'
  if (pctVal <= 35) return '#F97316'
  return '#EF4444'
}

function foodCostLabel(pctVal: number): string {
  if (pctVal <= 30) return 'Excellent'
  if (pctVal <= 33) return 'Acceptable'
  if (pctVal <= 35) return 'High'
  return 'Too High'
}

const benchmarks = [
  { type: 'Fine Dining', foodCost: '28-32%', markup: '3.1-3.6x' },
  { type: 'Casual Dining', foodCost: '28-35%', markup: '2.9-3.6x' },
  { type: 'Fast Casual', foodCost: '25-30%', markup: '3.3-4.0x' },
  { type: 'QSR / Fast Food', foodCost: '25-32%', markup: '3.1-4.0x' },
  { type: 'Pizza', foodCost: '20-28%', markup: '3.6-5.0x' },
  { type: 'Coffee / Beverage', foodCost: '12-20%', markup: '5.0-8.3x' },
  { type: 'Bar / Cocktails', foodCost: '18-24%', markup: '4.2-5.6x' },
]

const pricingTips = [
  { title: 'Use Charm Pricing', desc: 'Price items at $14.95 or $14.99 instead of $15.00. Studies show charm pricing increases sales by 8-24% compared to round numbers.' },
  { title: 'Anchor with Premium Items', desc: 'Place your most expensive item first in each menu section. It makes everything else look like a better deal by comparison.' },
  { title: 'Bundle for Perceived Value', desc: 'Combine a high-margin entree with low-cost sides as a "meal deal." Customers feel they are saving money while you increase average check size.' },
  { title: 'Raise Prices Gradually', desc: 'Increase prices 2-3% every 6-8 months rather than 10% once a year. Small, frequent adjustments are far less noticeable to guests.' },
  { title: 'Remove Dollar Signs', desc: 'Research from Cornell shows removing the "$" from menus increases average spend. Use "15" or "15.00" instead of "$15.00" on printed menus.' },
]

const comparisonTargets = [25, 28, 30, 33, 35]

export default function MenuPricingCalculatorPage() {
  const [recipeCost, setRecipeCost] = useState('4.50')
  const [targetPct, setTargetPct] = useState('30')
  const [currentPrice, setCurrentPrice] = useState('')
  const [dailySales, setDailySales] = useState('')

  const cost = num(recipeCost)
  const target = num(targetPct)
  const current = num(currentPrice)
  const daily = num(dailySales)

  const suggestedPrice = target > 0 ? cost / (target / 100) : 0
  const contributionMargin = suggestedPrice - cost
  const markupPct = cost > 0 ? ((suggestedPrice - cost) / cost) * 100 : 0

  const currentFoodCostPct = current > 0 && cost > 0 ? (cost / current) * 100 : 0
  const priceDifference = current > 0 ? suggestedPrice - current : 0
  const annualImpact = priceDifference !== 0 && daily > 0 ? priceDifference * daily * 365 : 0

  const hasResult = cost > 0 && target > 0
  const hasComparison = hasResult && current > 0

  const foodPortion = hasResult ? (target / 100) * 100 : 0
  const marginPortion = hasResult ? 100 - foodPortion : 0

  function reset() {
    setRecipeCost('4.50'); setTargetPct('30'); setCurrentPrice(''); setDailySales('')
  }

  return (
    <>
      <SEO
        title="Menu Pricing Calculator — Find Your Optimal Menu Price | Meridian"
        description="Calculate optimal menu prices using the food cost multiplier method. Enter your recipe cost and target food cost percentage to find the right price for every menu item."
        path="/tools/menu-pricing-calculator"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 pt-24 pb-4">
          <nav className="flex items-center gap-1.5 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <ChevronRight size={12} />
            <Link to="/tools" className="hover:text-[#A1A1A8]">Tools</Link>
            <ChevronRight size={12} />
            <span className="text-[#A1A1A8]">Menu Pricing Calculator</span>
          </nav>
        </div>

        <header className="max-w-3xl mx-auto px-4 sm:px-6 pb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-lg bg-[#17C5B0]/10 flex items-center justify-center">
              <DollarSign size={20} className="text-[#17C5B0]" />
            </div>
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">Menu Pricing Calculator</h1>
              <p className="text-[13px] text-[#6B7280]">Free tool for restaurant owners</p>
            </div>
          </div>
          <p className="text-[#A1A1A8] text-[15px] leading-relaxed">
            Find the optimal price for any menu item using your food cost percentage target. Enter your recipe cost, set your target margin, and instantly see the suggested price with markup and contribution margin.
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
              <div>
                <label className="block text-[13px] text-[#A1A1A8] mb-1.5">Recipe / Ingredient Cost per Serving ($)</label>
                <input
                  type="number"
                  value={recipeCost}
                  onChange={e => setRecipeCost(e.target.value)}
                  placeholder="4.50"
                  step="0.01"
                  min="0"
                  className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                />
                <p className="text-[11px] text-[#6B7280] mt-1">Total cost of all ingredients for one serving</p>
              </div>
              <div>
                <label className="block text-[13px] text-[#A1A1A8] mb-1.5">Target Food Cost Percentage (%)</label>
                <input
                  type="number"
                  value={targetPct}
                  onChange={e => setTargetPct(e.target.value)}
                  placeholder="30"
                  step="1"
                  min="1"
                  max="100"
                  className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                />
                <p className="text-[11px] text-[#6B7280] mt-1">Industry standard: 25-35% depending on concept</p>
                {target > 0 && (
                  <div className="mt-2">
                    <input
                      type="range"
                      min="10"
                      max="50"
                      value={target}
                      onChange={e => setTargetPct(e.target.value)}
                      className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                      style={{
                        background: `linear-gradient(to right, #17C5B0 0%, #17C5B0 ${((Math.min(target, 30) - 10) / 40) * 100}%, #F59E0B ${((30 - 10) / 40) * 100}%, #F59E0B ${((33 - 10) / 40) * 100}%, #F97316 ${((33 - 10) / 40) * 100}%, #F97316 ${((35 - 10) / 40) * 100}%, #EF4444 ${((35 - 10) / 40) * 100}%, #EF4444 100%)`,
                      }}
                    />
                    <div className="flex items-center gap-2 mt-1">
                      <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: foodCostColor(target) }} />
                      <span className="text-[11px] font-medium" style={{ color: foodCostColor(target) }}>{foodCostLabel(target)}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="border-t border-[#1F1F23] pt-4 mb-4">
              <p className="text-[13px] text-[#A1A1A8] mb-3">Optional — compare to your current pricing</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">Current Menu Price ($)</label>
                  <input
                    type="number"
                    value={currentPrice}
                    onChange={e => setCurrentPrice(e.target.value)}
                    placeholder="0"
                    step="0.01"
                    min="0"
                    className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                  />
                  <p className="text-[11px] text-[#6B7280] mt-1">What you currently charge for this item</p>
                </div>
                <div>
                  <label className="block text-[13px] text-[#A1A1A8] mb-1.5">Estimated Daily Sales (units)</label>
                  <input
                    type="number"
                    value={dailySales}
                    onChange={e => setDailySales(e.target.value)}
                    placeholder="0"
                    step="1"
                    min="0"
                    className="w-full px-3 py-2.5 rounded-lg border border-[#1F1F23] bg-[#0A0A0B] text-[#F5F5F7] font-mono text-[15px] placeholder-[#6B7280]/40 focus:outline-none focus:border-[#1A8FD6] transition-colors"
                  />
                  <p className="text-[11px] text-[#6B7280] mt-1">For calculating annual revenue impact</p>
                </div>
              </div>
            </div>

            {/* Results */}
            {hasResult && (
              <div className="border-t border-[#1F1F23] pt-6 mt-6">
                <h3 className="text-lg font-semibold mb-4">Your Results</h3>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                  <ResultCard label="Suggested Menu Price" value={usd(suggestedPrice)} sub={`at ${pct(target)} food cost`} color="#17C5B0" />
                  <ResultCard label="Contribution Margin" value={usd(contributionMargin)} sub="per serving" />
                  <ResultCard label="Markup" value={pct(markupPct)} sub={`${(suggestedPrice / cost).toFixed(1)}x multiplier`} />
                </div>

                {/* Price breakdown bar */}
                <div className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] p-4 mt-4">
                  <p className="text-[13px] text-[#A1A1A8] mb-3">Price breakdown</p>
                  <div className="h-8 rounded-full overflow-hidden flex">
                    <div
                      className="h-full flex items-center justify-center text-[11px] font-mono font-medium text-white transition-all duration-500"
                      style={{ width: `${foodPortion}%`, backgroundColor: foodCostColor(target), minWidth: '40px' }}
                    >
                      {usd(cost)}
                    </div>
                    <div
                      className="h-full flex items-center justify-center text-[11px] font-mono font-medium text-white bg-[#1A8FD6] transition-all duration-500"
                      style={{ width: `${marginPortion}%`, minWidth: '40px' }}
                    >
                      {usd(contributionMargin)}
                    </div>
                  </div>
                  <div className="flex justify-between mt-2 text-[11px] text-[#6B7280]">
                    <span>Food cost ({pct(target)})</span>
                    <span>Margin ({pct(100 - target)})</span>
                  </div>
                </div>

                {/* Current price comparison */}
                {hasComparison && (
                  <div className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] p-4 mt-4">
                    <p className="text-[13px] text-[#A1A1A8] mb-3">Current price comparison</p>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      <div className="text-center">
                        <p className="text-[11px] text-[#6B7280]">Current Food Cost %</p>
                        <p className="text-lg font-bold font-mono" style={{ color: foodCostColor(currentFoodCostPct) }}>{pct(currentFoodCostPct)}</p>
                        <p className="text-[11px]" style={{ color: foodCostColor(currentFoodCostPct) }}>{foodCostLabel(currentFoodCostPct)}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-[11px] text-[#6B7280]">Price Difference</p>
                        <p className={`text-lg font-bold font-mono ${priceDifference >= 0 ? 'text-[#17C5B0]' : 'text-[#EF4444]'}`}>
                          {priceDifference >= 0 ? '+' : ''}{usd(priceDifference)}
                        </p>
                        <p className="text-[11px] text-[#6B7280]">{priceDifference >= 0 ? 'increase suggested' : 'decrease suggested'}</p>
                      </div>
                      {annualImpact !== 0 && (
                        <div className="text-center">
                          <p className="text-[11px] text-[#6B7280]">Annual Impact</p>
                          <p className={`text-lg font-bold font-mono ${annualImpact >= 0 ? 'text-[#1A8FD6]' : 'text-[#EF4444]'}`}>
                            {annualImpact >= 0 ? '+' : ''}{usdInt(annualImpact)}
                          </p>
                          <p className="text-[11px] text-[#6B7280]">{daily} units/day x 365 days</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Price comparison at different targets */}
                <div className="rounded-lg border border-[#1F1F23] bg-[#0A0A0B] p-4 mt-4">
                  <p className="text-[13px] text-[#A1A1A8] mb-3">Price at different food cost targets</p>
                  <div className="overflow-x-auto -mx-2">
                    <table className="w-full text-[13px]">
                      <thead>
                        <tr className="border-b border-[#1F1F23]">
                          <th className="text-left py-2 px-2 text-[#6B7280] font-medium">Food Cost %</th>
                          <th className="text-center py-2 px-2 text-[#6B7280] font-medium">Menu Price</th>
                          <th className="text-center py-2 px-2 text-[#6B7280] font-medium">Margin</th>
                          <th className="text-center py-2 px-2 text-[#6B7280] font-medium">Markup</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparisonTargets.map(t => {
                          const price = cost / (t / 100)
                          const margin = price - cost
                          const mu = cost > 0 ? ((price - cost) / cost) * 100 : 0
                          const isSelected = t === Math.round(target)
                          return (
                            <tr key={t} className={`border-b border-[#1F1F23] ${isSelected ? 'bg-[#17C5B0]/5' : ''}`}>
                              <td className="py-2 px-2">
                                <div className="flex items-center gap-2">
                                  <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: foodCostColor(t) }} />
                                  <span className={`font-mono ${isSelected ? 'text-[#17C5B0] font-bold' : 'text-[#F5F5F7]'}`}>{t}%</span>
                                  {isSelected && <span className="text-[10px] text-[#17C5B0] ml-1">your target</span>}
                                </div>
                              </td>
                              <td className={`py-2 px-2 text-center font-mono ${isSelected ? 'text-[#17C5B0] font-bold' : 'text-[#F5F5F7]'}`}>{usd(price)}</td>
                              <td className="py-2 px-2 text-center font-mono text-[#A1A1A8]">{usd(margin)}</td>
                              <td className="py-2 px-2 text-center font-mono text-[#A1A1A8]">{pct(mu)}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Formula explanation */}
          <section className="mt-12">
            <h2 className="text-xl font-bold mb-4">How Menu Pricing Is Calculated</h2>
            <div className="rounded-lg border border-[#1F1F23] bg-[#111113] p-5 font-mono text-center text-[14px] text-[#A1A1A8] mb-4">
              Menu Price = Recipe Cost per Serving / Target Food Cost %
            </div>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              This is the food cost multiplier method, the industry standard for menu pricing. Divide your total recipe cost for one serving by your target food cost percentage (expressed as a decimal) to get the minimum price that hits your margin goal.
            </p>
            <p className="text-[#D1D1D6] text-[15px] leading-[1.75] mb-4">
              For example, if a pasta dish costs $4.50 in ingredients and you target a 30% food cost: $4.50 / 0.30 = <strong className="text-[#17C5B0]">$15.00</strong>. At this price, $4.50 covers food and $10.50 contributes toward labor, overhead, and profit.
            </p>
          </section>

          {/* Pricing Strategy Tips */}
          <section className="mt-10">
            <h2 className="text-xl font-bold mb-4">Pricing Strategy Tips</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {pricingTips.map(tip => (
                <div key={tip.title} className="rounded-lg border border-[#1F1F23] bg-[#111113] p-4">
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                      <TrendingUp size={14} className="text-[#1A8FD6]" />
                    </div>
                    <div>
                      <h3 className="text-[14px] font-semibold text-[#F5F5F7] mb-1">{tip.title}</h3>
                      <p className="text-[13px] text-[#A1A1A8] leading-relaxed">{tip.desc}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Benchmark Table */}
          <section className="mt-10">
            <h2 className="text-xl font-bold mb-4">Menu Pricing Benchmarks by Restaurant Type</h2>
            <div className="overflow-x-auto -mx-4 sm:mx-0">
              <table className="w-full min-w-[400px] text-[13px] border border-[#1F1F23] rounded-lg overflow-hidden">
                <thead><tr className="bg-[#111113] border-b border-[#1F1F23]">
                  <th className="text-left p-3 text-[#A1A1A8] font-medium">Restaurant Type</th>
                  <th className="text-center p-3 text-[#A1A1A8] font-medium">Target Food Cost</th>
                  <th className="text-center p-3 text-[#A1A1A8] font-medium">Typical Markup</th>
                </tr></thead>
                <tbody>
                  {benchmarks.map((row, i) => (
                    <tr key={row.type} className={`border-b border-[#1F1F23] ${i % 2 === 0 ? 'bg-[#0A0A0B]' : 'bg-[#111113]/50'}`}>
                      <td className="p-3 text-[#F5F5F7] font-medium">{row.type}</td>
                      <td className="p-3 text-center text-[#17C5B0] font-mono">{row.foodCost}</td>
                      <td className="p-3 text-center text-[#A1A1A8] font-mono">{row.markup}</td>
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

          {/* Related Tools */}
          <section className="mt-10">
            <h3 className="text-lg font-semibold mb-4">Related Tools</h3>
            <div className="flex flex-wrap gap-2">
              {[
                { to: '/tools/food-cost-calculator', label: 'Food Cost Calculator' },
                { to: '/tools/prime-cost-calculator', label: 'Prime Cost Calculator' },
                { to: '/guides/menu-pricing-strategy', label: 'Menu Pricing Strategy Guide' },
                { to: '/guides/restaurant-food-cost-guide', label: 'Food Cost Guide' },
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
            <h2 className="text-2xl font-bold">Stop Guessing Your Menu Prices</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px] max-w-lg mx-auto">Meridian connects to your POS and tracks food costs, menu performance, and pricing opportunities automatically — so every item on your menu is priced for profit.</p>
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
