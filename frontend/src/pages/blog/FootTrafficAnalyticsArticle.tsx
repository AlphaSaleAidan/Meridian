import { Link } from 'react-router-dom'
import { ChevronRight, ArrowRight, Clock, Calendar } from 'lucide-react'
import SEO from '@/components/SEO'

/* ── FAQ data ─────────────────────────────────────────────── */

const faqItems = [
  {
    q: 'How accurate is camera-based foot traffic counting?',
    a: 'Modern AI-powered camera counters achieve 95-98% accuracy under normal conditions. That far exceeds infrared beam counters (80-85%) and manual clicker counting (60-70%). Accuracy depends on camera placement, resolution, and lighting — but even a standard 1080p security camera at ceiling height will outperform every non-camera method on the market.',
  },
  {
    q: 'Do I need special cameras for foot traffic analytics?',
    a: 'No. Most existing security cameras work fine. You need at least 720p resolution and a clear, unobstructed view of your entrance. Ceiling-mounted cameras angled toward the door perform best. If your current cameras are analog-only, a single IP camera ($50-150) pointed at the entrance is all you need.',
  },
  {
    q: 'Is foot traffic analytics legal in Canada?',
    a: 'Yes, when implemented correctly. Under PIPEDA (Personal Information Protection and Electronic Documents Act), you must post visible signage informing visitors that counting technology is in use. The system must use aggregate counting only — no facial recognition, no individual tracking, no storing of biometric data. Most modern analytics platforms are designed for PIPEDA and CCPA compliance out of the box.',
  },
  {
    q: 'How does foot traffic correlate with restaurant revenue?',
    a: 'Foot traffic and revenue typically show a 0.6-0.8 correlation coefficient. The gap between traffic and revenue is your conversion rate — the percentage of walk-ins who actually make a purchase. Tracking both numbers independently lets you diagnose whether a slow day was caused by fewer visitors (a marketing problem) or fewer conversions (an operations or menu problem).',
  },
  {
    q: "What's a good conversion rate for a restaurant?",
    a: 'It depends on format. Fast casual restaurants typically convert 70-85% of walk-ins. Fine dining converts 90%+ because most visitors arrive with intent to eat. Coffee shops see 60-75% conversion since many people enter, look at the line, and leave. Food courts are lower at 40-55% because of high browse-and-walk-on traffic. If your conversion rate is below your format benchmark, focus on speed of service, menu visibility, and greeting behavior.',
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

const articleJsonLd = {
  '@type': 'Article',
  headline: 'The Complete Guide to Restaurant Foot Traffic Analytics in 2026',
  description:
    'Learn how modern foot traffic analytics works for restaurants and retail — from camera-based counting to POS correlation. No expensive hardware required.',
  datePublished: '2026-05-22',
  dateModified: '2026-05-22',
  author: {
    '@type': 'Organization',
    name: 'Meridian',
    url: 'https://meridian.tips',
  },
  publisher: {
    '@type': 'Organization',
    name: 'Meridian',
    url: 'https://meridian.tips',
  },
}

/* ── Tracking method cards ────────────────────────────────── */

const trackingMethods = [
  {
    name: 'Manual Counting',
    cost: 'Free',
    accuracy: '60-70%',
    privacy: 'None',
    bestFor: 'One-off audits, validating other methods',
    description:
      'Station an employee at the door with a clicker. It is the oldest method and still useful for spot checks, but it falls apart over full shifts. People lose focus after 20 minutes. Bathroom breaks create gaps. And you cannot run a manual count 7 days a week without burning labor dollars that should go to serving customers.',
  },
  {
    name: 'Infrared Beam Counters',
    cost: '$200-500',
    accuracy: '80-85%',
    privacy: 'Minimal',
    bestFor: 'Single-entrance stores with low budgets',
    description:
      'An infrared beam across your doorway counts each time the beam is broken. Simple and reliable for single-file traffic, but accuracy drops when two people walk in side by side or when someone pauses in the doorway. These counters also cannot distinguish between entering and exiting — you get total beam breaks, not net traffic.',
  },
  {
    name: 'Wi-Fi / Bluetooth Probing',
    cost: '$50-200/mo',
    accuracy: '70-80%',
    privacy: 'Significant concerns',
    bestFor: 'Malls and large retail where aggregate flow matters',
    description:
      'Sensors detect Wi-Fi probe requests that smartphones broadcast when searching for networks. This gives you a passive count of devices (and by proxy, people) in range. The problem: not everyone has Wi-Fi on, newer phones randomize their MAC addresses, and privacy regulations in Canada and several US states now restrict passive device tracking without consent. Accuracy has declined steadily since Apple and Google tightened MAC randomization in 2023.',
  },
  {
    name: 'Camera-Based AI Counting',
    cost: '$0-50/mo',
    accuracy: '95-98%',
    privacy: 'Low (aggregate only)',
    bestFor: 'Any restaurant or retail store with existing cameras',
    description:
      'Computer vision models analyze your existing security camera feeds to count people entering and exiting. Modern systems distinguish individuals in groups, handle overlapping paths, and separate staff from customers. Because the analysis happens on compressed video or edge devices, no facial data is stored. This is the highest-accuracy, lowest-friction method available today — especially if you already have cameras installed.',
  },
  {
    name: 'POS Transaction Correlation',
    cost: 'Free (with existing POS)',
    accuracy: 'Proxy only',
    privacy: 'None',
    bestFor: 'Restaurants that need a starting point today',
    description:
      'Your POS already counts every transaction. While it does not tell you about walk-ins who left without buying, transaction timestamps reveal peak hours, average party size, and day-over-day trends. Pairing POS data with even rough traffic estimates gives you a conversion rate — and that single number is more actionable than traffic or sales alone.',
  },
]

/* ── Component ────────────────────────────────────────────── */

export default function FootTrafficAnalyticsArticle() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
      <SEO
        title="The Complete Guide to Restaurant Foot Traffic Analytics in 2026 | Meridian"
        description="Learn how modern foot traffic analytics works for restaurants and retail — from camera-based counting to POS correlation. No expensive hardware required."
        path="/blog/restaurant-foot-traffic-analytics-guide"
        type="article"
        jsonLd={[articleJsonLd, faqJsonLd]}
      />

      {/* ── Article Header ────────────────────────────────── */}
      <header className="pt-32 pb-12 px-6">
        <div className="max-w-3xl mx-auto">
          {/* Breadcrumb */}
          <nav className="flex items-center gap-2 text-sm text-[#A1A1A8] mb-8">
            <Link to="/blog" className="hover:text-[#17C5B0] transition-colors">
              Blog
            </Link>
            <ChevronRight className="w-3 h-3" />
            <span className="text-[#F5F5F7]">Restaurant Foot Traffic Analytics Guide</span>
          </nav>

          <h1 className="text-3xl md:text-5xl font-bold leading-tight mb-6">
            The Complete Guide to Restaurant Foot Traffic Analytics in 2026
          </h1>

          <div className="flex items-center gap-6 text-sm text-[#A1A1A8]">
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              May 22, 2026
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              9 min read
            </span>
          </div>
        </div>
      </header>

      {/* ── Article Body ──────────────────────────────────── */}
      <article className="px-6 pb-24">
        <div className="max-w-3xl mx-auto text-[#D1D1D6] text-[16px] leading-relaxed space-y-12">

          {/* ── Introduction ─────────────────────────────── */}
          <section className="space-y-4">
            <p>
              Every restaurant operator knows their sales numbers. Most can tell you their best-selling item,
              their slowest day of the week, and roughly how much they spend on food cost. But ask how many
              people walked past the front door yesterday — or how many stepped inside and left without
              ordering — and you get a blank stare.
            </p>
            <p>
              That blind spot is expensive. Revenue is the product of two variables: the number of people
              who walk in and the percentage who buy something. Most restaurants only measure the second
              half of that equation. They optimize menus, train servers on upselling, and tweak pricing —
              all of which improve conversion. But they never measure traffic itself, so they cannot tell
              whether a slow Tuesday happened because fewer people showed up or because the people who
              showed up did not convert.
            </p>
            <p>
              Foot traffic analytics closes that gap. When you know how many people enter your restaurant
              every hour, you can match staffing to demand instead of guessing. You can measure whether an
              Instagram campaign actually drove more bodies through the door or just got likes. You can
              compare two potential lease locations using data instead of intuition. And you can do all of
              this in 2026 without spending tens of thousands on hardware — because the cameras you already
              have are enough.
            </p>
          </section>

          {/* ── What Is Foot Traffic Analytics? ───────────── */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">What Is Foot Traffic Analytics?</h2>
            <p>
              Foot traffic analytics is the practice of measuring how many people enter a physical location,
              when they arrive, how long they stay, and how they move through the space. In restaurants and
              retail, it turns an invisible metric — walk-in volume — into a number you can track, trend,
              and act on.
            </p>
            <p>
              The concept is not new. Retail chains have counted shoppers since the 1960s, starting with
              employees holding mechanical clickers at store entrances. In the 1980s, infrared beam counters
              automated the process — a sensor on each side of the door, an invisible beam between them,
              and a counter that incremented each time someone broke the beam. By the 2000s, Wi-Fi and
              Bluetooth probing emerged: sensors that passively detected smartphones to estimate how many
              devices (and therefore people) were nearby.
            </p>
            <p>
              The current generation uses computer vision. A camera pointed at the entrance feeds video to
              an AI model that detects, counts, and tracks individual people. Modern systems can count
              groups entering together, distinguish staff from customers, measure dwell time in specific
              zones, and map customer flow through the space — all without storing any personally
              identifiable information. The video is analyzed in real time and only aggregate numbers are
              retained.
            </p>
            <p>
              For restaurants specifically, foot traffic analytics answers questions that POS data alone
              cannot: How many potential customers walked past but did not enter? Of those who entered,
              how many left before ordering? Do lunch crowds arrive at 11:30 or 11:45 — and should prep
              start 15 minutes earlier?
            </p>
          </section>

          {/* ── 5 Ways to Track Foot Traffic ──────────────── */}
          <section className="space-y-6">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">5 Ways to Track Foot Traffic</h2>
            <p>
              Not every method works for every location. Here is an honest breakdown of the five most
              common approaches — what each costs, how accurate it is, and where it makes sense.
            </p>

            <div className="space-y-4">
              {trackingMethods.map((method) => (
                <div
                  key={method.name}
                  className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 space-y-4"
                >
                  <h3 className="text-lg font-semibold text-[#F5F5F7]">{method.name}</h3>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                    <div>
                      <span className="text-[#A1A1A8] block mb-1">Cost</span>
                      <span className="text-[#17C5B0] font-mono">{method.cost}</span>
                    </div>
                    <div>
                      <span className="text-[#A1A1A8] block mb-1">Accuracy</span>
                      <span className="text-[#17C5B0] font-mono">{method.accuracy}</span>
                    </div>
                    <div>
                      <span className="text-[#A1A1A8] block mb-1">Privacy Risk</span>
                      <span className="text-[#F5F5F7]">{method.privacy}</span>
                    </div>
                    <div>
                      <span className="text-[#A1A1A8] block mb-1">Best For</span>
                      <span className="text-[#F5F5F7]">{method.bestFor}</span>
                    </div>
                  </div>
                  <p className="text-[#A1A1A8] text-sm leading-relaxed">{method.description}</p>
                </div>
              ))}
            </div>

            <blockquote className="border-l-4 border-[#17C5B0] pl-6 py-2 text-[#A1A1A8] italic">
              The best approach for most restaurants in 2026 is camera-based counting paired with POS
              correlation. You get high-accuracy traffic numbers and you already have both pieces of
              hardware.
            </blockquote>
          </section>

          {/* ── What Good Numbers Look Like ───────────────── */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">What Good Foot Traffic Numbers Look Like</h2>
            <p>
              Raw traffic counts are meaningless without context. The number that matters is your
              <strong className="text-[#F5F5F7]"> foot-traffic-to-transaction conversion rate</strong> —
              the percentage of people who walk in and actually make a purchase. Here are benchmarks by
              restaurant format:
            </p>

            <div className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6">
              <div className="grid gap-4">
                {[
                  { type: 'Fast Casual', rate: '70-85%', note: 'High intent — most walk-ins are hungry and ready to order' },
                  { type: 'Fine Dining', rate: '90%+', note: 'Almost all visitors have reservations or firm intent' },
                  { type: 'Coffee Shops', rate: '60-75%', note: 'Drop-offs from long lines, menu hesitation, and grab-and-go browsers' },
                  { type: 'Food Courts', rate: '40-55%', note: 'High browse rate — shoppers walk through without buying' },
                  { type: 'Quick Service (QSR)', rate: '75-90%', note: 'Drive-thru inflates conversion; walk-in only is lower' },
                ].map((row) => (
                  <div key={row.type} className="flex flex-col md:flex-row md:items-center gap-1 md:gap-4 py-2 border-b border-[#1F1F23] last:border-0">
                    <span className="font-semibold text-[#F5F5F7] md:w-40 shrink-0">{row.type}</span>
                    <span className="text-[#17C5B0] font-mono md:w-24 shrink-0">{row.rate}</span>
                    <span className="text-[#A1A1A8] text-sm">{row.note}</span>
                  </div>
                ))}
              </div>
            </div>

            <p>
              Peak-hour patterns also vary by format. Most full-service restaurants see a lunch peak
              between <span className="text-[#17C5B0] font-mono">11:45 AM - 1:15 PM</span> and a dinner
              peak between <span className="text-[#17C5B0] font-mono">6:00 PM - 8:00 PM</span>. Coffee
              shops peak earlier, typically <span className="text-[#17C5B0] font-mono">7:00 - 9:00 AM</span>.
              Knowing your exact peak — not the industry average, but your location's actual data — tells
              you when prep should start, when the extra server needs to clock in, and when to run a
              promotion to fill a dead period.
            </p>
            <p>
              Seasonal variation matters too. Restaurants in tourist areas may see{' '}
              <span className="text-[#17C5B0] font-mono">2-3x</span> summer traffic compared to winter.
              Urban lunch spots near office towers dropped{' '}
              <span className="text-[#17C5B0] font-mono">30-40%</span> during the remote-work shift and
              have only partially recovered. Tracking these trends over months gives you a demand baseline
              that informs lease decisions, seasonal menu changes, and staffing plans.
            </p>
          </section>

          {/* ── How to Use Foot Traffic Data ──────────────── */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">How to Use Foot Traffic Data</h2>
            <p>
              Counting people is step one. The value comes from what you do with the numbers. Here are
              five ways restaurant operators are using foot traffic analytics to make better decisions.
            </p>

            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-[#F5F5F7] mb-2">Staff Scheduling Based on Traffic, Not Sales</h3>
                <p>
                  Most restaurants build schedules around historical sales data. The problem is that sales
                  are a lagging indicator — they tell you what happened after people were already served.
                  Traffic data is a leading indicator. If you know that foot traffic spikes at 11:30 AM
                  but your first lunch server does not clock in until noon, you are losing 30 minutes of
                  potential revenue to long wait times and walk-outs. Aligning labor to traffic curves
                  instead of sales curves reduces both over-staffing during slow periods and under-staffing
                  during rushes. Restaurants that make this switch typically save{' '}
                  <span className="text-[#17C5B0] font-mono">8-12%</span> on labor costs.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-[#F5F5F7] mb-2">Measuring Marketing ROI</h3>
                <p>
                  Did that Instagram campaign actually bring more people in, or did it just get likes?
                  Without foot traffic data, you can only measure marketing by looking at same-store sales —
                  but sales conflate traffic and conversion. A campaign that drives 50 extra walk-ins who
                  do not buy anything looks like a failure in POS data and a success in traffic data. The
                  diagnosis is different: the marketing worked; the in-store experience did not convert.
                  Separating traffic from conversion lets you assign accountability correctly and avoid
                  killing campaigns that are actually working.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-[#F5F5F7] mb-2">Menu Board and Layout Optimization</h3>
                <p>
                  Camera-based analytics can track where customers look and linger before ordering. If
                  people consistently study the left side of your menu board but your highest-margin items
                  are on the right, you have a layout problem. Some systems generate heat maps that show
                  dwell zones — areas where customers pause, read, or queue. Rearranging your menu board
                  or repositioning your counter display based on actual behavior data can lift average
                  ticket size by <span className="text-[#17C5B0] font-mono">5-15%</span>.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-[#F5F5F7] mb-2">Location Decisions</h3>
                <p>
                  Before signing a 5-year lease, you should know exactly how many people walk past that
                  location every hour. Foot traffic analytics platforms can provide pedestrian density
                  data for specific addresses — or you can place a temporary camera for a week-long
                  count. Comparing traffic between two prospective locations is far more reliable than
                  relying on a broker's claims or census data from three years ago. One chain operator
                  we work with avoids any location where weekday lunch-hour foot traffic falls below{' '}
                  <span className="text-[#17C5B0] font-mono">200 people per hour</span> — a rule that
                  has kept their location failure rate under <span className="text-[#17C5B0] font-mono">5%</span>.
                </p>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-[#F5F5F7] mb-2">Delivery vs. Dine-In Cannibalization</h3>
                <p>
                  Third-party delivery apps promise incremental revenue, but many restaurants find that
                  delivery orders replace dine-in visits rather than adding to them. If you see foot
                  traffic decline by <span className="text-[#17C5B0] font-mono">15%</span> after
                  launching on a delivery platform while total order volume stays flat, delivery is
                  cannibalizing your walk-in business — and you are paying{' '}
                  <span className="text-[#17C5B0] font-mono">25-30%</span> commission on orders that
                  would have been full-margin dine-in transactions. Foot traffic data makes this trade-off
                  visible so you can decide whether delivery is genuinely expanding your market or just
                  shifting revenue to a lower-margin channel.
                </p>
              </div>
            </div>
          </section>

          {/* ── Privacy and Compliance ────────────────────── */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">Privacy and Compliance</h2>
            <p>
              The most common objection to camera-based analytics is privacy. It is a valid concern — but
              modern systems are designed around it. Here is how compliant foot traffic analytics works.
            </p>
            <p>
              Camera-based counting systems process video frames to detect human shapes and movement
              vectors. They output a number — "14 people entered between 2:00 and 2:15 PM" — not images,
              faces, or identities. The video frame is analyzed and discarded. No biometric data is
              collected, stored, or transmitted.
            </p>
            <p>
              In Canada, PIPEDA governs how businesses collect and use personal information. Aggregate
              counting — where the system records only totals, not individuals — falls outside PIPEDA's
              definition of personal information, provided you are not using facial recognition or
              tracking identifiable individuals across visits. The Office of the Privacy Commissioner
              recommends posting visible signage at entrances stating that counting technology is in use.
            </p>
            <p>
              In the United States, state laws vary. California's CCPA, Illinois's BIPA, and Texas's
              CUBI all regulate biometric data — but anonymous people-counting is generally exempt because
              no biometric identifiers are collected. The key legal distinction is between{' '}
              <strong className="text-[#F5F5F7]">counting</strong> (aggregate, anonymous) and{' '}
              <strong className="text-[#F5F5F7]">identification</strong> (individual, biometric).
              Stick to counting and you stay on the right side of the law.
            </p>
            <blockquote className="border-l-4 border-[#17C5B0] pl-6 py-2 text-[#A1A1A8] italic">
              Best practices: Post signage at entrances. Use aggregate-only analytics. Never enable
              facial recognition. Process on-device when possible. Delete raw footage on a rolling
              schedule. Document your privacy practices in writing.
            </blockquote>
          </section>

          {/* ── CTA ───────────────────────────────────────── */}
          <section className="bg-[#111113] border border-[#1F1F23] rounded-xl p-8 md:p-10 text-center space-y-4">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">Start Tracking Foot Traffic</h2>
            <p className="text-[#A1A1A8] max-w-xl mx-auto">
              Meridian's camera intelligence module works with your existing security cameras. No new
              hardware. No complex installation. Connect your cameras, and start seeing traffic patterns,
              conversion rates, and peak-hour data within 24 hours.
            </p>
            <p className="text-[#A1A1A8]">First month free.</p>
            <Link
              to="/demo"
              className="inline-flex items-center gap-2 px-8 py-3 rounded-lg bg-[#17C5B0] text-[#0A0A0B] font-semibold text-base hover:brightness-110 transition-all mt-2"
            >
              Book a Demo <ArrowRight className="w-4 h-4" />
            </Link>
          </section>

          {/* ── FAQ ───────────────────────────────────────── */}
          <section className="space-y-6">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">Frequently Asked Questions</h2>
            <div className="space-y-3">
              {faqItems.map((item) => (
                <details
                  key={item.q}
                  className="group bg-[#111113] border border-[#1F1F23] rounded-xl overflow-hidden"
                >
                  <summary className="flex items-center justify-between cursor-pointer px-6 py-4 text-[15px] font-medium text-[#F5F5F7] list-none">
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

          {/* ── Related Articles ──────────────────────────── */}
          <section className="space-y-4">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">Related Articles</h2>
            <div className="grid md:grid-cols-2 gap-4">
              <Link
                to="/blog/how-to-know-if-restaurant-is-profitable"
                className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#17C5B0]/40 transition-colors group"
              >
                <h3 className="font-semibold text-[#F5F5F7] group-hover:text-[#17C5B0] transition-colors mb-2">
                  How to Know If a Restaurant Is Profitable
                </h3>
                <p className="text-sm text-[#A1A1A8]">
                  The financial metrics that separate thriving restaurants from those bleeding cash — and how to track them without an accountant.
                </p>
              </Link>
              <Link
                to="/blog/square-pos-analytics-what-it-tells-you"
                className="bg-[#111113] border border-[#1F1F23] rounded-xl p-6 hover:border-[#17C5B0]/40 transition-colors group"
              >
                <h3 className="font-semibold text-[#F5F5F7] group-hover:text-[#17C5B0] transition-colors mb-2">
                  Square POS Analytics: What It Actually Tells You
                </h3>
                <p className="text-sm text-[#A1A1A8]">
                  Square's built-in reports are a start. Here is what they miss and how to get the full picture of your restaurant's performance.
                </p>
              </Link>
            </div>
          </section>

        </div>
      </article>
    </div>
  )
}
