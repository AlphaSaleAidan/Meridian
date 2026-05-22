import { Link } from 'react-router-dom'
import SEO from '@/components/SEO'

/* ─── JSON-LD Structured Data ─────────────────────── */

const FAQ_ITEMS = [
  {
    q: 'What profit margin should a restaurant aim for?',
    a: 'The average restaurant net profit margin is 3-5%, though this varies significantly by restaurant type. Full-service restaurants typically see 3-9%, while fast-casual and quick-service concepts can hit 6-9%. A well-run restaurant with strong cost controls can achieve 10-15% net margins, which is considered excellent. Fine dining margins are often lower (1-5%) due to higher labor and ingredient costs, while pizza and coffee shops can reach 15%+ because of high-margin menu items.',
  },
  {
    q: 'How do I calculate food cost percentage?',
    a: 'Food cost percentage = (Beginning Inventory + Purchases - Ending Inventory) / Food Sales x 100. For example, if you start the week with $5,000 in inventory, purchase $3,000 in food, end with $4,500 in inventory, and generate $12,000 in food sales, your food cost percentage is ($5,000 + $3,000 - $4,500) / $12,000 x 100 = 29.2%. Most restaurants should target 28-35% food cost, though this varies by concept.',
  },
  {
    q: 'What is prime cost in a restaurant?',
    a: 'Prime cost is the sum of your total food and beverage costs (Cost of Goods Sold) plus your total labor costs, including wages, salaries, payroll taxes, and benefits. It is the single most important profitability metric in the restaurant industry because it typically accounts for 55-65% of total revenue. If your prime cost exceeds 65%, your restaurant is almost certainly struggling to generate meaningful profit, regardless of how high your revenue is.',
  },
  {
    q: 'Can POS data really show profitability?',
    a: 'Yes. Modern POS systems capture far more than just transaction totals. They record Cost of Goods Sold per item, labor hours and costs by shift, waste and void events, sales mix by daypart and category, discount and comp frequency, and table turn times. When this data is analyzed together, it provides real-time margin visibility at the item, shift, and location level. The key is connecting the POS data to an analytics layer that calculates these metrics automatically rather than trying to pull reports manually.',
  },
  {
    q: 'How often should I review restaurant profitability?',
    a: 'At minimum, review profitability weekly. High-volume restaurants (over $50,000/week in sales) should review daily. The specific cadence depends on the metric: food cost percentage should be tracked weekly with a full inventory count, labor cost should be reviewed daily against sales forecasts, prime cost should be calculated weekly, and full P&L analysis should happen monthly. Real-time POS analytics can surface anomalies (like a sudden spike in voids or a food cost jump) the moment they happen, so you do not have to wait for a scheduled review to catch problems.',
  },
]

const jsonLd = [
  {
    '@type': 'Article',
    headline: 'How to Know If Your Restaurant is Actually Profitable',
    description:
      'Most restaurant owners track revenue but miss true profitability. Learn the 7 metrics that actually matter — and how POS analytics reveals them automatically.',
    author: { '@type': 'Organization', name: 'Meridian' },
    publisher: {
      '@type': 'Organization',
      name: 'Meridian',
      url: 'https://meridian.tips',
    },
    datePublished: '2026-05-22',
    dateModified: '2026-05-22',
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': 'https://meridian.tips/blog/how-to-know-if-restaurant-is-profitable',
    },
  },
  {
    '@type': 'FAQPage',
    mainEntity: FAQ_ITEMS.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.a,
      },
    })),
  },
  {
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Home', item: 'https://meridian.tips' },
      { '@type': 'ListItem', position: 2, name: 'Blog', item: 'https://meridian.tips/blog' },
      {
        '@type': 'ListItem',
        position: 3,
        name: 'How to Know If Your Restaurant is Actually Profitable',
        item: 'https://meridian.tips/blog/how-to-know-if-restaurant-is-profitable',
      },
    ],
  },
]

