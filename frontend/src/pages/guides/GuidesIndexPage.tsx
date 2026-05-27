import { Link } from 'react-router-dom'
import { ArrowRight, BookOpen } from 'lucide-react'
import SEO from '@/components/SEO'
import { guides } from '@/data/seo-guides'

const categories = [
  {
    title: 'Food Waste & Cost Control',
    slugs: ['reduce-restaurant-food-waste', 'restaurant-food-cost-guide', 'lower-restaurant-expenses'],
  },
  {
    title: 'Revenue & Pricing',
    slugs: ['menu-pricing-strategy', 'why-restaurant-not-profitable', 'increase-average-ticket-size'],
  },
  {
    title: 'Operations & Forecasting',
    slugs: ['forecast-restaurant-sales', 'pos-data-business-decisions', 'restaurant-staffing-optimization'],
  },
]

const jsonLd = {
  '@type': 'CollectionPage',
  name: 'Restaurant Guides — Meridian',
  description: 'Free guides for restaurant owners on reducing costs, increasing revenue, and making data-driven decisions with POS analytics.',
  url: 'https://meridian.tips/guides',
  publisher: { '@type': 'Organization', name: 'Meridian', url: 'https://meridian.tips' },
}

export default function GuidesIndexPage() {
  return (
    <>
      <SEO
        title="Restaurant Guides — Cost Control, Pricing & Forecasting | Meridian"
        description="Free guides for restaurant owners. Learn how to reduce food waste, optimize menu pricing, forecast sales, and make better business decisions with POS data."
        path="/guides"
        jsonLd={jsonLd}
      />

      <div className="min-h-screen bg-[#0A0A0B] text-[#F5F5F7]">
        {/* Hero */}
        <header className="max-w-4xl mx-auto px-4 sm:px-6 pt-28 pb-12 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#1F1F23] bg-[#111113] text-[11px] text-[#A1A1A8] uppercase tracking-wide mb-6">
            <BookOpen size={12} />
            Free Guides for Restaurant Owners
          </div>
          <h1 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-[1.1]">
            Cut costs. Grow revenue.{' '}
            <span className="bg-gradient-to-r from-[#17C5B0] to-[#1A8FD6] bg-clip-text text-transparent">Use your data.</span>
          </h1>
          <p className="mt-5 text-lg text-[#A1A1A8] max-w-2xl mx-auto leading-relaxed">
            Practical, data-driven guides for restaurant and cafe owners who want to stop guessing and start knowing exactly where to improve.
          </p>
        </header>

        {/* Categories */}
        <main className="max-w-4xl mx-auto px-4 sm:px-6 pb-20 space-y-12">
          {categories.map(cat => (
            <section key={cat.title}>
              <h2 className="text-lg font-semibold text-[#F5F5F7] mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#17C5B0]" />
                {cat.title}
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {cat.slugs.map(slug => {
                  const guide = guides.find(g => g.slug === slug)
                  if (!guide) return null
                  return (
                    <Link
                      key={slug}
                      to={`/guides/${slug}`}
                      className="group flex flex-col p-5 rounded-xl border border-[#1F1F23] bg-[#111113] hover:border-[#2A2A30] transition-all duration-200"
                    >
                      <h3 className="text-[15px] font-semibold text-[#F5F5F7] group-hover:text-[#17C5B0] transition-colors leading-snug">
                        {guide.heroTitle} {guide.heroAccent}
                      </h3>
                      <p className="mt-2 text-[13px] text-[#6B7280] leading-relaxed line-clamp-3 flex-1">
                        {guide.description}
                      </p>
                      <div className="mt-4 flex items-center gap-1.5 text-[12px] text-[#1A8FD6] font-medium">
                        Read guide <ArrowRight size={12} className="transition-transform group-hover:translate-x-0.5" />
                      </div>
                    </Link>
                  )
                })}
              </div>
            </section>
          ))}
        </main>

        {/* CTA */}
        <section className="py-16 border-t border-[#1F1F23]/40">
          <div className="max-w-2xl mx-auto px-4 sm:px-6 text-center">
            <h2 className="text-2xl font-bold text-[#F5F5F7]">Ready to put these strategies on autopilot?</h2>
            <p className="mt-3 text-[#A1A1A8] text-[15px]">Meridian connects to your POS and does this analysis automatically — with specific dollar recommendations.</p>
            <Link
              to="/onboard"
              className="mt-6 inline-flex items-center gap-2 px-6 py-3 text-[14px] font-medium text-white bg-[#1A8FD6] rounded-lg hover:bg-[#1574B8] transition-colors"
            >
              Get Started Free <ArrowRight size={15} />
            </Link>
          </div>
        </section>

        <footer className="border-t border-[#1F1F23]/40 py-6">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 flex flex-wrap gap-x-6 gap-y-2 text-[12px] text-[#6B7280]">
            <Link to="/" className="hover:text-[#A1A1A8]">Home</Link>
            <Link to="/blog" className="hover:text-[#A1A1A8]">Blog</Link>
            <Link to="/for/restaurants" className="hover:text-[#A1A1A8]">For Restaurants</Link>
            <Link to="/for/coffee-shops" className="hover:text-[#A1A1A8]">For Coffee Shops</Link>
            <Link to="/onboard" className="hover:text-[#A1A1A8]">Get Started</Link>
          </div>
        </footer>
      </div>
    </>
  )
}