/* ─── Metric Card Component ───────────────────────── */

function MetricCard({
  number,
  title,
  target,
  good,
  bad,
}: {
  number: string
  title: string
  target: string
  good: string
  bad: string
}) {
  return (
    <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 mb-4">
      <div className="flex items-baseline gap-3 mb-2">
        <span className="text-[#17C5B0] font-mono text-lg font-bold">{number}</span>
        <h3 className="text-[#F5F5F7] font-semibold text-lg">{title}</h3>
      </div>
      <p className="text-sm text-[#A1A1A8] mb-3">
        Target: <span className="text-[#17C5B0] font-mono">{target}</span>
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-green-400 font-medium">Good looks like:</span>
          <p className="text-[#D1D1D6] mt-1">{good}</p>
        </div>
        <div>
          <span className="text-red-400 font-medium">Bad looks like:</span>
          <p className="text-[#D1D1D6] mt-1">{bad}</p>
        </div>
      </div>
    </div>
  )
}

/* ─── Main Article Component ──────────────────────── */

export default function RestaurantProfitabilityArticle() {
  return (
    <>
      <SEO
        title="How to Know If Your Restaurant is Actually Profitable | Meridian"
        description="Most restaurant owners track revenue but miss true profitability. Learn the 7 metrics that actually matter — and how POS analytics reveals them automatically."
        path="/blog/how-to-know-if-restaurant-is-profitable"
        type="article"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#D1D1D6]">
        <article className="max-w-3xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
          {/* ── Breadcrumb ─────────────────────────── */}
          <nav className="flex items-center gap-2 text-sm text-[#A1A1A8] mb-8">
            <Link to="/" className="hover:text-[#17C5B0] transition-colors">
              Home
            </Link>
            <span>/</span>
            <Link to="/blog" className="hover:text-[#17C5B0] transition-colors">
              Blog
            </Link>
            <span>/</span>
            <span className="text-[#D1D1D6] truncate">How to Know If Your Restaurant is Actually Profitable</span>
          </nav>

          {/* ── Article Header ─────────────────────── */}
          <header className="mb-12">
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-[#F5F5F7] leading-tight mb-4">
              How to Know If Your Restaurant is Actually Profitable
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-[#A1A1A8]">
              <time dateTime="2026-05-22">May 22, 2026</time>
              <span className="w-1 h-1 rounded-full bg-[#A1A1A8]" />
              <span>8 min read</span>
              <span className="w-1 h-1 rounded-full bg-[#A1A1A8]" />
              <span>Restaurant Profitability</span>
            </div>
          </header>

          {/* ── Introduction ───────────────────────── */}
          <section className="mb-12">
            <p className="text-lg leading-relaxed mb-4">
              Here is a question most restaurant owners are afraid to answer honestly: is your restaurant actually making money?
            </p>
            <p className="leading-relaxed mb-4">
              Not revenue. Not gross sales. Actual profit &mdash; the money left over after you have paid for every
              ingredient, every hour of labor, every utility bill, every credit card processing fee, and every piece of
              equipment that keeps the operation running.
            </p>
            <p className="leading-relaxed mb-4">
              The National Restaurant Association reports that roughly{' '}
              <span className="text-[#17C5B0] font-mono">60%</span> of restaurants fail within their first year, and{' '}
              <span className="text-[#17C5B0] font-mono">80%</span> close before their fifth anniversary. The most
              common reason is not bad food or poor location. It is poor financial visibility. Owners track the wrong
              numbers, realize too late that their margins have eroded, and run out of cash before they can course-correct.
            </p>
            <p className="leading-relaxed">
              The difference between restaurants that survive and restaurants that thrive almost always comes down to
              whether the owner knows their real numbers &mdash; not just top-line revenue, but the seven specific metrics
              that reveal whether each dollar of sales is actually translating into profit. This guide breaks down exactly
              what those metrics are, what healthy benchmarks look like, and how to track them without spending hours
              buried in spreadsheets every week.
            </p>
          </section>

          {/* ── Section 1: Revenue ≠ Profit ────────── */}
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">
              Revenue &ne; Profit: Why Most Owners Get This Wrong
            </h2>
            <p className="leading-relaxed mb-4">
              A restaurant generating <span className="text-[#17C5B0] font-mono">$1,000,000</span> per year in revenue
              sounds like a success. But revenue is the most misleading number in the restaurant business. It tells you
              how much money flowed through the register. It says nothing about how much stayed in your pocket.
            </p>
            <p className="leading-relaxed mb-4">
              Consider a typical full-service restaurant doing $1M in annual sales. Here is where that money actually goes:
            </p>
            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 mb-6 font-mono text-sm">
              <div className="grid grid-cols-2 gap-2">
                <span className="text-[#A1A1A8]">Revenue</span>
                <span className="text-[#F5F5F7] text-right">$1,000,000</span>
                <span className="text-[#A1A1A8]">Food &amp; beverage cost (32%)</span>
                <span className="text-red-400 text-right">-$320,000</span>
                <span className="text-[#A1A1A8]">Labor (30%)</span>
                <span className="text-red-400 text-right">-$300,000</span>
                <span className="text-[#A1A1A8]">Rent &amp; occupancy (8%)</span>
                <span className="text-red-400 text-right">-$80,000</span>
                <span className="text-[#A1A1A8]">Operating expenses (15%)</span>
                <span className="text-red-400 text-right">-$150,000</span>
                <span className="text-[#A1A1A8]">Marketing &amp; technology (3%)</span>
                <span className="text-red-400 text-right">-$30,000</span>
                <div className="col-span-2 border-t border-[#1F1F23] my-2" />
                <span className="text-[#F5F5F7] font-bold">Net profit</span>
                <span className="text-[#17C5B0] text-right font-bold">$120,000 (12%)</span>
              </div>
            </div>
            <p className="leading-relaxed mb-4">
              That <span className="text-[#17C5B0] font-mono">12%</span> margin is actually well above average &mdash;
              most restaurants operate between <span className="text-[#17C5B0] font-mono">3-5%</span> net profit. Now
              imagine that food costs creep up by just 3 percentage points because a supplier raises prices and no one
              catches it. Or labor costs spike because the schedule has too much overlap during slow shifts. Suddenly that
              $120,000 profit becomes $60,000. Another small shift and you are breaking even. One more and you are
              bleeding cash.
            </p>
            <blockquote className="border-l-4 border-[#17C5B0] pl-6 my-6 text-[#F5F5F7] italic">
              "The restaurant that fails is rarely the one with bad food. It is the one where the owner finds out about a
              margin problem three months after it started."
            </blockquote>
            <p className="leading-relaxed">
              This is why revenue alone is dangerous. It can go up while your profit goes down. The only way to know if
              your restaurant is actually profitable is to track the specific metrics that break down where every dollar
              goes &mdash; and to track them frequently enough that you catch problems while they are still fixable.
            </p>
          </section>

          {/* ── Section 2: The 7 Metrics ──────────── */}
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">
              The 7 Metrics That Actually Show Profitability
            </h2>
            <p className="leading-relaxed mb-6">
              These are the numbers that separate operators who know their business from operators who are guessing. Each
              one targets a different cost center, and together they give you a complete picture of whether your restaurant
              is making or losing money.
            </p>

            <MetricCard
              number="01"
              title="Food Cost Percentage"
              target="28-35% of food sales"
              good="Consistent week-over-week within 1-2% variance. You know your exact cost per dish, menu prices reflect actual ingredient costs, and you have a waste tracking system in place."
              bad="Fluctuating wildly (more than 3-4% swings week to week), consistently above 35%, or you have no idea what it is because you do not take regular inventory. This usually means portion control issues, untracked waste, or supplier price increases you have not caught."
            />

            <MetricCard
              number="02"
              title="Labor Cost Percentage"
              target="25-35% of total revenue"
              good="Labor costs are tightly aligned with sales volume. You schedule based on forecasted demand, not habit. Overtime is rare and intentional. You know your labor cost by daypart and can identify which shifts are overstaffed."
              bad="Above 35% consistently, or you are scheduling the same staff levels regardless of whether it is a Monday lunch or a Saturday dinner. High turnover is also a hidden labor cost &mdash; recruiting and training a single hourly employee costs $3,500-$5,000."
            />

            <MetricCard
              number="03"
              title="Prime Cost (Food + Labor)"
              target="Under 65% of total revenue"
              good="Prime cost between 55-63%. This is the single most important profitability indicator in the restaurant business. If your prime cost is under control, you have a strong foundation for profit even if other expenses fluctuate."
              bad="Prime cost above 65% means you are structurally unprofitable. Even with perfect control of every other expense category, there is not enough margin left to cover rent, utilities, insurance, marketing, maintenance, and still generate profit."
            />

            <MetricCard
              number="04"
              title="Revenue Per Labor Hour (RPLH)"
              target="$40-$70+ depending on concept"
              good="You generate at least $45 in revenue for every labor hour worked. You know which shifts are your most and least productive, and you can articulate why. RPLH trending upward over time means your labor efficiency is improving."
              bad="Below $35/hour for most restaurant types. You have shifts where a server is standing around with no tables, or kitchen staff is prepping for a rush that never materializes. Every idle labor hour directly reduces your profit."
            />

            <MetricCard
              number="05"
              title="Average Ticket Size"
              target="Varies by concept (track trend, not absolute)"
              good="Average check is stable or growing over time. Your staff is trained on upselling (appetizers, drinks, desserts) and you can see the impact in the data. You know your average ticket by daypart, by server, and by channel (dine-in vs. takeout)."
              bad="Declining average ticket, especially if you have not changed menu prices. This often signals that customers are trading down to cheaper items, that servers are not suggesting add-ons, or that your promotional mix is cannibalizing higher-margin items."
            />

            <MetricCard
              number="06"
              title="Table Turn Rate"
              target="1.5-3x per service period (full service)"
              good="You seat, serve, and turn tables efficiently without rushing guests. You know your average table time by party size, and you use reservations or waitlist management to minimize empty table time during peak hours."
              bad="Tables sit empty during peak hours because of slow kitchen ticket times or inefficient service flow. Or the opposite &mdash; you are turning so fast that guests feel rushed and stop coming back. Both extremes hurt profitability."
            />

            <MetricCard
              number="07"
              title="Void and Comp Rate"
              target="Under 2% of gross sales"
              good="Voids and comps are rare, documented, and always approved by a manager. You can explain every comp &mdash; it was a genuine service recovery, not a pattern. Your POS tracks voids by employee, and no single employee is an outlier."
              bad="Above 3-4%, or you see certain employees with void rates significantly higher than the team average. This is the number one theft indicator in the restaurant industry. A server voiding one $15 item per shift costs you $5,400/year. Three servers doing it costs $16,200."
            />
          </section>

          {/* ── Section 3: POS Analytics ───────────── */}
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">
              How POS Analytics Makes This Automatic
            </h2>
            <p className="leading-relaxed mb-4">
              The traditional approach to tracking restaurant profitability involves spreadsheets. Lots of them. You
              export sales reports from your POS, manually enter inventory counts, cross-reference labor schedules, and
              try to piece together a picture of how the week actually went. For most operators, this process takes{' '}
              <span className="text-[#17C5B0] font-mono">5-10 hours per week</span> &mdash; and the result is still a
              backward-looking snapshot that is already outdated by the time you finish calculating it.
            </p>
            <p className="leading-relaxed mb-4">
              Modern POS analytics eliminates this manual work entirely. When your POS system is connected to an
              analytics platform, every transaction, labor clock-in, inventory adjustment, and void is captured in real
              time. The seven metrics above are not calculated once a week on a Sunday night &mdash; they are calculated
              continuously and surfaced the moment something looks abnormal.
            </p>
            <p className="leading-relaxed mb-4">
              Here is what that looks like in practice:
            </p>
            <ul className="space-y-3 mb-6">
              {[
                'Food cost spikes 4% on Tuesday. You get an alert that afternoon instead of discovering it during your weekly review on Sunday.',
                'A new server has a void rate 3x the team average in their first two weeks. The system flags it before it becomes a $5,000 annual loss.',
                'Labor scheduling suggests cutting one prep cook on Mondays because your RPLH data shows that shift is consistently overstaffed.',
                'Your average ticket size on takeout orders is 30% lower than dine-in. Analytics identifies which menu items are underperforming on the takeout channel so you can adjust positioning.',
                'Forecasting models predict next week\'s sales by daypart based on historical patterns, weather, and local events, so you can build an optimized labor schedule before the week starts.',
              ].map((item, i) => (
                <li key={i} className="flex gap-3">
                  <span className="text-[#17C5B0] font-mono text-sm mt-1 shrink-0">&bull;</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
            <p className="leading-relaxed">
              The value is not just in the numbers themselves &mdash; it is in the speed at which you see them. A margin
              problem caught in one day costs you one day of losses. The same problem caught in one month costs you thirty
              days of losses. Automated POS analytics compresses that feedback loop from weeks to hours.
            </p>
          </section>

          {/* ── Section 4: What To Do ──────────────── */}
          <section className="mb-12">
            <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">
              What to Do If Your Numbers Don&rsquo;t Look Good
            </h2>
            <p className="leading-relaxed mb-4">
              If you have run these numbers and the results are uncomfortable, that is actually good news. You now know
              where the problem is, which means you can fix it. Here are the highest-impact actions for each cost center:
            </p>
            <div className="space-y-4 mb-6">
              <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
                <h3 className="text-[#F5F5F7] font-semibold mb-2">Food cost too high? Start with menu engineering.</h3>
                <p className="text-sm">
                  Identify your highest-volume and lowest-margin items. Rework recipes to reduce ingredient cost without
                  sacrificing quality, adjust portion sizes, eliminate menu items that are high-cost and low-popularity,
                  and renegotiate with suppliers or find alternative vendors. A{' '}
                  <span className="text-[#17C5B0] font-mono">2%</span> reduction in food cost on $1M in sales puts $20,000
                  back in your pocket annually.
                </p>
              </div>
              <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
                <h3 className="text-[#F5F5F7] font-semibold mb-2">Labor cost too high? Fix your scheduling.</h3>
                <p className="text-sm">
                  Use sales forecasts to build demand-based schedules instead of copying last week's schedule. Cross-train
                  employees so you need fewer people per shift. Stagger start times to match the actual ramp-up of
                  customer traffic. Reduce overtime by identifying which employees are consistently hitting 40+ hours.
                </p>
              </div>
              <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
                <h3 className="text-[#F5F5F7] font-semibold mb-2">Void rate suspicious? Investigate immediately.</h3>
                <p className="text-sm">
                  Pull void reports by employee and by time of day. Look for patterns &mdash; voids happening right before
                  close, voids concentrated on cash transactions, or one employee voiding items at 3-5x the rate of their
                  peers. Install cameras at the POS terminal. Most employee theft is caught through void pattern analysis,
                  not direct observation.
                </p>
              </div>
              <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-5">
                <h3 className="text-[#F5F5F7] font-semibold mb-2">Average ticket declining? Train and incentivize.</h3>
                <p className="text-sm">
                  Implement a server contest for highest average check. Script specific upsell suggestions (&ldquo;Would
                  you like to add our house-made garlic bread for $4?&rdquo; converts at 30%+ when suggested). Position
                  high-margin items in the top-right of your menu where eyes naturally go. Offer combo bundles on takeout
                  to increase order size.
                </p>
              </div>
            </div>
          </section>

          {/* ── CTA ────────────────────────────────── */}
          <section className="mb-16">
            <div className="bg-gradient-to-br from-[#111113] to-[#0A0A0B] border border-[#1F1F23] rounded-2xl p-8 sm:p-10 text-center">
              <h2 className="text-2xl sm:text-3xl font-bold text-[#F5F5F7] mb-4">
                See Your Real Numbers
              </h2>
              <p className="text-[#A1A1A8] max-w-lg mx-auto mb-6 leading-relaxed">
                Connect your POS to Meridian and get all seven profitability metrics calculated automatically. No
                spreadsheets. No manual inventory math. Just clear, real-time visibility into whether your restaurant is
                actually making money.
              </p>
              <p className="text-[#17C5B0] font-medium mb-6">First month free. Setup takes under 60 seconds.</p>
              <Link
                to="/demo"
                className="inline-flex items-center gap-2 bg-[#17C5B0] hover:bg-[#14b09d] text-[#0A0A0B] font-semibold px-8 py-3 rounded-full transition-colors"
              >
                Get Started
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </Link>
            </div>
          </section>

          {/* ── FAQ Section ────────────────────────── */}
          <section className="mb-16">
            <h2 className="text-2xl font-bold text-[#F5F5F7] mb-6">
              Frequently Asked Questions
            </h2>
            <div className="space-y-3">
              {FAQ_ITEMS.map((item, i) => (
                <details
                  key={i}
                  className="group bg-[#111113] border border-[#1F1F23] rounded-xl overflow-hidden"
                >
                  <summary className="flex items-center justify-between cursor-pointer px-6 py-4 text-[#F5F5F7] font-medium hover:text-[#17C5B0] transition-colors [&::-webkit-details-marker]:hidden">
                    <span className="pr-4">{item.q}</span>
                    <svg
                      className="w-5 h-5 shrink-0 text-[#A1A1A8] transition-transform group-open:rotate-45"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                    </svg>
                  </summary>
                  <div className="px-6 pb-5 text-[#D1D1D6] text-sm leading-relaxed">
                    {item.a}
                  </div>
                </details>
              ))}
            </div>
          </section>

          {/* ── Related Articles ───────────────────── */}
          <section className="mb-12">
            <h2 className="text-xl font-bold text-[#F5F5F7] mb-4">Related Articles</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link
                to="/blog/restaurant-foot-traffic-analytics-guide"
                className="block bg-[#111113] border border-[#1F1F23] rounded-xl p-5 hover:border-[#17C5B0]/40 transition-colors group"
              >
                <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-2">Analytics Guide</p>
                <p className="text-[#F5F5F7] font-semibold group-hover:text-[#17C5B0] transition-colors">
                  Restaurant Foot Traffic Analytics: The Complete Guide
                </p>
              </Link>
              <Link
                to="/what-is-pos-analytics"
                className="block bg-[#111113] border border-[#1F1F23] rounded-xl p-5 hover:border-[#17C5B0]/40 transition-colors group"
              >
                <p className="text-xs text-[#A1A1A8] uppercase tracking-wider mb-2">Educational</p>
                <p className="text-[#F5F5F7] font-semibold group-hover:text-[#17C5B0] transition-colors">
                  What Is POS Analytics? The Complete Guide for 2026
                </p>
              </Link>
            </div>
          </section>

          {/* ── Footer note ────────────────────────── */}
          <footer className="border-t border-[#1F1F23] pt-8 text-sm text-[#A1A1A8]">
            <p>
              Meridian is a POS analytics platform that connects to your existing point-of-sale system and transforms
              raw transaction data into profitability insights. We work with Square, Toast, Clover, Lightspeed, and
              Shopify POS.{' '}
              <Link to="/" className="text-[#17C5B0] hover:underline">
                Learn more &rarr;
              </Link>
            </p>
          </footer>
        </article>
      </div>
    </>
  )
}
